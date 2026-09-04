import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

const OUT = '/home/z/my-project/public/img/work';
fs.mkdirSync(OUT, { recursive: true });

const BASE = 'high quality, detailed, cinematic film still, professional color grade, no text, no watermark, no letters';

const JOBS = [
  {
    file: 'portrait.png',
    size: '1152x864',
    prompt: `Ultra-realistic studio portrait of a confident young African man in a black turtleneck, looking into the camera with a slight smile, dramatic red rim lighting from the left, pure black studio backdrop, subtle film grain, shallow depth of field, ${BASE}`,
  },
  {
    file: 'brand.png',
    size: '1152x864',
    prompt: `Modern anime illustration of a stylish young African businesswoman with braids in a red blazer, presenting colorful brand mood boards on a white studio wall, red and black accents, confident pose, crisp cel shading, ${BASE}`,
  },
  {
    file: 'editorial.png',
    size: '1152x864',
    prompt: `High-fashion editorial photograph, elegant African woman in a flowing red gown, fabric swirling dramatically in the wind, black studio background, single dramatic spotlight, magazine cover energy, ${BASE}`,
  },
  {
    file: 'event.png',
    size: '1152x864',
    prompt: `Joyful 3D children's cartoon style scene of animated kids celebrating at a birthday party, red and black balloons, confetti falling, big smiles, cake on the table, Pixar-like soft lighting, vibrant, ${BASE}`,
  },
  {
    file: 'studio.png',
    size: '1152x864',
    prompt: `2D cartoon illustration of a cheerful African boy director wearing a red cap, sitting behind a professional film camera on a movie set, big studio lights and boom mic around him, clapperboard in hand, red and black color scheme, ${BASE}`,
  },
  {
    file: 'commercial.png',
    size: '1152x864',
    prompt: `Dynamic commercial product shot of a white and red sneaker mid-air with a splash of red paint frozen around it, dramatic black background, studio strobe lighting, ultra realistic advertising photography, ${BASE}`,
  },
];

async function main() {
  const zai = await ZAI.create();
  for (const job of JOBS) {
    const out = path.join(OUT, job.file);
    if (fs.existsSync(out) && fs.statSync(out).size > 100000) {
      console.log(`skip ${job.file} (exists)`);
      continue;
    }
    let ok = false;
    for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
      try {
        const r = await zai.images.generations.create({ prompt: job.prompt, size: job.size });
        const b64 = r?.data?.[0]?.base64;
        if (!b64) throw new Error('no base64');
        const buf = Buffer.from(b64, 'base64');
        if (buf.length < 50000) throw new Error(`too small: ${buf.length}`);
        fs.writeFileSync(out, buf);
        console.log(`OK ${job.file} ${job.size} ${(buf.length / 1024).toFixed(0)}KB`);
        ok = true;
      } catch (e) {
        console.error(`FAIL ${job.file} attempt ${attempt}: ${e.message}`);
        await new Promise((res) => setTimeout(res, 2500 * attempt));
      }
    }
  }
  console.log('done');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
