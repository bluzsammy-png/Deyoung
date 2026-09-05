// Probe z-ai until it recovers from 429 (checks TTS + image), max ~8.5 min.
// Exit 0 = recovered, 1 = still limited when deadline hit.
import ZAI from "z-ai-web-dev-sdk";

const DEADLINE = Date.now() + 8.3 * 60 * 1000;
const zai = await ZAI.create();

async function tryTTS() {
  try {
    const r = await zai.audio.tts.create({ input: "Probe.", voice: "xiaochen", speed: 1.0, response_format: "wav", stream: false });
    const buf = Buffer.from(new Uint8Array(await r.arrayBuffer()));
    return buf.length > 4000;
  } catch {
    return false;
  }
}

async function tryIMG() {
  try {
    const r = await zai.images.generations.create({ prompt: "a small red circle on white, minimal", size: "1024x1024" });
    const b64 = r?.data?.[0]?.base64 || r?.data?.[0]?.b64_json;
    return Boolean(b64);
  } catch {
    return false;
  }
}

let round = 0;
while (Date.now() < DEADLINE) {
  round++;
  const t = await tryTTS();
  const i = t ? await tryIMG() : false;
  console.log(`probe#${round} tts=${t ? "OK" : "429"} img=${i ? "OK" : "429"} @${new Date().toISOString().slice(11, 19)}`);
  if (t && i) {
    console.log("ZAI_RECOVERED");
    process.exit(0);
  }
  // TTS + image generation share the window; when one clears the other usually follows.
  await new Promise((r) => setTimeout(r, t ? 45000 : 25000));
}
console.log("STILL_LIMITED");
process.exit(1);
