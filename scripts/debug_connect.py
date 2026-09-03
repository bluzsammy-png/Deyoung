"""Debug: capture console + network during the connect flow."""
import asyncio, os, shutil, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

PATI = Path("/home/z/my-project/pati")
DATA = Path("/tmp/pati_dbg2")
PORT = 8023
BASE = f"http://127.0.0.1:{PORT}"

async def main():
    shutil.rmtree(DATA, ignore_errors=True); DATA.mkdir(parents=True)
    env = dict(os.environ, PATI_DATA_DIR=str(DATA))
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "pati_api.app:app",
                             "--port", str(PORT)], cwd=str(PATI), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        token = ""
        for _ in range(40):
            time.sleep(0.5)
            tf = DATA / "bootstrap_admin_token.txt"
            if tf.exists():
                token = tf.read_text().strip(); break
        async with async_playwright() as p:
            b = await p.chromium.launch()
            page = await b.new_page(viewport={"width": 1280, "height": 900})
            page.on("console", lambda m: print(f"[{m.type}] {m.text}"))
            page.on("pageerror", lambda e: print(f"[PAGEERROR] {e}"))
            page.on("response", lambda r: print(f"[{r.status}] {r.url}") 
                    if "/api/" in r.url else None)
            await page.goto(BASE + "/", wait_until="networkidle")
            await page.wait_for_timeout(500)
            await page.fill("#tokenInput", token)
            await page.click("#connectBtn")
            await page.wait_for_timeout(3000)
            print("connLabel:", await page.text_content("#connLabel"))
            print("connMsg:", await page.text_content("#connMsg"))
            await b.close()
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill()

asyncio.run(main())
