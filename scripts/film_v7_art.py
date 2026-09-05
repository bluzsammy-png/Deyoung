#!/usr/bin/env python3
"""DeYoung film v7 — modern flat-vector character art (PIL, supersampled).

Design goals (v6 feedback: "1980 cartoon, sloppy"):
- Clean modern explainer style: soft cel shading, NO harsh outlines, rounded
  geometry, correct chest-up proportions (head ≈ 1/6.5 of frame height).
- 5 mouth states + blink lids + per-character accessories.
- Everything drawn at SS=3 supersampling then downscaled for smooth edges.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

SS = 3  # supersample factor


class ScaleDraw:
    """Wraps ImageDraw and multiplies every coordinate by SS so art code
    stays in clean design units while rendering supersampled."""

    def __init__(self, draw):
        self._d = draw

    def _s(self, v):
        if isinstance(v, (list, tuple)):
            return type(v)(self._s(x) for x in v)
        return v * SS

    def ellipse(self, box, **kw):
        self._d.ellipse(self._s(box), **kw)

    def rectangle(self, box, **kw):
        self._d.rectangle(self._s(box), **kw)

    def rounded_rectangle(self, box, radius=0, **kw):
        self._d.rounded_rectangle(self._s(box), radius=radius * SS, **kw)

    def pieslice(self, box, a0, a1, **kw):
        self._d.pieslice(self._s(box), a0, a1, **kw)

    def chord(self, box, a0, a1, **kw):
        self._d.chord(self._s(box), a0, a1, **kw)

    def arc(self, box, a0, a1, **kw):
        self._d.arc(self._s(box), a0, a1, **kw)

    def line(self, pts, **kw):
        self._d.line(self._s(pts), **kw)

    def polygon(self, pts, **kw):
        self._d.polygon(self._s(pts), **kw)

# ---------- palette helpers ----------

def shade(hex_color, factor):
    """Darken (factor<1) or lighten (factor>1) a hex color."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if factor <= 1:
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
    else:
        f = factor - 1
        r, g, b = min(255, int(r + (255 - r) * f)), min(255, int(g + (255 - g) * f)), min(255, int(b + (255 - b) * f))
    return (r, g, b)

def rgba(hex_color, a):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# ---------- character specs (the DeYoung cast) ----------

CHARACTERS = {
    "amara": {
        "skin": "#8D5A3B", "hair": "#1E1410", "top": "#C0392B", "top2": "#96281B",
        "style": "curly", "earrings": "#F5C24B", "glasses": False, "beard": False,
        "bg_word": "MORE THAN 15s",
    },
    "kossi": {
        "skin": "#6E4228", "hair": "#141010", "top": "#2C2F36", "top2": "#22252B",
        "style": "fade", "earrings": None, "glasses": False, "beard": False,
        "bg_word": "FULL SIXTY",
    },
    "zola": {
        "skin": "#A96F4A", "hair": "#241713", "top": "#DC2626", "top2": "#A31D1D",
        "style": "braids", "earrings": "#E8E6E3", "glasses": False, "beard": False,
        "bg_word": "TYPE IT",
    },
    "dee": {
        "skin": "#5C3620", "hair": "#100D0B", "top": "#1D2025", "top2": "#16181C",
        "style": "lowcut", "earrings": None, "glasses": True, "beard": True,
        "bg_word": "WE ROLL",
    },
}

# ---------- geometry ----------

# Canvas: chest-up composition, 1000 wide x 1150 tall (pre-SS units)
CW, CH = 1000, 1150
HEAD_CX, HEAD_CY = CW // 2, 360
HEAD_RX, HEAD_RY = 150, 172


def _head_box():
    return [HEAD_CX - HEAD_RX, HEAD_CY - HEAD_RY, HEAD_CX + HEAD_RX, HEAD_CY + HEAD_RY]


