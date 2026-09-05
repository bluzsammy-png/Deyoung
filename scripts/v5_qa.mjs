import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const MASTER = "/home/z/my-project/public/video/deyoung-film-web.mp4";
const CHECKS = {
  s1: [0.5, 6.5, ["one sentence", "sixty seconds", "done"]],
  s2: [7.5, 4.5, ["sign up", "ten seconds", "three ways"]],
  s3: [12.5, 6.5, ["already making", "my video"]],
  s4: [19.5, 6.5, ["watch it build", "scene by scene"]],
  s5: [26.5, 6.5, ["movie arrived", "ready to post"]],
  s6: [33.5, 6.5, ["same prompt", "every style"]],
  s7: [40.5, 7.5, ["straight to my feed", "zero editing"]],
  s8: [48.5, 7.5, ["say it", "film it"]],
};

const zai = await ZAI.create();
let pass = 0, fail = 0;
for (const [id, [ss, t, kws]] of Object.entries(CHECKS)) {
  const wav = `/tmp/mq_${id}.wav`;
  try {
    execSync(`ffmpeg -y -loglevel error -ss ${ss} -t ${t} -i ${MASTER} -vn -ac 1 -ar 16000 ${wav}`);
    const r = await zai.audio.asr.create({ file_base64: fs.readFileSync(wav).toString("base64") });
    const text = (r?.text || "").toString().toLowerCase();
    const hits = kws.filter((k) => text.includes(k));
    const ok = hits.length >= Math.ceil(kws.length / 2);
    ok ? pass++ : fail++;
    console.log(`${id} ${ok ? "PASS" : "MISS"} (${hits.join("/")}) | ${text.slice(0, 80)}`);
  } catch (e) {
    fail++;
    console.log(`${id} ASR_ERR ${e.message.slice(0, 70)}`);
  }
  await new Promise((r) => setTimeout(r, 2500));
}
console.log(`QA_RESULT pass=${pass} fail=${fail}`);
