// DeYoung film v3 — submit 8 speak-on-camera scenes (native audio + lip sync).
// State: campaign/tasks-v3.json
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const TASKS = "/home/z/my-project/campaign/tasks-v3.json";

const SCENES = [
  {
    id: "v3s1", dur: 10, quality: "quality",
    prompt: "Bright modern 2D cartoon animation style, clean bold outlines, flat vivid colors. A cheerful young man with round glasses sits at a small desk in a sunny cartoon room; his laptop suddenly erupts with a burst of colorful light and a finished movie clip pops out of the screen like a firework. He catches it, turns to the camera with a huge grin and speaks clearly to camera with natural lip sync: \"One sentence. Sixty seconds. Done.\" Energetic, snappy animation, slow push-in on his face as he talks. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s2", dur: 5, quality: "quality",
    prompt: "Minimal black stick-figure animation on a clean white background, playful bouncy motion. An energetic stick figure sprints toward three glowing doors labeled with simple circle, apple and envelope icons, dives through the middle one and lands inside a giant smartphone frame. He pops up, taps an imaginary wristwatch and speaks clearly with natural lip sync: \"Sign up? Ten seconds. Three ways.\" Fast comedic timing. No other on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s3", dur: 10, quality: "quality",
    prompt: "Photorealistic cinematic footage, warm modern living room. A young woman relaxes on a sofa holding her smartphone; quick macro insert of her thumb tapping a glowing red Create button in a sleek dark app interface. She lifts her head, looks straight into the lens, smiles and speaks naturally with clear lip sync: \"It's already making my video.\" Soft window light, shallow depth of field, gentle slow push-in, filmic grade. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s4", dur: 5, quality: "quality",
    prompt: "Vibrant cinematic anime style, dynamic lighting. A confident girl director wearing big headphones stands as holographic screens orbit around her, each screen showing a video scene assembling itself piece by piece. She sweeps her hand, the screens swirl, then she points at the camera and speaks clearly with natural lip sync: \"Watch it build — scene by scene.\" Energetic anime camera flourish. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s5", dur: 5, quality: "quality",
    prompt: "Soft crayon-textured children's cartoon style, warm pastel colors, rounded shapes. A cute round little robot waddles in carrying a big gift box with a glowing play button on the lid. The box bursts open with sparkles revealing a tiny glowing film. The robot looks up at the camera and speaks in a friendly childlike voice with natural lip sync: \"My movie arrived. Ready to post.\" Charming, wholesome, gentle bounce animation. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s6", dur: 10, quality: "quality",
    prompt: "Vertical split-screen: the left half is vibrant anime style, the right half is photorealistic live action — the SAME young man rendered in both styles, mirrored poses, standing back to back along the split line. On a shared beat they both snap their fingers; behind each of them an explosion of two completely different art styles of the same video. Both turn and speak in unison with natural lip sync: \"Same prompt. Every style you can imagine.\" High energy, seamless split-screen composition. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s7", dur: 5, quality: "quality",
    prompt: "Photorealistic cinematic handheld shot, golden hour city street. A young man walks toward camera holding up his smartphone; the screen shows a finished vertical video playing in a sleek dark player interface, its glow lighting his face. He glances at the lens with a confident smile and speaks naturally with clear lip sync: \"Straight to my feed. Zero editing.\" Warm backlight, soft lens flare, real-world texture. No on-screen text, no subtitles, no captions."
  },
  {
    id: "v3s8", dur: 10, quality: "quality",
    prompt: "Cinematic ensemble finale on a dark stage with dramatic red accent lighting and light haze. Five characters stand in a lineup side by side: a flat cartoon guy with round glasses, a black stick figure, a photorealistic young woman, an anime girl with headphones, and a cute crayon-style robot. One by one they step forward and wave, then all five point at the camera together and speak in unison with natural lip sync: \"Deyoung. If you can say it, you can film it.\" Epic slow push-out, red rim light, filmic grade. No on-screen text, no subtitles, no captions."
  },
];

const zai = await ZAI.create();
const state = fs.existsSync(TASKS) ? JSON.parse(fs.readFileSync(TASKS, "utf8")) : {};

for (const sc of SCENES) {
  if (state[sc.id]?.task_id && state[sc.id].status !== "FAIL") { console.log("have", sc.id, state[sc.id].task_id); continue; }
  for (let a = 1; a <= 4; a++) {
    try {
      const r = await zai.video.generations.create({
        prompt: sc.prompt,
        quality: sc.quality,
        with_audio: true,           // native dialogue + lip sync — the whole point of v3
        size: "1920x1080",
        fps: 30,
        duration: sc.dur,
      });
      state[sc.id] = { task_id: r.id, dur: sc.dur, status: r.task_status };
      console.log("submitted", sc.id, r.id, r.task_status);
      break;
    } catch (e) {
      console.log("attempt", a, "failed for", sc.id, ":", (e?.message || String(e)).slice(0, 140));
      if (a === 4) { state[sc.id] = { ...(state[sc.id] || {}), status: "FAIL" }; }
      await new Promise(res => setTimeout(res, 4000 * a));
    }
  }
  fs.writeFileSync(TASKS, JSON.stringify(state, null, 2));
}
console.log("SUBMIT_COMPLETE", JSON.stringify(Object.fromEntries(Object.entries(state).map(([k, v]) => [k, v.status]))));
