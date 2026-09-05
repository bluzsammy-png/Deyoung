#!/usr/bin/env python3
"""DeYoung social cards v2 — every card shows the mobile + web product experience."""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

B = "/home/z/my-project"
OUT = f"{B}/download/social"
os.makedirs(OUT, exist_ok=True)
AR = f"{B}/scripts/Archivo.ttf"        # variable [wdth,wght]
AB = f"{B}/scripts/ArchivoBlack.ttf"
MO = f"{B}/scripts/JetBrainsMono.ttf"  # variable [wght]
SILK = Image.open(f"{B}/campaign/social/silk.png").convert("RGB")
MARK = Image.open(f"{B}/campaign/social/mark-red.png").convert("RGBA")
SH = f"{B}/campaign/social/shots"

RED = (220, 38, 38)
RED_L = (240, 67, 67)
INK = (10, 10, 10)
WHITE = (255, 255, 255)
GREY = (235, 235, 240)

def F(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                tag = a.get("name") if isinstance(a, dict) else a.name
                tag = (tag.decode() if isinstance(tag, bytes) else str(tag)).lower()
                if "width" in tag or tag == "wdth": vals.append(100)
                else: vals.append(wght)
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    return f

def fit(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def bg(w, h, silk_dim=0.55):
    base = fit(SILK, w, h)
    base = ImageEnhance.Brightness(base).enhance(silk_dim)
    base = ImageEnhance.Color(base).enhance(1.08)
    ov = Image.new("RGB", (w, h), INK)
    return Image.blend(base, ov, 0.28)

def scrim(im, bottom=0.62, top=0.25):
    w, h = im.size
    g = Image.new("L", (1, h))
    for y in range(h):
        t = y / h
        v = 255 if t < top else (255 * (1 - (t - top) / max(1e-6, bottom - top)) if t < bottom else 0)
        g.putpixel((0, y), int(v))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    im.paste(dark, (0, 0, w, h), g.resize((w, h)))
    return im

def grain(im, a=10):
    import random
    w, h = im.size
    n = Image.new("L", (w // 2, h // 2))
    n.putdata([random.randint(128 - a, 128 + a) for _ in range((w // 2) * (h // 2))])
    n = n.resize((w, h))
    im = Image.composite(ImageEnhance.Brightness(im).enhance(1.12), im, n.point(lambda p: p if p > 128 else 0))
    return im

def sh_text(d, xy, txt, f, fill=WHITE, anchor="la", sh=3):
    x, y = xy
    d.text((x + sh, y + sh), txt, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), txt, font=f, fill=fill, anchor=anchor)

def chip(d, x, y, txt, f, fg=WHITE, bgc=(220, 38, 38), padx=18, pady=10, r=999):
    bb = d.textbbox((0, 0), txt, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.rounded_rectangle([x, y, x + tw + padx * 2, y + th + pady * 2 + bb[1]], radius=r, fill=bgc)
    d.text((x + padx, y + pady), txt, font=f, fill=fg)
    return y + th + pady * 2 + bb[1]

def laptop(screen, sw):
    """Return (img) laptop with screen embedded; screen width = sw."""
    sc = screen
    bez = max(10, sw // 60)
    w = sw + bez * 2
    h = round(sc.height * (sw / sc.width)) + bez * 2
    body = Image.new("RGBA", (w, h + round(w * 0.045)), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=bez, fill=(16, 16, 18, 255))
    scr = sc.resize((sw, round(sc.height * (sw / sc.width))), Image.LANCZOS)
    body.paste(scr, (bez, bez))
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=bez, outline=(60, 60, 64, 255), width=2)
    base_w, base_h = w + round(w * 0.09), round(w * 0.045)
    base = Image.new("RGBA", body.size, (0, 0, 0, 0))
    db = ImageDraw.Draw(base)
    db.rounded_rectangle([(body.width - base_w) // 2, h - 2, (body.width - base_w) // 2 + base_w, h - 2 + base_h], radius=base_h // 3, fill=(28, 28, 32, 255))
    db.rounded_rectangle([(body.width - base_w) // 2, h - 2, (body.width - base_w) // 2 + base_w, h - 2 + base_h], radius=base_h // 3, outline=(70, 70, 76, 255), width=2)
    body = Image.alpha_composite(base, body)
    sh = Image.new("RGBA", (body.width + 60, body.height + 60), (0, 0, 0, 0))
    sh.paste(body, (30, 30), body)
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out = Image.alpha_composite(out, sh)
    out.alpha_composite(body, (30, 30))
    return out

def phone(screen, target_h):
    """Phone mockup with notch; height = target_h."""
    ar = screen.height / screen.width
    w = round(target_h / ar)
    bez = max(8, w // 26)
    body = Image.new("RGBA", (w + bez * 2, target_h + bez * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    r = w // 7
    d.rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=r + bez, fill=(14, 14, 16, 255))
    scr = screen.resize((w, target_h), Image.LANCZOS)
    mask = Image.new("L", scr.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, target_h - 1], radius=r, fill=255)
    body.paste(scr, (bez, bez), mask)
    d.rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=r + bez, outline=(64, 64, 70, 255), width=2)
    nw = round(w * 0.36); nh = round(bez * 1.15)
    d.rounded_rectangle([(body.width - nw) // 2, bez + nh // 2 - 2, (body.width + nw) // 2, bez + nh // 2 + nh], radius=nh, fill=(14, 14, 16, 255))
    sh = Image.new("RGBA", (body.width + 50, body.height + 50), (0, 0, 0, 0))
    sh.paste(body, (25, 25), body)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out = Image.alpha_composite(out, sh)
    out.alpha_composite(body, (25, 25))
    return out

def footer(im, tag="COMING SOON"):
    w, h = im.size
    d = ImageDraw.Draw(im)
    line_y = h - round(h * 0.085)
    d.line([(round(w * 0.06), line_y), (round(w * 0.94), line_y)], fill=(255, 255, 255, 40), width=2)
    mk = MARK.resize((round(h * 0.052), round(h * 0.052)), Image.LANCZOS)
    im.paste(mk, (round(w * 0.06), line_y - mk.height // 2 - 2), mk)
    f1 = F(AB, round(h * 0.026))
    sh_text(d, (round(w * 0.06) + mk.width + round(w * 0.02), line_y), "DEYOUNG", f1, WHITE, anchor="lm", sh=2)
    f2 = F(MO, round(h * 0.021), 700)
    bb = d.textbbox((0, 0), tag, font=f2)
    d.text((round(w * 0.94), line_y), tag, font=f2, fill=RED_L, anchor="rm")
    return im

def paste_center(base, art, cx, cy):
    base.alpha_composite(art, (int(cx - art.width / 2), int(cy - art.height / 2)))

web_home = Image.open(f"{SH}/web-home.png").convert("RGB")
web_plans = Image.open(f"{SH}/web-plans.png").convert("RGB")
mob_home = Image.open(f"{SH}/mob-home.png").convert("RGB")
mob_plans = Image.open(f"{SH}/mob-plans.png").convert("RGB")
mob_req = Image.open(f"{SH}/mob-request.png").convert("RGB")

# ---------- card 1: coming soon (4:5) ----------
def card1():
    W, H = 1080, 1350
    im = bg(W, H, 0.5).convert("RGBA")
    im = scrim(im, 0.55, 0.18).convert("RGBA")
    lap = laptop(fit(web_home, 860, 540), 860)
    ph = phone(mob_home, 600)
    paste_center(im, lap, W // 2 - 30, 930)
    paste_center(im, ph, 830, 970)
    d = ImageDraw.Draw(im)
    f_eye = F(MO, 26, 700)
    d.text((W // 2, 118), "T H E   6 0 - S E C O N D   A I   F I L M   S T U D I O", font=f_eye, fill=RED_L, anchor="ma")
    sh_text(d, (W // 2, 190), "COMING", F(AB, 160), WHITE, anchor="ma")
    sh_text(d, (W // 2, 365), "SOON", F(AB, 160), WHITE, anchor="ma")
    f_sub = F(AR, 33, 500)
    d.text((W // 2, 545), "One prompt in. A full 60-second film out.", font=f_sub, fill=GREY, anchor="ma")
    chip(d, W // 2 - 150, 610, "MOBILE  +  WEB", F(MO, 24, 700))
    grain(im); footer(im)
    im.convert("RGB").save(f"{OUT}/01-coming-soon-4x5.jpg", quality=92)

# ---------- card 2: sixty seconds (4:5) ----------
def card2():
    W, H = 1080, 1350
    im = bg(W, H, 0.42).convert("RGBA")
    im = scrim(im, 0.5, 0.15).convert("RGBA")
    lap = laptop(fit(web_plans, 830, 520), 830)
    ph = phone(mob_plans, 700)
    paste_center(im, lap, W // 2 - 20, 850)
    paste_center(im, ph, W // 2 + 370, 920)
    d = ImageDraw.Draw(im)
    sh_text(d, (W // 2, 120), "60 SECONDS.", F(AB, 128), WHITE, anchor="ma")
    sh_text(d, (W // 2, 268), "ONE PASS.", F(AB, 128), RED_L, anchor="ma")
    f_sub = F(AR, 30, 500)
    d.text((W // 2, 452), "Where other engines stop at 15 —", font=f_sub, fill=GREY, anchor="ma", align="center")
    d.text((W // 2, 500), "DeYoung renders a full minute in one generation.", font=f_sub, fill=GREY, anchor="ma", align="center")
    chip(d, W // 2 - 208, 565, "SUBSCRIBE  ·  SUBMIT  ·  STREAM", F(MO, 23, 700))
    grain(im); footer(im)
    im.convert("RGB").save(f"{OUT}/02-sixty-seconds-4x5.jpg", quality=92)

# ---------- card 3: characters talk (4:5) ----------
def card3():
    W, H = 1080, 1350
    im = bg(W, H, 0.55).convert("RGBA")
    im = scrim(im, 0.55, 0.2).convert("RGBA")
    a = fit(Image.open(f"{B}/campaign/social/amara.png").convert("RGB"), 470, 470)
    k = fit(Image.open(f"{B}/campaign/social/kojo.png").convert("RGB"), 470, 470)
    ph = phone(mob_req, 560)
    for img, cx in ((a, 300), (k, 780)):
        m = Image.new("L", img.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width, img.height], radius=36, fill=255)
        fr = Image.new("RGBA", (img.width + 12, img.height + 12), (0, 0, 0, 0))
        ImageDraw.Draw(fr).rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=40, fill=(20, 20, 22, 255), outline=RED, width=3)
        fr.paste(img, (6, 6), m)
        paste_center(im, fr, cx, 700)
    paste_center(im, ph, 540, 760)
    d = ImageDraw.Draw(im)
    sh_text(d, (W // 2, 120), "REAL CHARACTERS.", F(AB, 84), WHITE, anchor="ma")
    sh_text(d, (W // 2, 225), "REAL DIALOGUE.", F(AB, 84), RED_L, anchor="ma")
    f_sub = F(AR, 31, 500)
    d.text((W // 2, 1075), "Amara and Kojo don't just appear —", font=f_sub, fill=GREY, anchor="ma", align="center")
    d.text((W // 2, 1123), "they speak, react, and carry your story.", font=f_sub, fill=GREY, anchor="ma", align="center")
    grain(im); footer(im, "60s AI FILM")
    im.convert("RGB").save(f"{OUT}/03-characters-talk-4x5.jpg", quality=92)

# ---------- card 4: what it can do (4:5) ----------
def card4():
    W, H = 1080, 1350
    im = bg(W, H, 0.45).convert("RGBA")
    im = scrim(im, 0.5, 0.15).convert("RGBA")
    ph = phone(mob_req, 780)
    lap = laptop(fit(web_plans, 640, 400), 640)
    paste_center(im, lap, 320, 1000)
    paste_center(im, ph, 800, 830)
    d = ImageDraw.Draw(im)
    sh_text(d, (70, 110), "WHAT IT", F(AB, 118), WHITE)
    sh_text(d, (70, 240), "CAN DO.", F(AB, 118), RED_L)
    feats = ["60s single-pass renders", "Lifelike speaking characters", "Pick length · tone · resolution", "Queue with honest ETAs", "Works on phone and desktop"]
    f_ch = F(AR, 30, 600); f_tick = F(MO, 30, 700)
    y = 420
    for t in feats:
        d.rounded_rectangle([70, y, 96, y + 34], radius=8, fill=RED)
        d.text((77, y - 2), "+", font=f_tick, fill=WHITE)
        sh_text(d, (116, y - 2), t, f_ch, GREY, sh=2)
        y += 66
    chip(d, 70, y + 16, "TRY IT ON MOBILE OR WEB", F(MO, 23, 700))
    grain(im); footer(im, "DEYOUNG.STUDIO")
    im.convert("RGB").save(f"{OUT}/04-what-it-can-do-4x5.jpg", quality=92)

# ---------- card 5: type your story (4:5) ----------
def card5():
    W, H = 1080, 1350
    im = bg(W, H, 0.5).convert("RGBA")
    im = scrim(im, 0.52, 0.16).convert("RGBA")
    ph = phone(mob_req, 840)
    lap = laptop(fit(web_home, 700, 440), 700)
    paste_center(im, lap, 320, 990)
    paste_center(im, ph, 730, 810)
    d = ImageDraw.Draw(im)
    sh_text(d, (W // 2, 112), "TYPE YOUR STORY.", F(AB, 92), WHITE, anchor="ma")
    f_sub = F(AR, 30, 500)
    d.text((W // 2, 238), "Prompt it once — DeYoung writes, shoots", font=f_sub, fill=GREY, anchor="ma", align="center")
    d.text((W // 2, 284), "and scores the whole scene.", font=f_sub, fill=GREY, anchor="ma", align="center")
    chip(d, W // 2 - 180, 350, "UP TO 60s · 1080p · WITH SOUND", F(MO, 22, 700))
    grain(im); footer(im)
    im.convert("RGB").save(f"{OUT}/05-type-your-story-4x5.jpg", quality=92)

# ---------- card 6: be first (1:1) ----------
def card6():
    W, H = 1080, 1080
    im = bg(W, H, 0.4).convert("RGBA")
    im = scrim(im, 0.5, 0.14).convert("RGBA")
    lap = laptop(fit(web_home, 740, 465), 740)
    ph = phone(mob_plans, 460)
    paste_center(im, lap, 490, 790)
    paste_center(im, ph, 810, 800)
    d = ImageDraw.Draw(im)
    f_eye = F(MO, 24, 700)
    d.text((W // 2, 96), "L I M I T E D   L A U N C H   C O H O R T", font=f_eye, fill=RED_L, anchor="ma")
    sh_text(d, (W // 2, 150), "BE FIRST", F(AB, 140), WHITE, anchor="ma")
    sh_text(d, (W // 2, 310), "IN LINE.", F(AB, 140), RED_L, anchor="ma")
    f_sub = F(AR, 30, 500)
    d.text((W // 2, 470), "Founding subscribers get priority renders on day one.", font=f_sub, fill=GREY, anchor="ma")
    chip(d, W // 2 - 120, 528, "DEYOUNG  ·  COMING SOON", F(MO, 23, 700))
    grain(im); footer(im, "BE FIRST")
    im.convert("RGB").save(f"{OUT}/06-be-first-1x1.jpg", quality=92)

# ---------- card 7: story 9:16 ----------
def card7():
    W, H = 1080, 1920
    im = bg(W, H, 0.45).convert("RGBA")
    im = scrim(im, 0.55, 0.16).convert("RGBA")
    ph = phone(mob_plans, 940)
    paste_center(im, ph, 700, 1240)
    lap = laptop(fit(web_plans, 560, 350), 560)
    paste_center(im, lap, 300, 1510)
    d = ImageDraw.Draw(im)
    f_eye = F(MO, 28, 700)
    d.text((W // 2, 150), "T H E   A I   F I L M   S T U D I O", font=f_eye, fill=RED_L, anchor="ma")
    sh_text(d, (W // 2, 220), "COMING", F(AB, 180), WHITE, anchor="ma")
    sh_text(d, (W // 2, 430), "SOON", F(AB, 180), WHITE, anchor="ma")
    f_sub = F(AR, 34, 500)
    d.text((W // 2, 640), "60-second films. Speaking characters.", font=f_sub, fill=GREY, anchor="ma")
    d.text((W // 2, 695), "One studio — pocket and desk.", font=f_sub, fill=GREY, anchor="ma")
    chip(d, W // 2 - 175, 770, "MOBILE  +  WEB  EXPERIENCE", F(MO, 24, 700))
    grain(im); footer(im, "SWIPE SOON")
    im.convert("RGB").save(f"{OUT}/07-coming-soon-story-9x16.jpg", quality=92)

for fn in (card1, card2, card3, card4, card5, card6, card7):
    fn(); print("ok", fn.__name__)
print("CARDS_DONE")
