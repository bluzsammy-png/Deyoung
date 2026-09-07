import "server-only";
import crypto from "crypto";

/**
 * W2.47 — Production AI engine for the studio (prompt enhancer + script writer).
 *
 * WHY THIS EXISTS: the first implementation called z-ai-web-dev-sdk, whose
 * credentials (.z-ai-config) resolve to sandbox-internal addresses — unreachable
 * from Railway. Every enhance/script call in production died with
 * "unavailable right now". The owner (admin) could not use either tool.
 *
 * DESIGN (sophisticated AND solid):
 *   1. OPTIONAL LLM upgrade — when AI_API_KEY / OPENAI_API_KEY (+ optional
 *      AI_BASE_URL, AI_MODEL) is configured, an OpenAI-compatible chat
 *      completion is attempted first with a hard timeout. Any failure falls
 *      through silently to the local engine. Plug in a key later, zero code
 *      changes.
 *   2. LOCAL CINEMATIC ENGINE — a self-contained composition system (no network,
 *      no keys, cannot fail on a missing config): a brief analyzer (subject /
 *      action / setting / cast extraction), per-niche cinematography banks
 *      (camera language, lighting, palettes, moods, film-style references),
 *      narrative beat structures, and seeded composition so every run varies.
 *      Output quality is curated, on-topic and always available.
 */

export const NICHES = [
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
] as const;

export type Niche = (typeof NICHES)[number];

export type ScriptShape = {
  title: string;
  logline: string;
  characters: { name: string; look: string; voice: string }[];
  scenes: { id: string; title: string; seconds: number; line: string; visual: string }[];
};

/* ------------------------------- tiny RNG --------------------------------- */

