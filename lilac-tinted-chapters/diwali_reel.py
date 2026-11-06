"""
Lilac Tinted Chapters: "ghar se door wali diwali" (Diwali away from home).

Illustrated-reel renderer: flat-colour characters with rough ink outlines on
painterly gradient backgrounds, Hinglish handwritten text, Hindi voiceover.

Open-source parts:
  - Voice: Kokoro-82M (Apache-2.0), Hindi voice hf_alpha, via kokoro-onnx
  - Fonts: Shadows Into Light Two (OFL), DejaVu Sans (free licence) for UI text
  - Music: tanpura drone + plucked melody in raag Yaman, synthesized here
  - Rendering: Pillow + numpy, encoding with ffmpeg

Usage:
  python diwali_reel.py --models /path/to/kokoro --work /tmp/work --out diwali.mp4
  python diwali_reel.py --models ... --preview sheet.png      # stills only
"""
import argparse, math, os, subprocess
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "ShadowsIntoLightTwo-Regular.ttf")
UI = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H, SS, FPS = 1080, 1920, 2, 24
BOIL_EVERY = 4
BUILD = 1.5                      # seconds for each illustration to "draw itself"
XFADE = 0.35
VOICE, SPEED = "hf_alpha", 0.9
LEAD, GAP = 0.35, 0.75
MUSIC_DB_BELOW_VOICE = 17

INK = (44, 24, 70)
HAIR = (36, 20, 56)
SKIN = (196, 138, 102)
SKIN2 = (176, 118, 86)
BLUSH = (226, 120, 130, 110)
HOODIE = (232, 162, 186)
PANTS = (62, 58, 132)
SAREE = (196, 56, 112)
GOLD = (242, 192, 88)
KURTA = (228, 146, 66)
WHITE = (250, 246, 255)
WARM = (255, 204, 110)
FLAME = (255, 168, 60)
CLAY = (190, 98, 62)

_rng = np.random.default_rng(5)


# ------------------------------------------------------------------ geometry
def P(*pts):
    return np.array(pts, float)


def ell(cx, cy, rx, ry=None, a0=0, a1=360, n=56):
    ry = rx if ry is None else ry
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], 1)


def rrect(x0, y0, x1, y1, r=20, n=8):
    pts = []
    for cx, cy, a0 in [(x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]:
        pts.append(ell(cx, cy, r, r, a0, a0 + 90, n))
    return np.vstack(pts)


def rot(pts, deg, c=None):
    pts = np.asarray(pts, float)
    c = pts.mean(0) if c is None else np.asarray(c, float)
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (pts - c) @ R.T + c


def resample(pts, step=6.0):
    pts = np.asarray(pts, float)
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    c = np.concatenate([[0], np.cumsum(d)])
    if c[-1] < 1e-6:
        return pts[:1].repeat(2, 0)
    s = np.append(np.arange(0, c[-1], step), c[-1])
    return np.stack([np.interp(s, c, pts[:, 0]), np.interp(s, c, pts[:, 1])], 1)


def rough(pts, j=2.2, closed=True):
    pts = np.asarray(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    r = resample(pts, 16)
    return r + _rng.normal(0, j, r.shape)


def curve(*pts, n=40):
    """Smooth Catmull-Rom through points."""
    p = np.asarray(pts, float)
    p = np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(p) - 2):
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2][None])
    return np.vstack(out)


# ------------------------------------------------------------------ scene
class Scene:
    def __init__(self, top, bottom, beats, text_col=WHITE, dream=False, night=False, text_y=500):
        self.top, self.bottom, self.beats, self.text_y = top, bottom, beats, text_y
        self.text_col, self.dream, self.night = text_col, dream, night
        self.items, self.blobs = [], []

    def fill(self, pts, col, line=True, lw=6, jit=2.0):
        self.items.append(dict(k="f", pts=rough(pts, jit), col=col, line=line, lw=lw))
        return self

    def shade(self, pts, col):
        return self.fill(pts, col, line=False)

    def ink(self, pts, w=6, col=INK, taper=0.3):
        self.items.append(dict(k="i", pts=resample(pts), w=w, col=col, taper=taper))
        return self

    def limb(self, pts, w, col):
        self.items.append(dict(k="l", pts=resample(curve(*pts, n=20)), w=w, col=col))
        return self

    def glow(self, x, y, r, col=WARM, strength=0.8, flicker=0.15):
        self.items.append(dict(k="g", x=x, y=y, r=r, col=col, s=strength, fl=flicker,
                               ph=_rng.uniform(0, 6.28)))
        return self

    def text(self, s, x, y, size, col=INK, font="hand", ang=0):
        self.items.append(dict(k="t", s=s, x=x, y=y, size=size, col=col, font=font, ang=ang))
        return self

    def blob(self, x, y, rx, ry, col):
        self.blobs.append((x, y, rx, ry, col))
        return self


