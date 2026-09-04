// DeYoung promo v3 — Step 3: poll tasks, download finished clips.
// Usage: node scripts/v3_poll.mjs [maxSeconds=540]
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const BASE = "/home/z/my-project/campaign/film/v3";
const TASKS = `${BASE}/tasks-v3.json`;
const CLIPS = `${BASE}/clips`;
fs.mkdirSync(CLIPS, { recursive: true });

const maxMs = (Number(process.argv[2]) || 540) * 1000;
const start = Date.now();
const zai = await ZAI.create();
const state = JSON.parse(fs.readFileSync(TASKS, "utf8"));
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));

while (Date.now() - start < maxMs) {
  let pending = 0;
  for (const id of Object.keys(state)) {
    const st = state[id];
    if (!st?.task_id || st.status === "DONE" || st.status === "FAIL") continue;
    pending++;
    try {
      const r = await zai.async.result.query(st.task_id);
      const status = r.task_status || r.status;
      if (status === "SUCCESS") {
        const urls = r.video_result?.map(v => v.url) || (r.video_url ? [r.video_url] : (r.url ? [r.url] : []));
        if (!urls.length) { console.log("SUCCESS no url", id, JSON.stringify(r).slice(0, 150)); continue; }
        const out = `${CLIPS}/${id}.mp4`;
        execSync(`curl -sL --max-time 220 -o "${out}" "${urls[0]}"`, { timeout: 240000 });
        const size = fs.existsSync(out) ? fs.statSync(out).size : 0;
        if (size < 200000) { console.log("too small", id, size); continue; }
        console.log("downloaded", id, (size / 1e6).toFixed(1) + "MB");
        st.status = "DONE"; st.file = out; st.bytes = size; save();
      } else if (status === "FAIL") {
        console.log("FAILED", id, JSON.stringify(r).slice(0, 150));
        st.status = "FAIL"; save();
      } else {
        console.log(new Date().toISOString().slice(11, 19), id, status);
        pending += 0; // still processing
      }
    } catch (e) {
      console.log("poll err", id, e.message.slice(0, 90));
    }
  }
  const done = Object.values(state).filter(s => s.status === "DONE").length;
  const failed = Object.values(state).filter(s => s.status === "FAIL").length;
  if (done + failed >= Object.keys(state).length && Object.keys(state).length >= 8) { console.log("ALL_SETTLED"); break; }
  if (pending === 0 && done + failed >= Object.keys(state).length) { console.log("ALL_SETTLED"); break; }
  await new Promise(r => setTimeout(r, 30000));
}
save();
const summary = Object.fromEntries(Object.entries(state).map(([k, v]) => [k, v.status || "none"]));
console.log("POLL_END", JSON.stringify(summary));
