// DeYoung promo v3 — Step 2: submit all 8 speaking-character scenes (i2v + native audio).
// Usage: node scripts/v3_submit.mjs [s1 s2 ...]   (default: all not-yet-submitted)
// State: campaign/film/v3/tasks-v3.json
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const BASE = "/home/z/my-project/campaign/film/v3";
const TASKS = `${BASE}/tasks-v3.json`;
fs.mkdirSync(`${BASE}/clips`, { recursive: true });

const b64 = (p) => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;

// Shared dialogue-craft: short lines, explicit "speaks clearly", sync language, no music/text.
const SYNC = `She looks straight into the lens and speaks clearly in English with natural mouth movement perfectly synchronized to her words. Clear audible voice, studio quality sound, no background music, no subtitles, no text on screen`;
const SYNC_M = `He looks straight into the lens and speaks clearly in English with natural mouth movement perfectly synchronized to his words. Clear audible voice, studio quality sound, no background music, no subtitles, no text on screen`;

const SCENES = {
  s1: { line: "One sentence. Sixty seconds. Done.", dur: 10, trim: 7,
    prompt: `Bright modern 2D cartoon animation style, clean bold outlines, flat vivid colors. A cheerful young man with round glasses sits at a small desk in a sunny cartoon room; his laptop suddenly erupts with a burst of colorful light and a finished movie clip pops out of the screen like a firework. He catches it, turns to the camera with a huge grin and speaks clearly to camera with natural lip sync: "One sentence. Sixty seconds. Done." Energetic, snappy animation, slow push-in on his face as he talks. No on-screen text, no subtitles, no captions.` },
  s2: { line: "Sign up? Ten seconds. Three ways.", dur: 10, trim: 7,
    prompt: `Minimal black stick-figure animation on a clean white background, playful bouncy motion. An energetic stick figure sprints toward three glowing doors with simple circle, apple and envelope icons, dives through the middle one and lands inside a giant smartphone frame. He pops up, taps an imaginary wristwatch and speaks clearly with natural lip sync: "Sign up? Ten seconds. Three ways." Fast comedic timing. No other on-screen text, no subtitles, no captions.` },
  s3: { line: "It's already making my video.", dur: 10, trim: 7,
    prompt: `Ultra realistic cinematic live action. A stylish young woman relaxes on a cozy sofa in warm golden window light, holding a smartphone that glows with a video editing app, progress ring filling up. She raises her eyebrows, delighted, and turns the phone slightly toward the camera. ${SYNC}: "It's already making my video." Genuine excited smile, shallow depth of field, filmic grade, gentle push-in` },
  s4: { line: "Watch it build — scene by scene.", dur: 10, trim: 7,
    prompt: `Vibrant cinematic anime style, dynamic lighting. A confident girl director wearing big headphones stands as holographic screens orbit around her, each screen showing a video scene assembling itself piece by piece. She sweeps her hand, the screens swirl, then she points at the camera and speaks clearly with natural lip sync: "Watch it build — scene by scene." Energetic anime camera flourish. No on-screen text, no subtitles, no captions.` },
  s5: { line: "My movie arrived. Ready to post.", dur: 10, trim: 7,
    prompt: `Soft crayon-textured children's cartoon style, warm pastel colors, rounded shapes. A cute round little robot waddles in carrying a big gift box with a glowing play button on the lid. The box bursts open with sparkles revealing a tiny glowing film. The robot looks up at the camera and speaks in a friendly childlike voice with natural lip sync: "My movie arrived. Ready to post." Charming, wholesome, gentle bounce animation. No on-screen text, no subtitles, no captions.` },
  s6: { line: "Same prompt. Every style you can imagine.", dur: 10, trim: 7,
    prompt: `Split-style cinematic shot of two creators side by side in a film studio with red practical lights glowing through haze: the left creator is a vibrant anime girl with purple hair, the right creator is photorealistic wearing a denim jacket. They talk to each other then both glance to camera. The anime girl says clearly in English with perfectly synchronized mouth movement: "Same prompt." Then the photorealistic man replies clearly in English with perfectly synchronized mouth movement: "Every style you can imagine." Clear studio-quality voices, no background music, no subtitles, slow confident orbit around them` },
  s7: { line: "Straight to my feed. Zero editing.", dur: 10, trim: 8,
    prompt: `Photorealistic cinematic handheld shot, golden hour city street. A young man walks toward camera holding up his smartphone; the screen shows a finished vertical video playing in a sleek dark player interface, its glow lighting his face. He glances at the lens with a confident smile and speaks naturally with clear lip sync: "Straight to my feed. Zero editing." Warm backlight, soft lens flare, real-world texture. No on-screen text, no subtitles, no captions.` },
  s8: { line: "Deyoung. If you can say it, you can film it.", dur: 10, trim: 8,
    prompt: `Cinematic ensemble finale on a dark stage with dramatic red accent lighting and light haze. Five characters stand in a lineup side by side: a flat cartoon guy with round glasses, a black stick figure, a photorealistic young woman, an anime girl with headphones, and a cute crayon-style robot. One by one they step forward and wave, then all five point at the camera together and speak in unison with natural lip sync: "Deyoung. If you can say it, you can film it." Epic slow push-out, red rim light, filmic grade. No on-screen text, no subtitles, no captions.` },
};

const wanted = process.argv.slice(2);
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
const queue = wanted.length ? wanted : Object.keys(SCENES).filter(id => !state[id]?.task_id);

const zai = await ZAI.create();
for (const id of queue) {
  const sc = SCENES[id];
  const img = `${BASE}/chars/${charImg(id)}.png`;
  if (!fs.existsSync(img)) { console.log("MISSING FRAME", id, img); continue; }
  for (let a = 1; a <= 5; a++) {
    try {
      const t = await zai.video.generations.create({
        prompt: sc.prompt, quality: "quality", with_audio: true,
        size: "1920x1080", fps: 30, duration: sc.dur,
        image_url: b64(img),
      });
      state[id] = { task_id: t.id, status: t.task_status || "SUBMITTED", trim: sc.trim, line: sc.line, submitted_at: new Date().toISOString() };
      console.log("submitted", id, t.id, t.task_status);
      break;
    } catch (e) {
      const is429 = /429/.test(e.message);
      state[id] = { ...(state[id] || {}), status: is429 ? "RATE_LIMITED" : "SUBMIT_ERR", err: e.message.slice(0, 160) };
      console.log("ERR", id, `attempt ${a}`, e.message.slice(0, 120));
      if (a === 5) break;
      await new Promise(r => setTimeout(r, is429 ? 90000 : 20000));
    }
  }
  fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
  await new Promise(r => setTimeout(r, 12000)); // pace submissions
}
console.log("SUBMIT_DONE", JSON.stringify(Object.fromEntries(queue.map(k => [k, state[k]?.status || "none"]))));

function charImg(id) {
  return { s1: "c1", s2: "c2", s3: "c3", s4: "c4", s5: "c5", s6: "c6", s7: "c7", s8: "c8" }[id] || id;
}
