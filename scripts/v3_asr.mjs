// DeYoung promo v3 — Step 4: ASR-verify each clip actually speaks its line (lip-sync QA).
// Usage: node scripts/v3_asr.mjs
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const BASE = "/home/z/my-project/campaign/film/v3";
const TASKS = `${BASE}/tasks-v3.json`;
const state = JSON.parse(fs.readFileSync(TASKS, "utf8"));

const KEYWORDS = {
  s1: ["one sentence", "sixty seconds", "done"],
  s2: ["sign up", "ten seconds", "three ways"],
  s3: ["already making", "video"],
  s4: ["watch it build", "scene by scene"],
  s5: ["movie arrived", "ready to post"],
  s6: ["same prompt", "every style"],
  s7: ["straight to my feed", "zero editing"],
  s8: ["deyoung", "say it", "film it"],
};

const zai = await ZAI.create();
const report = {};
let allPass = true;

for (const [id, st] of Object.entries(state)) {
  if (st.status !== "DONE" || !st.file || !fs.existsSync(st.file)) { report[id] = "NO_CLIP"; allPass = false; continue; }
  const wav = `/tmp/${id}_16k.wav`;
  try {
    execSync(`ffmpeg -y -loglevel error -i "${st.file}" -vn -ac 1 -ar 16000 -t 12 "${wav}"`, { timeout: 60000 });
    const b64 = fs.readFileSync(wav).toString("base64");
    const r = await zai.audio.asr.create({ file_base64: b64 });
    const text = (r?.text || r?.data?.text || JSON.stringify(r)).toString().toLowerCase();
    const kws = KEYWORDS[id] || [];
    const hits = kws.filter(k => text.includes(k));
    const ok = hits.length >= Math.ceil(kws.length / 2);
    report[id] = { ok, hits, transcript: text.slice(0, 110) };
    if (!ok) allPass = false;
    console.log(id, ok ? "PASS" : "MISS", "|", text.slice(0, 90));
  } catch (e) {
    report[id] = "ASR_ERR: " + e.message.slice(0, 90);
    allPass = false;
    console.log(id, "ASR_ERR", e.message.slice(0, 80));
  }
  await new Promise(r => setTimeout(r, 4000)); // pace ASR calls (throttle-aware)
}
fs.writeFileSync(`${BASE}/asr-report.json`, JSON.stringify(report, null, 2));
console.log(allPass ? "ASR_ALL_PASS" : "ASR_HAS_MISSES", JSON.stringify(Object.fromEntries(Object.entries(report).map(([k, v]) => [k, typeof v === "object" ? (v.ok ? "PASS" : "MISS") : v]))));
