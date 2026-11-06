"""
Lilac Tinted Chapters: scribble-story reel generator.

Everything here is open source:
  - Voice: Kokoro-82M (Apache-2.0) via kokoro-onnx
  - Font:  Caveat (SIL Open Font License)
  - Music: synthesized below with numpy (no samples, no licensing issues)
  - Drawing: procedural "scribble" strokes rendered with Pillow
  - Encoding: ffmpeg

Usage:
  python make_reel.py --models /path/to/kokoro/files --out reel.mp4
"""
import argparse, math, os, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "Caveat.ttf")

W, H, SS, FPS = 1080, 1920, 2, 24          # 9:16 reel, 2x supersampling
BOIL_EVERY = 3                              # line "boil" changes 8x per second
PAPER = (238, 229, 248)
INK = (54, 32, 78, 240)
DEEP = (112, 78, 165, 235)
LILAC = (178, 148, 218, 190)
SOFT = (205, 182, 236, 170)
VOICE, LANG, SPEED = "af_heart", "en-us", 0.88
LEAD, TAIL, FADE = 0.55, 0.85, 0.35
MUSIC_DB_BELOW_VOICE = 18                   # narration must sit clearly on top
HEADER = "lilac tinted chapters  ~  ch. 1"

# --------------------------------------------------------------------------
# shape helpers (design space = 1080 x 1920 pixels)
# --------------------------------------------------------------------------
_rng = np.random.default_rng(7)


def line(x1, y1, x2, y2, n=12):
    t = np.linspace(0, 1, n)[:, None]
    return np.hstack([x1 + (x2 - x1) * t, y1 + (y2 - y1) * t])


def poly(*pts):
    return np.array(pts, float)


def circle(cx, cy, r, ry=None, a0=-90, turns=1.06, n=64, jitter=0.04):
    ry = r if ry is None else ry
    a = np.radians(a0) + np.linspace(0, 2 * math.pi * turns, n)
    k = 1 + jitter * np.sin(a * 2 + _rng.uniform(0, 6))
    return np.stack([cx + r * k * np.cos(a), cy + ry * k * np.sin(a)], 1)


def arc(cx, cy, r, a0, a1, ry=None, n=40):
    ry = r if ry is None else ry
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + r * np.cos(a), cy + ry * np.sin(a)], 1)


def rect(x0, y0, x1, y1, ang=0):
    pts = poly((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0), (x0 + 10, y0 - 2))
    return rotate(pts, ang, ((x0 + x1) / 2, (y0 + y1) / 2)) if ang else pts


def rotate(pts, deg, c):
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(pts, float) - c) @ R.T + c


def hatch(rangefn, x0, x1, sp=16, slant=10):
    """Zig-zag scribble fill. rangefn(x) -> (ytop, ybottom) or None."""
    pts, i, x = [], 0, x0
    while x <= x1:
        r = rangefn(x)
        if r:
            pts.append((x + (slant if i % 2 else 0), r[i % 2]))
        i += 1
        x += sp / 2
    return np.array(pts, float) if len(pts) > 1 else None


def hatch_rect(x0, y0, x1, y1, sp=16):
    return hatch(lambda x: (y0, y1), x0, x1 - 10, sp)


def hatch_circle(cx, cy, r, sp=14):
    def f(x):
        d = r * r - (x - cx) ** 2
        return (cy - math.sqrt(d), cy + math.sqrt(d)) if d > 0 else None
    return hatch(f, cx - r + 2, cx + r - 2, sp, slant=6)


def wavy(x0, x1, y, amp=6, waves=4, n=60):
    x = np.linspace(x0, x1, n)
    return np.stack([x, y + amp * np.sin(np.linspace(0, waves * 2 * math.pi, n))], 1)


def squiggle_text(x0, x1, y, n=50):
    """A line of fake handwriting."""
    x = np.linspace(x0, x1, n)
    yy = y + 6 * np.sin(x * 0.35) + 3 * np.sin(x * 0.11)
    return np.stack([x, yy], 1)


