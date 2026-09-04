// DeYoung promo v5 — POST-DUB: clean TTS voice lines for every scene.
// Output: campaign/film/v3/dub/{id}.wav (44.1kHz), speed-matched to segment window.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const OUT = "/home/z/my-project/campaign/film/v3/dub";
fs.mkdirSync(OUT, { recursive: true });

// id -> [{text, voice}], window = max seconds the line may take (segment - 1.2s lead/out)
const LINES = {
  s1: [{ text: "One sentence. Sixty seconds. Done.", voice: "douji", window: 5.8 }],
  s2: [{ text: "Sign up? Ten seconds. Three ways.", voice: "jam", window: 3.8 }],
  s3: [{ text: "It's already making my video.", voice: "xiaochen", window: 5.8 }],
  s4: [{ text: "Watch it build — scene by scene.", voice: "chuichui", window: 5.8 }],
  s5: [{ text: "My movie arrived! Ready to post.", voice: "kazi", window: 5.8 }],
  s6: [
    { text: "Same prompt.", voice: "xiaochen", window: 2.0, part: "a" },
    { text: "Every style you can imagine.", voice: "tongtong", window: 3.6, part: "b" },
  ],
  s7: [{ text: "Straight to my feed. Zero editing.", voice: "douji", window: 6.8 }],
  s8: [{ text: "DeYoung. If you can say it — you can film it.", voice: "luodo", window: 6.8 }],
};

const zai = await ZAI.create();
const dur = (p) => parseFloat(execSync(
  `ffprobe -v error -show_entries format=duration -of csv=p=0 "${p}"`).toString().trim());

for (const [id, parts] of Object.entries(LINES)) {
  for (const ln of parts) {
    const out = `${OUT}/${id}${ln.part || ""}.wav`;
    let speed = 1.0;
    // up to 2 passes: measure, then speed up if too long
    for (let pass = 0; pass < 2; pass++) {
      const r = await zai.audio.tts.create({
        input: ln.text, voice: ln.voice, speed, response_format: "wav", stream: false });
      fs.writeFileSync(out, Buffer.from(new Uint8Array(await r.arrayBuffer())));
      const d = dur(out);
      console.log(`${id}${ln.part || ""} voice=${ln.voice} speed=${speed} dur=${d.toFixed(2)}s`);
      if (d <= ln.window) break;
      speed = Math.min(1.6, (d / ln.window) * speed * 1.05);
      speed = Math.round(speed * 20) / 20;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
}
console.log("DUB_ALL_DONE");
