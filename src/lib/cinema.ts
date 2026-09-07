import "server-only";
import type { Niche } from "./aiengine";

/**
 * W2.49 — THE DIRECTOR'S BRAIN
 *
 * A broad, self-contained knowledge core on filmmaking + animation that the
 * studio AI draws on for every script, prompt and storyboard. The owner's
 * commission: "give the AI a very broad knowledge on videos, animations and
 * all of that — think like kids think, think like a director would."
 *
 * DESIGN RULES:
 *   1. Every bank here is FUNCTIONAL — it feeds the director's pass
 *      (`buildVisualBible` + `directScene`) which the script writer, prompt
 *      enhancer and storyboard all consume. Nothing decorative.
 *   2. Two lenses run on every decision:
 *        - THE DIRECTOR: shot grammar, lens language, lighting philosophy,
 *          composition, color scripting, sound layering, editing rhythm.
 *        - THE KID: wonder-first design — what makes a child lean into the
 *          screen (big eyes, tiny heroes, transformations, running gags,
 *          gentle peril + reassurance, callbacks).
 *   3. Zero network, zero keys, deterministic guarantees — it can never be
 *      "unavailable right now" (the W2.47 lesson).
 */

/* ============================ SHOT GRAMMAR ================================ */

export type ShotCraft = {
  id: string;
  name: string;
  purpose: string; // when a director reaches for it
  kid: string; // what it feels like through a child's eyes
};

export const SHOT_CRAFT: ShotCraft[] = [
  { id: "est-wide", name: "sweeping establishing wide shot", purpose: "opens a scene so the audience learns the world in one breath — geography before grammar", kid: "the 'wow, where are we?' moment — like opening a pop-up book" },
  { id: "medium", name: "friendly medium shot", purpose: "the workhorse: who is here, what they feel, what they are about to do", kid: "sitting right next to the character on the couch" },
  { id: "closeup", name: "intimate close-up", purpose: "the face IS the story — doubt, delight, decision", kid: "you can see the exact second their heart goes boom" },
  { id: "ecu", name: "extreme close-up detail", purpose: "one object or feature magnified until it becomes the whole world — the magic pen, the trembling hand", kid: "ant-view of the tiniest, most important thing" },
  { id: "low-hero", name: "low-angle hero shot", purpose: "shoots up at the subject to grant size, courage, myth", kid: "makes small heroes feel as tall as grown-ups" },
  { id: "high-small", name: "high-angle small-world shot", purpose: "looks down to shrink the subject — vulnerable, lost, adorable", kid: "when the world is SO big and you are SO little" },
  { id: "pov", name: "first-person POV shot", purpose: "borrows the character's eyes — the audience becomes them", kid: "the camera holds their hand and runs" },
  { id: "ots", name: "over-the-shoulder shot", purpose: "puts us in the conversation while keeping both faces in play", kid: "peeking over a giant's shoulder at something wonderful" },
  { id: "two-shot", name: "balanced two-shot", purpose: "friendship framed: both characters share one image equally", kid: "best friends fit in one picture, always" },
  { id: "dutch", name: "tilted dutch-angle shot", purpose: "the horizon leans — something is wrong, exciting or upside-down", kid: "the tickly feeling that everything just got silly" },
  { id: "insert", name: "macro insert shot", purpose: "the mechanism of magic: gears, sparkles, a note being written", kid: "how the trick actually works, up close" },
  { id: "silhouette", name: "backlit silhouette shot", purpose: "shape is identity — mystery, drama, or a hero posed against the sky", kid: "guessing who it is before the big reveal" },
];

/* ============================ CAMERA MOVES ================================ */

export type MoveCraft = { id: string; name: string; when: string };

