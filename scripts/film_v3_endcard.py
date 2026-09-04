#!/usr/bin/env python3
"""DeYoung film v3 endcard — 1920x1080 PNG. Logo + wordmark + tagline + CTA."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
BG = (10, 10, 10)
RED = (220, 38, 38)
WHITE = (245, 245, 245)
GRAY = (150, 150, 150)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# subtle red vignette glow behind logo
glow = Image.new("RGB", (W, H), BG)
gd = ImageDraw.Draw(glow)
gd.ellipse([W // 2 - 520, 240, W // 2 + 520, 1000], fill=(38, 12, 12))
glow = glow.filter(ImageFilter.GaussianBlur(180))
img = Image.blend(img, glow, 0.55)
d = ImageDraw.Draw(img)

ARCHIVO = "/home/z/my-project/public/fonts/Archivo.ttf"

def font(size):
    return ImageFont.truetype(ARCHIVO, size)

def center_text(y, text, f, fill, stroke=0, stroke_fill=None, tracking=0):
    if tracking:
        # manual letter-spacing
        widths = [d.textlength(ch, font=f) + tracking for ch in text]
        total = sum(widths) - tracking
        x = (W - total) / 2
        for ch, w in zip(text, widths):
            d.text((x, y), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += w
        return
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)

# logo mark
icon = Image.open("/home/z/my-project/public/icon-512.png").convert("RGBA")
IS = 250
icon = icon.resize((IS, IS), Image.LANCZOS)
img.paste(icon, ((W - IS) // 2, 175), icon)

# wordmark
center_text(455, "DEYOUNG", font(150), WHITE, tracking=26)

# red rule
d.rectangle([W // 2 - 190, 660, W // 2 + 190, 666], fill=RED)

# tagline
center_text(700, "If you can say it, you can film it.", font(52), GRAY)

# CTA pill
cta = "Start free  ·  deyoung.site"
f_cta = font(46)
pad_x, pad_y = 46, 20
tw = d.textlength(cta, font=f_cta)
x0, y0 = (W - tw) / 2 - pad_x, 830
x1, y1 = (W + tw) / 2 + pad_x, 830 + 46 + 2 * pad_y
d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2, fill=RED)
d.text(((W - tw) / 2, y0 + pad_y - 2), cta, font=f_cta, fill=WHITE)

# platform line
center_text(975, "Web  ·  iOS  ·  Android — AI video in five styles", font(30), (110, 110, 110))

out = "/home/z/my-project/campaign/film/v3/endcard.png"
img.save(out)
print("endcard:", out)
