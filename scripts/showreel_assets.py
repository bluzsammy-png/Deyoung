#!/usr/bin/env python3
"""Build ShowReel assets for the DeYoung hero slideshow.
- Copies chosen character stills into public/showreel/
- Renders an animated stick-man run-cycle GIF (PIL frames)
- Cuts two muted square video loops from the v3 film scenes (ffmpeg)
"""
import os, shutil, subprocess

ROOT = "/home/z/my-project"
V3 = f"{ROOT}/campaign/film/v3"
CHARS_A = f"{V3}/chars"          # c1..c7 (film scene stills)
CHARS_B = f"{ROOT}/campaign/v3/chars"  # stick, lineup, ...
OUT = f"{ROOT}/public/showreel"
os.makedirs(OUT, exist_ok=True)

# ---- 1. copy stills ---------------------------------------------------------
copies = {
    f"{CHARS_B}/lineup.png": "style-lineup.png",
    f"{CHARS_A}/c1.png":     "style-cartoon.png",
    f"{CHARS_B}/stick.png":  "style-stickman.png",
    f"{CHARS_A}/c3.png":     "style-real.png",
    f"{CHARS_A}/c4.png":     "style-anime.png",
    f"{CHARS_A}/c5.png":     "style-kids.png",
    f"{CHARS_A}/c6.png":     "style-split.png",
}
for src, dst in copies.items():
    shutil.copyfile(src, f"{OUT}/{dst}")
    print("copied", dst)

# ---- 2. stick-man run cycle GIF ---------------------------------------------
try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.run(["pip", "install", "-q", "pillow"], check=True)
    from PIL import Image, ImageDraw
import math

S = 480
N_FRAMES = 10
FPS = 12

def draw_stick(frame_idx: int) -> Image.Image:
    """One frame of a stick-man run cycle, Deyoung red/black on white."""
    img = Image.new("RGB", (S, S), "#FFFFFF")
    d = ImageDraw.Draw(img)
    t = frame_idx / N_FRAMES * 2 * math.pi  # cycle phase

    cx = S / 2
    ground = S * 0.80
    hip_y = S * 0.52 + 6 * math.sin(2 * t)      # body bob (2x per cycle)
    head_r = 34
    head_cy = hip_y - 92 - 4 * math.sin(2 * t)

    BLACK = (17, 17, 17)
    RED = (220, 38, 38)
    LW = 14  # limb width

    # ground shadow (scales with bob for a hopping feel)
    sh_w = 64 + 10 * math.sin(2 * t)
    d.ellipse([cx - sh_w, ground - 10, cx + sh_w, ground + 8], fill=(230, 230, 230))

    # speed lines (red) behind runner
    for i in range(3):
        y = S * 0.30 + i * 46 + 8 * math.sin(t + i)
        x0 = S * 0.10 + (i % 2) * 24
        d.line([x0, y, x0 + 90 - i * 18, y], fill=(248, 180, 180), width=6)

    def limb(x0, y0, x1, y1, w=LW, col=BLACK):
        d.line([x0, y0, x1, y1], fill=col, width=w)
        r = w // 2
        d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=col)

    # legs — swing opposite phases with knee bend
    swing = 46
    for phase, dx in ((0, 1), (math.pi, -1)):
        hip_x = cx + 6 * dx
        knee_x = hip_x + swing * math.sin(t + phase) * dx
        knee_y = hip_y + 52 + 10 * math.cos(t + phase)
        foot_x = knee_x + 30 * math.sin(t + phase + 0.9) * dx
        foot_y = knee_y + 50 - 14 * max(0, math.sin(t + phase))  # front foot lifts
        limb(hip_x, hip_y, knee_x, knee_y)
        limb(knee_x, knee_y, foot_x, foot_y)

    # torso
    shoulder_y = hip_y - 78
    d.line([cx, hip_y, cx, shoulder_y], fill=BLACK, width=18)

    # arms — pumping opposite to legs
    for phase, dx in ((0, -1), (math.pi, 1)):
        sh_x = cx + 4 * dx
        elb_x = sh_x + 38 * math.sin(t + phase + math.pi) * dx
        elb_y = shoulder_y + 40
        hnd_x = elb_x + 26 * math.sin(t + phase + math.pi + 1.2) * dx
        hnd_y = elb_y + 26 - 8 * math.cos(t + phase)
        limb(sh_x, shoulder_y, elb_x, elb_y, w=12)
        limb(elb_x, elb_y, hnd_x, hnd_y, w=12)

    # head (with red camera-eye — the director look)
    d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=BLACK)
    eye_r = 9
    d.ellipse([cx + 6 - eye_r, head_cy - 8 - eye_r, cx + 6 + eye_r, head_cy - 8 + eye_r], fill=RED)

    # a tiny clapperboard in the leading hand
    # (drawn as a small red rect near front hand)
    return img

frames = [draw_stick(i) for i in range(N_FRAMES)]
gif_path = f"{OUT}/stickman-run.gif"
frames[0].save(
    gif_path, save_all=True, append_images=frames[1:], duration=int(1000 / FPS),
    loop=0, optimize=True,
)
print("gif", gif_path, os.path.getsize(gif_path) // 1024, "KB")

# ---- 3. muted square video loops --------------------------------------------
def cut_loop(src, dst, dur, crop_x_frac, crf=26):
    """scale to 720 high, center-ish square crop (crop_x_frac = left offset fraction), mute."""
    vf = f"scale=-2:720,crop=720:720:'(iw-720)*{crop_x_frac}':0,fps=30"
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-i", src, "-t", str(dur),
        "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
        "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst,
    ]
    subprocess.run(cmd, check=True)
    print("video", os.path.basename(dst), os.path.getsize(dst) // 1024, "KB")

# s1: cartoon boy sits right-of-center -> crop toward 58% x
cut_loop(f"{V3}/v3s1.mp4", f"{OUT}/clip-cartoon.mp4", 5.5, 0.58)
# s2: stick man left-of-center -> crop toward 40% x
cut_loop(f"{V3}/v3s2.mp4", f"{OUT}/clip-doors.mp4", 5.0, 0.40)

total = sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT))
print(f"TOTAL public/showreel: {total // 1024} KB")
