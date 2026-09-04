// Probe: read path (old task) + minimal create, to diagnose 429 scope.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
const zai = await ZAI.create();
try {
  const old = JSON.parse(fs.readFileSync("/home/z/my-project/campaign/tasks-audio.json", "utf8"));
  const first = Object.entries(old)[0];
  if (first) {
    const r = await zai.async.result.query(first[1].task_id);
    console.log("READ_PATH_OK old task", first[0], "->", r.task_status);
  } else console.log("no old tasks");
} catch (e) { console.log("READ_PATH_ERR", String(e.message).slice(0, 100)); }
try {
  const t = await zai.video.generations.create({ prompt: "A red ribbon flowing in slow motion on black background", quality: "speed", with_audio: false, size: "1920x1080", fps: 30, duration: 5 });
  console.log("CREATE_PROBE_OK", t.id, t.task_status);
} catch (e) { console.log("CREATE_PROBE_ERR", String(e.message).slice(0, 120)); }
