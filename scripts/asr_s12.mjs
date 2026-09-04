import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const zai = await ZAI.create();
const MASTER = "/home/z/my-project/public/video/deyoung-film-web.mp4";
const PARTS = { s1: [0, 7], s2: [7, 5] };
for (const [id, [ss, t]] of Object.entries(PARTS)) {
  try {
    const wav = `/tmp/${id}_full.wav`;
    execSync(`ffmpeg -y -loglevel error -ss ${ss} -t ${t} -i ${MASTER} -vn -ac 1 -ar 16000 ${wav}`);
    const r = await zai.audio.asr.create({ file_base64: fs.readFileSync(wav).toString("base64") });
    console.log(`${id}:`, (r?.text || "(empty)").toString().slice(0, 140));
  } catch (e) {
    console.log(`${id}_ERR:`, e.message.slice(0, 90));
  }
  await new Promise((r) => setTimeout(r, 3000));
}
