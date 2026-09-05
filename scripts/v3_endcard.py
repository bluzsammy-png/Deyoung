#!/usr/bin/env python3
"""DeYoung promo v3 — endcard PNG (1920x1080): wordmark, tagline, platforms, CTA."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BLACK, RED, WHITE, GREY = (8, 8, 10), (220, 38, 38), (255, 255, 255), (160, 160, 168)
FONT = "/home/z/my-project/public/fonts/Archivo.ttf"

img = Image.new("RGB", (W, H), BLACK)
d = ImageDraw.Draw(img)

# subtle red rim glow bottom
for i in range(140):
    a = int(26 * (1 - i / 140))
    d.rectangle([0, H - 140 + i, W, H], fill=(max(BLACK[0], RED[0] * a // 26), 8, 10))

def load(sz):
    return ImageFont.truetype(FONT, sz)

# wordmark
f_word, f_tag, f_cta, f_plat = load(190), load(52), load(44), load(34)
word = "DeYoung"
w = d.textlength(word, font=f_word)
d.text(((W - w) / 2, H / 2 - 210), word, font=f_word, fill=WHITE)
# red accent bar under wordmark
d.rectangle([(W - 260) / 2, H / 2 - 6, (W + 260) / 2, H / 2 + 6], fill=RED)
# tagline
tag = "If you can say it, you can film it."
w = d.textlength(tag, font=f_tag)
d.text(((W - w) / 2, H / 2 + 60), tag, font=f_tag, fill=GREY)
# platforms
plat = "Web  ·  iOS  ·  Android"
w = d.textlength(plat, font=f_plat)
d.text(((W - w) / 2, H / 2 + 170), plat, font=f_plat, fill=WHITE)
# CTA pill
cta = "Start free"
cw = d.textlength(cta, font=f_cta)
x0, y0 = (W - cw) / 2 - 44, H / 2 + 268
d.rounded_rectangle([x0, y0, x0 + cw + 88, y0 + 92], radius=46, fill=RED)
d.text((x0 + 44, y0 + 20), cta, font=f_cta, fill=WHITE)

img.save("/home/z/my-project/campaign/film/v3/endcard.png")
print("endcard saved")
