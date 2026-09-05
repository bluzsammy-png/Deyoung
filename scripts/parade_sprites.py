"""DeYoung parade sprite sheets — stick-character cast, transparent RGBA,
10-frame cycles rendered as horizontal sprite sheets for CSS steps() animation.
Characters: runner (red-eye director), walker kid (beanie), ponytail girl (scarf),
stick dog, hop-blob. White limbs + brand red accents (parade strip is black).
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = "/home/z/my-project"
OUT = f"{ROOT}/public/parade"
os.makedirs(OUT, exist_ok=True)

T = 256          # tile size
N = 10           # frames
W = (245, 245, 245, 255)      # white limbs
RED = (220, 38, 38, 255)
SOFT = (255, 255, 255, 30)    # soft shadow on black
SHEET_W = T * N

GROUND = int(T * 0.88)


def new_tile():
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def limb(d, x0, y0, x1, y1, w=10, col=W):
    d.line([x0, y0, x1, y1], fill=col, width=w)
    r = w // 2
    d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=col)


def shadow(d, cx, width, alpha_scale=1.0):
    a = int(28 * alpha_scale)
    d.ellipse([cx - width, GROUND - 7, cx + width, GROUND + 7], fill=(255, 255, 255, max(6, a)))


def save_sheet(frames, name):
    sheet = Image.new("RGBA", (SHEET_W, T), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * T, 0))
    path = f"{OUT}/{name}.png"
    sheet.save(path, optimize=True)
    print(name, os.path.getsize(path) // 1024, "KB")


def speed_lines(d, t, y0=70):
    for i in range(3):
        y = y0 + i * 34 + 5 * math.sin(t + i)
        x0 = 18 + (i % 2) * 14
        d.line([x0, y, x0 + 56 - i * 12, y], fill=(255, 255, 255, 60), width=4)


# ---------------------------------------------------------------- runner
def draw_runner(idx):
    img, d = new_tile()
    t = idx / N * 2 * math.pi
    cx, hip_y = T / 2 + 4, T * 0.52 + 5 * math.sin(2 * t)
    head_r, head_cy = 26, hip_y - 74 - 3 * math.sin(2 * t)
    shadow(d, cx, 40 + 7 * math.sin(2 * t))
    speed_lines(d, t)
    for phase, dx in ((0, 1), (math.pi, -1)):
        hip_x = cx + 5 * dx
        knee_x = hip_x + 34 * math.sin(t + phase) * dx
        knee_y = hip_y + 40 + 8 * math.cos(t + phase)
        foot_x = knee_x + 22 * math.sin(t + phase + 0.9) * dx
        foot_y = knee_y + 38 - 11 * max(0, math.sin(t + phase))
        limb(d, hip_x, hip_y, knee_x, knee_y)
        limb(d, knee_x, knee_y, foot_x, foot_y)
    shoulder_y = hip_y - 60
    limb(d, cx, hip_y, cx, shoulder_y, w=13)
    for phase, dx in ((0, -1), (math.pi, 1)):
        sh_x = cx + 3 * dx
        elb_x = sh_x + 28 * math.sin(t + phase + math.pi) * dx
        elb_y = shoulder_y + 30
        hnd_x = elb_x + 20 * math.sin(t + phase + math.pi + 1.2) * dx
        hnd_y = elb_y + 20 - 6 * math.cos(t + phase)
        limb(d, sh_x, shoulder_y, elb_x, elb_y, w=9)
        limb(d, elb_x, elb_y, hnd_x, hnd_y, w=9)
    d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=W)
    eye_r = 7
    d.ellipse([cx + 5 - eye_r, head_cy - 6 - eye_r, cx + 5 + eye_r, head_cy - 6 + eye_r], fill=RED)
    return img


# ---------------------------------------------------------------- walker kid (beanie + wave)
def draw_kid(idx):
    img, d = new_tile()
    t = idx / N * 2 * math.pi
    cx = T / 2 + 2
    hip_y = T * 0.54 + 3 * math.sin(2 * t)
    head_r, head_cy = 24, hip_y - 62 - 2 * math.sin(2 * t)
    shadow(d, cx, 34 + 4 * math.sin(2 * t))
    # legs — gentle walk swing
    for phase, dx in ((0, 1), (math.pi, -1)):
        hip_x = cx + 4 * dx
        knee_x = hip_x + 20 * math.sin(t + phase) * dx
        knee_y = hip_y + 32 + 4 * math.cos(t + phase)
        foot_x = knee_x + 16 * math.sin(t + phase + 1.1) * dx
        foot_y = knee_y + 30 - 8 * max(0, math.sin(t + phase))
        limb(d, hip_x, hip_y, knee_x, knee_y, w=9)
        limb(d, knee_x, knee_y, foot_x, foot_y, w=9)
    shoulder_y = hip_y - 48
    limb(d, cx, hip_y, cx, shoulder_y, w=12)
    # right arm walks, left arm waves up
    sh_x = cx + 3
    elb_x = sh_x - 20 * math.sin(t)
    elb_y = shoulder_y + 24
    limb(d, sh_x, shoulder_y, elb_x, elb_y, w=8)
    limb(d, elb_x, elb_y, elb_x - 14, elb_y + 16, w=8)
    wv = math.sin(t * 2)
    limb(d, cx - 3, shoulder_y, cx - 3 - 14, shoulder_y - 26 + 4 * wv, w=8)
    limb(d, cx - 3 - 14, shoulder_y - 26 + 4 * wv, cx - 3 - 26, shoulder_y - 40 + 6 * wv, w=8)
    # head + face
    d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=W)
    for ex in (10, -2):
        d.ellipse([cx + ex - 3, head_cy - 4 - 3, cx + ex + 3, head_cy - 4 + 3], fill=(17, 17, 17, 255))
    d.arc([cx - 9, head_cy + 2, cx + 9, head_cy + 12], 20, 160, fill=(17, 17, 17, 255), width=3)
    # red beanie
    d.pieslice([cx - head_r - 2, head_cy - head_r - 4, cx + head_r + 2, head_cy + 4], 180, 360, fill=RED)
    d.rectangle([cx - head_r - 2, head_cy - 8, cx + head_r + 2, head_cy - 2], fill=RED)
    d.ellipse([cx - 4, head_cy - head_r - 10, cx + 4, head_cy - head_r - 2], fill=RED)
    return img


# ---------------------------------------------------------------- ponytail girl (scarf)
def draw_girl(idx):
    img, d = new_tile()
    t = idx / N * 2 * math.pi
    cx, hip_y = T / 2 + 4, T * 0.52 + 5 * math.sin(2 * t)
    head_r, head_cy = 25, hip_y - 72 - 3 * math.sin(2 * t)
    shadow(d, cx, 38 + 6 * math.sin(2 * t))
    speed_lines(d, t, y0=60)
    for phase, dx in ((0, 1), (math.pi, -1)):
        hip_x = cx + 5 * dx
        knee_x = hip_x + 32 * math.sin(t + phase) * dx
        knee_y = hip_y + 38 + 7 * math.cos(t + phase)
        foot_x = knee_x + 21 * math.sin(t + phase + 0.9) * dx
        foot_y = knee_y + 36 - 10 * max(0, math.sin(t + phase))
        limb(d, hip_x, hip_y, knee_x, knee_y)
        limb(d, knee_x, knee_y, foot_x, foot_y)
    shoulder_y = hip_y - 58
    limb(d, cx, hip_y, cx, shoulder_y, w=12)
    for phase, dx in ((0, -1), (math.pi, 1)):
        sh_x = cx + 3 * dx
        elb_x = sh_x + 26 * math.sin(t + phase + math.pi) * dx
        elb_y = shoulder_y + 28
        hnd_x = elb_x + 18 * math.sin(t + phase + math.pi + 1.2) * dx
        hnd_y = elb_y + 18 - 6 * math.cos(t + phase)
        limb(d, sh_x, shoulder_y, elb_x, elb_y, w=8)
        limb(d, elb_x, elb_y, hnd_x, hnd_y, w=8)
    d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=W)
    eye_r = 6
    for ex in (8, -4):
        d.ellipse([cx + ex - eye_r, head_cy - 5 - eye_r, cx + ex + eye_r, head_cy - 5 + eye_r], fill=(17, 17, 17, 255))
    d.arc([cx - 8, head_cy + 3, cx + 8, head_cy + 13], 25, 155, fill=(17, 17, 17, 255), width=3)
    # ponytail — flowing 3-segment ribbon swinging with t
    px, py = cx - head_r + 4, head_cy - 8
    seg = [(px - 14, py + 6 + 5 * math.sin(t)), (px - 26, py + 20 + 8 * math.sin(t + 1)), (px - 34, py + 38 + 10 * math.sin(t + 2))]
    prev = (px, py)
    for pnt in seg:
        limb(d, prev[0], prev[1], pnt[0], pnt[1], w=8, col=RED)
        prev = pnt
    # red scarf ribbon behind neck
    sx, sy = cx - 12, shoulder_y + 4
    limb(d, sx, sy, sx - 20, sy + 6 + 6 * math.sin(t + 0.5), w=6, col=RED)
    limb(d, sx - 20, sy + 6 + 6 * math.sin(t + 0.5), sx - 34, sy + 18 + 8 * math.sin(t + 1.5), w=6, col=RED)
    return img


# ---------------------------------------------------------------- stick dog
def draw_dog(idx):
    img, d = new_tile()
    t = idx / N * 2 * math.pi
    bx, by = T / 2, T * 0.56 + 4 * math.sin(2 * t)   # body center
    shadow(d, bx, 44 + 6 * math.sin(2 * t))
    body_a, body_b = (bx - 42, by), (bx + 42, by - 4)
    limb(d, body_a[0], body_a[1], body_b[0], body_b[1], w=13)
    # 4 legs — front pair phase t, back pair t+pi (gallop)
    for phase, anchor_x in ((t, body_b[0] - 8), (t + 0.5, body_b[0] - 2),
                            (t + math.pi, body_a[0] + 8), (t + math.pi + 0.5, body_a[0] + 2)):
        knee_x = anchor_x + 12 * math.sin(phase)
        knee_y = by + 24
        foot_x = knee_x + 10 * math.sin(phase + 0.8)
        foot_y = by + 48 - 10 * max(0, math.sin(phase))
        limb(d, anchor_x, by, knee_x, knee_y, w=8)
        limb(d, knee_x, knee_y, foot_x, foot_y, w=8)
    # head at front (right), slight bob
    hx, hy = body_b[0] + 22, body_b[1] - 16 - 3 * math.sin(2 * t)
    limb(d, body_b[0], body_b[1] - 2, hx - 6, hy + 6, w=10)
    d.ellipse([hx - 16, hy - 15, hx + 16, hy + 15], fill=W)
    # snout + nose
    d.ellipse([hx + 10, hy - 4, hx + 30, hy + 6], fill=W)
    d.ellipse([hx + 26, hy - 2, hx + 32, hy + 4], fill=RED)
    d.ellipse([hx + 4, hy - 7, hx + 10, hy - 1], fill=(17, 17, 17, 255))
    # ear flapping
    ex = hx - 8 - 4 * math.sin(t * 2)
    d.polygon([ex, hy - 12, ex - 10, hy + 2 + 4 * math.sin(t * 2), ex + 2, hy - 2], fill=RED)
    # tail up wagging
    tx, ty = body_a[0], body_a[1] - 2
    limb(d, tx, ty, tx - 18, ty - 14 + 6 * math.sin(t * 2 + 1), w=7)
    limb(d, tx - 18, ty - 14 + 6 * math.sin(t * 2 + 1), tx - 26, ty - 26 + 8 * math.sin(t * 2 + 1), w=7)
    # red collar
    limb(d, hx - 4, hy + 10, hx + 8, hy + 13, w=6, col=RED)
    return img


# ---------------------------------------------------------------- hop blob
def draw_hopper(idx):
    img, d = new_tile()
    t = idx / N * 2 * math.pi
    hop = abs(math.sin(t))           # 0..1..0 twice per full cycle? sin gives 1 hump per pi
    lift = 46 * math.sin(t * 1) ** 1 if False else 46 * max(0.0, math.sin(t))
    cx = T / 2
    body_r = 34
    squash = 1 + 0.18 * (1 - min(1.0, lift / 46.0))
    by = T * 0.62 - lift
    shadow(d, cx, 30 + 8 * (1 - lift / 46.0))
    # body — red rounded blob with squash & stretch
    bw, bh = body_r * squash, body_r / squash
    d.ellipse([cx - bw, by - bh, cx + bw, by + bh], fill=RED)
    # face
    d.ellipse([cx - 12, by - 10, cx - 2, by - 0], fill=(255, 255, 255, 235))
    d.ellipse([cx + 4, by - 10, cx + 14, by - 0], fill=(255, 255, 255, 235))
    d.ellipse([cx - 9, by - 7, cx - 5, by - 3], fill=(17, 17, 17, 255))
    d.ellipse([cx + 7, by - 7, cx + 11, by - 3], fill=(17, 17, 17, 255))
    d.arc([cx - 8, by + 2, cx + 10, by + 14], 20, 160, fill=(255, 255, 255, 235), width=3)
    # stub legs kicking
    for phase, dx in ((0, -1), (math.pi, 1)):
        foot_y = by + bh + 10 - 8 * max(0, math.sin(t + phase))
        limb(d, cx + 10 * dx, by + bh - 4, cx + 16 * dx + 6 * math.sin(t + phase), foot_y, w=8, col=RED)
    # little film-camera eye on top (brand nod)
    d.ellipse([cx - 8, by - bh - 12, cx + 8, by - bh + 4], fill=(17, 17, 17, 220))
    d.ellipse([cx - 3, by - bh - 8, cx + 3, by - bh - 2], fill=W)
    return img


if __name__ == "__main__":
    save_sheet([draw_runner(i) for i in range(N)], "runner")
    save_sheet([draw_kid(i) for i in range(N)], "kid")
    save_sheet([draw_girl(i) for i in range(N)], "girl")
    save_sheet([draw_dog(i) for i in range(N)], "dog")
    save_sheet([draw_hopper(i) for i in range(N)], "hopper")
    print("done")