# ------------------------------------------------------------------ characters
def head(sc, cx, cy, r=70, hair="bob", look=0.0, mood="soft", bindi=False, specs=False):
    """look: -1 (left) .. 1 (right). mood: soft | smile | big | shout | sad | down"""
    if hair == "bob":
        sc.fill(np.vstack([ell(cx, cy - 4, r * 1.2, r * 1.15, 180, 360),
                           P((cx + r * 1.22, cy + r * 0.85), (cx - r * 1.22, cy + r * 0.85))]), HAIR, lw=5)
    if hair == "bun":
        sc.fill(ell(cx - look * r * 0.6, cy - r * 1.05, r * 0.45), HAIR, lw=5)
    sc.limb([(cx, cy + r * 0.6), (cx, cy + r * 1.35)], r * 0.42, SKIN)
    sc.fill(ell(cx, cy, r * 0.93, r), SKIN, lw=6)
    sc.shade(ell(cx + look * r * 0.1, cy + r * 0.86, r * 0.55, r * 0.12), SKIN2 + (120,))
    if hair == "bob":
        fr = np.vstack([ell(cx, cy - 2, r * 1.04, r * 1.06, 190, 350),
                        curve((cx + r * 0.98, cy - r * 0.25), (cx + r * 0.4, cy - r * 0.45),
                              (cx - r * 0.1 + look * 10, cy - r * 0.38), (cx - r * 0.98, cy - r * 0.2), n=12)])
        sc.fill(fr, HAIR, lw=5)
        sc.fill(P((cx - r * 1.02, cy - r * 0.3), (cx - r * 0.9, cy + r * 0.8),
                  (cx - r * 1.2, cy + r * 0.85), (cx - r * 1.2, cy - r * 0.1)), HAIR, line=False)
        sc.fill(P((cx + r * 1.02, cy - r * 0.3), (cx + r * 0.9, cy + r * 0.8),
                  (cx + r * 1.2, cy + r * 0.85), (cx + r * 1.2, cy - r * 0.1)), HAIR, line=False)
    elif hair == "bun":
        sc.fill(np.vstack([ell(cx, cy, r * 1.0, r * 1.04, 185, 355),
                           curve((cx + r * 0.95, cy - r * 0.3), (cx, cy - r * 0.62), (cx - r * 0.95, cy - r * 0.3), n=12)]),
                HAIR, lw=5)
        sc.ink(P((cx + look * 6, cy - r * 1.0), (cx + look * 6, cy - r * 0.62)), 3, (120, 60, 70))
    elif hair == "short":
        sc.fill(np.vstack([ell(cx, cy - 6, r * 1.0, r * 1.0, 180, 360),
                           curve((cx + r, cy - r * 0.2), (cx + r * 0.5, cy - r * 0.55),
                                 (cx - r * 0.6, cy - r * 0.6), (cx - r, cy - r * 0.15), n=12)]), HAIR, lw=5)
        sc.fill(ell(cx, cy - r * 0.85, r * 0.55, r * 0.2), (90, 80, 100), line=False)   # greying
    ex = cx + look * r * 0.18
    ey = cy + r * 0.08
    for s in (-1, 1):
        x = ex + s * r * 0.34
        if mood in ("big", "smile"):
            sc.ink(ell(x, ey + 6, r * 0.13, r * 0.09, 200, 340, 12), 5)
        elif mood == "down":
            sc.ink(P((x - r * 0.1, ey + 4), (x + r * 0.1, ey + 6)), 5)
        else:
            sc.fill(ell(x, ey, r * 0.07, r * 0.09, n=14), INK, line=False, jit=0.4)
        sc.ink(P((x - r * 0.13, ey - r * 0.27 + (6 if mood == "sad" and s < 0 else 0)),
                 (x + r * 0.12, ey - r * 0.29 + (6 if mood == "sad" and s > 0 else 0))), 4, HAIR)
        sc.shade(ell(x + s * r * 0.12, ey + r * 0.3, r * 0.16, r * 0.09), BLUSH)
    if specs:
        for s in (-1, 1):
            sc.ink(ell(ex + s * r * 0.34, ey, r * 0.22, r * 0.17), 4)
        sc.ink(P((ex - r * 0.12, ey), (ex + r * 0.12, ey)), 4)
    sc.ink(P((ex + look * 8, ey + r * 0.2), (ex + look * 14 + 4, ey + r * 0.34), (ex, ey + r * 0.36)), 4,
           SKIN2, taper=0.1)
    my = cy + r * 0.58
    if mood in ("big", "smile"):
        sc.fill(np.vstack([ell(ex, my - 8, r * 0.26, r * 0.2, 0, 180, 20)]), (120, 40, 70), lw=4)
    elif mood == "shout":
        sc.fill(ell(ex, my, r * 0.13, r * 0.16, n=20), (120, 40, 70), lw=4)
    elif mood == "sad":
        sc.ink(ell(ex, my + 8, r * 0.16, r * 0.08, 200, 340, 12), 4)
    else:
        sc.ink(ell(ex, my - 6, r * 0.15, r * 0.08, 20, 160, 12), 4)
    if bindi:
        sc.fill(ell(ex, cy - r * 0.32, 6, 6, n=10), (210, 40, 60), line=False, jit=0.3)
    if hair == "short":
        sc.fill(np.vstack([ell(ex, my - 14, r * 0.3, r * 0.1, 180, 360, 16)]), HAIR, lw=3)


def diya(sc, x, y, s=1.0, lit=True, glow_r=200):
    sc.fill(np.vstack([ell(x, y, 46 * s, 26 * s, 0, 180, 20), P((x - 46 * s, y))]), CLAY, lw=5)
    sc.ink(P((x - 40 * s, y + 6 * s), (x + 40 * s, y + 6 * s)), 3, (240, 160, 110), taper=0.4)
    sc.ink(P((x + 44 * s, y), (x + 62 * s, y - 10 * s)), 6)
    if lit:
        sc.fill(curve((x + 4 * s, y - 2 * s), (x - 10 * s, y - 28 * s), (x + 2 * s, y - 62 * s),
                      (x + 16 * s, y - 28 * s), (x + 4 * s, y - 2 * s), n=10), FLAME, lw=3, jit=0.6)
        sc.fill(ell(x + 3 * s, y - 20 * s, 6 * s, 12 * s, n=12), (255, 240, 180), line=False, jit=0.3)
        sc.glow(x + 3 * s, y - 30 * s, glow_r, WARM, 0.85, 0.22)


def string_lights(sc, pts, cols=((255, 210, 90), (255, 120, 150), (140, 220, 255), (255, 170, 80)),
                  every=60, glow=55):
    path = resample(curve(*pts, n=40), 4)
    sc.ink(path, 4, INK, taper=0.05)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    for i, d in enumerate(np.arange(20, L[-1], every)):
        k = np.searchsorted(L, d)
        x, y = path[min(k, len(path) - 1)]
        c = cols[i % len(cols)]
        sc.fill(ell(x, y + 10, 9, 12, n=12), c, lw=3, jit=0.4)
        sc.glow(x, y + 10, glow, c, 0.55, 0.45)


