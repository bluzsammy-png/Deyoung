// ASR-check a scene's generated audio: does it speak the intended line?
// Usage: node scripts/asr_scene.mjs s02
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const id = process.argv[2] || "s02";
const src = `/home/z/my-project/campaign/social/frames/${id}_audio.mp4`;
const wav = `/tmp/${id}_asr.wav`;

execSync(`ffmpeg -y -i "${src}" -t 10 -vn -ac 1 -ar 16000 "${wav}"`, { stdio: "ignore" });
const b64 = fs.readFileSync(wav).toString("base64");

const zai = await ZAI.create();
const res = await zai.audio.asr.create({ file_base64: b64, stream: false });
console.log("ASR:", JSON.stringify(res).slice(0, 600));
