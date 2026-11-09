"""
"why she wears sunglasses": short story reel starring Shachi's character.

Scene 1 uses the original artwork. Later scenes rebuild the character in code
with the same crayon look (peach face, orange dupatta hood, black fringe,
half-moon green sunglasses, cobalt sweater) so she can move.

Silent video: add music inside Instagram.

  python sunglasses.py
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "allowed"))
import allowed as A                                        # crayon/pencil canvas

FONT = os.path.join(HERE, "..", "allowed", "Gaegu-Bold.ttf")
W, H, FPS = 1080, 1920, 30
RW, RH = 1390, 2000                                         # character design space

PEACH = (255, 177, 154)
HOOD, HOOD_DK, HOOD_RED = (240, 127, 85), (231, 96, 44), (236, 92, 70)
BLUE = (64, 98, 220)
LENS = (178, 166, 72)
FRAME = (18, 16, 18)
TEXT = (70, 30, 36)


# ------------------------------------------------------------------ character
def C(*p):
    return np.array(p, float)


HOOD_PTS = [(470, 2000), (450, 1500), (400, 1200), (378, 1000), (400, 820), (470, 690), (560, 610), (680, 588),
            (790, 560), (910, 470), (1060, 400), (1170, 380), (1300, 450), (1390, 540), (1390, 1200), (1250, 1350),
            (1080, 1550), (960, 1780), (900, 2000)]
FACE_PTS = [(520, 860), (532, 712), (600, 648), (690, 630), (795, 652), (852, 760), (866, 900), (860, 1050),
            (818, 1150), (722, 1212), (632, 1240), (568, 1160), (528, 1010)]
L_LENS = (492, 880, 152, 200)                              # cx, cy, rx, ry (bottom half)
R_LENS = (757, 880, 105, 195)
EYES = [(548, 990), (728, 990)]


def half_disc(cx, cy, rx, ry, n=40):
    return A.ell(cx, cy, rx, ry, 0, 180, n)


def build_character():
    """Render the character (no eyes) once to a transparent RGBA sprite."""
    c = A.Canvas(seed=3, w=RW, h=RH)
    c.img = Image.new("RGBA", (RW * A.SS, RH * A.SS), (0, 0, 0, 0))
    hood = A.curve(*HOOD_PTS, n=8, closed=True)
    c.crayon(hood, HOOD)
    c.crayon(hood, HOOD, strength=0.75)
    stripe = np.vstack([A.curve((470, 690), (420, 850), (408, 1050), (450, 1260), (560, 1460), n=12),
                        A.curve((600, 1440), (500, 1250), (462, 1050), (474, 860), (515, 720), n=12)])
    c.crayon(stripe, HOOD_RED, strength=0.8)
    c.crayon(A.curve(*FACE_PTS, n=8, closed=True), PEACH, solid=True)
    fringe = [(515, 818)]
    for k, x in enumerate(np.linspace(520, 828, 24)):
        fringe.append((x, 808 if k % 2 else 822))
    fringe += [(832, 806), (690, 622)]
    c.crayon(np.array(fringe), FRAME, solid=True)
    rng = np.random.default_rng(4)
    for x in np.linspace(522, 826, 46):                     # brushy fringe strokes
        top = 622 + abs(x - 690) * 1.18
        c.pencil(C((x + rng.normal(0, 2), top + 8), (x + rng.normal(0, 3), 812 + rng.uniform(0, 16))), 5, FRAME,
                 sketch=False, taper=0.4)
    for cx, cy, rx, ry in (L_LENS, R_LENS):
        c.crayon(half_disc(cx, cy, rx, ry), LENS, solid=True)
    c.crayon(A.ell(640, 1080, 24, 10), (132, 60, 32), solid=True)
    c.crayon(A.curve((440, 1240), (300, 1340), (190, 1560), (160, 1800), (175, 2000), (520, 2000), (500, 1620),
                     (470, 1360), n=8, closed=True), BLUE)
    c.crayon(A.curve((440, 1240), (300, 1340), (190, 1560), (160, 1800), (175, 2000), (520, 2000), (500, 1620),
                     (470, 1360), n=8, closed=True), BLUE, strength=0.7)
    c.crayon(A.curve((1390, 1180), (1180, 1250), (1010, 1420), (930, 1660), (910, 2000), (1390, 2000), n=8,
                     closed=True), BLUE)
    c.crayon(A.curve((1390, 1180), (1180, 1250), (1010, 1420), (930, 1660), (910, 2000), (1390, 2000), n=8,
                     closed=True), BLUE, strength=0.7)
    for x0 in (600, 740):
        ys = np.linspace(1220, 1620, 60)
        c.pencil(np.stack([x0 + 14 * np.sin((ys - 1220) / 52), ys], 1), 10, (140, 106, 100), sketch=False)
    spr = c.img.resize((RW, RH), Image.LANCZOS)
    big = Image.new("RGBA", (RW * 2, RH * 2), (0, 0, 0, 0))     # solid black frames, like the original
    d = ImageDraw.Draw(big)
    for cx, cy, rx, ry in (L_LENS, R_LENS):
        d.line([tuple(p * 2) for p in half_disc(cx, cy, rx - 6, ry - 6, 80)], fill=FRAME + (255,), width=56,
               joint="curve")
        for q in (half_disc(cx, cy, rx - 6, ry - 6, 80)[0], half_disc(cx, cy, rx - 6, ry - 6, 80)[-1]):
            d.ellipse([q[0] * 2 - 28, q[1] * 2 - 28, q[0] * 2 + 28, q[1] * 2 + 28], fill=FRAME + (255,))
    d.rounded_rectangle([333 * 2, 862 * 2, 864 * 2, 892 * 2], radius=24, fill=FRAME + (255,))
    spr.alpha_composite(big.resize((RW, RH), Image.LANCZOS))
    masks = []
    for cx, cy, rx, ry in (L_LENS, R_LENS):
        m = Image.new("L", (RW, RH), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in half_disc(cx, cy, rx - 16, ry - 16)], fill=255)
        masks.append(m)
    return spr, masks


def pose(spr, masks, look=(0, 0), glow=0.0, blink=False):
    s = spr.copy()
    if glow > 0:
        gold = Image.new("RGBA", (RW, RH), (255, 214, 90, 0))
        for m in masks:
            gold.putalpha(m.point(lambda v: int(v * min(1, glow))))
            s.alpha_composite(gold)
    d = ImageDraw.Draw(s)
    if glow < 0.6:
        for ex, ey in EYES:
            x, y = ex + look[0] * 40, ey + look[1] * 26
            if blink:
                d.line([x - 16, y, x + 16, y], fill=(30, 28, 56), width=6)
            else:
                d.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(30, 28, 56))
    return s


def place(frame, s, cx, base_y, width, angle=0.0):
    """Paste the character so its bottom-centre sits at (cx, base_y)."""
    k = width / RW
    im = s.resize((int(RW * k), int(RH * k)), Image.BICUBIC)
    if angle:
        im = im.rotate(angle, Image.BICUBIC, expand=True, center=(im.width / 2, im.height))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(base_y - im.height)))
    return k


# ------------------------------------------------------------------ helpers
def crayon_bg(col, seed):
    c = A.Canvas(seed=seed, w=W, h=H)
    c.img = Image.new("RGBA", (W * A.SS, H * A.SS), col + (255,))
    c.crayon(C((0, 0), (W, 0), (W, H), (0, H)), tuple(min(255, v + 8) for v in col), strength=0.5)
    return c.img.resize((W, H), Image.LANCZOS)


def sprite(draw_fn, w, h, seed=1):
    c = A.Canvas(seed=seed, w=w, h=h)
    c.img = Image.new("RGBA", (w * A.SS, h * A.SS), (0, 0, 0, 0))
    draw_fn(c)
    return c.img.resize((w, h), Image.LANCZOS)


def sun_sprite():
    def f(c):
        c.crayon(A.ell(200, 200, 110), (255, 196, 64), solid=True)
        for k in range(12):
            a = 2 * math.pi * k / 12
            c.pencil(C((200 + 135 * math.cos(a), 200 + 135 * math.sin(a)),
                       (200 + 185 * math.cos(a), 200 + 185 * math.sin(a))), 16, (255, 170, 40), sketch=False)
    return sprite(f, 400, 400)


def bubble_sprite(text, tail_left=True):
    f_ = ImageFont.truetype(FONT, 58)
    w = int(f_.getlength(text)) + 90
    h = 130

    def f(c):
        c.crayon(A.rrect(8, 8, w - 8, h - 30, 36) if hasattr(A, "rrect") else
                 np.vstack([A.ell(w / 2, (h - 30) / 2 + 4, w / 2 - 8, (h - 30) / 2 - 4)]), (255, 252, 248), solid=True)
        tx = 60 if tail_left else w - 60
        c.crayon(C((tx - 18, h - 40), (tx + 18, h - 40), (tx + (-24 if tail_left else 24), h - 6)),
                 (255, 252, 248), solid=True)
    im = sprite(f, w, h)
    ImageDraw.Draw(im).text((w / 2, (h - 30) / 2 + 2), text, font=f_, fill=TEXT, anchor="mm")
    return im


def write_text(frame, lines, t0, t, y=330, size=78, col=TEXT, speed=22):
    """Lines appear letter by letter starting at t0 (seconds into the scene)."""
    f = ImageFont.truetype(FONT, size)
    d = ImageDraw.Draw(frame)
    n = int(max(0, t - t0) * speed)
    for i, ln in enumerate(lines):
        k = min(len(ln), n)
        n -= len(ln)
        if k > 0:
            d.text((W / 2, y + i * size * 1.15), ln[:k], font=f, fill=col, anchor="mm")


def sparkle(d, x, y, r, col=(255, 248, 210)):
    d.polygon([(x, y - r), (x + r * 0.22, y - r * 0.22), (x + r, y), (x + r * 0.22, y + r * 0.22),
               (x, y + r), (x - r * 0.22, y + r * 0.22), (x - r, y), (x - r * 0.22, y - r * 0.22)], fill=col)


def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ scenes
def main():
    print("building character + props...", flush=True)
    spr, masks = build_character()
    orig = Image.open(os.path.join(HERE, "src", "original.jpg")).convert("RGB")
    k = W / orig.width
    orig = orig.resize((W, int(orig.height * k)), Image.LANCZOS)
    bg_peach = crayon_bg(PEACH, 1)
    bg_sun = crayon_bg((255, 214, 150), 2)
    bg_lilac = crayon_bg((214, 196, 240), 3)
    sun = sun_sprite()
    bubbles = [(bubble_sprite("shaadi kab?"), -1, 640), (bubble_sprite("salary kitni hai?", False), 1, 800),
               (bubble_sprite("itni patli kyun?"), -1, 960)]

    scenes = [3.2, 3.0, 4.0, 4.2, 2.6]
    total = sum(scenes)
    starts = np.cumsum([0] + scenes[:-1])
    out = os.path.join(HERE, "why_she_wears_sunglasses.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                           "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    prev = None
    for fi in range(int(total * FPS)):
        T = fi / FPS
        si = int(np.searchsorted(starts, T, side="right") - 1)
        t = T - starts[si]
        dur = scenes[si]

        if si == 0:                                        # the original artwork
            fr = bg_peach.copy()
            z = 1 + 0.04 * t / dur
            im = orig.resize((int(W * z), int(orig.height * z)), Image.LANCZOS)
            fr.paste(im, ((W - im.width) // 2, H - im.height + int(40 * t / dur)))
            write_text(fr, ["everyone asks why", "she wears sunglasses."], 0.3, t, y=250)

        elif si == 1:                                      # is it the sun?
            fr = bg_sun.copy()
            r = 1 + 0.04 * math.sin(t * 3)
            s_ = sun.resize((int(400 * r), int(400 * r)))
            fr.alpha_composite(s_, (760 - s_.width // 2, 560 - s_.height // 2))
            shake = 5 * math.sin(t * 14) * ease((t - 1.6) / 0.2) * (1 - ease((t - 2.5) / 0.3))
            place(fr, pose(spr, masks, look=(0.6, -0.8)), W + 30 - 550, H + 90, 1100, shake)
            write_text(fr, ["is it the sun?"], 0.2, t, y=260)
            if t > 1.6:
                write_text(fr, ["no."], 1.6, t, y=360, size=96)

        elif si == 2:                                      # the relatives
            fr = bg_lilac.copy()
            lk = math.sin(t * 2.2)
            place(fr, pose(spr, masks, look=(lk, 0)), W + 30 - 550, H + 40, 1100)
            for j, (b, side, by) in enumerate(bubbles):
                tt = t - 0.5 - j * 0.55
                if tt < 0:
                    continue
                gx = 500 + side * 70                       # glasses on screen
                sx = W / 2 + side * 760
                if tt < 0.55:                              # fly in
                    x = sx + (gx - sx) * ease(tt / 0.55)
                    a = 1.0
                else:                                       # bounce back off the glasses
                    u = (tt - 0.55) / 0.9
                    x = gx + side * 520 * ease(u)
                    by = by - 40 * math.sin(min(1, u) * math.pi)
                    a = max(0, 1 - u * 0.9)
                bb = b.copy()
                bb.putalpha(bb.getchannel("A").point(lambda v: int(v * a)))
                fr.alpha_composite(bb, (int(x - b.width / 2), int(by - b.height / 2 + 160)))
                if 0.5 < tt < 0.75:
                    d = ImageDraw.Draw(fr)
                    for q in range(3):
                        sparkle(d, gx - side * 30 + q * 18 * side, 1060 + q * 26, 16, (255, 255, 255))
            write_text(fr, ["is it to dodge", "the relatives?"], 0.1, t, y=250)
            if t > 2.9:
                write_text(fr, ["...okay, partly."], 2.9, t, y=470, size=64)

        elif si == 3:                                      # the reveal
            fr = bg_peach.copy()
            zoom = 1 + 0.9 * ease(t / 1.2)
            glow = ease((t - 1.0) / 0.8)
            wz = 1100 * zoom
            kz = wz / RW                                   # keep the sunglasses centred while zooming
            k_ = place(fr, pose(spr, masks, glow=glow), 540 - 597 * kz + wz / 2, int(1100 + 1050 * kz), wz)
            if glow > 0:
                arr = np.asarray(fr, np.float32)
                yy, xx = np.mgrid[0:H, 0:W]
                gx, gy = 540, 1100
                g = np.exp(-(((xx - gx) / 520) ** 2 + ((yy - gy) / 300) ** 2))[..., None] * glow * 0.55
                arr[..., :3] = arr[..., :3] + (np.array([255, 230, 140], np.float32) - arr[..., :3]) * g
                fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                d = ImageDraw.Draw(fr)
                for q in range(9):
                    a = q * 0.7 + t * 1.3
                    rr = 200 + 260 * ((q * 0.37 + t * 0.4) % 1)
                    sz = 14 + 22 * abs(math.sin(t * 4 + q)) * glow
                    sparkle(d, gx + rr * math.cos(a), gy + rr * 0.7 * math.sin(a), sz)
            write_text(fr, ["nope."], 0.2, t, y=230, size=96)
            if t > 1.4:
                write_text(fr, ["her future is", "just that bright."], 1.4, t, y=370)

        else:                                              # end card
            fr = bg_peach.copy()
            place(fr, pose(spr, masks, glow=0.0, blink=(1.2 < t < 1.35)), W + 30 - 500, H + 140, 1000)
            write_text(fr, ["main character energy,", "every single day."], 0.0, t, y=300, speed=60)
            write_text(fr, ["lilac tinted chapters  ·  art by shachi"], 0.6, t, y=560, size=40,
                       col=(150, 80, 70), speed=80)

        fr = fr.convert("RGB")
        if si > 0 and t < 0.25 and prev is not None:       # soft cut
            fr = Image.blend(prev, fr, t / 0.25)
        if t > dur - 1 / FPS:
            prev = fr
        ff.stdin.write(fr.tobytes())
        if fi % 90 == 0:
            print(f"  {fi}/{int(total * FPS)}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