def city(sc, base=1460, lights=True):
    blocks = [(0, 900, 200), (190, 1020, 170), (350, 840, 210), (550, 980, 160), (700, 880, 190), (880, 1000, 200)]
    for x0, top, w in blocks:
        sc.fill(rrect(x0, top, x0 + w, base + 40, 6), (58, 52, 126), lw=4)
        for yy in range(top + 40, base, 70):
            for xx in range(x0 + 25, x0 + w - 30, 52):
                if _rng.random() < 0.45:
                    sc.fill(rrect(xx, yy, xx + 24, yy + 32, 3), WARM, line=False, jit=0.6)
                    if lights and _rng.random() < 0.4:
                        sc.glow(xx + 12, yy + 16, 40, WARM, 0.35, 0.1)
        if lights:
            string_lights(sc, [(x0 + 10, top + 30), (x0 + w / 2, top + 50), (x0 + w - 10, top + 30)],
                          every=34, glow=30)


# ------------------------------------------------------------------ story
def build():
    S = []

    # 1. mumma's call -------------------------------------------------------
    s = Scene((92, 90, 186), (158, 144, 222), [
        ("mumma ka call aaya.", "मम्मी का फ़ोन आया।"),
        ("\"beta, is baar toh aa rahi hai na?\"", "बेटा, इस बार तो आ रही है ना?"),
    ])
    s.blob(200, 800, 400, 300, (130, 118, 214)).blob(900, 1500, 420, 300, (120, 108, 200))
    s.shade(P((0, 1430), (1080, 1400), (1080, 1920), (0, 1920)), (112, 100, 192))
    s.fill(rrect(100, 640, 440, 1020, 8), (50, 52, 128))
    for x, y in [(150, 900), (210, 860), (300, 930), (360, 880), (250, 960), (390, 960)]:
        s.fill(rrect(x, y, x + 22, y + 30, 3), WARM, line=False, jit=0.5)
    string_lights(s, [(110, 700), (270, 740), (430, 700)], every=40, glow=40)
    s.ink(P((270, 645), (270, 1015)), 7).ink(P((105, 830), (435, 830)), 7)
    s.fill(curve((70, 610), (130, 760), (95, 900), (140, 1060), (60, 1070), (40, 620), n=10), (206, 166, 222))
    s.fill(P((250, 1250), (1030, 1250), (1030, 1430), (250, 1430)), (72, 54, 122))
    s.fill(rrect(260, 1140, 1020, 1270, 30), (236, 228, 250))
    s.fill(ell(905, 1110, 115, 52), (248, 242, 255))
    s.fill(curve((760, 1150), (840, 1120), (1000, 1140), (1015, 1265), (780, 1268), n=10), (190, 170, 236))
    # girl, cross-legged, phone at ear
    s.fill(P((440, 1195), (520, 1140), (600, 1150), (690, 1140), (775, 1190), (720, 1240),
             (600, 1222), (480, 1240)), PANTS)
    s.fill(ell(468, 1222, 30, 16), SKIN).fill(ell(748, 1222, 30, 16), SKIN)
    head(s, 600, 820, 80, "bob", look=-0.3, mood="soft")
    s.fill(P((520, 1165), (500, 1010), (528, 935), (600, 905), (672, 935), (700, 1010), (688, 1165)), HOODIE)
    s.ink(curve((545, 1080), (600, 1095), (655, 1080)), 4).ink(P((578, 930), (572, 1000)), 3).ink(
        P((620, 930), (626, 995)), 3)
    s.limb([(538, 950), (492, 1060), (525, 1135)], 48, HOODIE)
    s.fill(ell(530, 1145, 22, 18), SKIN)
    s.limb([(664, 948), (740, 1020), (700, 880)], 48, HOODIE)
    s.fill(rot(rrect(655, 790, 695, 880, 8), -12), (36, 28, 60))
    s.fill(ell(690, 860, 26, 22), SKIN)
    for i in range(3):
        s.ink(ell(700, 805, 40 + i * 22, 40 + i * 22, -70, -10, 10), 4, WHITE)
    S.append(s)

    # 2. the flight price ---------------------------------------------------
    s = Scene((74, 74, 168), (128, 118, 208), [
        ("flight ka price... das hazaar.", "फ़्लाइट का प्राइस... दस हज़ार।"),
        ("aur monday ko deadline.", "और मंडे को डेडलाइन।"),
    ])
    s.blob(850, 700, 380, 320, (110, 100, 196))
    s.fill(P((0, 1360), (1080, 1310), (1080, 1920), (0, 1920)), (136, 104, 152))
    s.fill(P((150, 1300), (930, 1300), (990, 1365), (90, 1365)), (204, 198, 228))
    s.fill(rrect(185, 690, 895, 1300, 18), (38, 32, 68))
    s.fill(rrect(212, 718, 868, 1272, 8), (242, 242, 252), lw=3)
    s.fill(rrect(212, 718, 868, 800, 6), (120, 108, 210), line=False)
    s.text("BLR  →  LKO", 540, 760, 40, WHITE, "ui")
    s.text("sat, 7 nov  ·  1 adult", 540, 850, 30, (110, 100, 140), "ui")
    s.text("₹ 10,214", 540, 960, 92, (214, 52, 78), "ui")
    s.text("only 2 seats left!", 540, 1050, 32, (214, 52, 78), "ui")
    s.fill(rrect(380, 1110, 700, 1190, 30), (120, 108, 210), lw=3)
    s.text("book now", 540, 1150, 34, WHITE, "ui")
    s.fill(rot(rrect(700, 1130, 900, 1300, 4), 8), (255, 222, 110), lw=4)
    s.text("deadline", 800, 1190, 46, INK, "hand", 8)
    s.text("monday!!", 800, 1245, 46, (200, 40, 70), "hand", 8)
    s.fill(rrect(840, 1420, 960, 1580, 14), (240, 236, 250))
    s.ink(ell(965, 1490, 34, 42, -80, 80, 14), 9)
    for x in (870, 905, 940):
        s.ink(curve((x, 1400), (x + 10, 1370), (x - 8, 1340), (x + 4, 1310)), 4, WHITE)
    s.fill(P((0, 1600), (80, 1560), (320, 1565), (470, 1700), (520, 1920), (0, 1920)), HOODIE)
    s.fill(ell(230, 1470, 175, 195), HAIR)
    s.ink(curve((140, 1360), (220, 1330), (320, 1370)), 3, (90, 70, 120))
    S.append(s)

    # 3. empty flat ---------------------------------------------------------
    s = Scene((88, 86, 178), (140, 128, 214), [
        ("flatmates sab ghar chale gaye.", "फ़्लैटमेट्स सब घर चले गए।"),
        ("flat itna shaant kabhi nahi tha.", "फ़्लैट इतना शांत कभी नहीं था।"),
    ])
    s.blob(300, 900, 360, 400, (106, 100, 196))
    s.shade(P((0, 1470), (1080, 1450), (1080, 1920), (0, 1920)), (106, 96, 186))
    s.fill(P((320, 630), (760, 630), (760, 1475), (320, 1475)), (124, 88, 142))
    s.ink(rrect(370, 690, 710, 980, 6), 4).ink(rrect(370, 1030, 710, 1420, 6), 4)
    s.fill(ell(712, 1080, 16), GOLD)
    s.fill(rot(rrect(405, 850, 675, 1070, 3), 4), (255, 236, 140), lw=4)
    s.text("gaye ghar!", 540, 925, 50, INK, "hand", -4)
    s.text("- riya & sneha :)", 545, 1005, 34, INK, "hand", -4)
    s.ink(P((520, 850), (540, 870)), 6, (210, 60, 80))
    s.fill(rrect(50, 1220, 280, 1480, 6), (162, 134, 192))
    for y in (1300, 1390):
        s.ink(P((55, y), (275, y)), 5)
    s.fill(ell(110, 1278, 34, 14), (236, 140, 170)).fill(ell(185, 1280, 34, 14), (236, 140, 170))
    s.fill(rrect(860, 640, 960, 700, 20), (238, 226, 250))
    s.ink(P((910, 560), (910, 640)), 4)
    s.glow(910, 720, 260, (255, 236, 200), 0.45, 0.04)
    S.append(s)

    # 4. imagining home -----------------------------------------------------
    s = Scene((134, 106, 204), (244, 176, 160), [
        ("ghar pe papa ladder pe chadh ke jhalar laga rahe honge,",
         "घर पे पापा सीढ़ी पे चढ़ के झालर लगा रहे होंगे,"),
        ("aur mumma neeche se chilla rahi hongi... \"dhyaan se!\"",
         "और मम्मी नीचे से चिल्ला रही होंगी... ध्यान से!"),
    ], text_col=INK, dream=True)
    s.blob(800, 900, 400, 300, (210, 150, 190))
    s.fill(P((40, 720), (1040, 720), (1040, 1720), (40, 1720)), (240, 216, 198))
    s.fill(P((20, 700), (1060, 700), (1060, 740), (20, 740)), (150, 80, 90))
    s.fill(P((400, 1150), (640, 1150), (640, 1720), (400, 1720)), (150, 74, 80))
    s.ink(rrect(430, 1190, 610, 1680, 6), 4)
    tor = curve((380, 1140), (520, 1190), (660, 1140), n=30)
    s.ink(tor, 4)
    for i, (x, y) in enumerate(resample(tor, 26)):
        s.fill(ell(x, y + 10, 13), (255, 150, 40) if i % 2 else (255, 205, 60), lw=3, jit=0.6)
        if i % 3 == 1:
            s.fill(rot(ell(x, y + 40, 8, 20, n=12), 10), (90, 150, 80), lw=3, jit=0.4)
    s.fill(ell(540, 1830, 260, 60), (250, 120, 150)).fill(ell(540, 1830, 180, 40), (255, 200, 80)).fill(
        ell(540, 1830, 90, 20), (120, 200, 220))
    diya(s, 340, 1700, 0.8, glow_r=150)
    # ladder + papa
    s.ink(P((800, 1720), (870, 880)), 10).ink(P((930, 1720), (990, 880)), 10)
    for y in range(940, 1700, 110):
        t = (y - 880) / 840
        s.ink(P((870 - 70 * t, y), (990 - 60 * t, y)), 8)
    s.limb([(862, 1170), (850, 1270), (858, 1380)], 40, (236, 232, 242))
    s.limb([(905, 1170), (910, 1270), (930, 1380)], 40, (236, 232, 242))
    s.fill(ell(852, 1392, 26, 12), SKIN).fill(ell(934, 1392, 26, 12), SKIN)
    s.fill(P((830, 1200), (820, 1030), (850, 995), (925, 995), (950, 1030), (945, 1200)), KURTA)
    s.ink(P((887, 1000), (887, 1090)), 3)
    head(s, 885, 925, 62, "short", look=-0.6, mood="smile", specs=True)
    s.limb([(838, 1015), (775, 935), (735, 840)], 36, KURTA)
    s.limb([(935, 1015), (965, 915), (940, 830)], 36, KURTA)
    s.fill(ell(732, 828, 18), SKIN).fill(ell(938, 818, 18), SKIN)
    string_lights(s, [(30, 780), (300, 830), (732, 828), (938, 818), (1060, 790)], every=58, glow=55)
    # mumma
    s.fill(P((650, 1300), (752, 1300), (800, 1720), (600, 1720)), SAREE)
    s.fill(P((735, 1300), (765, 1300), (640, 1720), (600, 1720)), GOLD, lw=4)
    s.limb([(745, 1310), (800, 1230), (820, 1150)], 30, SKIN)
    s.limb([(660, 1310), (700, 1400), (800, 1430)], 30, SKIN)
    head(s, 700, 1225, 58, "bun", look=0.6, mood="shout", bindi=True)
    for i in range(3):
        s.ink(P((780 + i * 18, 1150 - i * 22), (800 + i * 22, 1135 - i * 28)), 4)
    S.append(s)

    # 5. one diya ---------------------------------------------------------
    s = Scene((36, 36, 104), (92, 80, 172), [
        ("maine bhi ek diya khareeda.", "मैंने भी एक दिया ख़रीदा।"),
        ("chaalis rupaye ka.", "चालीस रुपये का।"),
    ], night=True)
    city(s, 1460)
    s.fill(P((0, 1480), (1080, 1480), (1080, 1920), (0, 1920)), (70, 62, 140))
    s.fill(P((0, 1440), (1080, 1440), (1080, 1485), (0, 1485)), (150, 132, 204))
    for x in range(40, 1080, 90):
        s.ink(P((x, 1485), (x, 1700)), 8)
    s.limb([(330, 1420), (470, 1330)], 64, PANTS)
    s.limb([(470, 1330), (462, 1468)], 54, PANTS)
    s.fill(ell(478, 1476, 36, 14), SKIN)
    s.fill(P((300, 1435), (312, 1255), (360, 1210), (440, 1220), (472, 1292), (425, 1435)), HOODIE)
    head(s, 430, 1145, 70, "bob", look=0.8, mood="down")
    s.limb([(432, 1255), (540, 1335), (636, 1395)], 42, HOODIE)
    s.fill(ell(650, 1398, 20, 16), SKIN)
    s.ink(P((660, 1394), (706, 1378)), 4, (230, 210, 180))
    diya(s, 750, 1432, 1.35, glow_r=360)
    S.append(s)

    # 6. video call -------------------------------------------------------
    s = Scene((66, 66, 156), (122, 110, 204), [
        ("video call pe sabne laddoo dikhaye,", "वीडियो कॉल पे सबने लड्डू दिखाए,"),
        ("jaise main screen se utha ke kha lungi.", "जैसे मैं स्क्रीन से उठा के खा लूँगी।"),
    ], text_y=440)
    s.blob(200, 1500, 300, 300, (150, 120, 210)).blob(900, 600, 260, 260, (110, 100, 200))
    s.fill(rrect(160, 560, 920, 1720, 60), (30, 24, 50))
    s.fill(rrect(188, 590, 892, 1690, 40), (244, 196, 160), lw=3)
    s.shade(rrect(188, 1250, 892, 1690, 40), (226, 170, 140))
    string_lights(s, [(200, 700), (540, 760), (880, 700)], every=48, glow=45)
    s.fill(P((610, 1010), (800, 1010), (830, 1260), (580, 1260)), KURTA)
    head(s, 705, 930, 66, "short", look=-0.2, mood="big", specs=True)
    s.limb([(790, 1030), (860, 940), (850, 850)], 34, KURTA)
    s.fill(ell(850, 838, 20), SKIN)
    for i in range(2):
        s.ink(ell(850, 838, 40 + i * 18, 40 + i * 18, -60, 30, 10), 4, INK)
    s.fill(P((300, 1130), (560, 1130), (610, 1690), (250, 1690)), SAREE)
    s.fill(P((520, 1130), (560, 1130), (330, 1690), (280, 1690)), GOLD, lw=4)
    head(s, 430, 1020, 96, "bun", look=0.1, mood="big", bindi=True)
    s.limb([(320, 1160), (300, 1260), (300, 1345)], 36, SKIN)
    s.limb([(545, 1160), (600, 1260), (640, 1340)], 36, SKIN)
    s.fill(ell(470, 1350, 200, 62), (214, 214, 228))
    s.ink(ell(470, 1350, 160, 44, 10, 170, 16), 3, (160, 160, 180))
    for (x, y) in [(400, 1330), (460, 1335), (520, 1330), (430, 1295), (490, 1295), (460, 1262)]:
        s.fill(ell(x, y, 30), (240, 156, 52), lw=4, jit=0.8)
        s.fill(ell(x - 8, y - 8, 7), (255, 214, 140), line=False, jit=0.3)
    s.fill(ell(298, 1350, 24, 20), SKIN).fill(ell(645, 1348, 24, 20), SKIN)
    s.fill(rrect(690, 610, 870, 830, 16), (96, 90, 176), lw=4)
    s.fill(P((735, 830), (745, 790), (805, 790), (815, 830)), HOODIE, line=False)
    head(s, 778, 730, 42, "bob", mood="smile")
    s.fill(ell(360, 1600, 44), (160, 150, 170)).fill(ell(540, 1600, 50), (226, 64, 86)).fill(
        ell(720, 1600, 44), (160, 150, 170))
    s.ink(ell(540, 1612, 26, 14, 190, 350, 12), 7, WHITE)
    s.text("mumma papa", 360, 640, 40, INK, "hand")
    S.append(s)

    # 7. the balcony ------------------------------------------------------
    s = Scene((34, 34, 100), (90, 78, 170), [
        ("phone pe diwali thodi choti lagti hai.", "फ़ोन पे दिवाली थोड़ी छोटी लगती है।"),
        ("par roshni utni hi hoti hai.", "पर रोशनी उतनी ही होती है।"),
    ], night=True)
    for (x, y, c) in [(250, 720, (255, 130, 170)), (820, 640, (255, 210, 100)), (600, 820, (150, 220, 255))]:
        for a in range(0, 360, 30):
            aa = math.radians(a)
            s.ink(P((x + 30 * math.cos(aa), y + 30 * math.sin(aa)), (x + 90 * math.cos(aa), y + 90 * math.sin(aa))),
                  5, c, taper=0.5)
        s.glow(x, y, 160, c, 0.4, 0.5)
    city(s, 1250)
    s.fill(P((0, 1240), (1080, 1240), (1080, 1275), (0, 1275)), (150, 132, 204))
    for x in range(40, 1080, 90):
        s.ink(P((x, 1275), (x, 1620)), 8)
    s.fill(P((0, 1610), (1080, 1610), (1080, 1920), (0, 1920)), (74, 64, 142))
    s.fill(P((330, 1615), (342, 1400), (390, 1350), (460, 1365), (470, 1500), (450, 1615)), HOODIE)
    s.limb([(390, 1600), (540, 1460)], 66, PANTS)
    s.limb([(540, 1460), (556, 1610)], 56, PANTS)
    s.fill(ell(575, 1616, 38, 14), SKIN)
    s.limb([(440, 1390), (520, 1450), (552, 1500)], 42, HOODIE)
    s.fill(ell(552, 1505, 20, 18), SKIN)
    head(s, 468, 1300, 72, "bob", look=0.7, mood="smile")
    s.fill(rrect(160, 1640, 260, 1690, 8), (36, 28, 60))
    diya(s, 720, 1600, 1.1, glow_r=340)
    S.append(s)

    # 8. end card ----------------------------------------------------------
    s = Scene((76, 72, 170), (150, 134, 216), [
        ("ghar se door sabko... happy diwali.", "घर से दूर सबको... हैप्पी दिवाली।"),
        ("tumhara diya bhi ginti mein aata hai.", "तुम्हारा दिया भी गिनती में आता है।"),
    ])
    s.blob(540, 1150, 420, 300, (120, 110, 206))
    for x in (380, 540, 700):
        diya(s, x, 1150, 1.2, glow_r=230)
    s.ink(curve((280, 1220), (540, 1250), (800, 1220)), 5, (200, 180, 240))
    s.text("lilac tinted chapters", 540, 1380, 52, WHITE, "hand")
    S.append(s)
    return S


