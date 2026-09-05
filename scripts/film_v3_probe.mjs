// Probe: dialogue-adherence test — does the model speak the EXACT line with strict prompting?
// Usage: node scripts/film_v3_probe.mjs
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const LINE = process.argv[2] || "One sentence. Sixty seconds. Done.";
const MODEL = process.argv[3] || undefined;

const prompt = [
  `Audio: the only spoken words in the entire video are exactly this sentence, spoken aloud in clear English: "${LINE}"`,
  `The character says this exact sentence and nothing else. No other dialogue. No background voices. No music.`,
  `Visual: close-up portrait, bright modern 2D cartoon style, a cheerful man with round glasses in a sunny room, looking straight into the camera, mouth moving in natural lip sync as he speaks that exact sentence, slow push-in.`,
  `Absolutely no text, no letters, no numbers, no captions, no subtitles, no writing anywhere in the image.`,
].join(" ");

const zai = await ZAI.create();
const body = { prompt, quality: "quality", with_audio: true, size: "1920x1080", fps: 30, duration: 5 };
if (MODEL) body.model = MODEL;
console.log("model:", MODEL || "(default)");
let r = null;
for (let a = 1; a <= 4 && !r; a++) {
  try { r = await zai.video.generations.create(body); }
  catch (e) {
    if (!String(e?.message).includes("429")) { console.log("SUBMIT ERR:", String(e?.message).slice(0, 120)); process.exit(1); }
    console.log(`429 — backing off (attempt ${a}/4), sleeping 170s`);
    await new Promise(res => setTimeout(res, 170000));
  }
}
if (!r) { console.log("GAVE_UP_429"); process.exit(1); }
console.log("task:", r.id, r.task_status);

// poll up to 8 min
const start = Date.now();
let url = null;
while (Date.now() - start < 8 * 60 * 1000) {
  await new Promise(res => setTimeout(res, 15000));
  const q = await zai.async.result.query(r.id);
  const st = q.task_status || q.status;
  console.log("poll:", st);
  if (st === "SUCCESS") { url = q.video_result?.[0]?.url || q.video_url || q.url; break; }
  if (st === "FAIL") { console.log("GEN FAILED"); process.exit(1); }
}
if (!url) { console.log("TIMEOUT"); process.exit(1); }
const res = await fetch(url);
fs.writeFileSync("/tmp/probe.mp4", Buffer.from(await res.arrayBuffer()));
console.log("saved /tmp/probe.mp4");

execSync(`ffmpeg -y -v error -i /tmp/probe.mp4 -vn -ac 1 -ar 16000 /tmp/probe.wav`);
const b64 = fs.readFileSync("/tmp/probe.wav").toString("base64");
const asr = await zai.audio.asr.create({ file_base64: b64, stream: false });
const text = asr?.text || JSON.stringify(asr);
console.log("EXPECTED:", LINE);
console.log("GOT     :", String(text).slice(0, 200));