function rng(): () => number {
  const buf = crypto.randomBytes(4);
  let a = buf.readUInt32LE(0) || 0x9e3779b9;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(r: () => number, arr: readonly T[]): T {
  return arr[Math.floor(r() * arr.length) % arr.length];
}

function shuffled<T>(r: () => number, arr: readonly T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/* --------------------------- brief analyzer -------------------------------- */

const STOP = new Set(
  ("a an the and or but of for with in on at to from by as is are was were be been being this that these those it its his her their our your my " +
    "i we you he she they them us him me make makes making create creating want wants need needs video film ad about into over under very just really " +
    "some any more most much many lot lots piece kind sort type like get gets got show shows showing").split(" ")
);

type Brief = {
  subject: string;
  action: string;
  nouns: string[];
  verbs: string[];
  adjectives: string[];
  setting: string | null;
  timeOfDay: string | null;
  cast: string[];
  words: string[];
};

const TIME_WORDS: Record<string, string> = {
  night: "night", midnight: "night", dusk: "dusk", sunset: "golden hour", sunrise: "dawn",
  dawn: "dawn", morning: "early morning", afternoon: "late afternoon", evening: "evening",
  day: "midday", noon: "midday", "golden hour": "golden hour",
};

/** Common English verbs (any regular inflection) — excluded from noun slots. */
const VERB_BANK = new Set(
  ("discover discover find find make make create create build build run run walk walk fly fly jump jump dance dance move move turn turn open open " +
   "grow grow shine shine glow glow ride ride drive drive swim swim play play sing sing cook cook paint paint draw draw explore explore travel travel " +
   "launch launch skate skate surf surf climb climb chase chase catch catch buy buy sell sell share share show show tell tell speak speak talk talk " +
   "laugh laugh smile smile cry cry sleep sleep wake wake eat eat drink drink read read write write study study learn learn teach teach help help " +
   "give give take take keep keep hold hold lift lift push push pull pull carry carry wear wear race race bring bring come come go go live live " +
   "look look watch watch see see hear hear feel feel think think know know say say ask ask try try start start stop stop finish finish fall fall " +
   "rise rise descend descend spin spin float float drift drift flow flow wave wave sparkle sparkle dream dream wish wish believe believe " +
   "transform transform unlock unlock collect collect gather gather deliver deliver pack pack wrap wrap pour pour mix mix stir stir slice slice " +
   "skateboard skateboard wrestle wrestle battle battle fight fight win win lose lose score score dodge dodge aim aim shoot shoot cast cast")
    .split(" ")
    .filter(Boolean)
);

function isVerbForm(word: string): boolean {
  const l = word.toLowerCase();
  if (VERB_BANK.has(l)) return true;
  if (l.endsWith("s") && VERB_BANK.has(l.slice(0, -1))) return true;
  if (l.endsWith("es") && VERB_BANK.has(l.slice(0, -2))) return true;
  if (l.endsWith("ed") && VERB_BANK.has(l.slice(0, -2))) return true;
  if (l.endsWith("ing") && VERB_BANK.has(l.slice(0, -3))) return true;
  if (l.endsWith("ing") && VERB_BANK.has(l.slice(0, -3) + "e")) return true;
  return false;
}

function analyzeBrief(text: string): Brief {
  const clean = text.replace(/[^A-Za-z0-9'’\s.,!?-]/g, " ");
  const words = clean.split(/\s+/).filter(Boolean);
  const lower = words.map((w) => w.toLowerCase());

  const nouns: string[] = [];
  const verbs: string[] = [];
  const adjectives: string[] = [];
  const cast: string[] = [];

  for (let i = 0; i < words.length; i++) {
    const w = words[i].replace(/[^A-Za-z0-9'’-]/g, "");
    if (!w) continue;
    const l = lower[i];
    if (STOP.has(l)) continue;
    // named entity: capitalized mid-sentence words that aren't the first word of the text.
    if (i > 0 && /^[A-Z][a-z]{2,}$/.test(w) && !cast.includes(w) && cast.length < 3) cast.push(w);
    if (isVerbForm(w)) {
      if (!verbs.includes(l)) verbs.push(l);
      continue; // verbs never become noun slots (47 QA: "while discovers fills the frame")
    }
    if (l.length > 2 && !nouns.includes(l)) nouns.push(l);
    if (w.length > 3 && /(ful|ous|y|bright|dark|soft|hard|neon|vibrant|pastel|golden|silent|loud|fast|slow|calm|epic|cozy|bold)$/i.test(l) && !adjectives.includes(l)) adjectives.push(l);
  }

  let setting: string | null = null;
  const settingWords = [
    "city", "street", "beach", "forest", "desert", "mountain", "kitchen", "office", "studio",
    "room", "house", "home", "market", "shop", "store", "school", "park", "bridge", "roof",
    "rooftop", "field", "farm", "factory", "lab", "library", "cafe", "car", "train", "bus",
    "boat", "ship", "island", "river", "lake", "ocean", "sea", "sky", "space", "moon", "jungle",
    "village", "town", "arena", "stadium", "gallery", "museum", "hotel", "pool", "gym", "stage",
  ];
  for (const l of lower) {
    if (settingWords.includes(l)) {
      setting = l;
      break;
    }
  }

  let timeOfDay: string | null = null;
  for (const [k, v] of Object.entries(TIME_WORDS)) {
    if (lower.includes(k)) {
      timeOfDay = v;
      break;
    }
  }

  const subject = nouns[0] ?? "story";
  const action = verbs[0] ?? nouns[1] ?? "unfolds";
  return { subject, action, nouns, verbs, adjectives, setting, timeOfDay, cast, words };
}

/* ------------------------- niche cinematography --------------------------- */

type NicheStyle = {
  camera: string[];
  light: string[];
  palette: string[];
  mood: string[];
  style: string[];
  settings: string[];
  titleA: string[];
  titleB: string[];
  castFallback: { name: string; look: string; voice: string }[];
};

const STYLES: Record<Niche, NicheStyle> = {
  "kids cartoon": {
    camera: ["wide establishing shot", "bouncy low-angle tracking shot", "playful dutch-angle push-in", "whip-pan into a close-up", "gentle crane rise"],
    light: ["bright soft sunshine with bouncy fill", "candy-colored rim light", "warm kitchen-glow practicals", "sparkling morning light"],
    palette: ["candy pastels", "crayon primaries", "sunny yellow-and-sky-blue", "bubblegum pink and mint"],
    mood: ["joyful and giggly", "wide-eyed wonder", "cozy storybook warmth", "bubbly chaos"],
    style: ["rounded 3D cartoon feature look", "soft storybook illustration style", "plush claymation feel", "bubbly preschool TV style"],
    settings: ["a sunny backyard", "a magical playroom", "a friendly treehouse", "a pastel village street"],
    titleA: ["The Little", "Pip and the", "The Great", "Tiny"],
    titleB: ["Adventure", "Surprise", "Playdate", "Big Day", "Rainbow Hunt"],
    castFallback: [
      { name: "Pip", look: "a small round hero with oversized curious eyes and a bright backpack", voice: "chirpy and eager" },
      { name: "Bubbles", look: "a bouncy sidekick with floppy ears and a crooked grin", voice: "giggly squeak" },
      { name: "Nana Bloom", look: "a warm grandmotherly figure with round glasses", voice: "cozy and reassuring" },
    ],
  },
  "product ad": {
    camera: ["macro detail glide", "slow 180-degree orbit", "sleek dolly-in to hero close-up", "floating product spin on black", "crisp rack-focus reveal"],
    light: ["controlled studio softbox with crisp specular highlights", "dramatic single key with deep falloff", "clean high-key white infinity light", "luxury rim-lit glow"],
    palette: ["premium matte black and gold", "clean white with one bold accent", "cool chrome and glass tones", "warm editorial neutrals"],
    mood: ["premium and confident", "fresh and irresistible", "precise and modern", "aspirational"],
    style: ["glossy commercial cinematography", "high-end tabletop commercial look", "Apple-style minimal product film", "luxury fragrance-ad grade"],
    settings: ["a seamless studio void", "a marble countertop stage", "a minimalist showroom", "a sunlit lifestyle set"],
    titleA: ["Meet", "The New", "Introducing", "Pure"],
    titleB: ["Perfection", "Upgrade", "Essential", "Moment", "Glow"],
    castFallback: [
      { name: "The Product", look: "the hero item, immaculately lit, every surface catching light", voice: "confident brand VO" },
      { name: "The Everyday Hero", look: "an effortlessly stylish user in modern casual wear", voice: "warm and genuine" },
    ],
  },
  "real estate": {
    camera: ["smooth gimbal walkthrough", "slow push through the doorway", "sweeping drone approach to the facade", "wide symmetrical interior reveal", "gliding window-pan to the view"],
    light: ["golden-hour sun flooding through tall windows", "airy natural daylight with soft shadows", "warm dusk interior lights layered with twilight", "bright midday openness"],
    palette: ["warm oak and cream", "cool coastal white and sea-glass blue", "earthy terracotta and sage", "crisp modern grey and glass"],
    mood: ["inviting and serene", "aspirational and calm", "grand yet homey", "quiet luxury"],
    style: ["architectural digest cinematography", "luxury property film look", "photoreal estate walkthrough grade", "magazine-quality interior photography in motion"],
    settings: ["a sun-drenched living room", "a chef's kitchen with stone island", "an infinity-edge pool terrace", "a landscaped garden pathway"],
    titleA: ["Welcome to", "Life at", "Inside", "Discover"],
    titleB: ["Home", "The Address", "Your Sanctuary", "The View", "Living"],
    castFallback: [
      { name: "The Host", look: "a poised figure in soft neutral attire, gesturing toward the light", voice: "calm and welcoming" },
      { name: "The Visitor", look: "a curious newcomer taking it all in", voice: "quiet amazement" },
    ],
  },
  "music video": {
    camera: ["rhythmic handheld orbit", "fast crash-zoom on the beat", "slow-motion hero walk toward camera", "strobe-lit silhouette dolly", "fisheye spin around the artist"],
    light: ["neon-soaked haze with practical tubes", "hard backlight and smoke silhouettes", "strobe-cut club lighting", "moody amber streetlight wash"],
    palette: ["electric magenta and cyan", "blood red and black", "chrome silver and deep violet", "sunset orange smoke"],
    mood: ["electric and defiant", "hypnotic and raw", "euphoric", "cool and untouchable"],
    style: ["kinetic music-video grammar", "anamorphic performance-film look", "gritty 16mm energy", "glossy Hype Williams sheen"],
    settings: ["a fog-filled warehouse", "a rain-slicked night street", "a mirrored dance hall", "a rooftop against the skyline"],
    titleA: ["Midnight", "Neon", "No", "Last"],
    titleB: ["Frequency", "Confession", "Chorus", "Static", "Encore"],
    castFallback: [
      { name: "The Artist", look: "magnetic lead performer, silhouette-cut against the haze", voice: "the hook itself" },
      { name: "The Crew", look: "dancers moving as one synchronized wave", voice: "chanted ad-libs" },
    ],
  },
  explainer: {
    camera: ["clean frontal framing", "confident lateral dolly", "top-down flat-lay sweep", "zoom into the key diagram", "orbit around the concept model"],
    light: ["even shadowless studio light", "soft gradient backdrop glow", "bright neutral key with gentle lift", "crisp digital- daylight"],
    palette: ["trusted navy and clean white", "friendly teal and coral accents", "monochrome with a single signal color", "soft pastel gradients"],
    mood: ["clear and reassuring", "smart and approachable", "focused and efficient", "curious"],
    style: ["minimal motion-graphics aesthetic", "isometric 3D explainer look", "clean SaaS-demo cinematography", "editorial infographic style"],
    settings: ["a minimal gradient backdrop", "an isometric miniature world", "a tidy desk workspace", "an abstract data landscape"],
    titleA: ["How", "Why", "The Simple Truth About", "A Guide to"],
    titleB: ["It Works", "The Idea", "In 60 Seconds", "Explained", "The Basics"],
    castFallback: [
      { name: "The Guide", look: "a friendly presenter gesturing at floating key visuals", voice: "clear and encouraging" },
      { name: "The Skeptic", look: "a relatable every-person with a raised eyebrow", voice: "curious, asks the obvious question" },
    ],
  },
  "social reel": {
    camera: ["punchy handheld follow", "snap-zoom to the point", "vertical tilt reveal", "quick-cut multi-angle bursts", "selfie-style walking shot"],
    light: ["bright ring-light clarity", "sun-drenched golden flare", "trendy overexposed bloom", "bold color-gel pop"],
    palette: ["high-saturation statement colors", "clean beige-and-white aesthetic", "vivid gradient backdrops", "black-and-white with one red accent"],
    mood: ["bold and scroll-stopping", "fun and punchy", "confident tip-sharing energy", "instantly relatable"],
    style: ["native vertical-video look", "trending reel cinematography", "UGC-authentic handheld feel", "crisp creator-studio grade"],
    settings: ["a curated content corner", "a buzzing city sidewalk", "a bright cafe table", "a mirror-lit room"],
    titleA: ["Stop Scrolling:", "POV:", "The", "Nobody Told You"],
    titleB: ["Truth About", "3-Second Hook", "This Changes Everything", "The Hack", "Wait For It"],
    castFallback: [
      { name: "The Creator", look: "expressive on-camera host, direct to lens", voice: "fast, friendly, confident" },
      { name: "The Friend", look: "reactive off-camera presence", voice: "gasps and hype" },
    ],
  },
  travel: {
    camera: ["epic drone reveal over the landscape", "low glide across the terrain", "handheld wander through the market", "timelapse of drifting clouds above the ridge", "slow push toward the horizon"],
    light: ["golden hour stretching long shadows", "crisp blue-sky daylight", "moody storm light breaking open", "soft overcast evenness"],
    palette: ["earth tones and sky blues", "sun-bleached sand and turquoise", "lush jungle greens", "alpine grey and glacier white"],
    mood: ["wanderlust and awe", "free and unhurried", "small human, vast world", "alive and buzzing"],
    style: ["cinematic travel-film grade", "documentary wanderlust look", "natural-light vista cinematography", "drone-epic tourism film"],
    settings: ["a winding coastal road", "a vibrant local bazaar", "a misty mountain pass", "an empty beach at dawn"],
    titleA: ["Passage to", "Wandering", "The Road to", "Postcards from"],
    titleB: ["Nowhere", "The Horizon", "Somewhere New", "The Long Way", "Home"],
    castFallback: [
      { name: "The Traveler", look: "a weathered backpack and curious eyes, walking into frame", voice: "reflective VO" },
      { name: "The Local", look: "a warm greeting from someone who knows the place", voice: "inviting accent" },
    ],
  },
  fashion: {
    camera: ["slow-motion strut toward lens", "snappy couture pose cuts", "arcing dolly around the silhouette", "detail macro on fabric and stitching", "hard-flash runway push"],
    light: ["high-contrast single spotlight", "hard flash with deep shadow falloff", "silky beauty light with soft haze", "editorial window-slash lighting"],
    palette: ["monochrome black with gold jewelry accents", "nude neutrals and ivory", "bold scarlet statement", "metallic silver futurism"],
    mood: ["imperious and elegant", "edgy confidence", "sensual and slow", "avant-garde"],
    style: ["vogue editorial cinematography", "high-fashion runway film", "grainy analog fashion look", "sleek luxury campaign grade"],
    settings: ["a marble runway hall", "a brutalist concrete backdrop", "a velvet-draped atelier", "a wind-swept rooftop"],
    titleA: ["The Cut of", "Silk &", "Wearing", "House of"],
    titleB: ["Shadow", "Storm", "Desire", "The New Form", "Atelier"],
    castFallback: [
      { name: "The Muse", look: "statuesque lead in the hero garment, every line intentional", voice: "poised silence" },
      { name: "The Dresser", look: "hands adjusting a collar just out of frame", voice: "whispered directions" },
    ],
  },
  gaming: {
    camera: ["FPS-style dolly through the corridor", "drone sweep over the battle arena", "crash-zoom on the power-up", "slow-mo dodge with speed-ramp", "over-the-shoulder aim push"],
    light: ["RGB glow and volumetric fog", "laser-grid neon corridors", "explosive muzzle-flash strobes", "holographic UI light on faces"],
    palette: ["toxic green and void black", "arcade purple and electric blue", "lava orange against gunmetal", "holo-cyan wireframes"],
    mood: ["high-octane and relentless", "strategic and tense", "victory-lap triumphant", "glitched and mysterious"],
    style: ["AAA game-cinematic look", "retro-arcade synthwave aesthetic", "esports-hype montage grade", "photoreal engine cutscene"],
    settings: ["a neon arena floor", "a loot-filled vault", "a boss-lair catwalk", "a respawn lobby"],
    titleA: ["Final", "Respawn:", "Boss", "Level"],
    titleB: ["Round", "One More Life", "Clutch", "Overdrive", "Unlock"],
    castFallback: [
      { name: "Player One", look: "geared-up avatar with glowing visor", voice: "locked-in determination" },
      { name: "The Rival", look: "shadowed opponent at the far end of the arena", voice: "taunting calm" },
    ],
  },
  custom: {
    camera: ["slow cinematic push-in", "sweeping establishing wide", "intimate handheld close-up", "graceful crane descent", "tracking follow through the scene"],
    light: ["soft natural key with atmospheric haze", "dramatic chiaroscuro contrast", "warm practicals in frame", "cool moonlight wash"],
    palette: ["muted filmic tones", "rich teal and amber", "desaturated documentary neutrals", "high-contrast silver and ink"],
    mood: ["quietly powerful", "cinematic and immersive", "honest and grounded", "awe-struck"],
    style: ["modern cinematic feature grade", "documentary-realist look", "anamorphic indie-film aesthetic", "photoreal drama cinematography"],
    settings: ["a quiet street at dusk", "a room full of history", "an open road ahead", "a doorway between light and shadow"],
    titleA: ["The Story of", "Beyond", "Before", "After"],
    titleB: ["The Beginning", "Everything", "The Fall", "Light", "Tomorrow"],
    castFallback: [
      { name: "The Protagonist", look: "a compelling figure carrying the story's weight", voice: "steady and human" },
      { name: "The Witness", look: "someone watching from the edge of the frame", voice: "soft observation" },
    ],
  },
};

/* ---------------------------- beat structure ------------------------------ */

type Beat = "hook" | "establish" | "turn" | "build" | "climax" | "resolve";

const BEAT_TITLES: Record<Beat, string[]> = {
  hook: ["The Spark", "First Light", "Cold Open", "The Hook"],
  establish: ["The World", "Meet the Moment", "Setup", "Ground Level"],
  turn: ["The Turn", "Shift", "New Information", "The Discovery"],
  build: ["Momentum", "Rising", "The Push", "Lock In"],
  climax: ["The Peak", "Everything at Once", "The Moment", "Point of No Return"],
  resolve: ["The Landing", "Resolution", "Final Frame", "The Button"],
};

function beatsFor(count: number): Beat[] {
  const arcs: Record<number, Beat[]> = {
    3: ["hook", "climax", "resolve"],
    4: ["hook", "establish", "turn", "resolve"],
    5: ["hook", "establish", "turn", "climax", "resolve"],
    6: ["hook", "establish", "build", "turn", "climax", "resolve"],
    7: ["hook", "establish", "build", "turn", "build", "climax", "resolve"],
    8: ["hook", "establish", "build", "turn", "build", "climax", "resolve", "resolve"],
    9: ["hook", "establish", "build", "turn", "build", "build", "climax", "resolve", "resolve"],
    10: ["hook", "establish", "build", "build", "turn", "build", "build", "climax", "resolve", "resolve"],
  };
  return arcs[Math.min(10, Math.max(3, count))];
}

/** Night-coherent lighting — avoids "night + sunshine" contradictions (47 polish). */
const NIGHT_LIGHTS = [
  "moody moonlight with warm window practicals",
  "cool blue night wash with glowing streetlamps",
  "soft lamplight pools against deep shadow",
  "neon glow cutting through the dark",
];

function coherentLight(light: string, tod: string | null, r: () => number): string {
  if (tod && /night|dusk|midnight/i.test(tod) && /sun|morning|day|midday/i.test(light)) {
    return pick(r, NIGHT_LIGHTS);
  }
  return light;
}

/* --------------------------- line templates ------------------------------- */

const LINE_TEMPLATES: Record<Beat, string[]> = {
  hook: ["It starts with {noun}.", "This is how {noun} begins.", "Everything was ordinary — until now.", "One moment. That's all it took."],
  establish: ["This is {setting}.", "{adj} and alive, just the way we like it.", "Every day looks like this.", "Here, anything can happen."],
  turn: ["Wait — {noun}?", "That's when it changed.", "Nobody expected {noun}.", "Then the door opened."],
  build: ["Faster now. Don't stop.", "We're close. I can feel it.", "One more push.", "Hold on — this is the good part."],
  climax: ["This. Is. It.", "NOW!", "All of it, right here.", "The whole story in one breath."],
  resolve: ["And just like that… {noun}.", "Some endings are beginnings.", "That's the magic of {noun}.", "Until next time."],
};

function fill(template: string, brief: Brief, setting: string): string {
  return template
    .replace("{noun}", brief.nouns[0] ?? "this")
    .replace("{setting}", setting.replace(/^an? /, ""))
    .replace("{adj}", brief.adjectives[0] ?? "bright");
}

/* ------------------------- optional LLM provider -------------------------- */

function llmConfig(): { url: string; key: string; model: string } | null {
  const key = process.env.AI_API_KEY || process.env.OPENAI_API_KEY || "";
  if (!key) return null;
  const base = (process.env.AI_BASE_URL || "https://api.openai.com/v1").replace(/\/$/, "");
  return { url: `${base}/chat/completions`, key, model: process.env.AI_MODEL || "gpt-4o-mini" };
}

async function llmJSON(system: string, user: string, maxTokens = 900): Promise<unknown | null> {
  const cfg = llmConfig();
  if (!cfg) return null;
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12_000);
    const res = await fetch(cfg.url, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${cfg.key}` },
      body: JSON.stringify({
        model: cfg.model,
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        max_tokens: maxTokens,
        temperature: 0.8,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!res.ok) return null;
    const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    const raw = (data.choices?.[0]?.message?.content ?? "").trim();
    const jsonText = raw.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
    return JSON.parse(jsonText);
  } catch {
    return null; // fall through to the local engine — never fail the request
  }
}

async function llmText(system: string, user: string, maxTokens = 300): Promise<string | null> {
  const cfg = llmConfig();
  if (!cfg) return null;
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12_000);
    const res = await fetch(cfg.url, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${cfg.key}` },
      body: JSON.stringify({
        model: cfg.model,
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        max_tokens: maxTokens,
        temperature: 0.8,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!res.ok) return null;
    const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    const text = (data.choices?.[0]?.message?.content ?? "").trim();
    return text || null;
  } catch {
    return null;
  }
}

/* --------------------------- public: enhance ------------------------------ */

/** Turn a rough idea into one vivid, cinematic video prompt (40–80 words). */
export async function enhancePrompt(prompt: string, niche: Niche): Promise<string> {
  const viaLLM = await llmText(
    "You are DeYoung's prompt director for an AI text-to-video film engine. Rewrite the user's rough idea into ONE vivid, cinematic video prompt of 40-80 words. " +
      `Niche: ${niche}. Include: subject + action, setting, camera language (shot/movement), lighting, mood, and visual style. No preamble, no quotes, no markdown — return the prompt text only.`,
    prompt
  );
  if (viaLLM) return viaLLM.slice(0, 800);

  const r = rng();
  const st = STYLES[niche];
  const brief = analyzeBrief(prompt);
  const camera = pick(r, st.camera);
  const light = coherentLight(pick(r, st.light), brief.timeOfDay ?? (/night|midnight|dusk/i.test(prompt) ? "night" : null), r);
  const palette = pick(r, st.palette);
  const mood = pick(r, st.mood);
  const style = pick(r, st.style);
  const setting = brief.setting ? `a ${niche === "kids cartoon" ? "storybook " : ""}${brief.setting}` : pick(r, st.settings);
  const tod = brief.timeOfDay ?? pick(r, ["golden hour", "blue hour", "bright midday", "atmospheric night"]);
  const topic = brief.nouns.slice(0, 3).join(", ") || prompt.slice(0, 60);

  const openers = [
    `${capitalize(prompt.replace(/\s+/g, " ").slice(0, 90).trim())}`,
    `A ${mood} scene about ${topic}`,
    `${capitalize(topic)} — brought to life`,
  ];
  const opener = openers[0].length > 12 ? openers[0] : pick(r, openers.slice(1));

  const shapes = [
    `${opener}. ${capitalize(camera)}, ${setting}, ${tod}. ${capitalize(light)}; ${palette} palette. ${capitalize(mood)} atmosphere, ${style}.`,
    `${opener} — told through a ${camera} in ${setting}. ${capitalize(tod)}, ${light}, ${palette} palette. The mood is ${mood}, shot as ${style}.`,
    `${opener}. Camera: ${camera} across ${setting} at ${tod}. Lighting: ${light}. Look: ${palette}, ${mood}, finished as ${style}.`,
  ];
  const out = pick(r, shapes).replace(/\s+/g, " ").trim();
  return out.length >= 40 ? out : `${out} Rich detail, cinematic depth, film-grade motion.`;
}

/* --------------------------- public: script ------------------------------- */

/** Write a full shot-by-shot script (characters + scenes) from a brief. */
export async function writeScript(briefText: string, niche: Niche, seconds: number): Promise<ScriptShape> {
  const viaLLM = await llmJSON(
    "You are DeYoung's AI screenwriter. Write a shot-by-shot script. Respond with VALID JSON ONLY matching: " +
      '{"title":string,"logline":string,"characters":[{"name":string,"look":string,"voice":string}],' +
      '"scenes":[{"id":string,"title":string,"seconds":number,"line":string,"visual":string}]}. ' +
      "Rules: 2-10 scenes, seconds sum <= total, every scene 5-12s, scene.visual = one concrete shot (camera + action + setting), scene.line = ONE spoken line <= 12 words, 1-3 characters, ids s1, s2, ...",
    `Total seconds: ${seconds}. Niche: ${niche}. Brief: ${briefText}`,
    1200
  );
  if (isShape(viaLLM)) return sanitizeShape(viaLLM, seconds);

  const r = rng();
  const st = STYLES[niche];
  const brief = analyzeBrief(briefText);
  const total = Math.min(120, Math.max(15, seconds));
  const count =
    total <= 20 ? 3 : total <= 30 ? 4 : total <= 45 ? 5 : total <= 60 ? 6 :
    total <= 75 ? 7 : total <= 90 ? 8 : total <= 105 ? 9 : 10;
  const beats = beatsFor(count);

  /* seconds: base spread, clamp 5..12, sum === total */
  let remaining = total;
  const sceneSecs: number[] = [];
  for (let i = 0; i < count; i++) {
    const left = count - i;
    let v = Math.floor(remaining / left);
    if (i === count - 1) v = remaining;
    v = Math.min(12, Math.max(5, v));
    sceneSecs.push(v);
    remaining -= v;
  }
  /* spread leftover seconds round-robin without breaking the 12s cap */
  let guard = 0;
  while (remaining > 0 && guard++ < count * 12) {
    for (let i = 0; i < count && remaining > 0; i++) {
      if (sceneSecs[i] < 12) {
        sceneSecs[i] += 1;
        remaining -= 1;
      }
    }
  }
  if (remaining > 0) sceneSecs[sceneSecs.length - 1] += remaining; // never truncates the film

  /* cast */
  const characters: ScriptShape["characters"] = [];
  for (const name of brief.cast) {
    if (characters.length >= 3) break;
    const arch = pick(r, st.castFallback);
    characters.push({ name, look: arch.look.replace(/the hero item/gi, name), voice: arch.voice });
  }
  for (const arch of shuffled(r, st.castFallback)) {
    if (characters.length >= 3) break;
    if (characters.some((c) => c.name === arch.name)) continue;
    characters.push({ ...arch });
  }

  /* scenes */
  const scenes = beats.map((beat, i) => {
    const secs = sceneSecs[i];
    const camera = pick(r, st.camera);
    const palette = pick(r, st.palette);
    const style = pick(r, st.style);
    const setting = brief.setting ? `a ${brief.setting}` : pick(r, st.settings);
    const tod = brief.timeOfDay ?? pick(r, ["golden hour", "soft morning light", "bright midday", "moody dusk", "neon-lit night"]);
    const light = coherentLight(pick(r, st.light), tod, r);
    const actor = characters[i % characters.length]?.name ?? characters[0]?.name ?? "The shot";
    const verb = pick(r, ["moves through", "discovers", "steps into", "turns toward", "reaches for", "pauses inside"]);
    const focus = brief.nouns[(i + 1) % Math.max(1, brief.nouns.length)] ?? brief.subject;
    const focusPhrase = /^(the|a|an|his|her|their|its)\s/i.test(focus) ? focus : `the ${focus}`;

    const visualBank = [
      `${capitalize(camera)} — ${actor} ${verb} ${setting} at ${tod}; ${light}, ${palette} palette, ${style}.`,
      `${capitalize(camera)} on ${actor} and ${focusPhrase}; ${setting}, ${tod}, ${light}. ${capitalize(style)}.`,
      `${capitalize(camera)}: ${actor} ${verb} ${setting} while ${focusPhrase} fills the frame — ${light}, ${palette}, ${style}.`,
    ];
    const visual = pick(r, visualBank).slice(0, 380);

    const line = fill(pick(r, LINE_TEMPLATES[beat]), brief, setting);
    const title = pick(r, BEAT_TITLES[beat]);
    return { id: `s${i + 1}`, title, seconds: secs, line, visual };
  });

  /* title — grammatical shapes built on ONE strong noun (47 QA: never
     "The Great Boy discovers"-style multi-word verb leaks) */
  const strongNouns = brief.nouns.filter((n) => n.length >= 3 && !isVerbForm(n));
  const noun1 = capitalize(strongNouns[0] ?? "Wonder");
  const noun2 = capitalize(strongNouns[1] ?? "");
  const titleShapes = [
    `${pick(r, st.titleA)} ${noun1}`.replace(/\s+/g, " "),
    noun2 ? `${noun1} & ${noun2}` : `${pick(r, st.titleA)} ${noun1}`,
    noun2 ? `The ${noun1} and the ${noun2}` : `The ${pick(r, st.titleB)}`,
  ];
  const title = pick(r, titleShapes).slice(0, 110);
  const logline = `A ${pick(r, st.mood)} ${niche} piece about ${strongNouns.slice(0, 3).map(capitalize).join(", ") || briefText.slice(0, 50)} — ${pick(r, ["told in one breath.", "shot like a memory.", "built scene by scene.", "from first spark to final frame."])}`.slice(0, 280);

  return { title, logline, characters: characters.slice(0, 3), scenes };
}

/* ------------------------------ helpers ----------------------------------- */

function capitalize(s: string): string {
  s = s.trim();
  if (!s) return s;
  return s[0].toUpperCase() + s.slice(1);
}

function isShape(v: unknown): v is ScriptShape {
  if (!v || typeof v !== "object") return false;
  const s = v as ScriptShape;
  return typeof s.title === "string" && Array.isArray(s.scenes) && s.scenes.length > 0;
}

/** Clamp an LLM-shaped script to the same guarantees as the local engine. */
function sanitizeShape(s: ScriptShape, seconds: number): ScriptShape {
  const scenes = s.scenes.slice(0, 10).map((sc, i) => ({
    id: sc.id || `s${i + 1}`,
    title: String(sc.title ?? `Scene ${i + 1}`).slice(0, 80),
    seconds: Math.min(12, Math.max(5, Math.round(Number(sc.seconds) || 5))),
    line: String(sc.line ?? "").slice(0, 200),
    visual: String(sc.visual ?? "").slice(0, 400),
  }));
  return {
    title: String(s.title).slice(0, 120) || "Untitled film",
    logline: String(s.logline ?? "").slice(0, 300),
    characters: (Array.isArray(s.characters) ? s.characters : []).slice(0, 4).map((c) => ({
      name: String(c?.name ?? "Cast").slice(0, 60),
      look: String(c?.look ?? "").slice(0, 200),
      voice: String(c?.voice ?? "").slice(0, 120),
    })),
    scenes,
  };
}
