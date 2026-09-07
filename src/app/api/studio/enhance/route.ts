import { bad, ok, str } from "@/lib/api";
import { guard } from "@/lib/ratelimit";
import { getStudioSession } from "@/lib/users";
import ZAI from "z-ai-web-dev-sdk";

const NICHES = [
  "kids cartoon",
  "product ad",
  "real estate",
  "music video",
  "explainer",
  "social reel",
  "travel",
  "fashion",
  "gaming",
  "custom",
];

/** W2: AI Prompt Enhancer — turns a rough idea into a cinematic render prompt. */
export async function POST(req: Request) {
  const limited = await guard(req, "ai");
  if (limited) return limited;
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  try {
    const body = await req.json().catch(() => ({}));
    const prompt = str(body.prompt, 2000);
    const niche = str(body.niche, 60).toLowerCase();
    if (prompt.length < 8) return bad("Write at least a few words to enhance");
    if (!NICHES.includes(niche)) return bad("Pick a niche for the enhancer");

    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages: [
        {
          role: "assistant",
          content:
            "You are DeYoung's prompt director for an AI text-to-video film engine. Rewrite the user's rough idea into ONE vivid, cinematic video prompt of 40-80 words. " +
            `Niche: ${niche}. Include: subject + action, setting, camera language (shot/movement), lighting, mood, and visual style. No preamble, no quotes, no markdown — return the prompt text only.`,
        },
        { role: "user", content: prompt },
      ],
      thinking: { type: "disabled" },
    });
    const enhanced = (completion.choices[0]?.message?.content ?? "").trim();
    if (!enhanced) return bad("The enhancer came back empty — try rephrasing", 502);
    return ok({ enhanced, niche });
  } catch (e) {
    console.error("studio enhance failed", e);
    return bad("Prompt enhancer is unavailable right now — try again shortly", 502);
  }
}
