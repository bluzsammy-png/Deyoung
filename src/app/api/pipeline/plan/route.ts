import { NextRequest } from "next/server";
import {
  DOCTOR_SYSTEM,
  SHOWRUNNER_SYSTEM,
  rateLimit,
  validatePlan,
  type FilmPlan,
} from "@/lib/pipeline";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

const MIN_LEN = 12;
const MAX_LEN = 600;

function clientIp(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    "local"
  );
}

function extractJsonText(res: unknown): string {
  const anyRes = res as { choices?: Array<{ message?: { content?: string } }> };
  return anyRes?.choices?.[0]?.message?.content ?? "";
}

/**
 * POST /api/pipeline/plan - the studio's creative brain.
 * One instruction in (a sentence or two), a complete 45-60s film plan out:
 * script, per-scene shot prompts, timings and a one-pass combined prompt
 * ready to submit to the render queue.
 *
 * Specialist stages (clean-room, our own prompts): showrunner → script doctor.
 * Rate-limited per IP; the AI stage is the expensive part, so abuse is throttled.
 */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const instruction = String(body?.instruction ?? "").trim().slice(0, MAX_LEN);
  if (instruction.length < MIN_LEN) {
    return Response.json(
      { error: `Describe your film in at least ${MIN_LEN} characters - one vivid sentence is enough.` },
      { status: 400 }
    );
  }

  if (!rateLimit(`plan:${clientIp(req)}`, 6, 60 * 60 * 1000)) {
    return Response.json(
      { error: "That's a lot of films! Try again in a little while." },
      { status: 429 }
    );
  }

  let ZAI: (typeof import("z-ai-web-dev-sdk"))["default"] | null = null;
  try {
    const mod = await import("z-ai-web-dev-sdk");
    ZAI = mod.default;
  } catch {
    return Response.json({ error: "Studio brain is offline - try again later." }, { status: 503 });
  }

  try {
    const zai = await ZAI.create();

    // ---- Stage 1: showrunner ----
    const draft = await zai.chat.completions.create({
      messages: [
        { role: "system", content: SHOWRUNNER_SYSTEM },
        { role: "user", content: `Instruction: ${instruction}` },
      ],
    });
    const draftPlan = validatePlan(JSON.parse(extractJsonText(draft) || "{}"), instruction);

    // ---- Stage 2: script doctor (critic pass) ----
    let plan: FilmPlan = draftPlan;
    try {
      const review = await zai.chat.completions.create({
        messages: [
          { role: "system", content: DOCTOR_SYSTEM },
          {
            role: "user",
            content: `Original instruction: ${instruction}\n\nPlan JSON:\n${JSON.stringify(draftPlan)}`,
          },
        ],
      });
      const reviewed = validatePlan(JSON.parse(extractJsonText(review) || "{}"), instruction);
      plan = { ...reviewed, doctorFixes: reviewed.doctorFixes.length ? reviewed.doctorFixes : [] };
    } catch {
      // critic pass is best-effort - the showrunner plan is already valid
      plan = { ...draftPlan, doctorFixes: [] };
    }

    return Response.json({ plan });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const busy = /429|rate|quota|throttl/i.test(msg);
    console.error("pipeline/plan error:", msg.slice(0, 300));
    return Response.json(
      {
        error: busy
          ? "The studio is busy right now - give it a couple of minutes and try again."
          : "Could not draft the film plan - try rephrasing your instruction.",
      },
      { status: busy ? 503 : 502 }
    );
  }
}
