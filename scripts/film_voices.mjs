// Generate DeYoung film voice-over lines via z-ai TTS.
// Voices: xiaochen = narrator (calm pro), tongtong = Amara (warm female), jam = Kojo (British male).
// Alternates generated as backups: luodo (Amara alt), kazi (narrator alt).
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const OUT = "/home/z/my-project/campaign/voices";
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(`${OUT}/alt`, { recursive: true });

const LINES = [
  { id: "v01-narrator", voice: "xiaochen", speed: 0.92, text: "Every story deserves the big screen." },
  { id: "v02-amara",    voice: "tongtong", speed: 0.95, text: "Your story deserves more than fifteen seconds." },
  { id: "v03-kojo",     voice: "jam",      speed: 0.95, text: "DeYoung gives it a full sixty." },
  { id: "v06a-amara",   voice: "tongtong", speed: 1.0,  text: "Write it." },
  { id: "v06b-kojo",    voice: "jam",      speed: 0.98, text: "We roll the cameras." },
  { id: "v07-endcard",  voice: "xiaochen", speed: 0.95, text: "DeYoung. Sixty seconds. One pass." },
  // alternates (backups, different flavour)
  { id: "alt/v01-narrator-kazi", voice: "kazi",  speed: 0.92, text: "Every story deserves the big screen." },
  { id: "alt/v02-amara-luodo",   voice: "luodo", speed: 0.95, text: "Your story deserves more than fifteen seconds." },
];

const zai = await ZAI.create();

for (const L of LINES) {
  const out = `${OUT}/${L.id}.wav`;
  if (fs.existsSync(out) && fs.statSync(out).size > 10000) { console.log("have", L.id); continue; }
  for (let a = 1; a <= 3; a++) {
    try {
      const res = await zai.audio.tts.create({
        input: L.text, voice: L.voice, speed: L.speed,
        response_format: "wav", stream: false,
      });
      const buf = Buffer.from(new Uint8Array(await res.arrayBuffer()));
      if (buf.length < 5000) throw new Error("suspiciously small audio " + buf.length);
      fs.writeFileSync(out, buf);
      console.log("ok", L.id, L.voice, buf.length, "bytes");
      break;
    } catch (e) {
      console.log("ERR", L.id, "attempt", a, e.message.slice(0, 90));
      if (a === 3) console.log("FAILED", L.id);
      else await new Promise(r => setTimeout(r, 5000));
    }
    await new Promise(r => setTimeout(r, 2500));
  }
}
console.log("TTS_DONE");
