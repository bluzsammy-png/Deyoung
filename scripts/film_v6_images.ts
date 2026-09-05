// DeYoung film v6 — TALKING CHARACTERS edition.
// Generates:
//   A) 4 character diptychs (16:9 sprite sheets: left = mouth closed, right = mouth open)
//   B) 3 non-talking scene stills (hook city, come-alive montage, mobile/web studio)
// Output: /home/z/my-project/campaign/v6/img/*.png
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const OUT = "/home/z/my-project/campaign/v6/img";
fs.mkdirSync(OUT, { recursive: true });

const STYLE =
  "flat vector cartoon illustration, bold clean shapes, thick outlines, " +
  "DeYoung brand colors: deep black background, vivid crimson red (#DC2626) and white accents, " +
  "cinematic rim lighting, modern Nigerian characters, confident expressive faces, " +
  "16:9 widescreen composition, diptych with a clean vertical split exactly down the middle: " +
  "LEFT panel and RIGHT panel show the IDENTICAL character, same clothes, same pose, same background, " +
  "ONLY the mouth differs. ";

const CHARACTERS = [
  {
    id: "amara",
    prompt:
      STYLE +
      "LEFT: young Nigerian woman creative director, short natural hair, red turtleneck, gold hoop earrings, " +
      "plain dark edit suite background with soft red monitor glow, no signs no writing anywhere, " +
      "confident warm friendly expression, relaxed eyebrows, gentle closed-mouth smile, MOUTH COMPLETELY SHUT, lips together, no teeth showing. " +
      "RIGHT: the exact same woman, same confident warm relaxed expression, same pose same clothes same background, " +
      "only her jaw dropped MOUTH STRETCHED WIDE OPEN mid-speech, big open dark mouth cavity, upper teeth visible, clearly talking, still friendly and confident.",
  },
  {
    id: "kossi",
    prompt:
      STYLE +
      "LEFT: young Nigerian man cinematographer, fade haircut, black bomber jacket with red zipper, " +
      "holding a cinema camera on his shoulder in a dark studio with red practical lights, relaxed smile MOUTH FULLY CLOSED. " +
      "RIGHT: the exact same man, same pose same clothes same background, MOUTH WIDE OPEN mid-speech, teeth visible.",
  },
  {
    id: "zola",
    prompt:
      STYLE +
      "LEFT: young Nigerian woman producer, braided ponytail, white hoodie with red headphones around neck, " +
      "holding a large smartphone showing a red play button, dark city rooftop at dusk behind her, bright smile MOUTH FULLY CLOSED. " +
      "RIGHT: the exact same woman, same pose same clothes same background, MOUTH WIDE OPEN mid-speech, teeth visible.",
  },
  {
    id: "dee",
    prompt:
      STYLE +
      "LEFT: the DeYoung mascot, confident young Nigerian man with a glowing red play-button symbol floating above his palm, " +
      "black varsity jacket with red trim, dark studio with red spotlight behind, charismatic closed-mouth grin. " +
      "RIGHT: the exact same mascot man, same pose same clothes same background, MOUTH WIDE OPEN mid-speech, teeth visible.",
  },
];

const SCENES = [
  {
    id: "hook",
    prompt:
      "flat vector cartoon illustration, bold clean shapes, thick outlines, DeYoung brand colors: black, crimson red, white. " +
      "Epic wide shot of Lagos at dawn: skyline silhouette, mainland bridge, deep red sun rising, " +
      "a giant glowing red play-button symbol hovering in the sky like a second sun, " +
      "searchlights, cinematic 16:9 widescreen, no text, no words, no letters.",
  },
  {
    id: "alive",
    prompt:
      "flat vector cartoon illustration, bold clean shapes, thick outlines, black background, crimson red and white accents. " +
      "Explosive montage collage bursting outward from a bright red play button: film strips, frames, " +
      "clapperboard, camera, music notes, light rays radiating, dynamic diagonal energy, " +
      "16:9 widescreen, no text, no words, no letters.",
  },
  {
    id: "anywhere",
    prompt:
      "flat vector cartoon illustration, bold clean shapes, thick outlines, DeYoung brand colors: black, crimson red, white. " +
      "Split composition: left half a hand holding a large smartphone showing a red play button and film timeline, " +
      "right half a laptop with the same red editing interface, both on a dark desk with red ambient light, " +
      "16:9 widescreen, no text, no words, no letters.",
  },
];

async function main() {
  const zai = await ZAI.create();
  for (const job of [...CHARACTERS, ...SCENES]) {
    const dst = `${OUT}/${job.id}.png`;
    if (fs.existsSync(dst) && fs.statSync(dst).size > 100000) {
      console.log(`SKIP ${job.id}`);
      continue;
    }
    let ok = false;
    for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
      try {
        const res = await zai.images.generations.create({
          prompt: job.prompt,
          size: "2880x832",
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
