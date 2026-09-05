// Probe: is z-ai SDK (TTS + image) responsive again? Tiny calls, short timeout.
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

async function main() {
  const zai = await ZAI.create();
  // 1) TTS probe
  try {
    const res = await withTimeout(
      zai.audio.tts.create({
        input: "Testing.",
        voice: "tongtong",
        speed: 1.0,
        response_format: "wav",
        stream: false,
      }),
      30000
    );
    const ab = await res.arrayBuffer();
    const buf = Buffer.from(new Uint8Array(ab));
    fs.writeFileSync("/home/z/my-project/scripts/probe_tts.wav", buf);
    console.log("TTS_OK bytes=" + buf.length);
  } catch (e: any) {
    console.log("TTS_FAIL " + (e?.message || String(e)).slice(0, 160));
  }
  // 2) Image probe
  try {
    const res = await withTimeout(
      zai.images.generations.create({
        prompt: "test swatch, red rectangle on white",
        size: "512x512",
      }),
      45000
    );
    const b64 = res?.data?.[0]?.base64 || res?.data?.[0]?.b64_json;
    if (b64) {
      fs.writeFileSync(
        "/home/z/my-project/scripts/probe_img.png",
        Buffer.from(b64, "base64")
      );
      console.log("IMG_OK");
    } else console.log("IMG_FAIL no data");
  } catch (e: any) {
    console.log("IMG_FAIL " + (e?.message || String(e)).slice(0, 160));
  }
}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error("timeout " + ms)), ms)),
  ]);
}

main().catch((e) => {
  console.log("PROBE_CRASH " + (e?.message || String(e)).slice(0, 160));
  process.exit(0);
});
