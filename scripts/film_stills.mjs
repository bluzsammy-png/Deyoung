// Generate DeYoung film character/scene stills (foreground-safe, sequential).
import ZAI from "z-ai-web-dev-sdk";
import fs from "fs";

const OUT = "/home/z/my-project/campaign/social";
const SHEETS = "/home/z/my-project/campaign/social/stills.json";

const AMARA = "ultra realistic cinematic portrait, Amara, a radiant young Black woman filmmaker in her late 20s, natural coily hair tied back, warm confident eyes, deep skin tone with warm highlights, wearing a deep burgundy silk jacket, standing in a dark film studio lit by soft crimson rim light and volumetric haze, looking straight into camera mid-sentence with mouth slightly open as if speaking passionately, shallow depth of field, 85mm lens, filmic color grade, red and black palette, 8k detail";
const KOJO = "ultra realistic cinematic portrait, Kojo, a charismatic Black man in his early 30s, short dreadlocks, neatly trimmed beard, wearing a black crew-neck sweatshirt with a small red crest, in a moody editing suite with dark walls and glowing red monitor light, mid-speech facing camera with animated expression, mouth open talking, cinematic rim lighting, shallow depth of field, 85mm lens, red and black filmic grade, 8k detail";
const DUO = "ultra realistic cinematic medium two-shot, Amara a young Black woman filmmaker in burgundy silk jacket and Kojo a Black man with short dreadlocks in black sweatshirt, standing side by side in a dark soundstage, both facing camera mid-conversation smiling, bold crimson practical lights and haze behind them, anamorphic look, filmic red-and-black grade, 8k detail";
const SILK = "abstract cinematic background, flowing crimson red silk fabric over deep black shadows, dramatic chiaroscuro lighting, elegant slow folds, macro texture, luxury film-title mood, red and black palette, ultra detailed, 8k";

const jobs = [
  ["amara.png", AMARA, "1024x1024"],
  ["kojo.png", KOJO, "1024x1024"],
  ["duo.png", DUO, "1344x768"],
  ["silk.png", SILK, "1344x768"],
];

const zai = await ZAI.create();
const state = fs.existsSync(SHEETS) ? JSON.parse(fs.readFileSync(SHEETS, "utf8")) : {};
const only = process.argv[2]; // optional: regenerate a single file

for (const [name, prompt, size] of jobs) {
  if (only && only !== name) continue;
  if (!only && state[name] === "done" && fs.existsSync(`${OUT}/${name}`)) {
    console.log("skip", name); continue;
  }
  let ok = false;
  for (let a = 1; a <= 3 && !ok; a++) {
    try {
      const r = await zai.images.generations.create({ prompt, size });
      const b64 = r?.data?.[0]?.base64;
      if (!b64) throw new Error("no base64");
      fs.writeFileSync(`${OUT}/${name}`, Buffer.from(b64, "base64"));
      console.log("done", name, fs.statSync(`${OUT}/${name}`).size);
      ok = true;
    } catch (e) {
      console.log(`retry ${a} ${name}:`, e.message);
      await new Promise(r => setTimeout(r, 2000 * a));
    }
  }
  state[name] = ok ? "done" : "fail";
  fs.writeFileSync(SHEETS, JSON.stringify(state, null, 2));
}
console.log("STILLS_COMPLETE");