# ------------------------------------------------------------------ rendering
_fonts, _bg, _glow = {}, {}, {}
SCENES = TL = None
GRAIN = None


def font(kind, size):
    key = (kind, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(HAND if kind == "hand" else UI, int(size))
    return _fonts[key]


def background(si):
    if si in _bg:
        return _bg[si]
    sc = SCENES[si]
    w, h = W // 4, H // 4
    t = np.linspace(0, 1, h)[:, None, None]
    g = np.array(sc.top, float) * (1 - t) + np.array(sc.bottom, float) * t
    img = Image.fromarray(np.broadcast_to(g, (h, w, 3)).astype(np.uint8))
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x, y, rx, ry, c in sc.blobs:
        pts = rough(ell(x / 4, y / 4, rx / 4, ry / 4, n=30), 6)
        d.polygon([tuple(p) for p in pts], fill=c + (150,))
    lay = lay.filter(ImageFilter.GaussianBlur(18))
    img = img.convert("RGBA")
    img.alpha_composite(lay)
    _bg[si] = img.convert("RGB").resize((W * SS, H * SS), Image.BICUBIC)
    return _bg[si]


def glow_sprite(r):
    if r not in _glow:
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x ** 2 + y ** 2) / r
        _glow[r] = np.clip(np.exp(-(d ** 2) * 4.0) * (d < 1), 0, 1).astype(np.float32)
    return _glow[r]


