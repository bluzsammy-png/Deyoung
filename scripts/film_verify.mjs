// DeYoung promo v3 — ASR quality gate: verify each DONE clip actually speaks its
// scripted line; un-verify failures so film_run.mjs resubmits them.
// Usage: node scripts/film_verify.mjs
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const BASE = "/home/z/my-project/campaign/film/v3";
const TASKS = `${BASE}/tasks-v3.json`;

const KEYWORDS = {
  s3: ["already making", "my video", "making my"],
  s4: ["watch it build", "scene by scene", "build"],
  s5: ["movie arrived", "ready to post"],
  s6: ["same prompt", "every style"],
  s7: ["straight to my feed", "zero editing", "my feed"],
  s8: ["say it", "film it"],
};

const state = JSON.parse(fs.readFileSync(TASKS, "utf8"));
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
const zai = await ZAI.create();

let dirty = false;
for (const [id, kws] of Object.entries(KEYWORDS)) {
  const st = state[id];
  if (!st || st.status !== "DONE" || !st.file || st.verified) continue;
  if (!fs.existsSync(st.file)) continue;
  const wav = `/tmp/${id}_gate.wav`;
  try {
    execSync(`ffmpeg -y -loglevel error -i "${st.file}" -vn -ac 1 -ar 16000 -t 12 "${wav}"`, { timeout: 60000 });
    const r = await zai.audio.asr.create({ file_base64: fs.readFileSync(wav).toString("base64") });
    const text = (r?.text || "").toString().toLowerCase();
    const hits = kws.filter((k) => text.includes(k));
    const ok = hits.length >= Math.ceil(kws.length / 2) || (kws.length <= 2 && hits.length >= 1);
    console.log(id, ok ? "PASS" : "MISS", "|", text.slice(0, 90));
    if (ok) { st.verified = true; st.transcript = text.slice(0, 200); dirty = true; }
    else {
      st.status = "RETRY"; st.task_id = null; delete st.file;
      st.verify_fail = text.slice(0, 200); dirty = true;
    }
  } catch (e) {
    console.log(id, "ASR_ERR", e.message.slice(0, 80));
  }
  await new Promise((r) => setTimeout(r, 3000));
}
save();
console.log("GATE_END", JSON.stringify(Object.fromEntries(Object.keys(KEYWORDS).map((k) => [k, state[k]?.verified ? "PASS" : state[k]?.status || "-"]))));