# --------------------------------------------------------------------------
# scene builder
# --------------------------------------------------------------------------
class Scene:
    def __init__(self, vo, header=True, draw_frac=0.62, draw_max=4.2):
        self.vo, self.header = vo, header
        self.draw_frac, self.draw_max = draw_frac, draw_max
        self.items = []

    def s(self, pts, col=INK, w=7, amp=2.6):
        if pts is not None:
            self.items.append(dict(k="s", pts=np.asarray(pts, float), col=col, w=w, amp=amp))
        return self

    def t(self, text, x, y, size, col=INK, ang=0, bold=False, anchor="mm"):
        self.items.append(dict(k="t", text=text, x=x, y=y, size=size, col=col,
                               ang=ang, bold=bold, anchor=anchor))
        return self


def girl_walking(sc, x, y, s=1.0):
    hx, hy = x, y - 300 * s
    sc.s(circle(hx, hy, 46 * s))                                     # head
    sc.s(np.vstack([arc(hx, hy, 52 * s, 170, 370),                    # hair + ponytail
                    poly((hx + 50 * s, hy - 10 * s), (hx + 95 * s, hy + 10 * s),
                         (hx + 110 * s, hy + 50 * s), (hx + 80 * s, hy + 30 * s))]))
    sc.s(poly((hx - 6 * s, hy + 46 * s), (hx - 6 * s, hy + 66 * s)))  # neck
    dress = poly((hx - 6 * s, hy + 66 * s), (x - 70 * s, y - 85 * s),
                 (x + 75 * s, y - 85 * s), (hx + 10 * s, hy + 66 * s), (hx - 6 * s, hy + 66 * s))
    sc.s(dress)
    sc.s(hatch(lambda xx: (hy + 90 * s + abs(xx - hx) * 0.2, y - 95 * s),
               x - 55 * s, x + 60 * s, 18), LILAC, 6, 1.6)
    sc.s(poly((x - 25 * s, y - 85 * s), (x - 55 * s, y)))             # legs
    sc.s(poly((x + 25 * s, y - 85 * s), (x + 50 * s, y - 5 * s)))
    sc.s(poly((hx, hy + 85 * s), (x - 75 * s, y - 150 * s)))          # arms
    sc.s(poly((hx + 8 * s, hy + 85 * s), (x + 70 * s, y - 165 * s), (x + 85 * s, y - 145 * s)))
    sc.s(poly((hx + 18 * s, hy - 4 * s), (hx + 24 * s, hy - 4 * s)), INK, 8)   # eye
    sc.s(arc(hx + 20 * s, hy + 12 * s, 12 * s, 20, 120), INK, 5)               # smile


def lilac_sprig(sc, x, y, s=1.0):
    sc.s(poly((x, y), (x - 8 * s, y - 120 * s), (x + 10 * s, y - 230 * s)), DEEP, 6)
    sc.s(np.vstack([arc(x - 40 * s, y - 120 * s, 40 * s, 0, 90)]), DEEP, 5)
    for i in range(9):
        cx = x + 10 * s + _rng.uniform(-38, 38) * s * (1 - i / 12)
        cy = y - 240 * s + i * 13 * s - 40 * s
        sc.s(circle(cx, cy, 15 * s, n=24), DEEP, 4, 1.4)
    sc.s(hatch_circle(x + 10 * s, y - 230 * s, 40 * s, 12), LILAC, 5, 1.2)


def bez(p0, c, p1, n=30):
    t = np.linspace(0, 1, n)[:, None]
    p0, c, p1 = map(np.array, (p0, c, p1))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * p1


def open_book(sc, cx, cy, w=320, h=230, lines=True):
    top, bot = cy - h / 2, cy + h / 2
    for sgn in (-1, 1):
        ox = cx + sgn * w
        sc.s(np.vstack([bez((cx, top + 25), (cx + sgn * w / 2, top - 35), (ox, top)),
                        poly((ox, bot)),
                        bez((ox, bot), (cx + sgn * w / 2, bot - 25), (cx, bot + 25))]))
    sc.s(line(cx, top + 25, cx, bot + 25))
    if lines:
        for i in range(5):
            yy = top + 60 + i * (h - 80) / 4
            sc.s(squiggle_text(cx - w + 40, cx - 40, yy), DEEP, 4, 1.2)
            sc.s(squiggle_text(cx + 40, cx + w - 40, yy), DEEP, 4, 1.2)


