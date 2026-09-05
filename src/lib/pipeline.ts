/**
 * DeYoung film pipeline - one instruction in, a complete film plan out.
 *
 * Clean-room implementation of the specialist-review pattern (inspired by
 * agency-style agent corpora and mature film pipelines): instead of one blob
 * prompt, generation runs through named specialist stages, each with its own
 * system prompt and a schema-validated hand-off:
 *
 *   1. SHOWRUNNER  - turns the raw instruction into a structured plan:
 *                    title, logline, style, cast, 4-6 scenes with spoken
 *                    lines + per-scene shot prompts, plus a `combinedPrompt`
 *                    for one-pass 45-60s generation.
 *   2. SCRIPT DOCTOR (critic) - reviews the plan against the original
 *                    instruction: speakable line lengths, scene timing that
 *                    adds up, no on-screen-text requests the video model
 *                    would hallucinate, unsafe/infringing content, weak
 *                    verbs. Returns a corrected plan + a list of fixes.
 *
 * Everything is validated locally before it leaves this module - a malformed
 * stage output is repaired or rejected, never passed downstream blindly.
 */

export type ScenePlan = {
  index: number;
  speaker: string;
  line: string;
  shotPrompt: string;
  seconds: number;
};

export type FilmPlan = {
  title: string;
  logline: string;
  style: string;
  totalSeconds: number;
  scenes: ScenePlan[];
  combinedPrompt: string;
  doctorFixes: string[];
};

const MIN_TOTAL = 40;
const MAX_TOTAL = 60;
const MAX_SCENES = 6;
const MIN_SCENES = 3;
const MAX_LINE_WORDS = 14;

/* ----------------------------------------------------------------- helpers */

function asString(v: unknown, max = 400): string {
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}

function clampInt(v: unknown, min: number, max: number, fallback: number): number {
  const n = Math.round(Number(v));
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

function parseJsonLoose(raw: string): unknown {
  const cleaned = raw.replace(/^```(?:json)?/i, "").replace(/```\s*$/, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(cleaned.slice(start, end + 1));
      } catch {
        /* fall through */
      }
    }
    throw new Error("model did not return parseable JSON");
  }
}

/* ------------------------------------------------------------- validation */

export function validatePlan(raw: unknown, instruction: string): FilmPlan {
  const obj = (raw ?? {}) as Record<string, unknown>;

  const title = asString(obj.title, 120) || "Untitled film";
  const logline = asString(obj.logline, 300);
  const style = asString(obj.style, 160) || "cinematic, bold, DeYoung brand";
  const combinedPrompt = asString(obj.combinedPrompt, 1600);

  const scenesRaw = Array.isArray(obj.scenes) ? obj.scenes : [];
  if (scenesRaw.length < MIN_SCENES) throw new Error("plan needs at least 3 scenes");

  const scenes: ScenePlan[] = scenesRaw.slice(0, MAX_SCENES).map((s, i) => {
    const sc = (s ?? {}) as Record<string, unknown>;
    const line = asString(sc.line, 160);
    const shotPrompt = asString(sc.shotPrompt, 500);
    if (!line) throw new Error(`scene ${i + 1} is missing a spoken line`);
    if (!shotPrompt) throw new Error(`scene ${i + 1} is missing a shot prompt`);
    const words = line.split(/\s+/).filter(Boolean).length;
    return {
      index: i + 1,
      speaker: asString(sc.speaker, 60) || `Voice ${i + 1}`,
      line,
      shotPrompt,
      seconds: clampInt(sc.seconds, 5, 15, Math.min(12, Math.max(8, words))),
    };
  });

  let total = clampInt(obj.totalSeconds, MIN_TOTAL, MAX_TOTAL, scenes.reduce((a, s) => a + s.seconds, 0));
  // keep the scene durations honest against the total
  const sceneSum = scenes.reduce((a, s) => a + s.seconds, 0);
  if (Math.abs(sceneSum - total) > 10) total = sceneSum;

  if (!combinedPrompt) throw new Error("plan is missing the one-pass combined prompt");

  const doctorFixes = Array.isArray(obj.doctorFixes)
    ? obj.doctorFixes.map((f) => asString(f, 240)).filter(Boolean).slice(0, 8)
    : [];

  void instruction; // kept for future relevance scoring
  return { title, logline, style, totalSeconds: total, scenes, combinedPrompt, doctorFixes };
}

/* ---------------------------------------------------------------- prompts */

export const SHOWRUNNER_SYSTEM = `You are DeYoung's showrunner - the specialist agent who turns ONE raw instruction into a complete short-film plan.

DeYoung is an AI video studio. The final film is 45-60 seconds, rendered by AI video models that CANNOT render reliable on-screen text or follow long dialogue. So:
- Every scene gets ONE short spoken line (max 12 words) that a narrator/character can say.
- Shot prompts must describe VISUALS only (subject, action, camera move, lighting, mood, setting). Never ask for text, captions, subtitles or lip-sync in the shot prompt.
- 4 to 6 scenes, each 6-14 seconds, total 45-60 seconds.
- Respect the user's instruction faithfully; if it is vague, make bold creative choices and say so in the logline.
- Style should fit the instruction (e.g. "3D Pixar-like animation", "gritty live-action", "anime") while staying bold and cinematic.

Return STRICT JSON only, no markdown fences, with exactly this shape:
{
  "title": string,
  "logline": string,
  "style": string,
  "totalSeconds": number,
  "scenes": [
    { "index": 1, "speaker": string, "line": string, "shotPrompt": string, "seconds": number }
  ],
  "combinedPrompt": string
}

"combinedPrompt" is a single vivid paragraph (max 140 words) describing the WHOLE film's visual arc for a one-pass AI video generation - it must capture the beginning, middle and end, the style, and the emotional payoff.`;

export const DOCTOR_SYSTEM = `You are DeYoung's script doctor - the critic agent that reviews a film plan before production.

You receive the user's original instruction and a JSON film plan. Fix REAL problems only:
- Lines that are too long to speak in the scene's seconds (rough rule: 2 words per second).
- Scene seconds that don't add up to totalSeconds (adjust scenes, keep total 45-60).
- Shot prompts that illegally request on-screen text, captions, subtitles or lip-sync - rewrite them as pure visuals.
- Unsafe, hateful, sexual, or clearly infringing content - replace with a safe alternative.
- A combinedPrompt that fails to capture the full story arc - rewrite it.
- Weak, passive verbs - punch them up.

Do NOT change the story, style, structure, or voice count unless a rule above forces it.

Return STRICT JSON only - the corrected plan in the exact same shape, plus a "doctorFixes" array (max 6 short strings, each one fix; empty array if the plan was already production-ready).`;

/* ------------------------------------------------------------ rate limiting */

const hits = new Map<string, number[]>();

export function rateLimit(key: string, max: number, windowMs: number): boolean {
  const now = Date.now();
  const arr = (hits.get(key) || []).filter((t) => now - t < windowMs);
  if (arr.length >= max) {
    hits.set(key, arr);
    return false;
  }
  arr.push(now);
  hits.set(key, arr);
  if (hits.size > 5000) {
    // keep the map bounded - drop the oldest quarter
    const cutoff = now - windowMs;
    for (const [k, v] of hits) {
      if (v.every((t) => t < cutoff)) hits.delete(k);
    }
  }
  return true;
}