export const CAMERA_CRAFT: MoveCraft[] = [
  { id: "push-in", name: "slow push-in", when: "realization grows — move toward what the character finally understands" },
  { id: "pull-out", name: "gentle pull-out reveal", when: "context blooms: what looked small is part of something huge" },
  { id: "tracking", name: "side tracking follow", when: "journey energy — walking, running, rolling toward a goal" },
  { id: "orbit", name: "180-degree orbit", when: "a discovery is centred; the world turns around it" },
  { id: "crane-up", name: "rising crane move", when: "a moment becomes bigger than the character — triumph or awe" },
  { id: "drone", name: "drone fly-over reveal", when: "scale and wonder — cities, oceans, kingdoms in one glide" },
  { id: "handheld", name: "bouncy handheld follow", when: "playful chaos, immediacy, being in the middle of the fun" },
  { id: "whip-pan", name: "whip-pan transition", when: "comedy timing — whoosh from one surprise into the next" },
  { id: "dolly-zoom", name: "dolly-zoom (vertigo) move", when: "the ground shifts under a realization — used sparingly, always felt" },
  { id: "rack-focus", name: "rack focus between planes", when: "two truths in one frame; the important one snaps into clarity" },
  { id: "crash-zoom", name: "crash-zoom punch", when: "a face or object deserves a drum-hit and a gasp" },
  { id: "steady-glide", name: "smooth gimbal glide", when: "dreamlike ease — gliding through a friendly world" },
];

/* ========================= LIGHTING PHILOSOPHY ============================ */

export type LightCraft = { id: string; name: string; feel: string };

export const LIGHT_CRAFT: LightCraft[] = [
  { id: "golden", name: "golden-hour backlight", feel: "nostalgia, promise, the day's best hug" },
  { id: "blue-hour", name: "blue-hour dusk wash", feel: "gentle mystery, bedtime-story calm" },
  { id: "threepoint", name: "classic three-point key light", feel: "clarity and confidence — the honest storyteller's light" },
  { id: "rembrandt", name: "Rembrandt side light", feel: "thoughtful faces, quiet depth" },
  { id: "chiaro", name: "dramatic chiaroscuro", feel: "high stakes; light versus shadow made visible" },
  { id: "silhouette-back", name: "hard backlight silhouette", feel: "myth-making — legends begin at sunset" },
  { id: "neon", name: "neon practical glow", feel: "electric nights, cities that hum" },
  { id: "soft-highkey", name: "airy high-key softness", feel: "safety and joy — nothing here will hurt you" },
  { id: "godrays", name: "volumetric god-rays", feel: "the magical made visible — dust motes as fairy dust" },
  { id: "firelight", name: "warm firelight practicals", feel: "gathering close, the oldest cinema there is" },
  { id: "moonwash", name: "cool moonlight wash", feel: "adventure after bedtime — the world remade at night" },
  { id: "overcast", name: "soft overcast evenness", feel: "honesty and calm — documentary truth" },
];

/* ============================ COMPOSITION ================================= */

export type CompositionCraft = { id: string; name: string; why: string };

export const COMPOSITION_CRAFT: CompositionCraft[] = [
  { id: "thirds", name: "rule-of-thirds framing", why: "eyes land where the lines cross — place the hero there and the frame breathes" },
  { id: "leading-lines", name: "leading lines into the subject", why: "roads, hallways and light beams quietly point at what matters" },
  { id: "symmetry", name: "centered symmetry", why: "formality, ritual, or a character perfectly balanced in their world" },
  { id: "negative-space", name: "brave negative space", why: "loneliness reads instantly; so does room to grow into" },
  { id: "frame-in-frame", name: "frame-within-a-frame", why: "doorways and windows make every scene feel discovered" },
  { id: "foreground-layer", name: "foreground-framed depth", why: "leaves, toys or shoulders in front add real depth to flat screens" },
  { id: "headroom", name: "clean headroom and lead-room", why: "space in the direction of a look keeps kid viewers oriented" },
  { id: "scale-contrast", name: "deliberate scale contrast", why: "a tiny hero against a giant door tells the whole story without words" },
];

/* =========================== COLOR SCRIPTING ============================== */

export type PaletteCraft = { id: string; palette: string; emotion: string };

