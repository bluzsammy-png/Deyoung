// Probe z-ai image + TTS availability with tiny calls (rate-limit check).
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

async function main() {
  const zai = await ZAI.create();
  // TTS probe
  try {
    const res = await zai.audio.speech.create({ input: "Probe.", voice: "tongtong", speed: 1.0 });
    const buf = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync("/tmp/probe_tts.wav", buf);
    console.log("TTS_OK", buf.length);
  } catch (e) {
    console.log("TTS_FAIL", String(e).slice(0, 200));
  }
  // Image probe
  try {
    const r = await zai.images.generations.create({
      prompt: "single flat test circle, red on white background, minimal",
      size: "512x512",
    });
    const b64 = r?.data?.[0]?.base64 || r?.data?.[0]?.b64_json;
    if (b64) {
      fs.writeFileSync("/tmp/probe_img.png", Buffer.from(b64, "base64"));
      console.log("IMG_OK", fs.statSync("/tmp/probe_img.png").size);
    } else console.log("IMG_FAIL no data", JSON.stringify(r).slice(0, 200));
  } catch (e) {
    console.log("IMG_FAIL", String(e).slice(0, 200));
  }
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(1); });
