#!/usr/bin/env node
/* Task 59 — cinematic flyer backgrounds (SDK direct, API-compliant sizes) */
const ZAI = require("/home/z/my-project/node_modules/z-ai-web-dev-sdk").default;
const fs = require("fs");

const OUT = "/home/z/my-project/campaign/flyers59/bg";

const JOBS = [
  {
    file: "bg-control.png",
    size: "1408x768",
    prompt:
      "Ultra wide cinematic shot of a dark AI render control room at night, long wall of glowing monitors showing abstract crimson waveforms and video timelines, lone silhouette standing with back to camera, volumetric red light spill on the floor, deep blacks, anamorphic widescreen flare, 35mm film grain, photorealistic, high contrast charcoal and crimson grade, no text, no letters, no readable words, no watermark",
  },
  {
    file: "bg-ribbon.png",
    size: "768x1408",
    prompt:
      "Vertical epic cinematic composition, lone figure standing in a vast dark warehouse studio looking up at a giant sweeping ribbon of glowing crimson light, volumetric fog, dramatic red rim light on the figure from behind, deep blacks, huge dark negative space above for typography, anamorphic flare, 35mm film grain, photorealistic, no text, no watermark, face not visible",
  },
  {
    file: "bg-silk.png",
    size: "864x1152",
    prompt:
      "Luxurious abstract macro photograph, flowing ribbons of crimson red light sweeping across draped black silk fabric, elegant deep folds, dramatic studio lighting, deep shadows, rich texture, high contrast, subtle film grain, photorealistic, dark moody premium aesthetic, no text, no watermark",
  },
];

(async () => {
  const zai = await ZAI.create();
  for (const j of JOBS) {
    const out = `${OUT}/${j.file}`;
    if (fs.existsSync(out) && fs.statSync(out).size > 100000) {
      console.log("skip (exists):", j.file);
      continue;
    }
    process.stdout.write("gen " + j.file + " ... ");
    const r = await zai.images.generations.create({ prompt: j.prompt, size: j.size });
    const b64 = r && r.data && r.data[0] && r.data[0].base64;
    if (!b64) throw new Error("no base64 for " + j.file);
    fs.writeFileSync(out, Buffer.from(b64, "base64"));
    console.log("ok", fs.statSync(out).size, "bytes");
  }
  console.log("ALL DONE");
})().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