export const COLOR_CRAFT: PaletteCraft[] = [
  { id: "candy", palette: "candy pastels on cream", emotion: "safety, sweetness, giggles" },
  { id: "primary-pop", palette: "crayon primaries", emotion: "energy, clarity, pure fun" },
  { id: "teal-amber", palette: "teal and amber cinema grade", emotion: "adventure with a warm heart" },
  { id: "sunset-hero", palette: "sunset oranges into purple dusk", emotion: "big feelings, brave endings" },
  { id: "mint-sky", palette: "mint and sky blue", emotion: "fresh mornings, new beginnings" },
  { id: "mono-accent", palette: "muted monochrome with one bold accent color", emotion: "the important thing glows — nothing distracts" },
  { id: "jewel", palette: "deep jewel tones with gold rim-light", emotion: "treasure, wonder, richness" },
  { id: "nordic", palette: "cool nordic blues with warm lantern pockets", emotion: "cozy against the cold — hygge cinema" },
];

/* ===================== 12 PRINCIPLES OF ANIMATION ========================= */

export type PrincipleCraft = { name: string; craft: string; kid: string };

export const ANIMATION_PRINCIPLES: PrincipleCraft[] = [
  { name: "Squash & Stretch", craft: "scale deforms with motion to sell weight and life", kid: "bouncy like the character is made of jelly" },
  { name: "Anticipation", craft: "wind up before action so the audience reads what's coming", kid: "the little crouch before the giant jump" },
  { name: "Staging", craft: "every idea staged clear and alone — one idea per beat", kid: "you always know exactly where to look" },
  { name: "Straight-Ahead & Pose-to-Pose", craft: "fluid chaos vs planned keys — blend both for controlled magic", kid: "sometimes the doodle knows where it's going" },
  { name: "Follow-Through & Overlap", craft: "hair, cloth and tails keep moving after the body stops", kid: "ears go boing after the character lands" },
  { name: "Slow In & Slow Out", craft: "ease in and out of keys — nothing organic moves at constant speed", kid: "things glide, they never robot-slide" },
  { name: "Arcs", craft: "limbs travel on curves, never dead straight lines", kid: "movements swoosh like rainbow paths" },
  { name: "Secondary Action", craft: "small supporting gestures amplify the main one", kid: "the sidekick's tiny nod that says 'yes!'" },
  { name: "Timing", craft: "frames between poses decide weight, mood and comedy", kid: "one extra pause makes the joke ten times bigger" },
  { name: "Exaggeration", craft: "push reality until the feeling is unmistakable", kid: "eyes pop SO big when the surprise lands" },
  { name: "Solid Drawing", craft: "form has volume and weight from every angle", kid: "characters feel huggable from any side" },
  { name: "Appeal", craft: "design with charm — silhouette-readable, lovable, alive", kid: "you want to hug them the second you meet them" },
];

/* ============================== KID LENS ================================== */

export type KidRule = { rule: string; why: string };

export const KID_CRAFT: KidRule[] = [
  { rule: "wonder before plot", why: "children forgive slow stories; they never forgive boring frames" },
  { rule: "tiny hero, giant world", why: "kids live at small scale — let them win anyway" },
  { rule: "transformation moments", why: "anything can become something else — that is the genre's purest magic" },
  { rule: "silly sidekick with heart", why: "laughter opens the door; loyalty makes it stay open" },
  { rule: "gentle peril, guaranteed reassurance", why: "a safe scare teaches courage; never leave a child alone in the dark" },
  { rule: "running gags and callbacks", why: "spotting the return of a joke is a child's first film-literacy thrill" },
  { rule: "big readable faces", why: "emotion must be readable from across the room, with sound off" },
  { rule: "objects with souls", why: "a brave pencil or a shy moon is a character, not a prop" },
  { rule: "repetition with escalation", why: "three tries, each bigger — the oldest and best kid-structure there is" },
  { rule: "parents smile too", why: "one warm adult-facing joke buys the rewatch" },
];

export const AGE_BANDS: Record<string, string> = {
  "3-6": "ultra-clear staging, soft edges, no real threat, songs and repetition",
  "7-9": "mild peril allowed, jokes with layers, heroes who earn their win",
  "10-12": "real stakes, quips, identity feelings, spectacle with consequence",
};

/* ============================ SOUND CRAFT ================================= */

export type SoundCraft = { beat: string; cue: string };

export const SOUND_CRAFT: Record<string, string> = {
  hook: "one signature sound that will return at the finale — plant the earworm",
  establish: "layered ambience that makes the place feel inhabited before anyone speaks",
  turn: "the music stops for a half-beat — silence is the loudest edit",
  build: "rhythmic percussion synced to movement; tempo climbs with the stakes",
  climax: "full score bloom, foley detail up close, the world at maximum volume",
  resolve: "music resolves home; one last soft foley detail says life goes on",
};