def draw_base(d, spec):
    """Torso, neck, ears, head base shape."""
    skin = shade(spec["skin"], 1.0)
    skin_sh = shade(spec["skin"], 0.86)

    # neck FIRST (behind head & collar): from under the chin to the chest
    d.rectangle([HEAD_CX - 74, HEAD_CY + HEAD_RY - 30, HEAD_CX + 74, 780], fill=skin_sh)
    d.chord([HEAD_CX - 74, HEAD_CY + HEAD_RY - 20, HEAD_CX + 74, HEAD_CY + HEAD_RY + 52], 0, 180, fill=shade(spec["skin"], 0.76))

    # torso — wide shoulder slope into chest, tall enough to exit frame bottom
    d.rounded_rectangle([110, 690, CW - 110, 1250], radius=200, fill=shade(spec["top"], 1.0))
    # shoulder highlights (two-tone shirt)
    d.chord([110, 690, HEAD_CX, 930], 180, 270, fill=shade(spec["top"], 1.12))
    # collar band
    d.rounded_rectangle([HEAD_CX - 136, 700, HEAD_CX + 136, 806], radius=56, fill=shade(spec["top2"], 0.9))

    # ears
    d.ellipse([HEAD_CX - HEAD_RX - 26, HEAD_CY - 10, HEAD_CX - HEAD_RX + 22, HEAD_CY + 74], fill=skin)
    d.ellipse([HEAD_CX + HEAD_RX - 22, HEAD_CY - 10, HEAD_CX + HEAD_RX + 26, HEAD_CY + 74], fill=skin)

    # head
    d.ellipse(_head_box(), fill=skin)


def draw_hair(d, spec):
    style = spec["style"]
    hair = shade(spec["hair"], 1.0)
    hi = shade(spec["hair"], 1.35)
    cx, cy = HEAD_CX, HEAD_CY

    if style == "curly":
        # curly afro: cluster of circles crowning the head
        for (dx, dy, r) in [(-120, -120, 78), (-50, -165, 86), (40, -170, 84), (118, -118, 76),
                            (-150, -50, 62), (148, -52, 62), (0, -120, 96)]:
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=hair)

    elif style == "fade":
        # fade: clean dome hugging the skull, crisp hairline
        d.pieslice([cx - HEAD_RX - 6, cy - HEAD_RY - 30, cx + HEAD_RX + 6, cy - HEAD_RY + 110], 180, 360, fill=hair)
    elif style == "braids":
        # crown + long box braids falling OUTSIDE the face line
        d.pieslice([cx - HEAD_RX - 12, cy - HEAD_RY - 34, cx + HEAD_RX + 12, cy - HEAD_RY + 150], 180, 360, fill=hair)
        for side in (-1, 1):
            for k in range(3):
                x0 = cx + side * (HEAD_RX - 18 + k * 30)
                d.rounded_rectangle([x0 - 17, cy - 120, x0 + 17, cy + 430], radius=16, fill=hair)
    elif style == "lowcut":
        d.pieslice([cx - HEAD_RX - 4, cy - HEAD_RY - 18, cx + HEAD_RX + 4, cy - HEAD_RY + 140], 180, 360, fill=hair)
        d.rounded_rectangle([cx - 70, cy - HEAD_RY - 6, cx + 40, cy - HEAD_RY + 14], radius=10, fill=hi)


