// QA: homepage visuals + film playback WITH audio.
import { chromium } from "playwright";

const OUT = "/home/z/my-project/campaign/qa";
const errors = [];
const b = await chromium.launch();
const pg = await b.newPage({ viewport: { width: 1280, height: 900 } });
pg.on("pageerror", (e) => errors.push("pageerror: " + e.message.slice(0, 120)));
pg.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text().slice(0, 120)); });

await pg.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 45000 });
await pg.waitForTimeout(1500);
await pg.screenshot({ path: `${OUT}/qa-home-desktop.png` });

// font check
const font = await pg.evaluate(() => getComputedStyle(document.body).fontFamily);
// video playback WITH audio
const videoState = await pg.evaluate(async () => {
  const v = document.querySelector("video");
  if (!v) return { found: false };
  v.muted = false;
  v.volume = 1;
  try { await v.play(); } catch (e) { return { found: true, playErr: String(e).slice(0, 100) }; }
  await new Promise((r) => setTimeout(r, 4000));
  return {
    found: true,
    muted: v.muted,
    currentTime: Number(v.currentTime.toFixed(2)),
    readyState: v.readyState,
    paused: v.paused,
    duration: Number(v.duration.toFixed(2)),
    audioPresent: !!(v.mozHasAudio || v.webkitAudioDecodedByteCount > 0 || v.audioTracks?.length),
  };
});
await pg.screenshot({ path: `${OUT}/qa-video-playing.png` });

// mobile
const m = await b.newPage({ viewport: { width: 390, height: 844 } });
await m.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 45000 });
await m.waitForTimeout(800);
await m.screenshot({ path: `${OUT}/qa-home-mobile.png` });

console.log("FONT:", font.slice(0, 80));
console.log("VIDEO:", JSON.stringify(videoState));
console.log("ERRORS:", errors.length ? errors.slice(0, 5) : "none");
await b.close();
