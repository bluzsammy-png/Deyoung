// DeYoung film v8 — "EVERY STYLE" mixed-style commercial assets.
// The user's brief: the commercial must MIX styles like the site's slideshow —
// children's cartoon, anime, real life, stick man — with a voice-over AND
// talking characters, >= 60 seconds.
//
// Generates:
//   A) 4 talking-head diptychs in 4 DIFFERENT styles (left = mouth closed, right = open)
//   B) 5 style scenes (quad split hook + one world per style)
// Reuses: v6 mascot diptych (dee.png), v6 product scene (anywhere.png), v6 music.wav
// Output: /home/z/my-project/campaign/v8/img/*.png, /home/z/my-project/campaign/v8/voices/*.wav
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const IMG = "/home/z/my-project/campaign/v8/img";
const VOX = "/home/z/my-project/campaign/v8/voices";
fs.mkdirSync(IMG, { recursive: true });
fs.mkdirSync(VOX, { recursive: true });

const BRAND =
  "no text, no words, no letters, no logos, no captions anywhere in the image. ";

// --- talking heads: diptych, identical halves except the mouth -------------
function diptych(leftDesc, rightDesc, style) {
  return (
    style +
    "16:9 widescreen diptych with a clean vertical split exactly down the middle: " +
    "LEFT panel and RIGHT panel show the IDENTICAL character — same face, same hair, " +
    "same clothes, same pose, same camera framing, same background — " +
    "ONLY the mouth differs. " +
    "LEFT panel: " + leftDesc + " " +
    "RIGHT panel: " + rightDesc + " " +
    BRAND
  );
}

const MOUTH_CLOSED = "mouth completely shut, lips together, relaxed friendly closed-mouth smile, no teeth showing, no open mouth";
const MOUTH_OPEN = "jaw dropped, mouth stretched wide open mid-speech, big open dark mouth cavity, teeth visible, clearly talking, same relaxed happy expression";

const DIPTYCHS = [
  {
    id: "kid",
    size: "2880x832",
    style:
      "children's Saturday-morning cartoon style: thick bouncy outlines, bright cheerful primary colours, " +
      "big expressive eyes, soft rounded shapes, playful sunny energy, clean pastel room background, " +
      "modern Nigerian kid host about 10 years old with puffy hair and a yellow t-shirt with a red play-button badge. ",
    left: MOUTH_CLOSED,
    right: MOUTH_OPEN,
  },
  {
    id: "anime",
    size: "2880x832",
    style:
      "modern anime style: crisp cel shading, dramatic expressive eyes, dynamic line art, " +
      "cinematic rim light, dusk city rooftop background with warm sky, " +
      "confident young Nigerian anime hero with short silver-streaked dark hair wearing a black jacket with red trim. ",
    left: MOUTH_CLOSED,
    right: MOUTH_OPEN,
  },
  {
    id: "stick",
    size: "2880x832",
    style:
      "hand-drawn stick figure doodle style: simple round white head with two dot eyes, " +
      "body drawn as clean bold black marker lines, minimal, charming, full of personality, " +
      "on a warm paper-white background with a single red accent doodle sun in the corner. ",
    left: MOUTH_CLOSED + " (its mouth is one short marker line)",
    right: MOUTH_OPEN + " (its mouth is a big open black oval)",
  },
  {
    id: "real",
    size: "2880x832",
    style:
      "photorealistic cinematic photograph, shot on 35mm, shallow depth of field, filmic colour grade, " +
      "soft key light, dark studio background with warm red practical lights, " +
      "confident young Nigerian woman presenter in an elegant black blazer with a red pocket square, natural hair. ",
    left: MOUTH_CLOSED,
    right: MOUTH_OPEN,
  },
  {
    id: "host",
    size: "2880x832",
    style:
      "glossy modern 3D render, high-end animated feature film quality, soft global illumination, subtle subsurface skin, " +
      "friendly young Nigerian woman presenter with short coily hair, headphones resting around her neck, " +
      "wearing a black bomber jacket with a red play-button emblem, standing in a sleek dark studio with a glowing red backdrop wall. ",
    left: MOUTH_CLOSED,
    right: MOUTH_OPEN,
  },
];