def sparkle(sc, x, y, r=22, col=DEEP):
    sc.s(line(x - r, y, x + r, y, 6), col, 5, 1)
    sc.s(line(x, y - r, x, y + r, 6), col, 5, 1)


def leaf(sc, x, y, s=1.0, ang=0):
    a = arc(0, 30, 60, -150, -30)
    b = arc(0, -30, 60, 30, 150)
    pts = np.vstack([a, b]) * s
    sc.s(rotate(pts + [x, y], ang, (x, y)), DEEP, 5, 1.6)
    sc.s(rotate(line(x - 55 * s, y, x + 70 * s, y), ang, (x, y)), DEEP, 4, 1.2)
    sc.s(hatch(lambda xx: (y - 10 * s, y + 10 * s), x - 35 * s, x + 35 * s, 12), LILAC, 5, 1)


def music_note(sc, x, y, s=1.0):
    sc.s(circle(x, y, 22 * s, 15 * s, n=30), DEEP, 6, 1.4)
    sc.s(hatch_circle(x, y, 16 * s, 8), DEEP, 5, 1)
    sc.s(poly((x + 21 * s, y), (x + 21 * s, y - 110 * s), (x + 60 * s, y - 80 * s)), DEEP, 6, 1.4)


def build_scenes():
    sc = []

    # 0 ---- title card
    s = Scene("Lilac Tinted Chapters. Chapter one: The Margins.", header=False,
              draw_frac=0.8, draw_max=3.6)
    lilac_sprig(s, 300, 520, 1.1)
    s.t("Lilac", 560, 470, 190, INK, -4, True)
    s.t("Tinted", 600, 650, 190, INK, -3, True)
    s.t("Chapters", 560, 830, 190, INK, -2, True)
    s.s(wavy(260, 860, 940, 10, 2), DEEP, 7)
    s.t("chapter one ~ the margins", 540, 1060, 80, DEEP, 0)
    sc.append(s)

    # 1 ---- Mira walks home
    s = Scene("Every evening, Mira walked home the long way.")
    s.s(wavy(40, 1040, 1080, 5, 3), INK, 7)
    for (x0, w, h) in [(60, 150, 170), (230, 120, 230)]:               # far houses
        s.s(rect(x0, 1080 - h, x0 + w, 1080), DEEP, 5, 1.6)
        s.s(poly((x0 - 15, 1080 - h), (x0 + w / 2, 1080 - h - 80), (x0 + w + 15, 1080 - h)), DEEP, 5, 1.6)
        s.s(rect(x0 + w / 2 - 20, 1080 - h + 50, x0 + w / 2 + 20, 1080 - h + 95), DEEP, 4, 1.2)
        s.s(hatch_rect(x0 + w / 2 - 16, 1080 - h + 54, x0 + w / 2 + 16, 1080 - h + 91, 9), LILAC, 4, 1)
    s.s(poly((830, 1080), (830, 480)))                                  # lamp post
    s.s(arc(770, 480, 60, 180, 360))
    s.s(poly((710, 480), (710, 510)))
    s.s(poly((680, 560), (695, 510), (725, 510), (740, 560), (680, 560)))
    s.s(hatch_circle(710, 590, 75, 16), SOFT, 6, 1.4)
    for a in range(0, 180, 30):
        r0, r1 = 95, 130
        aa = math.radians(a)
        s.s(line(710 + r0 * math.cos(aa), 560 + r0 * math.sin(aa),
                 710 + r1 * math.cos(aa), 560 + r1 * math.sin(aa), 5), DEEP, 5, 1)
    s.s(np.vstack([arc(230, 420, 60, 60, 300), arc(255, 420, 48, 290, 70)]), INK, 6)
    for (x, y) in [(420, 360), (560, 450), (130, 560), (950, 360)]:
        sparkle(s, x, y, 16)
    girl_walking(s, 540, 1080, 1.25)
    s.s(poly((420, 1060), (390, 1062)), DEEP, 4, 1)                      # motion dashes
    s.s(poly((410, 1000), (375, 1002)), DEEP, 4, 1)
    sc.append(s)

    # 2 ---- the bookshop
    s = Scene("Not because it was shorter. But because of the little bookshop on the corner, "
              "whose window glowed lilac after the rain.", draw_max=4.6)
    s.s(rect(170, 430, 910, 1090))
    s.t("BOOKS", 540, 400, 110, INK, 0, True)
    s.s(poly((150, 500), (930, 500)))
    s.s(np.vstack([arc(150 + i * 97.5 + 48.75, 500, 48.75, 180, 0, ry=42) for i in range(8)]))
    for i in range(0, 8, 2):
        x0 = 150 + i * 97.5
        s.s(hatch(lambda x: (502, 500 + 40), x0 + 8, x0 + 90, 14), LILAC, 5, 1.2)
    s.s(rect(230, 600, 640, 960))
    s.s(hatch_rect(240, 610, 630, 950, 22), LILAC, 7, 1.6)
    s.s(poly((240, 880), (630, 880)), INK, 6)
    for i, x in enumerate(range(270, 600, 38)):
        h = [150, 120, 165, 110, 140, 160, 125, 150, 135][i % 9]
        s.s(rect(x, 880 - h, x + 28, 880), INK, 5, 1.4)
    s.s(rect(700, 640, 850, 1090))
    s.s(circle(825, 870, 9, n=16), INK, 6, 1)
    s.s(circle(540, 1180, 320, 40, n=60), DEEP, 5, 1.4)                 # puddle
    s.s(hatch(lambda x: (1165, 1195), 300, 780, 26), LILAC, 5, 1)
    for _ in range(42):                                                  # rain
        x, y = _rng.uniform(60, 1020), _rng.uniform(260, 1200)
        s.s(line(x, y, x - 14, y + 42, 4), DEEP, 4, 1)
    sc.append(s)

    # 3 ---- the note
    s = Scene("One evening, tucked inside a book she'd never seen before, she found a note. "
              "It said: You always stop here. So do I.", draw_max=4.4)
    open_book(s, 540, 1000, 330, 280)
    s.s(rect(500, 470, 930, 760, ang=-6), INK, 6)
    s.s(hatch(lambda x: (484, 498), 520, 900, 30), SOFT, 4, 1)
    s.t("you always", 712, 560, 84, DEEP, 6)
    s.t("stop here.", 712, 640, 84, DEEP, 6)
    s.t("so do i.", 735, 722, 76, INK, 6, True)
    sparkle(s, 360, 560, 24)
    sparkle(s, 960, 520, 18)
    sparkle(s, 220, 1150, 16)
    sc.append(s)

    # 4 ---- she writes back
    s = Scene("She wrote back. Just one line. And left it in the very same book.")
    s.s(rect(170, 430, 910, 1060, ang=3), INK, 7)
    s.t("you always stop here.", 540, 560, 78, DEEP, 3)
    s.t("so do i.", 520, 650, 78, DEEP, 3)
    s.s(wavy(260, 820, 735, 4, 6), SOFT, 4, 1)
    s.t("then let's keep", 540, 840, 96, INK, 3, True)
    s.t("stopping here.", 560, 940, 96, INK, 3, True)
    pen = poly((760, 1010), (980, 760), (1010, 790), (790, 1040), (760, 1010))
    s.s(pen, INK, 6)
    s.s(poly((760, 1010), (740, 1065), (790, 1040)), INK, 6)
    s.s(poly((950, 790), (980, 820)), INK, 5)
    sc.append(s)

    # 5 ---- an autumn of margins
    s = Scene("For a whole autumn, they spoke in the margins. About the moon, and burnt toast, "
              "and the songs that made them cry.", draw_max=4.6)
    open_book(s, 540, 960, 240, 210)
    s.s(np.vstack([arc(250, 520, 80, 60, 300), arc(285, 520, 64, 290, 70)]), INK, 7)
    s.s(rect(700, 430, 900, 610, ang=8), INK, 7)                        # toast
    s.s(arc(800, 440, 105, 200, 340, ry=40), INK, 7)
    s.s(hatch_rect(725, 470, 875, 590, 14), (120, 90, 150, 170), 6, 1.6)
    s.s(poly((760, 520), (790, 505)), INK, 4, 1)
    music_note(s, 880, 820, 1.1)
    music_note(s, 160, 830, 0.9)
    leaf(s, 300, 1250, 1.0, 20)
    leaf(s, 790, 1220, 0.9, -25)
    leaf(s, 540, 640, 0.8, 10)
    for (a, b) in [((330, 600), (430, 800)), ((760, 630), (650, 800)), ((830, 860), (760, 900))]:
        s.s(line(*a, *b, 14), SOFT, 4, 1.4)
    sc.append(s)

    # 6 ---- she never saw who
    s = Scene("She never saw who it was. Somehow, she didn't need to.")
    cx, cy = 540, 600
    s.s(circle(cx, cy, 95))
    s.s(np.vstack([arc(cx, cy - 5, 120, 160, 380), poly((cx + 115, cy + 40), (cx + 120, cy + 140))]))
    s.s(poly((cx - 113, cy + 40), (cx - 120, cy + 140)))
    s.s(arc(cx - 35, cy + 5, 18, 200, 340), INK, 6)
    s.s(arc(cx + 35, cy + 5, 18, 200, 340), INK, 6)
    s.s(arc(cx, cy + 35, 30, 20, 160), INK, 6)
    s.s(hatch_circle(cx - 60, cy + 40, 18, 8), LILAC, 5, 1)
    s.s(hatch_circle(cx + 60, cy + 40, 18, 8), LILAC, 5, 1)
    s.s(poly((cx - 20, cy + 95), (cx - 150, 1080), (cx + 150, 1080), (cx + 20, cy + 95)))
    s.s(hatch(lambda x: (cy + 130 + abs(x - cx) * 0.3, 1065), cx - 130, cx + 130, 20), LILAC, 6, 1.6)
    s.s(rect(cx - 85, 760, cx + 85, 880, ang=-8), INK, 7)
    s.s(hatch_rect(cx - 75, 770, cx + 75, 870, 12), DEEP, 4, 1)
    s.s(poly((cx - 110, 720), (cx - 80, 830), (cx - 20, 860)))
    s.s(poly((cx + 110, 720), (cx + 85, 820), (cx + 30, 850)))
    s.s(poly((cx - 50, 1080), (cx - 55, 1190)))
    s.s(poly((cx + 50, 1080), (cx + 55, 1190)))
    hx, hy = 820, 420
    heart = np.vstack([arc(hx - 30, hy, 30, 150, 360), arc(hx + 30, hy, 30, 180, 390),
                       poly((hx + 55, hy + 18), (hx, hy + 85), (hx - 55, hy + 18))])
    s.s(heart, DEEP, 6)
    s.s(hatch(lambda x: (hy - 15, hy + 60 - abs(x - hx) * 0.9), hx - 50, hx + 50, 12), LILAC, 5, 1)
    sparkle(s, 260, 420, 20)
    sc.append(s)

    # 7 ---- when the rain stops
    s = Scene("Because some people arrive as faces. Some arrive as handwriting. "
              "And some arrive exactly when the rain stops.", draw_max=4.6)
    for i, col in enumerate([DEEP, LILAC, SOFT]):
        s.s(arc(540, 1000, 420 - i * 45, 180, 360), col, 16 - i * 2, 2)
    s.s(np.vstack([arc(540, 760, 260, 190, 350, ry=150)]))              # umbrella
    pts = []
    for i in range(5):
        x0 = 540 - 256 + i * 102.4
        pts.append(arc(x0 + 51.2, 734, 51.2, 180, 0, ry=-26))
    s.s(np.vstack(pts))
    s.s(hatch(lambda x: (760 - 140 * math.sqrt(max(0, 1 - ((x - 540) / 250) ** 2)) + 8, 725),
              300, 780, 18), LILAC, 6, 1.6)
    s.s(poly((540, 610), (540, 1020), (545, 1050), (520, 1060), (505, 1040)))
    for (x, y) in [(220, 440), (380, 360), (690, 380), (860, 470)]:
        s.s(line(x, y, x - 12, y + 34, 4), DEEP, 4, 1)
    for (x, y, r) in [(170, 1150, 22), (900, 1110, 26), (300, 280, 18), (800, 260, 22), (540, 330, 16)]:
        sparkle(s, x, y, r)
    sc.append(s)

    # 8 ---- end card
    s = Scene("To be continued.", header=False, draw_frac=0.7, draw_max=2.4)
    lilac_sprig(s, 540, 760, 1.0)
    s.t("to be continued...", 540, 900, 130, INK, -3, True)
    s.t("chapter two, soon", 540, 1040, 80, DEEP, 0)
    s.s(arc(540, 1080, 230, 20, 160, ry=20), DEEP, 5)
    sc.append(s)
    return sc