def brush_poly(pts, w, taper, seed):
    n = len(pts)
    if n < 2:
        return None
    tg = np.gradient(pts, axis=0)
    nr = np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9
    nm = np.stack([-tg[:, 1], tg[:, 0]], 1) / nr
    t = np.linspace(0, 1, n)
    r = np.random.default_rng(seed)
    prof = np.ones(n)
    if taper > 0:
        prof = 0.3 + 0.7 * np.clip(np.minimum(t, 1 - t) / taper, 0, 1) ** 0.7
    prof *= 1 + 0.16 * np.sin(2 * np.pi * t * r.uniform(1, 3) + r.uniform(0, 6))
    hw = (w * prof / 2)[:, None]
    return np.vstack([pts + nm * hw, (pts - nm * hw)[::-1]])


def wob(pts, seed, amp=1.4):
    r = np.random.default_rng(seed)
    n = len(pts)
    t = np.linspace(0, 1, n)
    off = np.zeros((n, 2))
    for k in (1, 2):
        fr = r.uniform(0.5, 1.5) * k * (n / 60 + 0.5)
        off[:, 0] += amp / k * np.sin(2 * np.pi * fr * t + r.uniform(0, 6))
        off[:, 1] += amp / k * np.sin(2 * np.pi * fr * t + r.uniform(0, 6))
    return pts + off + r.normal(0, amp * 0.4, 2)


