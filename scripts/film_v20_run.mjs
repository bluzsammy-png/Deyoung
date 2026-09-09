// DeYoung 20s UGC launch film (v20) — submit+poll+download for scenes u1..u4.
// Modeled on the PROVEN film_run.mjs (v3 pipeline): 429-aware, FAIL-aware, downloads clips.
// u1/u4 = i2v from the SAME creator still (character continuity) + lip-synced dialogue (with_audio).
// u2/u3 = t2v silent UI/montage shots (narrator VO lands on these at mix time).
// Usage: node scripts/film_v20_run.mjs [maxMinutes=45]
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const BASE = "/home/z/my-project/campaign/film/v20";
const TASKS = `${BASE}/tasks-v20.json`;
const CLIPS = `${BASE}/clips`;
const STILL = `${BASE}/stills/creator.png`;
const MAXTRY = 4;
fs.mkdirSync(CLIPS, { recursive: true });

const b64 = (p) => `data:image/png;base64,${fs.readFileSync(p).toString("base64")}`;
const SAY = (line, extra) =>
  `The character speaks in English, saying exactly and only this sentence, with mouth movements perfectly synchronized to every word: "${line}" No other dialogue, no narration, no extra words. She says just this one line clearly with studio quality sound. ${extra} Clear audible voice, no background music, no subtitles, no text on screen`;

const SCENES = {
  u1: {
    dur: 5, audio: true, image: STILL,
    prompt: SAY("I typed one sentence - and got a whole video.",
      `Vertical selfie video: she films herself at arm's length in a cozy bedroom at night with warm LED strip glow behind her, grins and says the line straight into the camera with infectious UGC energy, then flips the phone in her hand to show a glowing dark video-editing timeline on its screen. Handheld phone-camera feel with slight natural wobble, realistic skin texture, authentic influencer vlog lighting.`),
  },
  u2: {
    dur: 5, audio: false, image: null,
    prompt: `Vertical close-up over-the-shoulder shot: hands typing on a phone in a dim cozy room at night, the screen shows a sleek dark AI film studio interface with a single glowing prompt box, the typed sentence lifts off the keyboard as light particles and fans out into three floating storyboard scene cards with tiny sketches that snap onto a timeline. Soft keyboard taps, crystalline UI chime feel, shallow depth of field, cinematic bokeh, crisp screen detail, photorealistic, no subtitles, no text overlays besides the app interface.`,
  },
  u3: {
    dur: 5, audio: false, image: null,
    prompt: `Vertical rapid joyful montage on a phone screen: three storyboard scene cards burst into tiny video thumbnails that stack like polaroids, a progress ring sweeps around a glowing GPU spark icon, and an audio waveform dances under the thumbnails. Whooshing card transitions, rising render energy, glowing neon accents on dark UI, crisp macro screen detail, photorealistic, energetic build-up, no subtitles, no text overlays besides the app interface.`,
  },
  u4: {
    dur: 5, audio: true, image: STILL,
    prompt: SAY("Deyoung dot site - type it, watch it, post it.",
      `Vertical selfie video: same cozy bedroom at night with warm LED strip glow, she holds the phone up next to her face with its screen showing a finished video playing, says the line straight into the camera, throws a double thumbs-up and winks as the screen light flares softly. Handheld UGC selfie energy, realistic skin texture, authentic influencer lighting.`),
  },
};

const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};
for (const id of Object.keys(SCENES)) if (!state[id]) state[id] = { status: "NEW" };
const save = () => fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
save();

const maxMs = (Number(process.argv[2]) || 45) * 60 * 1000;
const start = Date.now();
const zai = await ZAI.create();
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

const download = (id, url) => {
  const out = `${CLIPS}/${id}.mp4`;
  execSync(`curl -sL --max-time 300 -o "${out}" "${url}"`, { stdio: "inherit" });
  const sz = fs.statSync(out).size;
  if (sz < 200000) throw new Error(`download too small: ${sz}`);
  log("DOWNLOADED", id, (sz / 1e6).toFixed(1) + "MB");
};

while (Date.now() - start < maxMs) {
  let open = 0;
  // 1) submit scenes that have no task in flight
  for (const [id, sc] of Object.entries(SCENES)) {
    const st = state[id];
    if (st.task_id || st.status === "DONE") continue;
    if ((st.tries || 0) >= MAXTRY) { log("GIVEUP", id); continue; }
    open++;
    try {
      const args = {
        prompt: sc.prompt, quality: "quality", with_audio: sc.audio, watermark_enabled: false,
        size: "768x1344", fps: 30, duration: sc.dur,
      };
      if (sc.image) args.image_url = b64(sc.image);
      const t = await zai.video.generations.create(args);
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
        break;
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
      st.status = r.task_status; st.polled_at = Date.now();
      if (r.task_status === "SUCCESS") {
        const url = r.video_result?.[0]?.url || r.video_url || r.url;
        if (!url) { st.status = "FAIL_NO_URL"; st.task_id = null; st.last_err = JSON.stringify(r).slice(0, 200); save(); log("NO-URL", id); continue; }
        download(id, url);
        st.clip = `${CLIPS}/${id}.mp4`; st.status = "DONE"; st.url = url;
        delete st.task_id;
      } else if (r.task_status === "FAIL") {
        log("FAIL", id, "— will resubmit (tries:", st.tries, ")");
        st.task_id = null; st.status = "RETRY";
      }
      save();
    } catch (e) {
      log("poll-err", id, String(e.message).slice(0, 80));
    }
  }
  const done = Object.values(state).filter((s) => s.status === "DONE").length;
  if (done === 4) { log("ALL 4 SCENES DONE"); break; }
  if (open === 0) { log("nothing in flight, sleep 15s"); await new Promise((r) => setTimeout(r, 15000)); }
  else await new Promise((r) => setTimeout(r, 20000));
}
save();
const doneList = Object.entries(state).filter(([, s]) => s.status === "DONE");
console.log("FINAL:", doneList.map(([i]) => i).join(",") || "NONE");
process.exit(doneList.length === 4 ? 0 : 1);