# --------------------------------------------------------------------------
# audio: voice + music box
# --------------------------------------------------------------------------
def make_voice(scenes, models):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
    clips = []
    for sc in scenes:
        a, sr = k.create(getattr(sc, "say", None) or sc.vo, voice=VOICE, speed=SPEED, lang=LANG)
        clips.append(np.asarray(a, np.float32))
    return clips, sr


def music_box(dur, sr):
    """Soft A-minor-ish music box + pad, original composition."""
    t_total = int(dur * sr)
    out = np.zeros(t_total, np.float32)
    beat = 60 / 72 / 2                                  # eighth notes at 72 bpm
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67]]
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    f = lambda m: 440 * 2 ** ((m - 69) / 12)
    i, t = 0, 0.0
    nlen = int(2.2 * sr)
    tt = np.arange(nlen) / sr
    while t < dur:
        ch = chords[(i // 8) % 4]
        m = ch[pattern[i % 8]] + 12
        fr = f(m)
        note = (np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 2.8)
                + 0.35 * np.sin(2 * np.pi * fr * 2.01 * tt) * np.exp(-tt * 5)
                + 0.12 * np.sin(2 * np.pi * fr * 3.98 * tt) * np.exp(-tt * 8))
        note *= np.minimum(1, tt / 0.004) * (0.8 if i % 2 else 1.0)
        s0 = int(t * sr)
        seg = out[s0:s0 + nlen]
        seg += note[:len(seg)] * 0.22
        if i % 8 == 0:                                   # pad chord each bar
            plen = min(int(beat * 8 * sr * 1.3), t_total - s0)
            pt = np.arange(plen) / sr
            env = np.minimum(1, pt / 0.8) * np.minimum(1, (plen / sr - pt) / 0.8)
            pad = sum(np.sin(2 * np.pi * f(mm) * pt) for mm in ch) / 4
            out[s0:s0 + plen] += (pad * env * 0.10).astype(np.float32)
        i += 1
        t += beat
    # simple reverb
    ir_len = int(1.6 * sr)
    ir = np.random.default_rng(3).normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / sr * 3.2)
    ir[0] = 1 / 0.03
    n = len(out) + ir_len
    nfft = 1 << (n - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(out, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(out)] * 0.03
    fade = np.minimum(1, np.arange(len(out)) / (1.5 * sr))
    fade = fade * np.minimum(1, (len(out) - np.arange(len(out))) / (2.0 * sr))
    return (wet * fade).astype(np.float32)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
SCENES, TIMELINE, CAPTIONS = None, None, None
_font_cache, _text_cache = {}, {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        f = ImageFont.truetype(FONT, int(size * SS))
        f.set_variation_by_name("Bold" if bold else "Regular")
        _font_cache[key] = f
    return _font_cache[key]


def text_img(it):
    key = id(it)
    if key not in _text_cache:
        f = font(it["size"], it["bold"])
        l, t, r, b = f.getbbox(it["text"])
        pad = 20 * SS
        im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - l, pad - t), it["text"], font=f, fill=it["col"])
        _text_cache[key] = im
    return _text_cache[key]