/* ========================= GENRE / DIRECTOR VOICES ======================== */

export type DirectorVoice = { id: string; voice: string; rule: string };

export const DIRECTOR_VOICES: Record<Niche, DirectorVoice> = {
  "kids cartoon": { id: "heart-first", voice: "Pixar-heart with Ghibli wonder", rule: "every frame huggable, every stakes gentle, every ending earned" },
  "product ad": { id: "obsession-craft", voice: "Apple-launch minimalism", rule: "the product is the protagonist; light it like a hero, cut like a heartbeat" },
  "real estate": { id: "quiet-luxury", voice: "Architectural-Digest serenity", rule: "nobody runs; light does the selling; the house is the character arc" },
  "music video": { id: "rhythm-king", voice: "kinetic Hype-Williams energy", rule: "the edit IS the chorus; every cut lands on the beat" },
  explainer: { id: "clarity-coach", voice: "friendly motion-graphics precision", rule: "one idea per scene; the diagram is the drama" },
  "social reel": { id: "hook-surgeon", voice: "native vertical-native boldness", rule: "the first second is the title, the thumbnail and the promise" },
  travel: { id: "wander-cinema", voice: "documentary wanderlust", rule: "small human, vast world; let landscapes hold the shots long" },
  fashion: { id: "shadow-tailor", voice: "Vogue editorial contrast", rule: "fabric is texture-acting; shadows are the second model" },
  gaming: { id: "hype-engine", voice: "AAA game-cinematic adrenaline", rule: "victory poses, speed ramps, respawn logic" },
  custom: { id: "story-first", voice: "modern cinematic feature honesty", rule: "serve the story; the style follows the feeling" },
};

/* ========================= THE DIRECTOR'S PASS ============================ */

export type VisualBible = {
  styleAnchor: string;
  palette: string;
  lightPhilosophy: string;
  lensFeel: string;
  directorVoice: string;
  kidPromise: string;
  bibleLine: string;
};

export type Direction = {
  shot: string;
  move: string;
  light: string;
  composition: string;
  emotion: string;
  sound: string;
  principle: string;
  note: string;
};

export type Beat = "hook" | "establish" | "turn" | "build" | "climax" | "resolve";

/** Per-beat directorial instinct — which shots and feelings serve the story moment. */
const BEAT_INSTINCT: Record<Beat, { shots: string[]; moves: string[]; emotions: string[] }> = {
  hook: { shots: ["est-wide", "silhouette", "high-small"], moves: ["drone", "pull-out", "crane-up"], emotions: ["curiosity", "awe", "a giggle of surprise"] },
  establish: { shots: ["medium", "est-wide", "two-shot"], moves: ["steady-glide", "tracking", "handheld"], emotions: ["warmth", "belonging", "safe excitement"] },
  turn: { shots: ["ecu", "insert", "closeup"], moves: ["rack-focus", "push-in", "crash-zoom"], emotions: ["wonder", "a gasp", "wide-eyed discovery"] },
  build: { shots: ["low-hero", "pov", "tracking-follow"], moves: ["tracking", "handheld", "orbit"], emotions: ["momentum", "growing courage", "giddy speed"] },
  climax: { shots: ["low-hero", "dutch", "closeup"], moves: ["crash-zoom", "dolly-zoom", "crane-up"], emotions: ["triumph", "heart-pounding joy", "the big brave yes"] },
  resolve: { shots: ["two-shot", "est-wide", "medium"], moves: ["pull-out", "crane-up", "steady-glide"], emotions: ["cozy contentment", "a happy sigh", "see-you-soon warmth"] },
};

type R = () => number;
function pick<T>(r: R, arr: readonly T[]): T {
  return arr[Math.floor(r() * arr.length) % arr.length];
}

