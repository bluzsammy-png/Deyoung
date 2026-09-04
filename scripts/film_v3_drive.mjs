// DeYoung film v3 driver — resumable: submit (429-aware) + poll + download.
// Usage: node scripts/film_v3_drive.mjs [maxSeconds]
// State: campaign/tasks-v3.json   Clips: campaign/film/v3/<id>.mp4
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import path from "path";

const TASKS = "/home/z/my-project/campaign/tasks-v3.json";
const OUT = "/home/z/my-project/campaign/film/v3";
const maxMs = (Number(process.argv[2]) || 500) * 1000;
const start = Date.now();

const SCENES = [
  { id: "v3s1", dur: 10 },
  { id: "v3s2", dur: 5 },
  { id: "v3s3", dur: 10 },
  { id: "v3s4", dur: 5 },
  { id: "v3s5", dur: 5 },
  { id: "v3s6", dur: 10 },
  { id: "v3s7", dur: 5 },
  { id: "v3s8", dur: 10 },
];

fs.mkdirSync(OUT, { recursive: true });
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const zai = await ZAI.create();

// Merge SCENES meta (durations) into state if missing
for (const sc of SCENES) if (!state[sc.id]) state[sc.id] = { dur: sc.dur, status: "NEW" };
save();

let lastSubmitAt = 0;

async function submitNext() {
  const sc = SCENES.find(s => !state[s.id].task_id || state[s.id].status === "FAIL");
  if (!sc) return false;
  const since = Date.now() - lastSubmitAt;
  if (since < 20000) await sleep(20000 - since); // spacing
  for (let a = 1; a <= 3; a++) {
    try {
      lastSubmitAt = Date.now();
      const r = await zai.video.generations.create({
        prompt: PROMPTS[sc.id],
        quality: "quality",
        with_audio: true,
        size: "1920x1080",
        fps: 30,
        duration: sc.dur,
      });
      state[sc.id] = { ...state[sc.id], task_id: r.id, status: r.task_status, submitted_at: Date.now() };
      save();
      console.log(`[${sc.id}] submitted -> ${r.id} (${r.task_status})`);
      return true;
    } catch (e) {
      const msg = (e?.message || String(e));
      console.log(`[${sc.id}] submit attempt ${a} failed: ${msg.slice(0, 120)}`);
      if (msg.includes("429")) { await sleep(150000); } else { await sleep(8000); }
    }
  }
  return false;
}

async function pollAndDownload() {
  let active = 0;
  for (const sc of SCENES) {
    const st = state[sc.id];
    if (st.status === "DONE") continue;
    if (!st.task_id) continue; // not submitted — not active
    try {
      const r = await zai.async.result.query(st.task_id);
      const status = r.task_status || r.status;
      if (status === "SUCCESS") {
        const url = r.video_result?.[0]?.url || r.video_url || r.url || r.video;
        if (!url) { console.log(`[${sc.id}] SUCCESS but no url`); st.status = "FAIL"; save(); active++; continue; }
        const file = path.join(OUT, `${sc.id}.mp4`);
        const res = await fetch(url);
        if (!res.ok) { console.log(`[${sc.id}] download HTTP ${res.status}`); active++; continue; }
        const buf = Buffer.from(await res.arrayBuffer());
        fs.writeFileSync(file, buf);
        st.status = "DONE"; st.file = file; st.bytes = buf.length; st.url_expires = "24h";
        save();
        console.log(`[${sc.id}] DONE ${(buf.length / 1e6).toFixed(1)}MB`);
      } else if (status === "FAIL") {
        st.status = "FAIL"; delete st.task_id; save();
        console.log(`[${sc.id}] generation FAILED (will resubmit)`);
      } else {
        // PROCESSING — stall guard: 25 min max per scene
        if (st.submitted_at && Date.now() - st.submitted_at > 25 * 60 * 1000) {
          console.log(`[${sc.id}] STALL >25min — marking FAIL for resubmit`);
          st.status = "FAIL"; delete st.task_id; save();
        }
        active++;
      }
    } catch (e) {
      console.log(`[${sc.id}] poll error: ${(e?.message || String(e)).slice(0, 100)}`);
      active++;
    }
    await sleep(1200);
  }
  return active;
}

// Embedded prompts (same as submit script) so the driver is self-sufficient
const PROMPTS = JSON.parse(fs.readFileSync("/home/z/my-project/scripts/film_v3_prompts.json", "utf8"));

let loop = 0;
while (Date.now() - start < maxMs) {
  loop++;
  const active = await pollAndDownload();
  const done = SCENES.filter(s => state[s.id].status === "DONE").length;
  console.log(`loop ${loop}: done ${done}/8, active ${active}`);
  if (done === 8) { console.log("ALL_SCENES_DONE"); break; }
  if (active === 0) { await submitNext(); }
  await sleep(15000);
}
console.log("DRIVER_EXIT", JSON.stringify(Object.fromEntries(SCENES.map(s => [s.id, state[s.id].status]))));
