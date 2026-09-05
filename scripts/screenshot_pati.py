"""Screenshot PATI status page + API docs, desktop and phone viewport."""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = "/home/z/my-project/download"

SHOTS = [
    ("status_page", "/", 1280, 800),        # desktop view of the dashboard
    ("status_page_phone", "/", 390, 844),   # iPhone-sized view
    ("api_docs", "/docs", 1280, 800),       # interactive API console
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name, path, w, h in SHOTS:
            page = await browser.new_page(viewport={"width": w, "height": h})
            await page.goto(BASE + path, wait_until="networkidle")
            await page.wait_for_timeout(400)
            await page.screenshot(path=f"{OUT}/pati_{name}.png", full_page=True)
            await page.close()
            print(f"saved pati_{name}.png ({w}x{h})")
        await browser.close()

asyncio.run(main())
