#!/usr/bin/env python3
"""DeYoung logo rebrand: new D-play mark + full asset set.
Design: bold geometric D, play-triangle counter cut, cinematic red gradient,
top bevel highlight. Renders SVG + PNG app icons + og-image via Playwright.
"""
import asyncio, os, base64
from playwright.async_api import async_playwright

BASE = "/home/z/my-project"
FONT = f"{BASE}/scripts/Archivo.ttf"

# ---------- the mark (viewBox 1024) ----------
# D: squircle-ish bowl; counter: confident play triangle cut out (evenodd)
GRAD = (
    '<linearGradient id="dg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#FF6A5E"/>'
    '<stop offset="0.45" stop-color="#E11D2E"/>'
    '<stop offset="1" stop-color="#8F0E1E"/>'
    "</linearGradient>"
)
D_PATH = (
    "M300 90 H520 C758 90 900 268 900 512 C900 756 758 934 520 934 H300 Z "
    "M462 296 L772 512 L462 728 Z"
)
BEVEL = (
    "M300 90 H520 C636 90 731 124 806 196 C716 148 618 132 520 132 H300 Z"
)

def mark_svg(size=1024, bg=None):
    rect = f'<rect width="1024" height="1024" rx="{bg[1]}" fill="{bg[0]}"/>' if bg else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 1024 1024">
