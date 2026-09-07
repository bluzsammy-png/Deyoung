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

type ScriptShape = {
  title: string;
  logline: string;
  characters: { name: string; look: string; voice: string }[];
  scenes: { id: string; title: string; seconds: number; line: string; visual: string }[];
};

/** W2: AI Script Writer — niche + brief → full script with scenes and characters. */
export async function POST(req: Request) {
  const limited = await guard(req, "ai");
  if (limited) return limited;
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  try {
    const body = await req.json().catch(() => ({}));
    const brief = str(body.brief, 4000);
    const niche = str(body.niche, 60).toLowerCase();
    const seconds = Math.min(60, Math.max(10, Number(body.seconds) || 30));
    if (brief.length < 10) return bad("Describe your idea in a sentence or two first");
    if (!NICHES.includes(niche)) return bad("Pick a niche for the writer");

    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
      messages: [
        {
          role: "assistant",
          content:
            `You are DeYoung's AI screenwriter. Write a shot-by-shot script for a ${seconds}-second vertical-friendly film. ` +
            `Niche: ${niche}. Respond with VALID JSON ONLY (no markdown fence, no commentary) matching exactly:\n` +
            '{"title":string,"logline":string,"characters":[{"name":string,"look":string,"voice":string}],' +
            '"scenes":[{"id":string,"title":string,"seconds":number,"line":string,"visual":string}]}\n' +
            "Rules: 3-6 scenes whose seconds sum to <= the total; every scene is at least 5 seconds; each scene.visual is one concrete shot description " +
            "(camera + action + setting); each scene.line is ONE spoken line of dialogue or VO (<= 12 words); " +
            "1-3 characters total; ids are s1, s2, ...",
        },
        { role: "user", content: brief },
      ],
      thinking: { type: "disabled" },
    });
    const raw = (completion.choices[0]?.message?.content ?? "").trim();
    const jsonText = raw.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
    let script: ScriptShape;
    try {
      script = JSON.parse(jsonText) as ScriptShape;
    } catch {
      return bad("The writer returned a malformed script — try again", 502);
    }
    if (!script.title || !Array.isArray(script.scenes) || script.scenes.length === 0) {
      return bad("The writer came back incomplete — try again", 502);
    }
    script.characters = Array.isArray(script.characters) ? script.characters.slice(0, 4) : [];
    script.scenes = script.scenes.slice(0, 8).map((sc, i) => ({
      id: sc.id || `s${i + 1}`,
      title: String(sc.title ?? `Scene ${i + 1}`).slice(0, 80),
      seconds: Math.min(20, Math.max(5, Number(sc.seconds) || Math.round(seconds / script.scenes.length))),
      line: String(sc.line ?? "").slice(0, 200),
      visual: String(sc.visual ?? "").slice(0, 400),
    }));
    script.logline = String(script.logline ?? "").slice(0, 300);
    script.title = String(script.title).slice(0, 120);
    return ok({ script, niche });
  } catch (e) {
    console.error("studio script failed", e);
    return bad("Script writer is unavailable right now — try again shortly", 502);
  }
}
