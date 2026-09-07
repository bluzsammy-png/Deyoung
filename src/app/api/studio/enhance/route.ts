import { bad, ok, str } from "@/lib/api";
import { guard } from "@/lib/ratelimit";
import { getStudioSession } from "@/lib/users";
import { NICHES, enhancePrompt, type Niche } from "@/lib/aiengine";

/** W2.47: AI Prompt Enhancer — runs on the production AI engine (see lib/aiengine). */
export async function POST(req: Request) {
  const limited = await guard(req, "ai");
  if (limited) return limited;
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  const body = await req.json().catch(() => ({}));
  const prompt = str(body.prompt, 2000);
  const niche = str(body.niche, 60).toLowerCase();
  if (prompt.length < 8) return bad("Write at least a few words to enhance");
  if (!NICHES.includes(niche as Niche)) return bad("Pick a niche for the enhancer");

  const enhanced = await enhancePrompt(prompt, niche as Niche);
  if (!enhanced) return bad("The enhancer came back empty — try rephrasing", 502);
  return ok({ enhanced, niche });
}