def item_len(it):
    if it["k"] == "s":
        return float(np.sum(np.linalg.norm(np.diff(it["pts"], axis=0), axis=1))) + 1
    return text_img(it).width / SS * 1.3


def resample(pts, step=7.0):
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    c = np.concatenate([[0], np.cumsum(d)])
    if c[-1] < 1e-6:
        return pts[:1]
    s = np.append(np.arange(0, c[-1], step), c[-1])
    return np.stack([np.interp(s, c, pts[:, 0]), np.interp(s, c, pts[:, 1])], 1)


def wobble(pts, seed, amp):
    r = np.random.default_rng(seed)
    n = len(pts)
    t = np.linspace(0, 1, n)
    L = n * 7.0
    off = np.zeros((n, 2))
    for k in range(3):
        fr = r.uniform(0.6, 1.6) * (k + 1) * (L / 350 + 0.5)
        a = amp / (k + 1)
        off[:, 0] += a * np.sin(2 * np.pi * fr * t + r.uniform(0, 6.3))
        off[:, 1] += a * np.sin(2 * np.pi * fr * t + r.uniform(0, 6.3))
    off += r.normal(0, amp * 0.45, 2)
    return pts + off


def draw_scene(img, d, sc, p, boil, si):
    total = sum(it["_len"] for it in sc.items)
    budget = p * total
    tip = None
    for ii, it in enumerate(sc.items):
        if budget <= 0:
            break
        frac = min(1.0, budget / it["_len"])
        budget -= it["_len"]
        seed = si * 100003 + ii * 7919 + boil * 31
        if it["k"] == "s":
            pts = wobble(it["_rs"], seed, it["amp"])
            m = max(2, int(len(pts) * frac))
            pts = pts[:m] * SS
            w = int(it["w"] * SS)
            d.line([tuple(q) for q in pts], fill=it["col"], width=w, joint="curve")
            for q in (pts[0], pts[-1]):
                d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=it["col"])
            if frac < 1:
                tip = pts[-1]
        else:
            im = text_img(it)
            if it["ang"]:
                im = im.rotate(it["ang"], resample=Image.BICUBIC, expand=True)
            r = np.random.default_rng(seed)
            jx, jy = r.normal(0, 1.3 * SS, 2)
            cw = max(1, int(im.width * frac))
            crop = im.crop((0, 0, cw, im.height))
            x = int(it["x"] * SS - im.width / 2 + jx)
            y = int(it["y"] * SS - im.height / 2 + jy)
            img.alpha_composite(crop, (max(0, x), max(0, y)))
            if frac < 1:
                tip = (x + cw, y + im.height * 0.6)
    if tip is not None:
        d.ellipse([tip[0] - 9 * SS, tip[1] - 9 * SS, tip[0] + 9 * SS, tip[1] + 9 * SS], fill=INK)


