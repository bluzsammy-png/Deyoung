// Poll video tasks, download finished, keep <=2 active by submitting pending scenes.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const TASKS = "/home/z/my-project/campaign/tasks.json";
const FRAMES = "/home/z/my-project/campaign/social/frames";
const S = "/home/z/my-project/campaign/social";
const RUN_MS = parseInt(process.argv[2] || "110000", 10);
const b64 = p => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;

const SCENES = {
  s02: { dur: 10, quality: "quality", image: `${S}/amara.png`, prompt: "The woman looks straight into the lens and speaks passionately to camera, natural mouth movement as she talks, subtle confident hand gesture, breathing life into the frame, cinematic shallow depth of field, soft crimson rim light, gentle slow push-in, filmic grade, no text" },
  s04: { dur: 5, quality: "speed", prompt: "Cinematic macro shot of hands typing a story prompt on a glowing smartphone, the screen lights up with a warm red interface, reflections of the screen glow on the fingers, dark desk, shallow depth of field, filmic red and black grade, no readable text" },
  s05: { dur: 5, quality: "speed", prompt: "Cinematic shot of glowing particles and ribbons of red light streaming out of a dark smartphone screen and swirling into the air like a forming galaxy, volumetric light, black studio void, elegant and magical, filmic grade, no text" },
  s06: { dur: 10, quality: "quality", image: `${S}/duo.png`, prompt: "The two creators talk to each other and glance to camera with smiles, natural conversation mouth movement, relaxed confident body language, crimson practical lights glowing through haze behind them, slow cinematic orbit, filmic grade, no text" },
  s07: { dur: 5, quality: "speed", prompt: "Cinematic desk scene at night, a smartphone and a laptop side by side both playing a vivid red-toned film, screen glow lighting the dark room, soft bokeh, slow dolly across the desk, filmic red and black grade, no readable text" },
  s08: { dur: 5, quality: "speed", image: `${S}/silk.png`, prompt: "The crimson silk fabric flows and ripples slowly in slow motion, elegant folds catching the light, deep black shadows behind, luxurious cinematic mood, subtle drift of the camera, no text" },
};

const zai = await ZAI.create();
const load = () => JSON.parse(fs.readFileSync(TASKS, "utf8"));
const save = s => fs.writeFileSync(TASKS, JSON.stringify(s, null, 2));
const t0 = Date.now();

while (Date.now() - t0 < RUN_MS) {
  const st = load();
  const ids = Object.keys(st).filter(k => st[k].task_id && !["SUCCESS", "FAIL", "DOWNLOADED"].includes(st[k].status));
  let active = 0;
  for (const id of ids) {
    try {
      const r = await zai.async.result.query(st[id].task_id);
      st[id].remote = r.task_status;
      if (r.task_status === "SUCCESS") {
        const url = r.video_result?.[0]?.url || r.video_url || r.url;
        if (url) {
          const res = await fetch(url);
          if (res.ok) {
            fs.writeFileSync(`${FRAMES}/${id}.mp4`, Buffer.from(await res.arrayBuffer()));
            st[id].status = "DOWNLOADED"; st[id].file = `${FRAMES}/${id}.mp4`;
            console.log(new Date().toISOString().slice(11, 19), id, "DOWNLOADED", fs.statSync(`${FRAMES}/${id}.mp4`).size);
          } else console.log(id, "dl http", res.status);
        } else console.log(id, "SUCCESS no url", JSON.stringify(r).slice(0, 200));
      } else if (r.task_status === "FAIL") {
        st[id].status = "FAIL"; console.log(id, "FAIL");
      } else active++;
    } catch (e) { console.log(id, "query err", e.message.slice(0, 80)); }
    await new Promise(r => setTimeout(r, 1500));
  }
  // rolling submission: keep 2 in flight
  const pending = Object.keys(SCENES).filter(k => !st[k]?.task_id);
  while (active < 2 && pending.length) {
    const id = pending.shift();
    const sc = SCENES[id];
    try {
      const payload = { prompt: sc.prompt, quality: sc.quality, with_audio: false, size: "1920x1080", fps: 30, duration: sc.dur };
      if (sc.image) payload.image_url = b64(sc.image);
      const t = await zai.video.generations.create(payload);
      st[id] = { task_id: t.id, status: t.task_status || "SUBMITTED", dur: sc.dur, quality: sc.quality };
      active++; console.log(new Date().toISOString().slice(11, 19), id, "SUBMITTED", t.id);
    } catch (e) { console.log(id, "submit err", e.message.slice(0, 90)); break; }
    await new Promise(r => setTimeout(r, 8000));
  }
  save(st);
  const done = Object.values(st).filter(v => v.status === "DOWNLOADED").length;
  const total = Object.keys(SCENES).length + 2; // s01..s08
  console.log(new Date().toISOString().slice(11, 19), `state: ${done}/${total} downloaded, ${active} in flight`);
  if (done === total) { console.log("ALL_CLIPS_READY"); break; }
  await new Promise(r => setTimeout(r, 20000));
}