const LENS_BY_NICHE: Record<Niche, string> = {
  "kids cartoon": "soft short lenses with gentle depth — everything feels touchable",
  "product ad": "macro precision glass, razor-sharp on the hero surface",
  "real estate": "wide architectural glass, verticals kept perfectly straight",
  "music video": "anamorphic flares and fast primes riding the beat",
  explainer: "clean flat-field rendering, distortion-free",
  "social reel": "phone-native wide with snap-focus energy",
  travel: "long-lens compression for vistas, wide for immersion",
  fashion: "85mm portrait compression with silky falloff",
  gaming: "engine-crisp wide FOV with speed-ramp motion blur",
  custom: "natural human-eye focal lengths, honest perspective",
};

const KID_PROMISES: string[] = [
  "a tiny hero the smallest viewer will root for from the first frame",
  "at least one pure transformation moment that earns a gasp",
  "a face so readable the story works with the sound off",
  "one running gag planted early and paid off at the end",
  "a world that feels safe enough to laugh loud in",
];

/**
 * Build ONE visual bible per film — the consistency contract every scene
 * signs. Anchoring style/palette/lens per film (not per scene) is how
 * characters and worlds stay recognizably the same across scenes.
 */
export function buildVisualBible(niche: Niche, brief: string, r: R): VisualBible {
  const voice = DIRECTOR_VOICES[niche];
  const palette = pick(r, COLOR_CRAFT);
  const light = pick(r, LIGHT_CRAFT);
  const kidPromise = pick(r, KID_PROMISES);
  const night = /night|midnight|dark|moon/i.test(brief);
  const lightPhilosophy = night
    ? "cool moonlight wash with warm practical pockets — adventure after bedtime"
    : light.name;
  const bible: VisualBible = {
    styleAnchor: voice.voice,
    palette: palette.palette,
    lightPhilosophy,
    lensFeel: LENS_BY_NICHE[niche],
    directorVoice: voice.rule,
    kidPromise,
    bibleLine: `${voice.voice} — ${palette.palette} (${palette.emotion}), ${lightPhilosophy}, ${LENS_BY_NICHE[niche]}. Director's rule: ${voice.rule}. Promise to the audience: ${kidPromise}.`,
  };
  return bible;
}

/**
 * Direct ONE scene: choose shot, move, light, composition, emotion, sound and
 * an animation principle, then explain the choice as a director's note that
 * blends director-craft with kid-thinking.
 */
export function directScene(
  beat: Beat,
  index: number,
  bible: VisualBible,
  r: R,
  subject?: string
): Direction {
  const instinct = BEAT_INSTINCT[beat];
  const shotPool = instinct.shots.map((id) => SHOT_CRAFT.find((s) => s.id === id)!).filter(Boolean);
  const movePool = instinct.moves.map((id) => CAMERA_CRAFT.find((m) => m.id === id)!).filter(Boolean);
  const shot = pick(r, shotPool.length ? shotPool : SHOT_CRAFT);
  const move = pick(r, movePool.length ? movePool : CAMERA_CRAFT);
  const composition = pick(r, COMPOSITION_CRAFT);
  const emotion = pick(r, instinct.emotions);
  const principle = ANIMATION_PRINCIPLES[index % ANIMATION_PRINCIPLES.length];
  const sound = SOUND_CRAFT[beat];
  const hero = subject ? `${subject}` : "the hero";

  const note = `${capitalize(shot.name)} ${move.name}: ${shot.purpose}. Through a kid's eyes: ${shot.kid}. Composition — ${composition.name} (${composition.why}); frame for ${emotion}. Animation principle in play: ${principle.name} — ${principle.kid}. Sound: ${sound}.`;

  return {
    shot: shot.name,
    move: move.name,
    light: bible.lightPhilosophy,
    composition: composition.name,
    emotion,
    sound,
    principle: `${principle.name} — ${principle.kid}`,
    note: note.slice(0, 500),
  };
}

function capitalize(s: string): string {
  s = s.trim();
  if (!s) return s;
  return s[0].toUpperCase() + s.slice(1);
}

/** One line describing how the film will be directed — shown above the storyboard. */
export function bibleHeadline(bible: VisualBible): string {
  const voice = bible.styleAnchor.startsWith("Pixar") ? "with heart and wonder" : `in the ${bible.styleAnchor} voice`;
  return `Directed ${voice} — ${bible.palette}, ${bible.lightPhilosophy}.`;
}