def draw_brush(d, pts, w, col, taper, seed, caps=False):
    poly = brush_poly(pts * SS, w * SS, taper, seed)
    if poly is None:
        return
    d.polygon([tuple(p) for p in poly], fill=col)
    if caps:
        for q in (pts[0] * SS, pts[-1] * SS):
            rr = w * SS / 2
            d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=col)


def item_weight(it):
    if it["k"] == "i":
        return float(np.sum(np.linalg.norm(np.diff(it["pts"], axis=0), axis=1))) * 0.6 + 10
    if it["k"] == "g":
        return 0
    return 40


def render_scene(si, lt, boil, final=False):
    sc = SCENES[si]
    img = background(si).copy()
    d = ImageDraw.Draw(img, "RGBA")
    total = sum(it["_w"] for it in sc.items)
    budget = (1.0 if final else min(1.0, lt / BUILD) ** 0.8) * total
    glows = []
    for ii, it in enumerate(sc.items):
        if budget <= 0:
            break
        frac = 1.0 if it["_w"] == 0 else min(1.0, budget / it["_w"])
        budget -= it["_w"]
        seed = si * 7919 + ii * 104729 + boil * 31
        k = it["k"]
        if k == "f":
            pts = wob(it["pts"], seed, 1.0)
            d.polygon([tuple(p * SS) for p in pts], fill=it["col"])
            if it["line"]:
                draw_brush(d, pts, it["lw"], INK, 0.06, seed)
        elif k == "l":
            pts = wob(it["pts"], seed, 0.8)
            draw_brush(d, pts, it["w"] + 11, INK, 0, seed, True)
            draw_brush(d, pts, it["w"], it["col"], 0, seed, True)
        elif k == "i":
            pts = wob(it["pts"], seed, 1.2)
            m = max(2, int(len(pts) * frac))
            draw_brush(d, pts[:m], it["w"], it["col"], it["taper"], seed, it["taper"] == 0)
        elif k == "t":
            f = font(it["font"], it["size"] * SS)
            if it["ang"]:
                l, t, r, b = f.getbbox(it["s"])
                tim = Image.new("RGBA", (r - l + 40, b - t + 40), (0, 0, 0, 0))
                ImageDraw.Draw(tim).text((20 - l, 20 - t), it["s"], font=f, fill=it["col"])
                tim = tim.rotate(it["ang"], Image.BICUBIC, expand=True)
                img.paste(tim, (int(it["x"] * SS - tim.width / 2), int(it["y"] * SS - tim.height / 2)), tim)
            else:
                d.text((it["x"] * SS, it["y"] * SS), it["s"], font=f, fill=it["col"], anchor="mm")
        elif k == "g":
            glows.append(it)
    small = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32)
    tt = boil * BOIL_EVERY / FPS
    for g in glows:
        r = int(g["r"])
        spr = glow_sprite(r)
        fl = 1 + g["fl"] * (0.6 * math.sin(tt * 7 + g["ph"]) + 0.4 * math.sin(tt * 13.3 + g["ph"] * 2))
        x0, y0 = int(g["x"]) - r, int(g["y"]) - r
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + 2 * r + 1), min(H, y0 + 2 * r + 1)
        if xa >= xb or ya >= yb:
            continue
        a = spr[ya - y0:yb - y0, xa - x0:xb - x0, None] * g["s"] * fl
        reg = small[ya:yb, xa:xb]
        small[ya:yb, xa:xb] = reg + (np.array(g["col"], np.float32) - reg * 0.35) * a * 0.75
    if sc.dream:
        small = small * (1 - VIGNETTE) + 250 * VIGNETTE
    small += GRAIN
    return np.clip(small, 0, 255)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], []
    for w_ in words:
        if cur and f.getlength(" ".join(cur + [w_])) > maxw:
            lines.append(" ".join(cur))
            cur = [w_]
        else:
            cur.append(w_)
    lines.append(" ".join(cur))
    return lines