def layout_caption(text, maxw=900, size=64):
    f = font(size, True)
    words, lines, cur = text.split(), [], []
    for w_ in words:
        trial = " ".join(cur + [w_])
        if cur and f.getlength(trial) / SS > maxw:
            lines.append(cur)
            cur = [w_]
        else:
            cur.append(w_)
    lines.append(cur)
    out, total_chars, acc = [], len(text), 0
    lh = size * 1.05
    y0 = 1430 - (len(lines) - 1) * lh / 2
    for li, ln in enumerate(lines):
        full = " ".join(ln)
        x = 540 - f.getlength(full) / SS / 2
        for w_ in ln:
            out.append((w_, x, y0 + li * lh, acc / total_chars))
            x += f.getlength(w_ + " ") / SS
            acc += len(w_) + 1
    return out


def render_frame(fi):
    t = fi / FPS
    si = max(i for i, (s0, _, _) in enumerate(TIMELINE) if s0 <= t)
    s0, dur, vo = TIMELINE[si]
    sc = SCENES[si]
    lt = t - s0
    draw_dur = min(sc.draw_max, dur * sc.draw_frac)
    p = min(1.0, max(0.0, lt / draw_dur))
    p = 1 - (1 - p) ** 1.6                                   # ease out
    boil = fi // BOIL_EVERY

    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_scene(img, d, sc, p, boil, si)

    if sc.header:
        f = font(46, False)
        txt = HEADER
        d.text((W * SS / 2, 150 * SS), txt, font=f, fill=DEEP, anchor="mm")
    # captions, word by word with the voice
    f = font(64, True)
    vt = (lt - LEAD) / max(vo, 0.1)
    for w_, x, y, start in CAPTIONS[si]:
        if vt >= start - 0.02:
            r = np.random.default_rng(boil * 13 + int(x))
            jx, jy = r.normal(0, 0.8 * SS, 2)
            d.text((x * SS + jx, y * SS + jy), w_, font=f, fill=INK, anchor="lm")

    img = img.resize((W, H), Image.LANCZOS)
    frame = PAPER_IMG.copy()
    frame.alpha_composite(img)
    k = min(1.0, max(0.0, (lt - (dur - FADE)) / FADE))
    if k > 0 and si < len(SCENES) - 1:
        frame = Image.blend(frame, PAPER_IMG, k)
    return frame.convert("RGB").tobytes()


