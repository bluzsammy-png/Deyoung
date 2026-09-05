"""Generate PATI dashboard PWA assets: icons, favicon, OG share image.

Run once; outputs are committed into pati_api/static/ so end users need no
Pillow at install time (FREE_FIRST: no build step on the owner's machine).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/home/z/my-project/pati/pati_api/static")
OUT.mkdir(parents=True, exist_ok=True)

BG = (11, 15, 20)        # #0b0f14
PANEL = (19, 32, 43)     # #13202b
TEAL = (102, 217, 194)   # #66d9c2
TEAL_DIM = (60, 150, 130)
BLUE = (138, 180, 248)   # #8ab4f8
TEXT = (215, 226, 238)   # #d7e2ee
MUT = (140, 155, 170)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def rounded_bg(size: int, radius: int, bg=BG, border=True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=bg,
                        outline=(31, 53, 71, 255) if border else None, width=2)
    return img


def draw_mark(img: Image.Image, scale: float = 1.0, ox: int = 0, oy: int = 0) -> None:
    """Draw the PATI mark: a 'P' built from a bar + ring + spark dot."""
    d = ImageDraw.Draw(img)
    size = img.width
    s = size * scale
    ox = int(ox * size)
    oy = int(oy * size)
    # vertical bar of the P
    bar_w = int(0.13 * s)
    bar_h = int(0.62 * s)
    x0 = int(0.26 * s) + ox
    y0 = int(0.19 * s) + oy
    d.rounded_rectangle([x0, y0, x0 + bar_w, y0 + bar_h], radius=bar_w // 2, fill=TEAL)
    # ring (bowl of the P)
    r = int(0.21 * s)
    ring_w = int(0.13 * s)
    cx = x0 + bar_w // 2 + r
    cy = y0 + r
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=TEAL, width=ring_w)
    # spark dot
    dot_r = int(0.045 * s)
    dx = int(0.72 * s) + ox
    dy = int(0.24 * s) + oy
    d.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=BLUE)


def make_icon(size: int, maskable: bool = False) -> Image.Image:
    img = rounded_bg(size, radius=int(size * (0.02 if maskable else 0.18)),
                     border=False)
    if maskable:  # keep mark inside the 80% safe zone
        draw_mark(img, scale=0.78, ox=0.11, oy=0.11)
    else:
        draw_mark(img, scale=0.92, ox=0.04, oy=0.04)
    return img


def make_favicon_64() -> Image.Image:
    return make_icon(64, maskable=True)


def make_og_image() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(img)
    # panel stripes
    d.rectangle([0, 0, w, 6], fill=TEAL)
    d.rounded_rectangle([48, 120, 200, 272], radius=36, fill=PANEL)
    icon = make_icon(128, maskable=False)
    img.paste(icon, (60, 132), icon)
    # headline
    f_big = ImageFont.truetype(FONT_BOLD, 84)
    f_sub = ImageFont.truetype(FONT_REG, 34)
    f_small = ImageFont.truetype(FONT_BOLD, 26)
    d.text((240, 130), "PATI", font=f_big, fill=TEAL)
    d.text((240, 224), "Your personal AI - free forever", font=f_sub, fill=TEXT)
    # FREE_ONLY badge
    d.rounded_rectangle([240, 300, 700, 352], radius=14, fill=PANEL,
                        outline=(31, 53, 71), width=2)
    d.text((262, 312), "FREE_ONLY = true   MAX_SPEND = 0", font=f_small, fill=TEAL)
    # capability chips
    chips = ["video", "images", "voice + music", "research", "code", "files"]
    x = 240
    y = 390
    for c in chips:
        f_c = ImageFont.truetype(FONT_REG, 28)
        cw = int(d.textlength(c, font=f_c)) + 44
        d.rounded_rectangle([x, y, x + cw, y + 56], radius=28, fill=PANEL)
        d.text((x + 22, y + 12), c, font=f_c, fill=TEXT)
        x += cw + 18
        if x > 780 and c == "voice + music":
            x = 240
            y += 76
    # footer
    d.text((240, 560), "Local-first control plane - installs as an app on iOS and Android",
           font=ImageFont.truetype(FONT_REG, 26), fill=MUT)
    return img.convert("RGB")


for size, name, maskable in [
    (192, "icon-192.png", False),
    (512, "icon-512.png", False),
    (512, "icon-maskable-512.png", True),
    (180, "apple-touch-icon.png", True),
    (64, "favicon-64.png", True),
]:
    make_icon(size, maskable).save(OUT / name, "PNG")
    print("wrote", name)

make_og_image().save(OUT / "og-image.png", "PNG")
print("wrote og-image.png")

# vector favicon (crisp on modern browsers)
(OUT / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="12" fill="#0b0f14"/>'
    '<rect x="17" y="12" width="8" height="40" rx="4" fill="#66d9c2"/>'
    '<circle cx="37" cy="25" r="13" fill="none" stroke="#66d9c2" stroke-width="8"/>'
    '<circle cx="47" cy="15" r="3" fill="#8ab4f8"/>'
    "</svg>", encoding="utf-8")
print("wrote favicon.svg")
