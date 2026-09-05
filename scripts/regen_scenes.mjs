// Regenerate character dialogue scenes WITH native audio (true lip-sync).
// Usage: node scripts/regen_scenes.mjs s02 s03 s06
// Records task ids to campaign/tasks-audio.json
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const TASKS = "/home/z/my-project/campaign/tasks-audio.json";
const S = "/home/z/my-project/campaign/social";
const b64 = p => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;

const SCENES = {
  s02: { dur: 10, quality: "quality", image: `${S}/amara.png`,
    prompt: `The woman looks straight into the lens and speaks passionately to camera with natural mouth movement perfectly synchronized to her words. She says clearly in English: "Your story deserves more than fifteen seconds." Confident subtle hand gesture, soft crimson rim light, gentle slow push-in, cinematic shallow depth of field, filmic red and black grade, clear audible voice with studio quality sound, no background music, no text` },
  s03: { dur: 10, quality: "quality", image: `${S}/kojo.png`,
    prompt: `The man speaks directly to camera with charismatic energy, mouth movement perfectly synchronized to his words. He says clearly in English: "DeYoung gives it a full sixty." Small emphatic nod, red monitor light flickering softly behind him, cinematic slow push-in, shallow depth of field, filmic grade, clear audible voice with studio quality sound, no background music, no text` },
  s06: { dur: 10, quality: "quality", image: `${S}/duo.png`,
    prompt: `Two creators talk to each other then glance to camera, mouths perfectly synchronized to their words. The woman says clearly in English: "Write it." Then the man replies clearly in English: "We roll the cameras." Relaxed confident body language, crimson practical lights glowing through haze behind them, slow cinematic orbit, filmic grade, clear audible voices with studio quality sound, no background music, no text` },
};

const wanted = process.argv.slice(2);
if (!wanted.length) { console.error("usage: regen_scenes.mjs s02 s03 s06"); process.exit(1); }

const zai = await ZAI.create();
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};

for (const id of wanted) {
  const sc = SCENES[id];
  if (!sc) { console.error("unknown scene", id); continue; }
  for (let a = 1; a <= 5; a++) {
    try {
      const payload = {
        prompt: sc.prompt, quality: sc.quality, with_audio: true,
        size: "1920x1080", fps: 30, duration: sc.dur,
        image_url: b64(sc.image),
      };
      const t = await zai.video.generations.create(payload);
      state[id] = { task_id: t.id, status: t.task_status || "SUBMITTED", dur: sc.dur, with_audio: true, submitted_at: new Date().toISOString() };
      console.log("submitted", id, t.id, t.task_status);
      break;
    } catch (e) {
      const is429 = /429/.test(e.message);
      state[id] = { ...(state[id] || {}), status: is429 ? "RATE_LIMITED" : "SUBMIT_ERR", err: e.message.slice(0, 200) };
      console.log("ERR", id, `attempt ${a}`, e.message.slice(0, 120));
      if (a === 5) break;
      await new Promise(r => setTimeout(r, is429 ? 45000 : 8000));
    }
  }
  fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
  await new Promise(r => setTimeout(r, 12000)); // pace submissions
}
console.log("SUBMIT_DONE", JSON.stringify(Object.fromEntries(Object.entries(state).map(([k, v]) => [k, v.status]))));
