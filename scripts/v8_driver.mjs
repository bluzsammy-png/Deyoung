// v8 driver — waits for the z-ai quota, then immediately generates assets.
// Repeats probe -> generate cycles until every v8 asset exists or the burst
// deadline hits (fits a 10-min tool call). Resume-safe: the asset script
// skips files that already exist.
import { execSync, spawnSync } from "child_process";
import fs from "fs";

const DEADLINE = Date.now() + 8.7 * 60 * 1000;
const IMG = "/home/z/my-project/campaign/v8/img";
const VOX = "/home/z/my-project/campaign/v8/voices";
const NEED_IMG = ["quad", "kid", "anime", "stick", "real", "host", "sc_kids", "sc_anime", "sc_stick", "sc_real", "sc_split", "sc_make"];
const NEED_VOX = ["v01_hook", "v02_kid", "v03_anime", "v04_stick", "v05_real", "v06_styles", "v06b_split", "v07_make", "v08_join", "v09_end"];

function missing() {
  const m = [];
  for (const id of NEED_IMG) {
    const p = `${IMG}/${id}.png`;
    if (!(fs.existsSync(p) && fs.statSync(p).size > 150000)) m.push("img:" + id);
  }
  for (const id of NEED_VOX) {
    const p = `${VOX}/${id}.wav`;
    if (!(fs.existsSync(p) && fs.statSync(p).size > 12000)) m.push("vox:" + id);
  }
  return m;
}

let round = 0;
while (Date.now() < DEADLINE) {
  round++;
  const left = missing();
  if (left.length === 0) {
    console.log("ASSETS_COMPLETE");
    process.exit(0);
  }
  console.log(`-- round ${round}: ${left.length} missing (${left.slice(0, 6).join(",")}${left.length > 6 ? "…" : ""})`);
  const w = spawnSync("node", ["scripts/zai_wait.mjs"], { cwd: "/home/z/my-project", timeout: 8.4 * 60 * 1000 });
  const out = (w.stdout?.toString() || "") + (w.stderr?.toString() || "");
  if (/ZAI_RECOVERED/.test(out)) {
    console.log("quota recovered — generating");
    try {
      const g = spawnSync("node", ["scripts/film_v8_assets.mjs"], { cwd: "/home/z/my-project", timeout: 8.4 * 60 * 1000 });
      console.log((g.stdout?.toString() || "").split("\n").slice(-14).join("\n"));
    } catch (e) {
      console.log("gen burst ended:", String(e).slice(0, 120));
    }
  } else {
    console.log("still limited, cycling");
  }
}
const left = missing();
console.log(left.length === 0 ? "ASSETS_COMPLETE" : `BURST_END missing=${left.length}: ${left.join(",")}`);
