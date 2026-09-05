// DeYoung film v3 production runner — strict dialogue-adherence pipeline.
// Usage: node scripts/film_v3_patient.mjs [maxSeconds]
// Gate: adherence probe must PASS before scenes are generated.
// State: campaign/v3prod.json   Clips: campaign/film/v3/<id>_a<N>.mp4
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const OUT = "/home/z/my-project/campaign/film/v3";
const STATE = "/home/z/my-project/campaign/v3prod.json";
const maxMs = (Number(process.argv[2]) || 500) * 1000;
const T0 = Date.now();
fs.mkdirSync(OUT, { recursive: true });

const VISUALS = JSON.parse(fs.readFileSync("/home/z/my-project/scripts/film_v3_prompts.json", "utf8"));
const LINES = {
  v3s1: "One sentence. Sixty seconds. Done.",
  v3s2: "Sign up? Ten seconds. Three ways.",
  v3s3: "It's already making my video.",
  v3s4: "Watch it build — scene by scene.",
  v3s5: "My movie arrived. Ready to post.",
  v3s6: "Same prompt. Every style you can imagine.",
  v3s7: "Straight to my feed. Zero editing.",
  v3s8: "Deyoung. If you can say it, you can film it.",
};
const KEYWORDS = {
  v3s1: ["sentence", "sixty", "seconds", "done"],
  v3s2: ["sign", "up", "ten", "seconds", "three", "ways"],
  v3s3: ["already", "making", "video"],
  v3s4: ["watch", "build", "scene"],
  v3s5: ["movie", "arrived", "ready", "post"],
  v3s6: ["same", "prompt", "every", "style", "imagine"],
  v3s7: ["straight", "feed", "zero", "editing"],
  v3s8: ["deyoung", "say", "film"],
};
const ORDER = ["v3s1", "v3s2", "v3s3", "v3s4", "v3s5", "v3s6", "v3s7", "v3s8"];
const DUR = { v3s1: 10, v3s2: 5, v3s3: 10, v3s4: 5, v3s5: 5, v3s6: 10, v3s7: 5, v3s8: 10 };

const strictPrompt = (visual, line) =>
  `Audio: the only spoken words in the entire video are exactly this sentence, spoken aloud in clear English: "${line}" ` +
  `The character says this exact sentence and nothing else. No other dialogue. No background voices. No music. ` +
  `Visual: ${visual} ` +
  `Absolutely no text, no letters, no numbers, no captions, no subtitles, no writing anywhere in the image.`;

