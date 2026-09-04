// QA a v3 scene clip: ffprobe facts + 3 frames + ASR transcript check.
// Usage: node scripts/film_v3_qa.mjs v3s1
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const id = process.argv[2];
const file = `/home/z/my-project/campaign/film/v3/${id}.mp4`;
const KEYWORDS = {
  v3s1: ["sentence", "sixty", "seconds", "done"],
  v3s2: ["sign", "up", "ten", "seconds", "three", "ways"],
  v3s3: ["already", "making", "video"],
  v3s4: ["watch", "build", "scene"],
  v3s5: ["movie", "arrived", "ready", "post"],
  v3s6: ["same", "prompt", "style", "imagine"],
  v3s7: ["straight", "feed", "zero", "editing"],
  v3s8: ["say", "film"],
};

if (!fs.existsSync(file)) { console.log("MISSING", file); process.exit(1); }

const probe = execSync(
  `ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height,r_frame_rate -of json "${file}"`
).toString();
const j = JSON.parse(probe);
const dur = parseFloat(j.format?.duration || "0");
console.log(`== ${id}: ${dur.toFixed(2)}s, ${(j.format?.size / 1e6).toFixed(1)}MB, streams: ${j.stream?.map(s => `${s.codec_type}/${s.codec_name}`).join(" + ")}`);

// frames for visual check
for (const t of [0.5, dur / 2, dur - 0.5]) {
  execSync(`ffmpeg -y -v error -ss ${t.toFixed(2)} -i "${file}" -frames:v 1 /tmp/${id}_f${t.toFixed(1)}.jpg`);
}
console.log("frames: /tmp/" + id + "_f*.jpg");

// ASR the spoken audio
execSync(`ffmpeg -y -v error -i "${file}" -vn -ac 1 -ar 16000 /tmp/${id}.wav`);
const b64 = fs.readFileSync(`/tmp/${id}.wav`).toString("base64");
const zai = await ZAI.create();
const asr = await zai.audio.asr.create({ file_base64: b64, stream: false });
const text = (asr?.text || asr?.data?.text || JSON.stringify(asr)).slice(0, 200);
console.log("TRANSCRIPT:", text);
const kws = KEYWORDS[id] || [];
const hits = kws.filter(k => text.toLowerCase().includes(k));
console.log(`KEYWORDS: ${hits.length}/${kws.length} [${kws.join(" ")}] -> ${hits.join(",")}`);
console.log(hits.length >= Math.ceil(kws.length / 2) ? "VERDICT: PASS" : "VERDICT: CHECK_NEEDED");