def draw_beat_text(frame, sc, beat_i, bt, vo):
    text, _ = sc.beats[beat_i]
    f = font("hand", 78)
    lines = wrap(text, f, 900)
    if len(lines) > 1:                       # balance line lengths, no orphans
        lines = wrap(text, f, f.getlength(text) / len(lines) * 1.12)
    lh = 96
    y0 = sc.text_y - (len(lines) - 1) * lh / 2
    total = sum(len(l) for l in lines)
    reveal = min(1.0, max(0.0, bt / max(0.9, min(vo * 0.7, 2.2)))) * total
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    acc = 0
    for i, ln in enumerate(lines):
        n = int(np.clip(reveal - acc, 0, len(ln)))
        acc += len(ln)
        if n <= 0:
            continue
        full_w = f.getlength(ln)
        x = W / 2 - full_w / 2
        d.text((x + 2, y0 + i * lh + 3), ln[:n], font=f, fill=(30, 16, 50, 90), anchor="lm")
        d.text((x, y0 + i * lh), ln[:n], font=f, fill=sc.text_col + (255,), anchor="lm")
    frame.alpha_composite(lay)


def frame_at(fi):
    t = fi / FPS
    si = max(i for i, s in enumerate(TL) if s["start"] <= t)
    st = TL[si]
    lt = t - st["start"]
    boil = fi // BOIL_EVERY
    arr = render_scene(si, lt, boil)
    zoom = 1 + 0.035 * (lt / st["dur"])
    im = Image.fromarray(arr.astype(np.uint8))
    cw, ch = W / zoom, H / zoom
    im = im.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    im = im.convert("RGBA")
    bi = max(i for i, b in enumerate(st["beats"]) if b["start"] <= lt) if lt >= st["beats"][0]["start"] else None
    if bi is not None:
        b = st["beats"][bi]
        draw_beat_text(im, SCENES[si], bi, lt - b["start"], b["vo"])
    k = (lt - (st["dur"] - XFADE)) / XFADE
    if k > 0 and si < len(SCENES) - 1:
        nxt = Image.fromarray(render_scene(si + 1, 0.0, boil).astype(np.uint8)).convert("RGBA")
        im = Image.blend(im, nxt, min(1.0, k))
    if si == len(SCENES) - 1:
        tail = (lt - (st["dur"] - 0.8)) / 0.8
        if tail > 0:
            im = Image.blend(im, Image.new("RGBA", (W, H), (20, 14, 40, 255)), min(1.0, tail))
    return im.convert("RGB").tobytes()


def init_globals():
    global GRAIN, VIGNETTE
    r = np.random.default_rng(1)
    GRAIN = r.normal(0, 3.0, (H, W, 1)).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.55) / (H * 0.5)) ** 2)
    VIGNETTE = (np.clip((v - 0.85) / 0.4, 0, 1) ** 1.5 * 0.55)[..., None].astype(np.float32)


