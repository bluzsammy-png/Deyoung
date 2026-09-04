// DeYoung promo v3 — Step 1: generate character/style reference frames (i2v sources).
// Usage: node scripts/v3_chars.mjs
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";
import { execSync } from "child_process";

const OUT = "/home/z/my-project/campaign/film/v3/chars";
fs.mkdirSync(OUT, { recursive: true });

// 1344x768 ≈ 16:9 landscape — feeds 1920x1080 i2v
const FRAMES = {
  c1: `Flat vector-style 2D cartoon illustration, bold clean outlines, bright saturated colors: a cheerful young man with round glasses and a yellow hoodie sitting at a tidy creative desk with a laptop, looking amazed as colorful light bursts from the laptop screen, modern minimalist home office, big expressive eyes, white background with red accents, no text, no letters`,
  c2: `Minimalist stick figure drawing, thick bold black lines on a clean white background, a confident stick-man character mid-stride walking toward three simple doors floating in the scene, playful energy, subtle red accent on one door, hand-drawn marker style, no text, no letters`,
  c3: `Ultra realistic cinematic photograph: a stylish young woman relaxing on a cozy sofa in a warm modern living room, holding a smartphone with both hands, soft window light, shallow depth of field, golden hour tones, genuine excited smile looking at the phone, filmic color grade, no text, no letters`,
  c4: `Vibrant anime illustration, studio-quality cel shading: a determined anime girl film director with short purple hair wearing headphones around her neck, standing in a dark studio surrounded by floating glowing holographic video screens and a light storyboard, dramatic rim lighting in red and cyan, dynamic composition, no text, no letters`,
  c5: `Children's storybook illustration, soft crayon and pastel texture: a cute rounded toy-like robot with big friendly eyes holding a glowing gift box shaped like a video frame, kindergarten drawing style with gentle primary colors, cheerful and innocent, simple shapes, no text, no letters`,
  c6: `Creative split-style illustration of two creators standing side by side in a film studio: the left person rendered in vibrant anime cel-shaded style with purple hair, the right person rendered in photorealistic cinematic style wearing a denim jacket, both smiling confidently at the camera, dramatic red practical lights in the background, no text, no letters`,
  c7: `Ultra realistic cinematic photograph: a young man standing on a city rooftop at dusk, holding up a smartphone displaying a bright colorful video player screen, city bokeh lights behind him, satisfied proud expression looking at the phone, shallow depth of field, filmic grade, no text, no letters`,
  c8: `Group lineup illustration of five diverse characters standing shoulder to shoulder facing the camera and smiling: a flat cartoon man in a yellow hoodie, a bold black stick figure, a photorealistic young woman, a vibrant anime girl with purple hair, and a cute crayon-style robot, each rendered in their own distinct art style, clean dark studio background with subtle red rim light, no text, no letters`,
};

const zai = await ZAI.create();
const results = {};
for (const [id, prompt] of Object.entries(FRAMES)) {
  const file = `${OUT}/${id}.png`;
  if (fs.existsSync(file) && fs.statSync(file).size > 50000) { results[id] = "EXISTS"; continue; }
  for (let a = 1; a <= 4; a++) {
    try {
      const r = await zai.images.generations.create({ prompt, size: "1344x768" });
      const b64 = r?.data?.[0]?.b64_json || r?.data?.[0]?.base64 || r?.images?.[0]?.b64_json;
      const url = r?.data?.[0]?.url || r?.images?.[0]?.url;
      if (b64) { fs.writeFileSync(file, Buffer.from(b64, "base64")); results[id] = "B64_OK"; break; }
      if (url) {
        execSync(`curl -sL --max-time 60 -o "${file}" "${url}"`);
        results[id] = "URL_OK"; break;
      }
      results[id] = "NO_DATA: " + JSON.stringify(r).slice(0, 120);
    } catch (e) {
      results[id] = `ERR${a}: ` + e.message.slice(0, 120);
      await new Promise(r2 => setTimeout(r2, 8000));
    }
  }
  console.log(id, results[id]);
}
console.log("CHARS_DONE", JSON.stringify(results));