// --- scenes ----------------------------------------------------------------
const SCENES = [
  {
    id: "quad",
    size: "2880x832",
    prompt:
      "16:9 widescreen image split into FOUR equal vertical panels, each panel the SAME wide shot of a red play-button " +
      "glowing over a city skyline at dusk but drawn in a DIFFERENT style: panel 1 children's Saturday-morning cartoon " +
      "style with thick outlines and bright colours, panel 2 modern anime style with cel shading, panel 3 minimal black " +
      "stick-figure doodle on white, panel 4 photorealistic cinematic film still. The styles blend smoothly at the seams. " +
      "Epic, energetic, cohesive. " + BRAND,
  },
  {
    id: "sc_kids",
    size: "2880x832",
    prompt:
      "children's Saturday-morning cartoon style, thick bouncy outlines, bright cheerful colours: a joyful Nigerian neighbourhood " +
      "street with kids running, a red play-button kite flying in a blue sky, dogs, balloons, pure happiness, wide cinematic shot. " + BRAND,
  },
  {
    id: "sc_anime",
    size: "2880x832",
    prompt:
      "modern anime style, crisp cel shading, dramatic sky: a young anime hero standing on a rooftop at golden dusk, coat flowing, " +
      "a glowing red play-button symbol shining in the clouds like a rising sun, city lights below, epic wide shot. " + BRAND,
  },
  {
    id: "sc_stick",
    size: "2880x832",
    prompt:
      "minimal hand-drawn stick-figure doodle world on warm paper-white: stick characters skateboarding, dancing and filmmaking " +
      "with a drawn clapperboard and a drawn camera, bold black marker lines, one red accent, wide playful composition. " + BRAND,
  },
  {
    id: "sc_real",
    size: "2880x832",
    prompt:
      "photorealistic cinematic film still, 35mm, golden hour: a busy Lagos street with warm light flares, a young woman filming " +
      "herself with a gimbal, shallow depth of field, rich filmic colour grade, authentic real-life energy, wide shot. " + BRAND,
  },
  {
    id: "sc_split",
    size: "2880x832",
    prompt:
      "16:9 widescreen image with a clean vertical split exactly down the middle: LEFT panel a modern anime girl with silver-streaked " +
      "dark hair on a dusk city rooftop, cel shaded, RIGHT panel a photorealistic real African actress with natural hair under warm studio " +
      "lights, 35mm film still — the two women stand back to back matching poses, one seamless poster-like composition, dramatic and stylish. " + BRAND,
  },
  {
    id: "sc_make",
    size: "2880x832",
    prompt:
      "sleek cinematic shot down a dark editing studio desk: a glowing laptop showing a red play-button interface, four pairs of hands " +
      "reaching toward the keyboard drawn in different styles — one children's cartoon hand, one anime hand, one black-marker stick hand, " +
      "one photorealistic hand — warm rim light, red practical lights, epic and fun, wide shot. " + BRAND,
  },
];

// --- voices ----------------------------------------------------------------
const LINES = [
  { id: "v01_hook",    voice: "xiaochen", speed: 0.92, text: "One story. Every style you can imagine." },
  { id: "v02_kid",     voice: "tongtong", speed: 1.06, text: "Hi! I'm your Saturday morning cartoon. Bright, bold, and I bet I already made you smile." },
  { id: "v03_anime",   voice: "jam",      speed: 0.98, text: "Straight out of an anime. Cinematic. Dramatic. Powered by one prompt." },
  { id: "v04_stick",   voice: "kazi",     speed: 1.05, text: "Stick man! Two lines, one big idea, and I still move like the wind." },
  { id: "v05_real",    voice: "luodo",    speed: 0.95, text: "And I am real life. Shot, graded and mixed like a cinema commercial." },
  { id: "v06_styles",  voice: "xiaochen", speed: 0.9,  text: "Cartoons. Anime. Stick figures. Real life. One engine speaks every visual language, and you can blend them inside a single film." },
  { id: "v06b_split",  voice: "xiaochen", speed: 0.9,  text: "Same prompt, two worlds. Switch them, or blend them. Your call." },
  { id: "v07_make",    voice: "xiaochen", speed: 0.92, text: "Type your story. Pick your style. DeYoung rolls the cameras, up to sixty seconds in one pass, on web and mobile." },
  { id: "v08_join",    voice: "xiaochen", speed: 0.9,  text: "Sign up, pick your plan, and your studio comes alive. Queue, renders and live support, all in one place." },
  { id: "v09_end",     voice: "xiaochen", speed: 0.9,  text: "DeYoung. Every style. Every story. One engine." },
];