# ------------------------------------------------------------------ audio
def make_voice(models):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
    out = []
    for sc in SCENES:
        row = []
        for _, hi in sc.beats:
            a, sr = k.create(hi, voice=VOICE, speed=SPEED, lang="hi")
            row.append(np.asarray(a, np.float32))
        out.append(row)
    return out, sr


def pluck(freq, dur, sr, bright=0.5, decay=0.996):
    n = int(dur * sr)
    p = max(2, int(sr / freq))
    x = np.zeros(n)
    x[:p] = np.random.default_rng(int(freq)).uniform(-1, 1, p)
    a = 0.5 * decay
    y = lfilter([1.0], np.r_[1, np.zeros(p - 1), -a, -a], x)
    y = lfilter([bright, 1 - bright], [1], y)
    return y / (np.abs(y).max() + 1e-9)


def music(dur, sr):
    n = int(dur * sr) + sr
    out = np.zeros(n)
    sa = 146.83                                     # D3
    f = lambda st, o=0: sa * 2 ** ((st + 12 * o) / 12)
    # tanpura: Pa(low) Sa Sa Sa(low), repeating
    cycle = [f(7, -1), f(0), f(0), f(0, -1)]
    t, i = 0.0, 0
    while t < dur:
        fr = cycle[i % 4]
        s = pluck(fr, 4.0, sr, 0.2, 0.9995) * 0.35
        k = int(t * sr)
        out[k:k + len(s)] += s[:n - k]
        t += 0.85
        i += 1
    # melody in Yaman: N R G, R G M P, G R S ...
    phrase = [(11, -1, 1), (2, 0, 1), (4, 0, 2), (2, 0, 1), (4, 0, 1), (6, 0, 1), (7, 0, 3),
              (6, 0, 1), (4, 0, 1), (2, 0, 1), (4, 0, 2), (2, 0, 1), (0, 0, 4), (None, 0, 2),
              (7, 0, 1), (9, 0, 1), (11, 0, 2), (0, 1, 2), (11, 0, 1), (9, 0, 1), (7, 0, 2),
              (6, 0, 1), (4, 0, 1), (2, 0, 2), (0, 0, 4), (None, 0, 2)]
    beat = 60 / 66
    t = 2.0
    while t < dur - 2:
        for st, o, ln in phrase:
            if st is not None and t < dur - 2:
                s = pluck(f(st, o + 1), 2.5, sr, 0.55, 0.998) * 0.5
                k = int(t * sr)
                out[k:k + len(s)] += s[:n - k]
            t += ln * beat * 0.5
    ir_len = int(1.8 * sr)
    ir = np.random.default_rng(3).normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / sr * 3.0)
    m = len(out) + ir_len
    nfft = 1 << (m - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(out, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(out)]
    out = out + wet * (np.abs(out).max() / (np.abs(wet).max() + 1e-9)) * 0.35
    fade = np.minimum(1, np.arange(n) / (2.0 * sr)) * np.minimum(1, (n - np.arange(n)) / (2.5 * sr))
    return (out * fade).astype(np.float32)


# ------------------------------------------------------------------ main
def prepare():
    global SCENES
    SCENES = build()
    for sc in SCENES:
        for it in sc.items:
            it["_w"] = item_weight(it)
    init_globals()


def main():
    global TL
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--work", default=".")
    ap.add_argument("--out", default="diwali.mp4")
    ap.add_argument("--preview")
    args = ap.parse_args()
    prepare()

    if args.preview:
        thumbs = []
        for si, sc in enumerate(SCENES):
            arr = render_scene(si, 99, 0, final=True)
            im = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
            draw_beat_text(im, sc, len(sc.beats) - 1, 99, 1)
            thumbs.append(im.convert("RGB").resize((360, 640)))
        cols = 4
        sheet = Image.new("RGB", (360 * cols, 640 * math.ceil(len(thumbs) / cols)), "white")
        for i, th in enumerate(thumbs):
            sheet.paste(th, ((i % cols) * 360, (i // cols) * 640))
        sheet.save(args.preview)
        print("preview:", args.preview)
        return

    print("voice...", flush=True)
    clips, sr = make_voice(args.models)
    TL, t = [], 0.0
    for sc, row in zip(SCENES, clips):
        beats, lt = [], 0.0
        for c in row:
            vo = len(c) / sr
            beats.append(dict(start=lt, vo=vo, vo_at=lt + LEAD))
            lt += LEAD + vo + GAP
        lt += 0.4
        TL.append(dict(start=t, dur=lt, beats=beats))
        t += lt
    total = t + 0.6

    voice = np.zeros(int(total * sr) + sr, np.float32)
    for st, row in zip(TL, clips):
        for b, c in zip(st["beats"], row):
            i0 = int((st["start"] + b["vo_at"]) * sr)
            voice[i0:i0 + len(c)] += c
    voice *= 0.9 / (np.abs(voice).max() + 1e-6)
    mus = music(len(voice) / sr, sr)[:len(voice)]
    env = np.convolve(np.abs(voice), np.ones(int(0.3 * sr)) / (0.3 * sr), "same")
    duck = 1 - 0.5 * np.clip(env / 0.05, 0, 1)
    rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))
    mus *= rms(voice) / rms(mus) * 10 ** (-MUSIC_DB_BELOW_VOICE / 20)
    mix = voice + mus * duck
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    raw = os.path.join(args.work, "diwali_raw.wav")
    wav = os.path.join(args.work, "diwali_mix.wav")
    sf.write(raw, mix, sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ac", "2", "-ar", "44100", wav], check=True)

    nframes = int(total * FPS)
    print(f"rendering {nframes} frames ({total:.1f}s)...", flush=True)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
         args.out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, fr in enumerate(pool.imap(frame_at, range(nframes), chunksize=4)):
            ff.stdin.write(fr)
            if i % 240 == 0:
                print(f"  {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done:", args.out)


if __name__ == "__main__":
    main()
