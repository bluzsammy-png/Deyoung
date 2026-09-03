// Poll z-ai audio-scene tasks; download finished clips.
// Usage: node scripts/film_poll_audio.mjs [maxSeconds]
// State: campaign/tasks-audio.json
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const TASKS = "/home/z/my-project/campaign/tasks-audio.json";
const FRAMES = "/home/z/my-project/campaign/social/frames";
const QUEUE = ["s02", "s03", "s06"];

const maxMs = (Number(process.argv[2]) || 90) * 1000;
const start = Date.now();
const zai = await ZAI.create();
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));

while (Date.now() - start < maxMs) {
  let allDone = true;
  for (const id of QUEUE) {
    const st = state[id];
    if (st?.status === "DONE") continue;
    allDone = false;
    if (!st?.task_id) continue; // not submitted yet
    try {
      const r = await zai.async.result.query(st.task_id);
      const status = r.task_status || r.status;
      if (status === "SUCCESS") {
        const urls = r.video_result?.map(v => v.url) || (r.video_url ? [r.video_url] : (r.url ? [r.url] : []));
        if (!urls.length) {
          console.log("SUCCESS but no url for", id, JSON.stringify(r).slice(0, 200));
          continue;
        }
        execSync(`curl -sL --max-time 220 -o "${FRAMES}/${id}_audio.mp4" "${urls[0]}"`, { timeout: 240000 });
        const size = fs.statSync(`${FRAMES}/${id}_audio.mp4`).size;
        if (size < 50000) { console.log("download too small for", id, size); continue; }
        console.log("downloaded", id, size, "bytes");
        st.status = "DONE";
        st.file = `${id}_audio.mp4`;
        save();
      } else if (status === "FAIL") {
        console.log("FAILED", id, JSON.stringify(r).slice(0, 200));
        st.status = "FAIL";
        save();
      } else {
        console.log(new Date().toISOString().slice(11, 19), id, status);
      }
    } catch (e) {
      console.log("poll err", id, e.message.slice(0, 100));
    }
  }
  if (allDone) { console.log("ALL_DONE"); break; }
  await new Promise(r => setTimeout(r, 25000));
}
save();
console.log("POLL_END", JSON.stringify(Object.fromEntries(QUEUE.map(id => [id, state[id]?.status || "none"]))));