<defs>{GRAD}</defs>
{rect}
<path fill="url(#dg)" fill-rule="evenodd" d="{D_PATH}"/>
<path fill="#FFFFFF" opacity="0.16" d="{BEVEL}"/>
</svg>'''

def write(path, text):
    with open(path, "w") as f:
        f.write(text)
    print("wrote", path, os.path.getsize(path))

os.makedirs(f"{BASE}/public/fonts", exist_ok=True)

# 1) standalone mark + favicon (transparent)
write(f"{BASE}/public/logo.svg", mark_svg())
write(f"{BASE}/public/favicon.svg", mark_svg(64))

# 2) self-host the display font for the site (Next local font + CSS fallback)
import shutil
shutil.copy(f"{BASE}/scripts/Archivo.ttf", f"{BASE}/public/fonts/Archivo.ttf")
print("font copied -> public/fonts/Archivo.ttf")

MARK_B64 = base64.b64encode(mark_svg().encode()).decode()

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Archivo'; src:url('file://{FONT}') format('truetype-variations'); font-weight:100 900; }}
* {{ margin:0; box-sizing:border-box; }}
body {{ background:#222; font-family:'Archivo',sans-serif; display:flex; flex-direction:column; gap:24px; padding:24px; align-items:flex-start; }}
.ic {{ border-radius:23.1%; background:
      radial-gradient(120% 120% at 20% 0%, #1C1C1E 0%, #0A0A0B 55%, #050506 100%);
      display:flex; align-items:center; justify-content:center; position:relative;
      box-shadow: inset 0 0 0 2.5% rgba(225,29,46,.85), inset 0 2% 6% rgba(255,255,255,.08); }}
.ic svg {{ filter: drop-shadow(0 3% 4% rgba(0,0,0,.45)); }}
.row {{ display:flex; gap:24px; align-items:flex-start; }}
.og {{ width:1200px; height:630px; background:#0A0A0B; position:relative; overflow:hidden; }}
.og .glow {{ position:absolute; width:900px; height:900px; right:-260px; top:-330px; border-radius:50%;
      background:radial-gradient(circle, rgba(225,29,46,.30) 0%, rgba(225,29,46,.10) 40%, transparent 68%); }}
.og .glow2 {{ position:absolute; width:700px; height:700px; left:-280px; bottom:-380px; border-radius:50%;
      background:radial-gradient(circle, rgba(225,29,46,.16) 0%, transparent 62%); }}
.og .inner {{ position:absolute; inset:0; padding:76px 84px; display:flex; flex-direction:column; }}
.og .brand {{ display:flex; align-items:center; gap:34px; }}
.og h1 {{ color:#fff; font-size:150px; font-weight:900; letter-spacing:-.03em; line-height:.95; }}
.og h1 .r {{ color:#E11D2E; }}
.chip {{ margin-top:26px; display:inline-flex; width:fit-content; border:2px solid rgba(255,255,255,.22);
      color:rgba(255,255,255,.82); font-weight:700; letter-spacing:.34em; font-size:24px; padding:12px 22px; }}
.chip b {{ color:#E11D2E; margin-right:14px; }}
.og p.sub {{ margin-top:30px; color:rgba(255,255,255,.62); font-size:30px; font-weight:500; max-width:880px; line-height:1.35; }}
.sprockets {{ position:absolute; left:84px; right:84px; bottom:40px; display:flex; gap:14px; }}
.sprockets i {{ flex:1; height:12px; border-radius:4px; background:rgba(225,29,46,.55); }}
.sprockets i:nth-child(3n) {{ background:rgba(255,255,255,.30); }}
.og .corner {{ position:absolute; top:0; left:0; right:0; height:10px; background:linear-gradient(90deg,#E11D2E,#8F0E1E); }}
.lock {{ display:flex; align-items:center; gap:18px; }}
.lock .w {{ color:#fff; font-weight:900; font-size:44px; letter-spacing:-.02em; }}
</style></head><body>

<!-- app icon 512 -->
<div id="icon512" class="ic" style="width:512px;height:512px">{mark_svg(320)}</div>
<!-- maskable: full bleed, mark 62% -->
<div id="maskable" class="ic" style="width:512px;height:512px;border-radius:0;box-shadow:none">{mark_svg(310)}</div>
<!-- apple touch 180 -->
<div id="apple" class="ic" style="width:180px;height:180px">{mark_svg(112)}</div>
<!-- favicon 64 -->
<div id="fav" class="ic" style="width:64px;height:64px;box-shadow:inset 0 0 0 2px rgba(225,29,46,.9)">{mark_svg(40)}</div>

<!-- og image -->
<div class="og" id="og">
  <div class="corner"></div><div class="glow"></div><div class="glow2"></div>
  <div class="inner">
    <div class="brand">{mark_svg(170)}
      <div>
        <h1>DE<span class="r">YOUNG</span></h1>
        <div class="chip"><b>&#9654;</b> AI FILM STUDIO</div>
      </div>
    </div>
    <p class="sub">60-second single-pass AI video — where other engines stop at 15. Speaking characters, real delivery. Subscribe or book online.</p>
  </div>
  <div class="sprockets">{('<i></i>' * 14)}</div>
</div>

</body></html>"""

OUT = f"{BASE}/campaign/logo"
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/logo_page.html", "w") as f:
    f.write(HTML)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1400, "height": 2400}, device_scale_factor=1)
        await pg.goto(f"file://{OUT}/logo_page.html")
        await pg.wait_for_timeout(700)
        shots = [
            ("#icon512", f"{BASE}/public/icon-512.png"),
            ("#maskable", f"{BASE}/public/maskable-512.png"),
            ("#apple", f"{BASE}/public/apple-touch-icon.png"),
            ("#fav", f"{BASE}/public/favicon-64.png"),
            ("#og", f"{BASE}/public/img/og-image.png"),
        ]
        for sel, path in shots:
            await pg.locator(sel).screenshot(path=path)
            print("shot", sel, "->", path, os.path.getsize(path))
        # icon-192 from the same 512 element? render separately via css zoom: use screenshot scale
        await pg.locator("#icon512").screenshot(path=f"{BASE}/public/icon-192.png", scale="css")
        import PIL.Image as I
        im = I.open(f"{BASE}/public/icon-192.png"); im = im.resize((192, 192), I.LANCZOS)
        im.save(f"{BASE}/public/icon-192.png"); print("icon-192 resized", im.size)
        # transparent social mark 1024
        pg2 = await b.new_page(viewport={"width": 1024, "height": 1024})
        await pg2.set_content(f"<body style='margin:0'>{mark_svg()}</body>")
        await pg2.screenshot(path=f"{BASE}/campaign/social/mark-red.png", omit_background=True)
        print("mark-red ->", os.path.getsize(f"{BASE}/campaign/social/mark-red.png"))
        await b.close()

asyncio.run(main())
print("REBRAND_DONE")
