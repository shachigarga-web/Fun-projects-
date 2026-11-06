"""
"YOU'RE ALLOWED" affirmation series for lilac tinted chapters.

Look: off-white paper, graphite pencil props, crayon-textured colour on the
mascot only, big chunky title + small spaced handwritten line.

Mascot (original, lilac tinted chapters): long dark curly hair, warm brown skin,
gold hoops, lilac top, little lilac flower clip.

  python allowed.py --slides          # carousel PNGs (1080x1350) in out/
  python allowed.py --reel            # 9:16 reel with gentle motion in out/
  python allowed.py --only 1          # just slide 1
"""
import argparse, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE_F = os.path.join(HERE, "Chewy-Regular.ttf")
SUB_F = os.path.join(HERE, "Gaegu-Bold.ttf")
W, H, SS = 1080, 1350, 2

PAPER = (247, 243, 239)
GRAPHITE = (58, 52, 60)
TEXT = (28, 24, 30)
SKIN, SKIN_SH = (198, 140, 108), (176, 118, 90)
HAIR = (34, 28, 38)
LILAC, LILAC_DK, LILAC_LT = (178, 152, 222), (120, 98, 180), (214, 198, 240)
PANTS = (96, 86, 168)
CHEEK = (234, 128, 140)
GOLD = (222, 172, 64)
WARM = (246, 196, 96)
CREAM = (250, 244, 232)


# ------------------------------------------------------------------ geometry
def P(*p):
    return np.array(p, float)


def curve(*pts, n=20, closed=False):
    p = np.asarray(pts, float)
    p = np.vstack([p[-1], p, p[0], p[1]]) if closed else np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(p) - 2):
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(p[-2][None])
    return np.vstack(out)


def ell(cx, cy, rx, ry=None, a0=0, a1=360, n=60, rot=0):
    ry = rx if ry is None else ry
    a = np.radians(np.linspace(a0, a1, n))
    pts = np.stack([rx * np.cos(a), ry * np.sin(a)], 1)
    r = math.radians(rot)
    return pts @ np.array([[math.cos(r), math.sin(r)], [-math.sin(r), math.cos(r)]]) + [cx, cy]


