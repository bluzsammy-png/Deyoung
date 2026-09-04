// Submit all DeYoung film scenes; persist task ids to campaign/tasks.json.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const TASKS = "/home/z/my-project/campaign/tasks.json";
const S = "/home/z/my-project/campaign/social";
const b64 = p => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;

const SCENES = [
  { id: "s01", dur: 5, quality: "speed",
    prompt: "Cinematic aerial drone shot pushing slowly over Lagos at dusk, deep black silhouettes of the skyline, crimson neon glow reflecting on wet streets below, volumetric haze, anamorphic film look, red and black color grade, dramatic and moody, no text" },
  { id: "s02", dur: 10, quality: "quality", image: `${S}/amara.png`,
    prompt: "The woman looks straight into the lens and speaks passionately to camera, natural mouth movement as she talks, subtle confident hand gesture, breathing life into the frame, cinematic shallow depth of field, soft crimson rim light, gentle slow push-in, filmic grade, no text" },
  { id: "s03", dur: 10, quality: "quality", image: `${S}/kojo.png`,
    prompt: "The man speaks directly to camera with charismatic energy, natural talking mouth movement, small emphatic nod, red monitor light flickering softly behind him, cinematic slow push-in, shallow depth of field, filmic grade, no text" },
  { id: "s04", dur: 5, quality: "speed",
    prompt: "Cinematic macro shot of hands typing a story prompt on a glowing smartphone, the screen lights up with a warm red interface, reflections of the screen glow on the fingers, dark desk, shallow depth of field, filmic red and black grade, no readable text" },
  { id: "s05", dur: 5, quality: "speed",
    prompt: "Cinematic shot of glowing particles and ribbons of red light streaming out of a dark smartphone screen and swirling into the air like a forming galaxy, volumetric light, black studio void, elegant and magical, filmic grade, no text" },
  { id: "s06", dur: 10, quality: "quality", image: `${S}/duo.png`,
    prompt: "The two creators talk to each other and glance to camera with smiles, natural conversation mouth movement, relaxed confident body language, crimson practical lights glowing through haze behind them, slow cinematic orbit, filmic grade, no text" },
  { id: "s07", dur: 5, quality: "speed",
    prompt: "Cinematic desk scene at night, a smartphone and a laptop side by side both playing a vivid red-toned film, screen glow lighting the dark room, soft bokeh, slow dolly across the desk, filmic red and black grade, no readable text" },
  { id: "s08", dur: 5, quality: "speed", image: `${S}/silk.png`,
    prompt: "The crimson silk fabric flows and ripples slowly in slow motion, elegant folds catching the light, deep black shadows behind, luxurious cinematic mood, subtle drift of the camera, no text" },
];

const zai = await ZAI.create();
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};

for (const sc of SCENES) {
  if (state[sc.id]?.task_id && state[sc.id].status !== "FAIL") { console.log("have", sc.id); continue; }
  for (let a = 1; a <= 5; a++) {
    try {
      const payload = {
        prompt: sc.prompt, quality: sc.quality, with_audio: false,
        size: "1920x1080", fps: 30, duration: sc.dur,
      };
      if (sc.image) payload.image_url = b64(sc.image);
      const t = await zai.video.generations.create(payload);
      state[sc.id] = { task_id: t.id, status: t.task_status || "SUBMITTED", dur: sc.dur, quality: sc.quality };
      console.log("submitted", sc.id, t.id);
      break;
    } catch (e) {
      const is429 = /429/.test(e.message);
      state[sc.id] = { ...(state[sc.id] || {}), status: is429 ? "RATE_LIMITED" : "SUBMIT_ERR", err: e.message };
      console.log("ERR", sc.id, `attempt ${a}`, e.message);
      if (a === 5) break;
      await new Promise(r => setTimeout(r, is429 ? 30000 : 8000));
    }
  }
  fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
  await new Promise(r => setTimeout(r, 12000)); // pace submissions
}
console.log("SUBMIT_COMPLETE", JSON.stringify(Object.fromEntries(Object.entries(state).map(([k, v]) => [k, v.status]))));