const zai = await ZAI.create();

async function genImage(job) {
  const dst = `${IMG}/${job.id}.png`;
  if (fs.existsSync(dst) && fs.statSync(dst).size > 150000) {
    console.log("SKIP img", job.id);
    return true;
  }
  // short backoff — the runner executes in foreground bursts and resumes,
  // so burning attempts fast per burst beats long sleeps
  const waits = [15, 25, 40, 55];
  for (let attempt = 1; attempt <= waits.length; attempt++) {
    try {
      const res = await zai.images.generations.create({ prompt: job.prompt, size: job.size });
      const b64 = res?.data?.[0]?.base64 || res?.data?.[0]?.b64_json;
      if (!b64) throw new Error("no data");
      const buf = Buffer.from(b64, "base64");
      if (buf.length < 80000) throw new Error("tiny image " + buf.length);
      fs.writeFileSync(dst, buf);
      console.log("OK img", job.id, buf.length);
      return true;
    } catch (e) {
      const w = waits[attempt - 1];
      console.log(`RETRY img ${job.id}#${attempt} in ${w}s: ${(e?.message || String(e)).slice(0, 100)}`);
      await new Promise((r) => setTimeout(r, w * 1000));
    }
  }
  return false;
}

async function genVoice(L) {
  const dst = `${VOX}/${L.id}.wav`;
  if (fs.existsSync(dst) && fs.statSync(dst).size > 12000) {
    console.log("SKIP vox", L.id);
    return true;
  }
  const waits = [12, 20, 30, 45];
  for (let attempt = 1; attempt <= waits.length; attempt++) {
    try {
      const res = await zai.audio.tts.create({
        input: L.text, voice: L.voice, speed: L.speed, response_format: "wav", stream: false,
      });
      const buf = Buffer.from(new Uint8Array(await res.arrayBuffer()));
      if (buf.length < 6000) throw new Error("tiny audio " + buf.length);
      fs.writeFileSync(dst, buf);
      let d = "?";
      try {
        d = execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 "${dst}"`).toString().trim();
      } catch {}
      console.log("OK vox", L.id, L.voice, d + "s");
      return true;
    } catch (e) {
      const w = waits[attempt - 1];
      console.log(`RETRY vox ${L.id}#${attempt} in ${w}s: ${(e?.message || String(e)).slice(0, 100)}`);
      await new Promise((r) => setTimeout(r, w * 1000));
    }
  }
  return false;
}

const DEADLINE = Date.now() + 8.6 * 60 * 1000; // fit inside a 10-min tool burst
let fails = 0;
let round = 0;
while (Date.now() < DEADLINE) {
  round++;
  fails = 0;
  // voices first — TTS has its own quota and the film timing depends on it
  for (const L of LINES) if (!(await genVoice(L))) fails++;
  for (const job of DIPTYCHS) if (!(await genImage(job))) fails++;
  for (const job of SCENES) if (!(await genImage(job))) fails++;
  if (fails === 0) break;
  console.log(`-- round ${round} incomplete (${fails} pending), cycling --`);
  await new Promise((r) => setTimeout(r, 20000));
}

console.log(fails === 0 ? "ASSETS_DONE" : `ASSETS_INCOMPLETE fails=${fails}`);
if (fails > 0) process.exit(1);