def resample(pts, step=3.0):
    pts = np.asarray(pts, float)
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    c = np.concatenate([[0], np.cumsum(d)])
    if c[-1] < 1e-6:
        return pts[:1].repeat(2, 0)
    s = np.append(np.arange(0, c[-1], step), c[-1])
    return np.stack([np.interp(s, c, pts[:, 0]), np.interp(s, c, pts[:, 1])], 1)


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, seed=0, w=W, h=H):
        self.w, self.h = w, h
        self.rng = np.random.default_rng(seed)
        self.img = Image.new("RGB", (w * SS, h * SS), PAPER).convert("RGBA")
        self._grain = None

    def grain(self):
        if self._grain is None:
            r = np.random.default_rng(99)
            fine = r.random((self.h * SS, self.w * SS)).astype(np.float32)
            coarse = np.asarray(Image.fromarray((r.random((self.h * SS // 6, self.w * SS // 6)) * 255).astype(np.uint8))
                                .resize((self.w * SS, self.h * SS), Image.BICUBIC), np.float32) / 255
            self._grain = (fine, coarse)
        return self._grain

    def _composite(self, mask, col, alpha=1.0):
        a = np.asarray(mask, np.float32) / 255 * alpha
        lay = np.zeros((self.h * SS, self.w * SS, 4), np.uint8)
        lay[..., :3] = col[:3]
        lay[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(lay, "RGBA"))

    def crayon(self, pts, col, strength=1.0, off=(0, 0), solid=False):
        """Flat colour with waxy crayon tooth and slightly rough edge."""
        pts = np.asarray(pts, float)
        pts = resample(np.vstack([pts, pts[:1]]), 10) + self.rng.normal(0, 1.2, (1, 2)) + off
        pts = pts + self.rng.normal(0, 0.9, pts.shape)
        m = Image.new("L", (self.w * SS, self.h * SS), 0)
        ImageDraw.Draw(m).polygon([tuple(p * SS) for p in pts], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(1.2))
        fine, coarse = self.grain()
        a = np.asarray(m, np.float32) / 255
        tooth = np.clip((0.86 if solid else 0.62) + 0.5 * fine * (0.6 + 0.6 * coarse), 0, 1)
        self._composite(Image.fromarray((a * tooth * 255).astype(np.uint8)), col, strength)

    def pencil(self, pts, w=3.2, col=GRAPHITE, sketch=True, taper=0.25):
        """Graphite line: grainy, tapered, with a faint second pass."""
        pts = resample(pts, 2.5)
        passes = [(0, 0, 1.0)] + ([(self.rng.normal(0, 1.2), self.rng.normal(0, 1.2), 0.45)] if sketch else [])
        m = Image.new("L", (self.w * SS, self.h * SS), 0)
        d = ImageDraw.Draw(m)
        for dx, dy, a in passes:
            q = pts + [dx, dy] + self.rng.normal(0, 0.35, pts.shape)
            n = len(q)
            t = np.linspace(0, 1, n)
            prof = 0.35 + 0.65 * np.clip(np.minimum(t, 1 - t) / taper, 0, 1) if taper else np.ones(n)
            tg = np.gradient(q, axis=0)
            nm = np.stack([-tg[:, 1], tg[:, 0]], 1) / (np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9)
            hw = (w * prof / 2)[:, None]
            poly = np.vstack([q + nm * hw, (q - nm * hw)[::-1]]) * SS
            d.polygon([tuple(p) for p in poly], fill=int(255 * a))
        fine, _ = self.grain()
        a = np.asarray(m, np.float32) / 255 * np.clip(0.45 + 0.75 * fine, 0, 1)
        self._composite(Image.fromarray((a * 255).astype(np.uint8)), col, 0.92)

    def text(self, s, x, y, font, size, col=TEXT, track=0, anchor="center"):
        f = ImageFont.truetype(font, int(size * SS))
        widths = [f.getlength(ch) + track * SS for ch in s]
        total = sum(widths) - track * SS
        cx = x * SS - (total / 2 if anchor == "center" else 0)
        d = ImageDraw.Draw(self.img)
        spans = []
        for ch, wd in zip(s, widths):
            d.text((cx, y * SS), ch, font=f, fill=col, anchor="ls")
            spans.append((cx / SS, (cx + wd) / SS))
            cx += wd
        return spans                                      # per-char x spans (for doodles)

    def result(self):
        return self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)


# ------------------------------------------------------------------ mascot
def mascot_head(c, cx, cy, r=88, eyes="closed", tilt=0, mouth="smile", look=(0, 0)):
    """Long curly hair, warm skin, gold hoops, lilac flower clip."""
    rng = c.rng
    # hair mass behind (curly silhouette made of bumps)
    pts = []
    for a in np.linspace(150, 390, 26):
        rr = r * (1.32 + 0.07 * math.sin(math.radians(a) * 9))
        pts.append((cx + rr * math.cos(math.radians(a)), cy - 8 + rr * 0.98 * math.sin(math.radians(a))))
    pts += [(cx + r * 1.38, cy + r * 1.05), (cx + r * 1.22, cy + r * 1.5), (cx + r * 0.85, cy + r * 1.2),
            (cx - r * 0.85, cy + r * 1.2), (cx - r * 1.22, cy + r * 1.5), (cx - r * 1.38, cy + r * 1.05)]
    hair = curve(*pts, n=6, closed=True)
    c.crayon(hair, HAIR, solid=True)
    for i in range(7):                                    # a few curl strokes for texture
        s_ = 1 if i % 2 else -1
        x0 = cx + s_ * rng.uniform(1.0, 1.22) * r
        y0 = cy + rng.uniform(0.0, 0.85) * r
        c.pencil(ell(x0, y0, 10, 13, 0, 300, 16), 2.4, (88, 80, 96), sketch=False)
    # face
    face = ell(cx, cy + 4, r * 0.86, r * 0.92, rot=tilt)
    c.crayon(face, SKIN)
    c.pencil(ell(cx, cy + 4, r * 0.86, r * 0.92, 20, 160, 30, rot=tilt), 2.6)
    # curly fringe over forehead
    fr = [(cx - r * 0.95, cy - r * 0.05)]
    for i, a in enumerate(np.linspace(195, 345, 9)):
        rr = r * (0.98 if i % 2 else 1.08)
        fr.append((cx + rr * math.cos(math.radians(a)), cy - 6 + rr * math.sin(math.radians(a))))
    fr += [(cx + r * 0.95, cy - r * 0.05), (cx + r * 0.55, cy - r * 0.42), (cx + r * 0.1, cy - r * 0.5),
           (cx - r * 0.35, cy - r * 0.45), (cx - r * 0.75, cy - r * 0.3)]
    c.crayon(curve(*fr, n=5, closed=True), HAIR, solid=True)
    # side curls framing the face
    for s in (-1, 1):
        c.crayon(curve((cx + s * r * 0.8, cy - r * 0.1), (cx + s * r * 0.98, cy + r * 0.5),
                       (cx + s * r * 0.9, cy + r * 1.05), (cx + s * r * 1.1, cy + r * 0.5),
                       (cx + s * r * 1.05, cy - r * 0.1), n=6, closed=True), HAIR, solid=True)
    # hoops
    for s in (-1, 1):
        c.pencil(ell(cx + s * r * 0.86, cy + r * 0.52, 11, 14), 3.2, GOLD, sketch=False, taper=0)
    # flower clip
    fx, fy = cx + r * 0.72, cy - r * 0.62
    for k in range(5):
        a = math.radians(k * 72 - 90)
        c.crayon(ell(fx + 13 * math.cos(a), fy + 13 * math.sin(a), 10), LILAC_LT)
    c.crayon(ell(fx, fy, 6), WARM)
    # face features
    ey = cy + r * 0.1 + look[1] * r * 0.08
    for s in (-1, 1):
        ex = cx + s * r * 0.34 + look[0] * r * 0.12
        if eyes == "closed":
            c.pencil(ell(ex, ey - 4, 13, 9, 20, 160, 14), 3.6, TEXT, sketch=False, taper=0.3)
        elif eyes == "down":
            c.pencil(P((ex - 12, ey + 2), (ex + 12, ey + 4)), 3.6, TEXT, sketch=False)
        else:
            c.crayon(ell(ex, ey, 6.5, 8.5), TEXT)
            c.crayon(ell(ex + 2, ey - 3, 2, 2), (255, 255, 255))
        c.crayon(ell(ex + s * 12, ey + r * 0.3, 17, 10), CHEEK, 0.75)
    my = cy + r * 0.52
    if mouth == "smile":
        c.pencil(ell(cx, my - 8, 12, 8, 20, 160, 12), 3.2, TEXT, sketch=False)
    elif mouth == "open":
        c.crayon(ell(cx, my, 11, 9), (130, 50, 70))
    elif mouth == "flat":
        c.pencil(P((cx - 9, my), (cx + 9, my)), 3.2, TEXT, sketch=False)


def limb(c, pts, w, col, outline=True):
    path = curve(*pts, n=14)
    tg = np.gradient(path, axis=0)
    nm = np.stack([-tg[:, 1], tg[:, 0]], 1) / (np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9)
    poly = np.vstack([path + nm * w / 2, ell(*path[-1], w / 2, n=12)[:0], (path - nm * w / 2)[::-1]])
    c.crayon(np.vstack([poly, ell(*path[0], w / 2, n=10)]), col)
    c.crayon(ell(*path[-1], w / 2, n=14), col)
    if outline:
        c.pencil(path + nm * w / 2, 2.4)
        c.pencil(path - nm * w / 2, 2.4)


def hand(c, x, y, r=17):
    c.crayon(ell(x, y, r, r * 0.88), SKIN)
    c.pencil(ell(x, y, r, r * 0.88, 200, 340, 12), 2.2)


# ------------------------------------------------------------------ slides
def header(c, sub, circle_word=None, title="YOU'RE ALLOWED"):
    c.text(title, 540, 320, TITLE_F, 128, TEXT, track=4)
    spans = c.text(sub, 540, 440, SUB_F, 58, TEXT, track=5)
    if circle_word and circle_word in sub:
        i = sub.index(circle_word)
        x0, x1 = spans[i][0], spans[i + len(circle_word) - 1][1]
        cx, w = (x0 + x1) / 2, (x1 - x0) / 2 + 20
        c.pencil(ell(cx, 425, w, 34, 160, 520, 60), 4.5, LILAC_DK, sketch=True, taper=0.15)
    c.text("lilac tinted chapters", 540, 1290, SUB_F, 34, (196, 186, 198), track=2)


def slide_rest(c):
    header(c, "to rest without feeling guilty", "rest")
    # props: window with moon, plant, floor line, cushion
    c.pencil(P((170, 600), (380, 600), (380, 860), (170, 860), (170, 600)), 3)
    c.pencil(P((275, 600), (275, 860)), 2.6)
    c.pencil(P((170, 730), (380, 730)), 2.6)
    c.pencil(np.vstack([ell(230, 660, 26, 26, 60, 300, 24), ell(244, 660, 21, 21, 290, 70, 20)]), 2.6)
    for x, y in [(330, 640), (310, 790), (210, 800)]:
        c.pencil(P((x - 8, y), (x + 8, y)), 2.2, sketch=False)
        c.pencil(P((x, y - 8), (x, y + 8)), 2.2, sketch=False)
    c.pencil(P((120, 1110), (960, 1104)), 3)
    c.pencil(P((840, 1104), (830, 1010), (930, 1010), (920, 1104)), 3)
    for a in (-60, -30, 0, 30, 55):
        rr = math.radians(a - 90)
        c.pencil(curve((880, 1010), (880 + 50 * math.cos(rr), 960 + 40 * math.sin(rr)),
                       (880 + 90 * math.cos(rr), 1000 + 90 * math.sin(rr))), 2.6)
    c.pencil(curve((330, 1104), (320, 860), (360, 820), (720, 820), (760, 860), (750, 1104)), 3)
    # mascot sitting, hugging a mug
    c.crayon(curve((420, 1104), (400, 1040), (440, 990), (540, 975), (640, 990), (680, 1040), (660, 1104),
                   n=10, closed=True), PANTS)
    c.pencil(curve((420, 1104), (400, 1040), (440, 990), (540, 975), (640, 990), (680, 1040), (660, 1104)), 2.6)
    mascot_head(c, 540, 700, 88, eyes="closed")
    c.crayon(curve((452, 1000), (440, 900), (470, 830), (540, 815), (610, 830), (640, 900), (628, 1000),
                   n=10, closed=True), LILAC)
    c.pencil(curve((452, 1000), (440, 900), (470, 830), (540, 815), (610, 830), (640, 900), (628, 1000)), 2.6)
    limb(c, [(470, 850), (450, 930), (505, 960)], 44, LILAC)
    limb(c, [(610, 850), (630, 930), (575, 960)], 44, LILAC)
    # mug
    c.crayon(P((508, 920), (572, 920), (568, 990), (512, 990)), CREAM)
    for y in (938, 958, 976):
        c.crayon(P((510, y), (570, y), (570, y + 8), (510, y + 8)), LILAC_LT)
    c.pencil(P((508, 920), (572, 920), (568, 990), (512, 990), (508, 920)), 2.6)
    c.pencil(ell(578, 952, 14, 18, -80, 80, 14), 2.6)
    hand(c, 506, 962)
    hand(c, 574, 962)
    for x in (526, 554):
        c.pencil(curve((x, 905), (x + 8, 885), (x - 4, 865), (x + 6, 845)), 3.4, (255, 255, 255), sketch=False)


def standing_body(c, cx, top=815, waist=1010, floor=1104):
    legs = [(-1, cx - 32), (1, cx + 32)]
    for s, lx in legs:
        c.crayon(curve((lx - 30, waist - 10), (lx - 28, floor - 6), (lx + 28, floor - 6), (lx + 30, waist - 10),
                       n=6, closed=True), PANTS)
        c.pencil(P((lx - 30, waist), (lx - 28, floor - 6)), 2.4)
        c.pencil(P((lx + 30, waist), (lx + 28, floor - 6)), 2.4)
        c.crayon(ell(lx + s * 8, floor - 4, 32, 12), (70, 60, 80))
    body = curve((cx - 88, waist + 10), (cx - 96, 900), (cx - 70, top + 20), (cx, top), (cx + 70, top + 20),
                 (cx + 96, 900), (cx + 88, waist + 10), n=10, closed=True)
    c.crayon(body, LILAC)
    c.pencil(curve((cx - 88, waist + 10), (cx - 96, 900), (cx - 70, top + 20), (cx, top), (cx + 70, top + 20),
                   (cx + 96, 900), (cx + 88, waist + 10), (cx - 88, waist + 10)), 2.6)


def note(c, x, y, w, h, ang, text, struck=True):
    pts = ell(0, 0, 1, n=4)  # placeholder to keep signature simple
    corners = np.array([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
    r = math.radians(ang)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    q = corners @ R.T + [x, y]
    c.crayon(q, CREAM)
    c.pencil(np.vstack([q, q[:1]]), 2.4)
    f = ImageFont.truetype(SUB_F, int(34 * SS))
    lay = Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        d.text((w * SS / 2, h * SS / 2 + (i - (len(lines) - 1) / 2) * 38 * SS), ln, font=f, fill=TEXT, anchor="mm")
    lay = lay.rotate(-ang, Image.BICUBIC, expand=True)
    c.img.alpha_composite(lay, (int(x * SS - lay.width / 2), int(y * SS - lay.height / 2)))
    if struck:
        a = P((-w / 2 + 14, 6), (w / 2 - 14, -4)) @ R.T + [x, y]
        c.pencil(a, 5, LILAC_DK, taper=0.2)


def slide_labels(c):
    header(c, "to say no to the labels", "no")
    note(c, 210, 640, 250, 110, -8, "be more\nsettled")
    note(c, 860, 600, 250, 110, 7, "prioritize\nhome")
    note(c, 880, 860, 270, 110, -5, "don't be too\nambitious")
    note(c, 190, 900, 230, 100, 6, "focus on\nmarriage")
    c.pencil(P((120, 1104), (960, 1104)), 3)
    standing_body(c, 520)
    mascot_head(c, 520, 700, 88, eyes="open", mouth="flat", look=(1, 0))
    limb(c, [(452, 850), (430, 940), (440, 1010)], 42, LILAC)
    hand(c, 442, 1022)
    limb(c, [(590, 848), (660, 830), (712, 760)], 42, LILAC)
    palm = curve((698, 770), (694, 730), (700, 690), (708, 672), (716, 690), (720, 664), (729, 662), (733, 688),
                 (740, 668), (749, 670), (750, 696), (758, 684), (766, 690), (760, 730), (752, 770),
                 n=4, closed=True)                                # raised open palm: "no"
    c.crayon(palm, SKIN)
    c.pencil(np.vstack([palm, palm[:1]]), 2.4)
    for i in range(3):
        c.pencil(P((770 + i * 6, 700 + i * 30), (800 + i * 6, 695 + i * 30)), 3, LILAC_DK, sketch=False)


def slide_more(c):
    header(c, "to want more for yourself", "more")
    c.pencil(P((600, 560), (960, 560), (960, 920), (600, 920), (600, 560)), 3)
    c.pencil(P((640, 700), (690, 620), (740, 700), (640, 700)), 2.6)                # mountain
    c.pencil(P((650, 660), (672, 640)), 2.2, sketch=False)
    c.pencil(curve((800, 640), (850, 620), (900, 640)), 2.6)                          # plane trail
    c.pencil(P((880, 630), (912, 640), (884, 650)), 2.6)
    c.pencil(P((660, 860), (740, 780)), 3.4)                                          # paintbrush
    c.crayon(ell(742, 777, 9, 14, rot=45), LILAC_DK)
    c.crayon(curve((850, 800), (830, 770), (850, 760), (865, 778), (880, 760), (900, 770), (880, 800),
                   (865, 822), n=4, closed=True), CHEEK)                              # heart
    star = [(780 + (34 if k % 2 == 0 else 15) * math.cos(math.radians(-90 + k * 36)),
             600 + (34 if k % 2 == 0 else 15) * math.sin(math.radians(-90 + k * 36))) for k in range(10)]
    c.crayon(np.array(star), WARM)
    c.pencil(np.vstack([star, star[:1]]), 2.4)
    c.pencil(P((120, 1104), (960, 1104)), 3)
    standing_body(c, 400)
    mascot_head(c, 400, 700, 88, eyes="open", mouth="smile", look=(1, -1))
    limb(c, [(335, 850), (318, 940), (330, 1010)], 42, LILAC)
    hand(c, 332, 1022)
    limb(c, [(468, 845), (600, 760), (740, 640)], 42, LILAC)
    hand(c, 752, 628, 19)
    for (x, y) in [(560, 600), (540, 650)]:
        c.pencil(P((x - 9, y), (x + 9, y)), 2.2, sketch=False)
        c.pencil(P((x, y - 9), (x, y + 9)), 2.2, sketch=False)


def slide_love(c):
    header(c, "to make time for what you love", "love")
    c.pencil(P((690, 1104), (760, 600)), 3.2)                    # easel
    c.pencil(P((900, 1104), (830, 600)), 3.2)
    c.pencil(P((795, 1104), (795, 900)), 3.2)
    c.crayon(P((640, 620), (930, 620), (930, 880), (640, 880)), LILAC_LT)
    c.crayon(P((640, 760), (930, 760), (930, 830), (640, 830)), (250, 170, 150))
    c.crayon(P((640, 820), (930, 820), (930, 880), (640, 880)), (140, 120, 200))
    c.crayon(ell(840, 760, 40, 40, 180, 360, 30), WARM)
    c.pencil(P((640, 620), (930, 620), (930, 880), (640, 880), (640, 620)), 3)
    c.pencil(P((620, 890), (950, 890)), 3.2)
    c.pencil(P((120, 1104), (960, 1104)), 3)
    standing_body(c, 400)
    mascot_head(c, 400, 700, 88, eyes="closed", mouth="smile")
    limb(c, [(468, 850), (560, 820), (620, 760)], 42, LILAC)
    hand(c, 628, 752)
    c.pencil(P((630, 748), (668, 720)), 3.6)
    c.crayon(ell(672, 716, 6, 9, rot=40), (250, 170, 150))
    limb(c, [(335, 850), (300, 920), (330, 960)], 42, LILAC)
    c.crayon(ell(310, 975, 62, 34, rot=-10), CREAM)                # palette
    c.pencil(ell(310, 975, 62, 34, rot=-10), 2.4)
    for (x, y, col) in [(280, 965, CHEEK), (305, 958, WARM), (332, 965, LILAC_DK), (300, 990, (140, 120, 200))]:
        c.crayon(ell(x, y, 9, 7), col)
    hand(c, 330, 962)


def slide_choose(c):
    header(c, "to choose yourself, every time", "yourself")
    c.pencil(P((120, 1104), (960, 1104)), 3)
    standing_body(c, 540)
    mascot_head(c, 540, 700, 88, eyes="closed", mouth="smile")
    limb(c, [(472, 850), (520, 930), (610, 880)], 42, LILAC)       # self-hug
    limb(c, [(608, 850), (560, 940), (470, 890)], 42, LILAC)
    hand(c, 616, 872)
    hand(c, 464, 882)
    for (x, y, s) in [(330, 640, 1.0), (760, 600, 1.2), (800, 900, 0.8), (280, 900, 0.9)]:
        c.crayon(curve((x, y + 26 * s), (x - 26 * s, y), (x - 14 * s, y - 16 * s), (x, y - 6 * s),
                       (x + 14 * s, y - 16 * s), (x + 26 * s, y), n=4, closed=True), CHEEK)
    for (x, y) in [(400, 560), (700, 520), (860, 760), (220, 770)]:
        c.pencil(P((x - 10, y), (x + 10, y)), 2.2, sketch=False)
        c.pencil(P((x, y - 10), (x, y + 10)), 2.2, sketch=False)


SLIDES = [slide_labels, slide_more, slide_love, slide_rest, slide_choose]


def make_reel(paths_by_variant, out, per=3.2, xf=0.35, fps=30):
    """9:16 reel: each slide sits on paper, lines 'boil' between drawn variants, soft crossfades."""
    RW, RH = 1080, 1920
    pad = Image.new("RGB", (RW, RH), PAPER)
    frames_per = int(per * fps)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{RW}x{RH}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                           "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    slides = [[Image.open(p) for p in v] for v in paths_by_variant]

    def frame(i, f):
        v = slides[i][(f // 8) % len(slides[i])]                       # boil ~4x per second
        z = 1 + 0.025 * f / frames_per
        im = v.resize((round(W * z), round(H * z)), Image.BICUBIC)
        im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
        fr = pad.copy()
        fr.paste(im, (0, (RH - H) // 2))
        return fr

    for i in range(len(slides)):
        for f in range(frames_per):
            fr = frame(i, f)
            if i + 1 < len(slides) and f > frames_per - xf * fps:
                fr = Image.blend(fr, frame(i + 1, 0), (f - (frames_per - xf * fps)) / (xf * fps))
            ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slides", action="store_true")
    ap.add_argument("--reel", action="store_true")
    ap.add_argument("--only", type=int)
    a = ap.parse_args()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    idx = [a.only - 1] if a.only else range(len(SLIDES))
    for i in idx:
        c = Canvas(seed=i + 1)
        SLIDES[i](c)
        p = os.path.join(HERE, "out", f"slide_{i + 1:02d}.png")
        c.result().save(p)
        print("wrote", p)
    if a.reel:
        variants = []
        for i in range(len(SLIDES)):
            vs = [os.path.join(HERE, "out", f"slide_{i + 1:02d}.png")]
            for k in (1, 2):                                   # extra hand-drawn wobble variants
                c = Canvas(seed=(i + 1) * 100 + k)
                SLIDES[i](c)
                p = os.path.join(HERE, "out", f".boil_{i + 1:02d}_{k}.png")
                c.result().save(p)
                vs.append(p)
            variants.append(vs)
        out = os.path.join(HERE, "out", "youre_allowed_reel.mp4")
        make_reel(variants, out)
        print("wrote", out)


if __name__ == "__main__":
    main()
