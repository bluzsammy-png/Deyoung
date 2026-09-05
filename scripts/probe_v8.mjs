import ZAI from "z-ai-web-dev-sdk";
const zai = await ZAI.create();
const t0 = Date.now();
try {
  const r = await zai.audio.tts.create({ input: "Testing one two.", voice: "xiaochen", speed: 1.0, response_format: "wav", stream: false });
  const buf = Buffer.from(new Uint8Array(await r.arrayBuffer()));
  console.log("TTS OK", buf.length, "bytes in", ((Date.now()-t0)/1000).toFixed(1) + "s");
} catch (e) { console.log("TTS FAIL", ((Date.now()-t0)/1000).toFixed(1)+"s", (e?.message||String(e)).slice(0,200)); }
const t1 = Date.now();
try {
  const r = await zai.images.generations.create({ prompt: "a red circle on white background, minimal", size: "1024x1024" });
  const b64 = r?.data?.[0]?.base64 || r?.data?.[0]?.b64_json;
  console.log("IMG OK", b64 ? Buffer.from(b64,"base64").length : 0, "bytes in", ((Date.now()-t1)/1000).toFixed(1) + "s");
} catch (e) { console.log("IMG FAIL", ((Date.now()-t1)/1000).toFixed(1)+"s", (e?.message||String(e)).slice(0,200)); }
