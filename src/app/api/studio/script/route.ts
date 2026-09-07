import { bad, ok, str } from "@/lib/api";
import { guard } from "@/lib/ratelimit";
import { getStudioSession } from "@/lib/users";
import { NICHES, writeScript, type Niche } from "@/lib/aiengine";

/** W2.47: AI Script Writer — runs on the production AI engine (see lib/aiengine). */
export async function POST(req: Request) {
  const limited = await guard(req, "ai");
  if (limited) return limited;
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  const body = await req.json().catch(() => ({}));
  const brief = str(body.brief, 4000);
  const niche = str(body.niche, 60).toLowerCase();
  const seconds = Math.min(120, Math.max(15, Number(body.seconds) || 30));
  if (brief.length < 10) return bad("Describe your idea in a sentence or two first");
  if (!NICHES.includes(niche as Niche)) return bad("Pick a niche for the writer");

  const script = await writeScript(brief, niche as Niche, seconds);
  if (!script.title || !Array.isArray(script.scenes) || script.scenes.length === 0) {
    return bad("The writer came back incomplete — try again", 502);
  }
  return ok({ script, niche });
}
