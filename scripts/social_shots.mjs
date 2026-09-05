// Capture DeYoung site screenshots for social device mockups.
import { chromium } from "playwright";

const OUT = "/home/z/my-project/campaign/social/shots";
import fs from "fs";
fs.mkdirSync(OUT, { recursive: true });

const b = await chromium.launch();
try {
  // desktop
  const d = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await d.goto("http://localhost:3000/", { waitUntil: "networkidle", timeout: 45000 });
  await d.waitForTimeout(2500);
  await d.screenshot({ path: `${OUT}/web-home.png` });
  await d.evaluate(() => { location.hash = "#plans"; });
  await d.waitForTimeout(2200);
  await d.screenshot({ path: `${OUT}/web-plans.png` });

  // mobile
  const m = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await m.goto("http://localhost:3000/", { waitUntil: "networkidle", timeout: 45000 });
  await m.waitForTimeout(2200);
  await m.screenshot({ path: `${OUT}/mob-home.png` });
  await m.evaluate(() => { location.hash = "#plans"; });
  await m.waitForTimeout(2000);
  await m.screenshot({ path: `${OUT}/mob-plans.png` });
  await m.evaluate(() => { location.hash = "#request"; });
  await m.waitForTimeout(2000);
  await m.screenshot({ path: `${OUT}/mob-request.png` });
  console.log("SHOTS_OK");
} catch (e) {
  console.log("SHOT_ERR", e.message.slice(0, 200));
} finally {
  await b.close();
}
