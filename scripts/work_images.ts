// Recent Works — real work sample per category tile (Portrait, Brand, Editorial,
// Event, Studio, Commercial). Photorealistic client-work stills, brand-tied
// red accents. Output: /home/z/my-project/public/img/work/v2-<cat>.png (1024x768 = 4:3 tiles)
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const OUT = "/home/z/my-project/public/img/work";
fs.mkdirSync(OUT, { recursive: true });

const WORKS = [
  {
    id: "portrait",
    prompt:
      "professional portrait photography, dramatic studio portrait of a young Nigerian woman, " +
      "deep crimson red gel lighting on one side of her face, pure black background, confident gaze, " +
      "medium format look, razor sharp, magazine quality portfolio piece, no text",
  },
  {
    id: "brand",
    prompt:
      "brand campaign photography, stylish Nigerian man in a bold crimson red jacket against a minimal " +
      "concrete wall, fashion lookbook aesthetic, strong shadows, editorial composition, " +
      "professional commercial portfolio piece, no text",
  },
  {
    id: "editorial",
    prompt:
      "high-fashion editorial photography, Nigerian model in avant-garde sculptural outfit, " +
      "hard directional light, crimson red fabric accent flowing, dark studio, dramatic pose, " +
      "magazine editorial spread quality, no text",
  },
  {
    id: "event",
    prompt:
      "event photography, packed concert crowd with hands raised in the air, crimson red and white stage light beams " +
      "cutting through haze, confetti falling, lead performer silhouetted far away on stage, shot from inside the crowd, " +
      "pure energy, completely wordless image, absolutely no signage no banners no writing no letters no typography anywhere, no text",
  },
  {
    id: "studio",
    prompt:
      "behind the scenes photography inside a film studio: videographer operating a cinema camera on a gimbal, " +
      "softbox and red practical lights, dark studio set, crew monitors glowing, professional production still, no text",
  },
  {
    id: "commercial",
    prompt:
      "commercial product photography, luxury perfume bottle frozen splash, dramatic crimson red and white " +
      "studio lighting on black, water droplets suspended, ultra sharp advertising key visual, no text",
  },
];

async function main() {
  const zai = await ZAI.create();
  for (const job of WORKS) {
    const dst = `${OUT}/v2-${job.id}.png`;
    if (fs.existsSync(dst) && fs.statSync(dst).size > 100000) {
      console.log(`SKIP ${job.id}`);
      continue;
    }
    let ok = false;
    for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
      try {
        const res = await zai.images.generations.create({
          prompt: job.prompt,
          size: "1024x768",
        });
        const b64 = res?.data?.[0]?.base64 || res?.data?.[0]?.b64_json;
        if (!b64) throw new Error("no data");
        const buf = Buffer.from(b64, "base64");
        if (buf.length < 50000) throw new Error("tiny image " + buf.length);
        fs.writeFileSync(dst, buf);
        console.log(`OK ${job.id} bytes=${buf.length}`);
        ok = true;
      } catch (e: any) {
        console.log(`RETRY ${job.id}#${attempt}: ${(e?.message || String(e)).slice(0, 120)}`);
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
    if (!ok) {
      console.log(`FAIL ${job.id}`);
      process.exitCode = 1;
    }
  }
}
main().catch((e) => {
  console.log("CRASH " + (e?.message || String(e)).slice(0, 200));
  process.exit(1);
});