def make_paper():
    r = np.random.default_rng(11)
    base = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
    small = r.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    grain = np.array(Image.fromarray(((small * 25) + 128).clip(0, 255).astype(np.uint8))
                     .resize((W, H), Image.BICUBIC), np.float32) - 128
    fine = r.normal(0, 3.5, (H, W)).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    base += (grain * 0.25 + fine)[..., None]
    base -= (vig * 38)[..., None] * np.array([0.9, 1.0, 0.6])
    return Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")


def main():
    global SCENES, TIMELINE, CAPTIONS, PAPER_IMG
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", default="reel.mp4")
    ap.add_argument("--work", default=".")
    ap.add_argument("--remux", help="existing rendered video: keep its frames, only redo audio")
    args = ap.parse_args()

    SCENES = build_scenes()
    for sc in SCENES:
        for it in sc.items:
            if it["k"] == "s":
                it["_rs"] = resample(it["pts"])
            it["_len"] = item_len(it)
    PAPER_IMG = make_paper()

    print("voice...", flush=True)
    clips, sr = make_voice(SCENES, args.models)
    TIMELINE, t = [], 0.0
    for c in clips:
        vo = len(c) / sr
        dur = LEAD + vo + TAIL
        TIMELINE.append((t, dur, vo))
        t += dur
    total = t
    CAPTIONS = [layout_caption(sc.vo) for sc in SCENES]

    voice = np.zeros(int(total * sr) + sr, np.float32)
    for (s0, _, _), c in zip(TIMELINE, clips):
        i0 = int((s0 + LEAD) * sr)
        voice[i0:i0 + len(c)] += c
    voice *= 0.92 / (np.abs(voice).max() + 1e-6)
    music = music_box(len(voice) / sr, sr)
    env = np.convolve(np.abs(voice), np.ones(int(0.3 * sr)) / (0.3 * sr), "same")
    duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
    rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))
    music *= rms(voice) / rms(music) * 10 ** (-MUSIC_DB_BELOW_VOICE / 20)
    mix = voice + music * duck
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    raw = os.path.join(args.work, "mix_raw.wav")
    sf.write(raw, mix, sr)
    # Loudness-normalize to the level Instagram/TikTok play at, stereo 44.1k.
    wav = os.path.join(args.work, "mix.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ac", "2", "-ar", "44100", wav],
                   check=True)

    if args.remux:      # reuse already-rendered frames, only replace the audio
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.remux, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out],
                       check=True)
        print("done (audio replaced):", args.out)
        return

    nframes = int(total * FPS)
    print(f"rendering {nframes} frames ({total:.1f}s)...", flush=True)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest",
         "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, fr in enumerate(pool.imap(render_frame, range(nframes), chunksize=4)):
            ff.stdin.write(fr)
            if i % 120 == 0:
                print(f"  {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done:", args.out)


if __name__ == "__main__":
    main()
