#!/usr/bin/env python3
"""Render the DeYoung D-play monogram to a transparent PNG via Playwright."""
import asyncio, os
from playwright.async_api import async_playwright

OUT = "/home/z/my-project/campaign/social/mark-red.png"
SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#F04343"/><stop offset="1" stop-color="#B91C1C"/>
    </linearGradient>
  </defs>
  <path fill="url(#g)" fill-rule="evenodd" d="
    M300 90 h210 c210 0 350 150 350 400 s-140 400 -350 400 H300 Z
    M470 260 v460 h40 c110 0 175 -90 175 -230 s-65 -230 -175 -230 Z"/>
  <circle cx="238" cy="512" r="74" fill="#FFFFFF"/>
  <path d="M226 470 l96 42 -96 42 Z" fill="#DC2626"/>
</svg>"""

async def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1024, "height": 1024})
        await pg.set_content(f"<body style='margin:0'>{SVG}</body>")
        await pg.screenshot(path=OUT, omit_background=True)
        await b.close()
    print("mark ->", OUT, os.path.getsize(OUT))

asyncio.run(main())