def draw_face(d, spec, mouth, blink):
    """mouth: 0 closed smile, 1 half, 2 open, 3 wide, 4 small-o. blink: 0/1."""
    cx, cy = HEAD_CX, HEAD_CY
    skin = shade(spec["skin"], 1.0)

    # eyes: almond whites + iris + pupil + highlight; y center ~ -30
    eye_y = cy - 28
    for side in (-1, 1):
        ex = cx + side * 74
        box = [ex - 46, eye_y - 26, ex + 46, eye_y + 26]
        if blink:
            d.rectangle([box[0] - 4, eye_y - 26, box[2] + 4, eye_y + 24], fill=skin)
            d.arc(box, 15, 165, fill=shade(spec["skin"], 0.55), width=9)
        else:
            d.ellipse(box, fill="#F7F3EE")
            iris_r = 21
            d.ellipse([ex - iris_r, eye_y - iris_r, ex + iris_r, eye_y + iris_r], fill="#4A2C18")
            d.ellipse([ex - 10, eye_y - 10, ex + 10, eye_y + 10], fill="#140C07")
            d.ellipse([ex + 2, eye_y - 16, ex + 12, eye_y - 6], fill="#FFFFFF")
        # lash/lid line
        d.arc([box[0] - 6, box[1] - 10, box[2] + 6, box[3] + 2], 200, 340, fill=shade(spec["skin"], 0.5), width=8)

    # brows — confident, thick, softly arced
    brow_y = eye_y - 46
    for side in (-1, 1):
        bx = cx + side * 76
        d.rounded_rectangle([bx - 52, brow_y - 12, bx + 52, brow_y + 10], radius=10, fill=shade(spec["hair"], 1.0))

    # nose — soft shade arc only (no hard cartoon lines)
    d.arc([cx - 26, cy + 8, cx + 26, cy + 74], 300, 80, fill=shade(spec["skin"], 0.72), width=10)

    # glasses (dee)
    if spec.get("glasses"):
        for side in (-1, 1):
            ex = cx + side * 74
            d.rounded_rectangle([ex - 58, eye_y - 40, ex + 58, eye_y + 40], radius=22, outline="#26292F", width=9)
        d.line([cx - 18, eye_y - 4, cx + 18, eye_y - 4], fill="#26292F", width=8)
        d.line([cx + 128, eye_y - 8, cx + HEAD_RX + 6, eye_y - 12], fill="#26292F", width=8)
        d.line([cx - 128, eye_y - 8, cx - HEAD_RX - 6, eye_y - 12], fill="#26292F", width=8)

    # beard (dee) — full jaw mass behind the mouth (mouth paints over it)
    if spec.get("beard"):
        d.chord([cx - 126, cy + 64, cx + 126, cy + HEAD_RY + 90], 24, 156, fill=shade(spec["hair"], 0.98))

    # mouth
    my = cy + 112
    dark = "#4A1F1C"
    teeth = "#F7F3EE"
    tongue = "#B0555A"
    if mouth == 0:
        d.arc([cx - 56, my - 26, cx + 56, my + 30], 20, 160, fill=shade(spec["skin"], 0.5), width=11)
    elif mouth == 4:
        r = 17
        d.ellipse([cx - r, my - r, cx + r, my + r], fill=dark)
    else:
        rx, ry = {1: (34, 20), 2: (46, 34), 3: (56, 48)}[mouth]
        d.rounded_rectangle([cx - rx, my - ry, cx + rx, my + ry], radius=min(rx, ry), fill=dark)
        # upper teeth strip
        th = max(8, ry // 3)
        d.rounded_rectangle([cx - rx + 6, my - ry + 4, cx + rx - 6, my - ry + 4 + th], radius=5, fill=teeth)
        if mouth >= 2:
            # tongue hint at bottom
            d.chord([cx - rx + 10, my + ry - 22, cx + rx - 10, my + ry + 10], 180, 360, fill=tongue)

    # earrings
    if spec.get("earrings"):
        col = spec["earrings"]
        for side in (-1, 1):
            ex = cx + side * (HEAD_RX + 0)
            d.ellipse([ex - 13, cy + 66, ex + 13, cy + 92], outline=col, width=8)



def render_character(name, mouth, blink):
    """Return RGB PIL image (CW x CH) of the character."""
    spec = CHARACTERS[name]
    img = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    d = ScaleDraw(draw)
    draw_base(d, spec)
    draw_hair(d, spec)
    draw_face(d, spec, mouth, blink)
    # cel shading — soft right-side shade, clipped to the character body
    from PIL import ImageChops
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse([(HEAD_CX + 60) * SS, (HEAD_CY - HEAD_RY + 40) * SS, (HEAD_CX + HEAD_RX + 110) * SS, (HEAD_CY + HEAD_RY + 40) * SS], fill=(15, 8, 5, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(8 * SS))
    alpha = ImageChops.multiply(sh.getchannel("A"), img.getchannel("A"))
    sh.putalpha(alpha)
    img.alpha_composite(sh)
    img = img.resize((CW, CH), Image.LANCZOS)
    return img  # RGBA — background stays transparent


if __name__ == "__main__":
    import os, sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v7chars"
    os.makedirs(out, exist_ok=True)
    for cname in CHARACTERS:
        for m in range(5):
            for b in (0, 1):
                p = f"{out}/{cname}-m{m}-b{b}.png"
                render_character(cname, m, b).save(p)
        print("rendered", cname)
