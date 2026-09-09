#!/usr/bin/env python3
"""Task 59 — render DeYoung social flyers (HTML/CSS -> PNG via Playwright)."""
from playwright.sync_api import sync_playwright
import os

B = "/home/z/my-project"
SRC = f"{B}/campaign/flyers59"
OUT = f"{B}/download/social"
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("poster-4x5.html",   1080, 1350, "deyoung-poster-4x5.png"),
    ("plans-1x1.html",    1080, 1080, "deyoung-plans-1x1.png"),
    ("story-9x16.html",   1080, 1920, "deyoung-story-9x16.png"),
    ("banner-16x9.html",  1600,  900, "deyoung-banner-16x9.png"),
    ("film-4x5.html",     1080, 1350, "deyoung-film-4x5.png"),
    ("trust-1x1.html",    1080, 1080, "deyoung-trust-1x1.png"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--force-color-profile=srgb"])
    for f, w, h, out in JOBS:
        pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.goto(f"file://{SRC}/{f}")
        pg.wait_for_load_state("networkidle")
        pg.evaluate("() => document.fonts.ready")
        pg.wait_for_timeout(450)
        # fail loudly on broken images / fonts
        broken = pg.evaluate(
            "() => [...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src)"
        )
        assert not broken, f"{f}: broken images {broken}"
        pg.screenshot(path=f"{OUT}/{out}")
        sz = os.path.getsize(f"{OUT}/{out}")
        print(f"OK {out}  {sz} bytes")
        pg.close()
    browser.close()
print("ALL RENDERED")