const scenePrompt = (id) => {
  // reuse approved visuals, strip any embedded dialogue sentence + the old "no text" tail (strict wrapper re-adds)
  let v = VISUALS[id];
  v = v.replace(/"\.”?$/g, "").replace(/:\s*"[^"]*"\.?/, ".");
  return strictPrompt(v, LINES[id]);
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const state = fs.existsSync(STATE) ? JSON.parse(fs.readFileSync(STATE, "utf8"))
  : { probe: {}, scenes: {}, lastApiCall: 0 };
const save = () => fs.writeFileSync(STATE, JSON.stringify(state, null, 2));

const zai = await ZAI.create();

async function pacedSubmit(body) {
  const gap = Date.now() - state.lastApiCall;
  if (gap < 90000) await sleep(90000 - gap);
  for (let a = 1; a <= 12; a++) {
    try {
      state.lastApiCall = Date.now(); save();
      return await zai.video.generations.create(body);
    } catch (e) {
      const m = String(e?.message || e);
      console.log(`  submit 429 (${a}/12), sleep 300s`);
      if (!m.includes("429")) { console.log("  submit err:", m.slice(0, 120)); await sleep(20000); }
      else await sleep(300000);
    }
  }
  return null;
}

async function genClip(prompt, dur) {
  const r = await pacedSubmit({ prompt, quality: "quality", with_audio: true, size: "1920x1080", fps: 30, duration: dur });
  if (!r) return { error: "submit_failed" };
  console.log("  task:", r.id);
  while (Date.now() - T0 < maxMs) {
    await sleep(20000);
    let q;
    try { q = await zai.async.result.query(r.id); }
    catch (e) { console.log("  poll err:", String(e?.message).slice(0, 80)); continue; }
    const st = q.task_status || q.status;
    if (st === "SUCCESS") {
      const url = q.video_result?.[0]?.url || q.video_url || q.url;
      if (!url) return { error: "no_url" };
      const res = await fetch(url);
      return { buf: Buffer.from(await res.arrayBuffer()) };
    }
    if (st === "FAIL") return { error: "gen_failed" };
    if (Date.now() - state.lastApiCall > 1000) state.lastApiCall = Date.now() - 60000; // polls don't count toward submit pacing
  }
  return { error: "run_timeout" };
}

function asrText(file) {
  const wav = `/tmp/${Date.now()}.wav`;
  execSync(`ffmpeg -y -v error -i "${file}" -vn -ac 1 -ar 16000 "${wav}"`);
  const b64 = fs.readFileSync(wav).toString("base64");
  fs.unlinkSync(wav);
  return zai.audio.asr.create({ file_base64: b64, stream: false }).then((r) =>
    String(r?.text || JSON.stringify(r)).toLowerCase()
      .replace(/60/g, "sixty").replace(/10/g, "ten").replace(/\b3\b/g, "three")
      .replace(/[^a-z ]/g, " ")
  );
}

const score = (text, id) => {
  const kws = KEYWORDS[id];
  const hits = kws.filter((k) => text.includes(k));
  return { hits: hits.length, total: kws.length, pass: hits.length >= Math.ceil(kws.length / 2) };
};

// ---------- PHASE 1: adherence probe ----------
if (!state.probe.pass) {
  console.log("== PROBE ==");
  const p = state.probe;
  if (!p.tried) p.tried = 0;
  while (!p.pass && Date.now() - T0 < maxMs) {
    p.tried++; save();
    console.log(`probe attempt ${p.tried}`);
    const g = await genClip(strictPrompt(
      "close-up portrait, bright modern 2D cartoon style, a cheerful man with round glasses in a sunny room, looking straight into the camera, mouth moving in natural lip sync as he speaks that exact sentence, slow push-in",
      LINES.v3s1), 5);
    if (g.error) { console.log("probe gen error:", g.error); if (g.error === "run_timeout") break; continue; }
    const f = `${OUT}/probe_a${p.tried}.mp4`;
    fs.writeFileSync(f, g.buf);
    const text = await asrText(f);
    const sc = score(text, "v3s1");
    p.transcripts = p.transcripts || [];
    p.transcripts.push(text);
    save();
    console.log(`probe transcript: "${text}" -> ${sc.hits}/${sc.total} ${sc.pass ? "PASS" : "FAIL"}`);
    p.pass = sc.pass; save();
  }
  if (!state.probe.pass) { console.log("PROBE_NOT_PASSED — stopping to protect quota"); console.log("EXIT_PROBE_FAIL"); process.exit(2); }
  console.log("PROBE PASSED — proceeding to scenes");
}

// ---------- PHASE 2: scenes ----------
for (const id of ORDER) {
  if (Date.now() - T0 >= maxMs) break;
  const s = state.scenes[id] || (state.scenes[id] = { variants: [], best: null });
  const need = () => !(s.best && s.best.pass);
  let attempt = (s.variants?.length || 0);
  while (need() && attempt < 3 && Date.now() - T0 < maxMs) {
    attempt++;
    console.log(`== ${id} variant ${attempt} ==`);
    const g = await genClip(scenePrompt(id), DUR[id]);
    if (g.error === "run_timeout") break;
    if (g.error) { console.log(`${id} gen error:`, g.error); continue; }
    const f = `${OUT}/${id}_a${attempt}.mp4`;
    fs.writeFileSync(f, g.buf);
    const text = await asrText(f);
    const sc = score(text, id);
    s.variants.push({ file: f, text, hits: sc.hits, pass: sc.pass });
    if (!s.best || sc.hits > s.best.hits) s.best = { file: f, text, hits: sc.hits, pass: sc.pass };
    save();
    console.log(`${id}: "${text}" ${sc.hits}/${sc.total} ${sc.pass ? "PASS" : "fail"}`);
  }
}

const summary = Object.fromEntries(ORDER.map((id) => {
  const s = state.scenes[id];
  return [id, s?.best ? `${s.best.hits}/${s.best.total}${s.best.pass ? " PASS" : ""}` : "pending"];
}));
console.log("RUNNER_STATE", JSON.stringify({ probe: state.probe.pass ? "PASS" : "FAIL", scenes: summary }));
