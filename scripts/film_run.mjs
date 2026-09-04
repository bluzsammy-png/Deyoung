// DeYoung promo v3 — unified submit+poll+download runner for scenes s3..s8.
// 429-aware, provider-FAIL-aware (auto-resubmit up to MAXTRY), downloads finished clips.
// Usage: node scripts/film_run.mjs [maxMinutes=42]
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const BASE = "/home/z/my-project/campaign/film/v3";
const TASKS = `${BASE}/tasks-v3.json`;
const CLIPS = `${BASE}/clips`;
const C = "/home/z/my-project/campaign/v3/chars";
const MAXTRY = 4;
fs.mkdirSync(CLIPS, { recursive: true });

const b64 = (p) => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;
const SAY = (line, extra) =>
  `The character speaks in English, saying exactly and only this sentence, with mouth movements perfectly synchronized to every word: "${line}" No other dialogue, no narration, no extra words. She/He says just this one line clearly with studio quality sound. ${extra} Clear audible voice, no background music, no subtitles, no text on screen`;

const SCENES = {
  s3: { dur: 10, image: `${C}/maya.png`,
    prompt: SAY("It's already making my video.",
      `She looks up from the phone she is holding, turns her face to the lens and says the line with a warm confident smile, then glances back down and taps the screen once. Ultra realistic cinematic live action, shallow depth of field, warm evening living room light with crimson practical lamps, gentle slow push-in, filmic grade.`) },
  s4: { dur: 10, image: `${C}/yuki.png`,
    prompt: SAY("Watch it build — scene by scene.",
      `She gestures like a conductor and the three holographic screens around her flare alive one by one, each lighting up with a new glowing video frame while her jacket flutters. Modern anime style, crisp cel shading, dramatic red and cyan rim light, dark studio, dynamic camera orbit, cinematic energy.`) },
  s5: { dur: 10, image: `${C}/bea.png`,
    prompt: SAY("My movie arrived! Ready to post.",
      `The friendly round robot hands her the glowing gift box, she hugs it with sparkling excited eyes and bounces with joy, rainbow shimmering behind. Cute children's picture-book cartoon style, soft crayon textures, rounded shapes, bright pastel colors with red accents, cheerful bouncy animation.`) },
  s6: { dur: 10, image: `${C}/duo.png`,
    prompt: SAY("Same prompt. Every style you can imagine.",
      `Two characters stand side by side facing the viewer, one anime girl and one realistic woman, taking turns speaking the line with confident smiles and synchronized mouth movement. Dark studio with a vertical red light divider between them, subtle camera push-in, cinematic staging.`) },
  s7: { dur: 10, image: `${C}/felix.png`,
    prompt: SAY("Straight to my feed. Zero editing.",
      `He watches the video playing on the phone he holds up, the screen glow painting his amazed face, then looks up to the lens laughing with delight and tilts the phone toward the viewer. Ultra realistic cinematic live action, night bedroom lit by warm fairy lights, shallow depth of field, gentle push-in, filmic grade.`) },
  s8: { dur: 10, image: `${C}/lineup.png`,
    prompt: SAY("If you can say it — you can film it.",
      `All five characters stand together facing the viewer, each in their own art style — flat cartoon, stick figure, ultra realistic, anime, and children's picture book — speaking the line together with synchronized mouth movement, then all five nod and smile at the camera. Dark stage with soft red spotlights, crossover ensemble composition, cinematic staging, confident celebratory energy.`) },
};

const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
for (const id of Object.keys(SCENES)) if (!state[id]) state[id] = { status: "NEW" };
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
save();

const maxMs = (Number(process.argv[2]) || 42) * 60 * 1000;
const start = Date.now();
const zai = await ZAI.create();
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

while (Date.now() - start < maxMs) {
  let open = 0;
  // 1) submit scenes that have no task in flight
  for (const [id, sc] of Object.entries(SCENES)) {
    const st = state[id];
    if (st.task_id || st.status === "DONE") continue;
    if ((st.tries || 0) >= MAXTRY) { log("GIVEUP", id); continue; }
    open++;
    try {
      const t = await zai.video.generations.create({
        prompt: sc.prompt, quality: "quality", with_audio: true, watermark_enabled: false,
        size: "1920x1080", fps: 30, duration: sc.dur, image_url: b64(sc.image),
      });
      st.task_id = t.id; st.status = t.task_status || "SUBMITTED";
      st.tries = (st.tries || 0) + 1; st.submitted_at = Date.now();
      save(); log("SUBMITTED", id, t.id);
      await new Promise((r) => setTimeout(r, 8000));
    } catch (e) {
      const m = String(e.message);
      st.last_err = m.slice(0, 140); save();
      if (/429/.test(m)) {
        log("429", id, "— sleep 45s, defer rest of submit pass");
        await new Promise((r) => setTimeout(r, 45000));
        break; // rate-limited: stop hammering, go poll, retry next cycle
      }
      log("submit-err", id, m.slice(0, 80), "sleep 20s");
      await new Promise((r) => setTimeout(r, 20000));
    }
  }
  // 2) poll scenes with a task in flight
  for (const [id] of Object.entries(SCENES)) {
    const st = state[id];
    if (!st.task_id || st.status === "DONE") continue;
    open++;
    try {
      const r = await zai.async.result.query(st.task_id);
      const status = r.task_status || r.status;
      if (status === "SUCCESS") {
        const urls = r.video_result?.map((v) => v.url) || (r.video_url ? [r.video_url] : (r.url ? [r.url] : []));
        if (!urls.length) { log("SUCCESS-no-url", id); st.task_id = null; st.status = "RETRY"; save(); continue; }
        const out = `${CLIPS}/${id}.mp4`;
        try {
          execSync(`curl -sL --max-time 220 -o "${out}" "${urls[0]}"`, { timeout: 240000 });
        } catch (d) { log("dl-err", id, String(d.message).slice(0, 60)); continue; }
        const size = fs.existsSync(out) ? fs.statSync(out).size : 0;
        if (size < 200000) { log("too-small", id, size); continue; }
        st.status = "DONE"; st.file = out; st.bytes = size; save();
        log("DONE", id, (size / 1e6).toFixed(1) + "MB");
      } else if (status === "FAIL") {
        log("PROVIDER-FAIL", id, JSON.stringify(r).slice(0, 120));
        st.task_id = null; st.status = "RETRY"; st.last_err = "provider FAIL"; save();
      } else {
        log(id, status);
      }
    } catch (e) {
      log("poll-err", id, String(e.message).slice(0, 80));
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  const done = Object.keys(SCENES).filter((id) => state[id].status === "DONE").length;
  const dead = Object.keys(SCENES).filter((id) => (state[id].tries || 0) >= MAXTRY && state[id].status !== "DONE").length;
  if (done + dead >= Object.keys(SCENES).length) { log("ALL_SETTLED", `done=${done} dead=${dead}`); break; }
  if (!open) { log("IDLE-all-gaveup"); break; }
  await new Promise((r) => setTimeout(r, 15000));
}
save();
const summary = Object.fromEntries(Object.entries(SCENES).map(([k, _]) => [k, state[k].status]));
console.log("RUN_END", JSON.stringify(summary));
