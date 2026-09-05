#!/usr/bin/env python3
"""Generate DeYoung brand assets: avatar, gallery placeholders, OG image, PWA icons.
Palette: white #FFFFFF, red #DC2626, black #0A0A0A."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = "/home/z/my-project/public"
IMG = os.path.join(OUT, "img")
os.makedirs(IMG, exist_ok=True)

RED = (220, 38, 38)
RED_DARK = (153, 27, 27)
BLACK = (10, 10, 10)
WHITE = (255, 255, 255)
GREY = (245, 245, 245)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def font(size):
    for p in FONT_DIRS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def centered(draw, text, w, y, fnt, fill):
    bb = draw.textbbox((0, 0), text, font=fnt)
    tw = bb[2] - bb[0]
    draw.text(((w - tw) / 2, y), text, font=fnt, fill=fill)


# ---------- avatar (DY monogram) ----------
def avatar(size=800):
    im = Image.new("RGB", (size, size), BLACK)
    d = ImageDraw.Draw(im)
    # red quarter accent
    d.pieslice([size * 0.1, size * 0.1, size * 1.9, size * 1.9], 180, 270, fill=RED)
    f = font(int(size * 0.42))
    centered(d, "DY", size, size * 0.27, f, WHITE)
    d.rectangle([0, size - int(size * 0.08), size, size], fill=RED)
    return im


avatar(800).save(os.path.join(IMG, "avatar-default.png"))
avatar(800).resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, "favicon-64.png"))

# ---------- PWA icons ----------
for s, name in [(192, "icon-192.png"), (512, "icon-512.png")]:
    im = Image.new("RGB", (s, s), BLACK)
    d = ImageDraw.Draw(im)
    d.rectangle([0, s - int(s * 0.12), s, s], fill=RED)
    f = font(int(s * 0.5))
    centered(d, "DY", s, s * 0.24, f, WHITE)
    im.save(os.path.join(OUT, name))

# maskable: safe zone 80%
m = Image.new("RGB", (512, 512), RED)
d = ImageDraw.Draw(m)
f = font(200)
centered(d, "DY", 512, 150, f, WHITE)
m.save(os.path.join(OUT, "maskable-512.png"))

# apple touch icon
avatar(180).save(os.path.join(OUT, "apple-touch-icon.png"))

# ---------- favicon.svg ----------
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" fill="#0A0A0A"/>
<rect y="52" width="64" height="12" fill="#DC2626"/>
<text x="32" y="42" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="bold" fill="#FFFFFF" text-anchor="middle">DY</text>
</svg>"""
with open(os.path.join(OUT, "favicon.svg"), "w") as fh:
    fh.write(svg)

# ---------- OG share image ----------
og = Image.new("RGB", (1200, 630), BLACK)
d = ImageDraw.Draw(og)
d.rectangle([0, 0, 1200, 14], fill=RED)
d.rectangle([0, 616, 1200, 630], fill=RED)
f_big = font(150)
f_small = font(40)
centered(d, "DEYOUNG", 1200, 190, f_big, WHITE)
d.rectangle([420, 360, 780, 378], fill=RED)
centered(d, "BOOK ONLINE  •  PAY ANYWHERE", 1200, 420, f_small, (200, 200, 200))
og.save(os.path.join(IMG, "og-image.png"))

# ---------- gallery placeholders ----------
def gallery(w, h, idx, base, accent, label):
    im = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(im)
    # diagonal accent band
    d.polygon([(0, h), (w * 0.35, 0), (w * 0.55, 0), (w * 0.2, h)], fill=accent)
    d.rectangle([0, h - int(h * 0.1), w, h], fill=accent if base == BLACK else BLACK)
    f = font(min(w, h) // 9)
    centered(d, label, w, h * 0.42, f, WHITE if base in (BLACK, RED_DARK) else BLACK)
    f2 = font(min(w, h) // 22)
    centered(d, f"DEYOUNG • {idx:02d}", w, h * 0.58, f2, RED if base != RED else WHITE)
    return im


specs = [
    (1200, 900, 1, BLACK, RED, "PORTRAIT"),
    (1200, 900, 2, WHITE, RED, "BRAND"),
    (900, 1200, 3, BLACK, RED, "EDITORIAL"),
    (1200, 900, 4, RED_DARK, WHITE, "EVENT"),
    (900, 1200, 5, WHITE, BLACK, "STUDIO"),
    (1200, 900, 6, BLACK, RED, "COMMERCIAL"),
]
for w, h, idx, base, accent, label in specs:
    gallery(w, h, idx, base, accent, label).save(os.path.join(IMG, f"gallery-{idx}.png"))

# payment-method illustrative strip (used on book page when manual)
pm = Image.new("RGB", (1200, 300), WHITE)
d = ImageDraw.Draw(pm)
d.rectangle([0, 0, 1200, 300], fill=GREY)
labels = ["BANK", "MOBILE MONEY", "USSD", "CARDS"]
x = 60
for i, lb in enumerate(labels):
    box = Image.new("RGB", (250, 160), BLACK)
    bd = ImageDraw.Draw(box)
    bd.rectangle([0, 130, 250, 160], fill=RED)
    centered(bd, lb, 250, 55, font(30), WHITE)
    pm.paste(box, (x, 70))
    x += 280
pm.save(os.path.join(IMG, "pay-methods.png"))

print("assets generated:")
for root, _, files in os.walk(OUT):
    for f in sorted(files):
        print(" ", os.path.relpath(os.path.join(root, f), OUT))
