// Narrator-led voice track for the DeYoung film (v2).
// ALL spoken words are one narrator — no fake character dialogue.
// Voices: xiaochen (primary), kazi (alternate). Alternates written to alt/.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const OUT = "/home/z/my-project/campaign/voices2";
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(`${OUT}/alt`, { recursive: true });

const LINES = [
  { id: "n01", speed: 0.9, text: "Every story deserves the big screen." },
  { id: "n02", speed: 0.9, text: "Your story deserves more than fifteen seconds." },
  { id: "n03", speed: 0.9, text: "DeYoung gives it a full sixty." },
  { id: "n04", speed: 0.9, text: "Type your story. Pick your length. And watch it come alive." },
  { id: "n06", speed: 0.92, text: "Write it. We roll the cameras." },
  { id: "n07", speed: 0.9, text: "Mobile or web. Your studio travels with you." },
  { id: "n08", speed: 0.92, text: "DeYoung. Sixty seconds. One pass." },
];

const zai = await ZAI.create();

async function gen(voice, L, out) {
  const res = await zai.audio.tts.create({
    input: L.text, voice, speed: L.speed, response_format: "wav", stream: false,
  });
  const buf = Buffer.from(new Uint8Array(await res.arrayBuffer()));
  if (buf.length < 5000) throw new Error("suspiciously small audio " + buf.length);
  fs.writeFileSync(out, buf);
  const d = execDur(out);
  console.log("ok", voice, L.id, buf.length, "bytes", d + "s");
}

function execDur(p) {
  try {
    return execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 "${p}"`)
      .toString().trim().slice(0, 5);
  } catch { return "?"; }
}

import { execSync } from "child_process";

for (const L of LINES) {
  for (const [voice, dir] of [["xiaochen", ""], ["kazi", "alt/"]]) {
    const out = `${OUT}/${dir}${L.id}.wav`;
    if (fs.existsSync(out) && fs.statSync(out).size > 10000) { console.log("have", dir + L.id); continue; }
    for (let a = 1; a <= 3; a++) {
      try { await gen(voice, L, out); break; }
      catch (e) {
        console.log("ERR", dir + L.id, "attempt", a, e.message.slice(0, 90));
        if (a === 3) console.log("FAILED", dir + L.id);
        else await new Promise(r => setTimeout(r, 5000));
      }
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}
console.log("TTS2_DONE");
