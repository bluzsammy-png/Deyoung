// Patient sequential submitter — one scene at a time, 60s backoff on 429.
// Usage: node scripts/v3_submit2.mjs   (rerun until all scenes submitted)
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const TASKS = "/home/z/my-project/campaign/v3/tasks-v3.json";
const C = "/home/z/my-project/campaign/v3/chars";
const b64 = (p) => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;

const SAY = (line, extra) =>
  `The character looks straight into the lens and speaks clearly in English: "${line}" Mouth movement perfectly synchronized to the words, natural facial performance. ${extra} Clear audible voice with studio quality sound, no background music, no subtitles, no text on screen`;

const SCENES = {
  s01: { dur: 10, image: `${C}/momo.png`,
    prompt: SAY("One sentence. Sixty seconds. Done.",
      `He bursts into joyful laughter and throws both arms up as the film frames erupting from his laptop screen swirl faster and brighter around him. Flat 2D cartoon animation style, bold outlines, vivid colors, smooth lively character animation, gentle zoom-in, deep charcoal background with red and yellow accents.`) },
  s02: { dur: 5, image: `${C}/stick.png`,
    prompt: SAY("Sign up? Ten seconds. Three ways.",
      `The stick figure dashes through the glowing doorways one after another, each door bursting open with a puff of energy as he passes, playful bouncy motion. Minimalist stick figure animation, thick black ink lines on clean white background, snappy energetic movement like a viral whiteboard cartoon.`) },
  s03: { dur: 10, image: `${C}/maya.png`,
    prompt: SAY("It's already making my video.",
      `She looks up from the phone she is holding, turns her face to the lens and says the line with a warm confident smile, then glances back down and taps the screen once. Ultra realistic cinematic live action, shallow depth of field, warm evening living room light with crimson practical lamps, gentle slow push-in, filmic grade.`) },
  s04: { dur: 10, image: `${C}/yuki.png`,
    prompt: SAY("Watch it build — scene by scene.",
      `She gestures like a conductor and the three holographic screens around her flare alive one by one, each lighting up with a new glowing video frame while her jacket flutters. Modern anime style, crisp cel shading, dramatic red and cyan rim light, dark studio, dynamic camera orbit, cinematic energy.`) },
  s05: { dur: 5, image: `${C}/bea.png`,
    prompt: SAY("My movie arrived! Ready to post.",
      `The friendly round robot hands her the glowing gift box, she hugs it with sparkling excited eyes and bounces with joy, rainbow shimmering behind. Cute children's picture-book cartoon style, soft crayon textures, rounded shapes, bright pastel colors with red accents, cheerful bouncy animation.`) },
  s06: { dur: 5, image: `${C}/duo.png`,
    prompt: `Split screen: on the left half the anime girl looks into the lens and speaks clearly in English: "Same prompt." On the right half the realistic woman then answers clearly in English: "Every style you can imagine." Both with mouth movement perfectly synchronized to their words, both smirking with confidence. Clean vertical red divider line, anime cel shading on the left, ultra realistic cinematic photography on the right, matching poses, subtle camera push-in on both halves, clear studio quality voices, no background music, no subtitles, no text on screen.` },
  s07: { dur: 10, image: `${C}/felix.png`,
    prompt: SAY("Straight to my feed. Zero editing.",
      `He watches the video playing on the phone he holds up, the screen glow painting his amazed face, then looks up to the lens laughing with delight and tilts the phone toward the viewer. Ultra realistic cinematic live action, night bedroom lit by warm fairy lights, shallow depth of field, gentle push-in, filmic grade.`) },
  s08: { dur: 10, image: `${C}/lineup.png`,
    prompt: SAY("If you can say it — you can film it.",
      `All five characters stand together facing the viewer, each in their own art style — flat cartoon, stick figure, ultra realistic, anime, and children's picture book — and speak the line in unison with synchronized mouth movement, then all five nod and smile at the camera. Dark stage with soft red spotlights, crossover ensemble composition, each character animated in their native style, cinematic staging, confident celebratory energy.`) },
};

const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
const deadline = Date.now() + 7.6 * 60 * 1000; // keep trying for ~7.6 min per run
const zai = await ZAI.create();

while (Date.now() < deadline) {
  const pending = Object.keys(SCENES).filter((id) => !state[id]?.task_id);
  if (!pending.length) { console.log("ALL_SUBMITTED"); process.exit(0); }
  const id = pending[0];
  const sc = SCENES[id];
  try {
    const t = await zai.video.generations.create({
      prompt: sc.prompt, quality: "quality", with_audio: true, watermark_enabled: false,
      size: "1920x1080", fps: 30, duration: sc.dur, image_url: b64(sc.image),
    });
    state[id] = { task_id: t.id, status: t.task_status || "SUBMITTED", dur: sc.dur, submitted_at: new Date().toISOString() };
    fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
    console.log("SUBMITTED", id, t.id, t.task_status);
    await new Promise((r) => setTimeout(r, 5000)); // small gap, next scene
  } catch (e) {
    const m = String(e.message);
    const wait = /429/.test(m) ? 90000 : 15000;
    console.log(new Date().toISOString().slice(11, 19), `ERR ${id}:`, m.slice(0, 90), `-> sleep ${wait / 1000}s`);
    await new Promise((r) => setTimeout(r, wait));
  }
}
const left = Object.keys(SCENES).filter((id) => !state[id]?.task_id);
console.log(left.length ? `TIME_UP ${left.length} pending: ${left.join(",")}` : "ALL_SUBMITTED");
