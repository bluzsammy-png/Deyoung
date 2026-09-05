// DeYoung film v6 — per-CHARACTER voices (this is what makes the cast talk).
// amara/kossi/zola/dee speak their own lines; xiaochen narrates hook/alive/anywhere/endcard.
// Output: /home/z/my-project/campaign/v6/voices/<id>.wav (+ ffprobe duration in durations.json)
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const OUT = "/home/z/my-project/campaign/v6/voices";
fs.mkdirSync(OUT, { recursive: true });

const LINES = [
  { id: "n01_hook",   voice: "xiaochen", speed: 0.9,  text: "Every story deserves the big screen." },
  { id: "n02_amara",  voice: "tongtong", speed: 0.95, text: "Your story deserves more than fifteen seconds." },
  { id: "n03_kossi",  voice: "kazi",     speed: 0.95, text: "DeYoung gives it a full sixty." },
  { id: "n04_zola",   voice: "tongtong", speed: 1.0,  text: "Type your story. Pick your length." },
  { id: "n05_alive",  voice: "xiaochen", speed: 0.9,  text: "And watch it come alive." },
  { id: "n06_dee",    voice: "kazi",     speed: 0.92, text: "Write it. We roll the cameras." },
  { id: "n07_anywhere", voice: "xiaochen", speed: 0.9, text: "Mobile or web. Your studio travels with you." },
  { id: "n08_end",    voice: "xiaochen", speed: 0.92, text: "DeYoung. Sixty seconds. One pass." },
];

function dur(p) {
  const out = execSync(
    `ffprobe -v error -show_entries format=duration -of csv=p=0 "${p}"`
  ).toString().trim();
  return parseFloat(out);
}

async function main() {
  const zai = await ZAI.create();
  const durations = {};

  for (const L of LINES) {
    const dst = `${OUT}/${L.id}.wav`;
    if (fs.existsSync(dst) && fs.statSync(dst).size > 20000) {
      durations[L.id] = dur(dst);
      console.log(`SKIP ${L.id} ${durations[L.id].toFixed(2)}s`);
      continue;
    }
    let ok = false;
    for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
      try {
        const res = await zai.audio.tts.create({
          input: L.text, voice: L.voice, speed: L.speed,
          response_format: "wav", stream: false,
        });
        const buf = Buffer.from(new Uint8Array(await res.arrayBuffer()));
        if (buf.length < 8000) throw new Error("suspiciously small " + buf.length);
        fs.writeFileSync(dst, buf);
        durations[L.id] = dur(dst);
        console.log(`OK ${L.id} [${L.voice}] ${durations[L.id].toFixed(2)}s`);
        ok = true;
      } catch (err: any) {
        console.log(`RETRY ${L.id}#${attempt}: ${(err?.message || String(err)).slice(0, 120)}`);
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
    if (!ok) { console.log(`FAIL ${L.id}`); process.exitCode = 1; }
  }

  fs.writeFileSync(`${OUT}/durations.json`, JSON.stringify(durations, null, 2));
  console.log("durations.json written");
}

main().catch((e) => {
  console.log("CRASH " + (e?.message || String(e)).slice(0, 200));
  process.exit(1);
});
