"""
Lilac Tinted Chapters, Chapter 2: "Diwali, from far away".
Same scribble style and pipeline as make_reel.py (Chapter 1), new story.

  python diwali_scribble.py --models /path/to/kokoro --work /tmp/work --out chapter2.mp4
"""
import math
import numpy as np
import make_reel as m
from make_reel import (Scene, INK, DEEP, LILAC, SOFT, line, poly, circle, arc, rect, hatch,
                       hatch_rect, hatch_circle, wavy, sparkle, lilac_sprig, rotate)

m.HEADER = "lilac tinted chapters  ~  ch. 2"
RED = (200, 40, 70, 235)
WARM = (236, 150, 60, 230)


# ---------------------------------------------------------------- people
def person(s, x, fy, h, hair="bob", bindi=False, glasses=None, beard=False, outfit="kurta",
           arms=None, look=0, mood="smile"):
    """Front-facing scribble person. arms: dict side(-1/1) -> list of points from shoulder."""
    r = 0.085 * h
    cy = fy - h + r
    hx = x + look * r * 0.15
    sh_y = cy + r + 0.05 * h
    hem = fy - (0.30 if outfit == "kurta" else 0.22) * h
    # hair behind head
    if hair == "wavy":
        pts = [(hx - r * 1.15, cy + r * 1.5)]
        for a in np.linspace(200, 340, 9):
            rr = r * (1.25 + 0.08 * math.sin(a / 9))
            pts.append((hx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))))
        pts.append((hx + r * 1.15, cy + r * 1.5))
        s.s(np.array(pts))
        s.s(wavy(hx - r * 1.2, hx - r * 1.05, cy + r * 1.2, 4, 1, 8))
        s.s(hatch(lambda xx: (cy - r * 1.1, cy + r * 1.45), hx - r * 1.2, hx - r * 0.85, 10), DEEP, 5, 1)
        s.s(hatch(lambda xx: (cy - r * 1.1, cy + r * 1.45), hx + r * 0.85, hx + r * 1.2, 10), DEEP, 5, 1)
    s.s(circle(hx, cy, r))
    if hair == "bob":
        s.s(np.vstack([arc(hx, cy, r * 1.1, 160, 380)]))
        s.s(poly((hx - r * 1.05, cy + r * 0.2), (hx - r * 1.0, cy + r * 0.9)))
        s.s(poly((hx + r * 1.05, cy + r * 0.2), (hx + r * 1.0, cy + r * 0.9)))
        s.s(hatch(lambda xx: (cy - r * 1.1, cy - r * 0.55), hx - r * 0.9, hx + r * 0.9, 11), DEEP, 5, 1)
    elif hair == "wavy":
        s.s(arc(hx, cy - r * 0.1, r * 1.05, 190, 350))
        s.s(hatch(lambda xx: (cy - r * 1.12, cy - r * 0.6), hx - r * 0.85, hx + r * 0.85, 11), DEEP, 5, 1)
    elif hair == "bald":
        s.s(arc(hx - r * 0.95, cy + r * 0.1, r * 0.35, 120, 250), DEEP, 6)
        s.s(arc(hx + r * 0.95, cy + r * 0.1, r * 0.35, -70, 60), DEEP, 6)
        s.s(arc(hx - r * 0.25, cy - r * 0.55, r * 0.3, 200, 290), SOFT, 5, 1)
    elif hair == "curly":
        for i in range(7):
            a = math.radians(195 + i * 25)
            s.s(circle(hx + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a), r * 0.32, n=18), INK, 6, 1.6)
        s.s(hatch_circle(hx, cy - r * 0.95, r * 0.6, 10), DEEP, 5, 1)
    ex, ey = hx + look * r * 0.2, cy + r * 0.05
    if glasses == "round":
        for sx in (-1, 1):
            s.s(circle(ex + sx * r * 0.38, ey, r * 0.24, n=20), INK, 5, 1)
        s.s(poly((ex - r * 0.14, ey), (ex + r * 0.14, ey)), INK, 5, 1)
    elif glasses == "aviator":
        for sx in (-1, 1):
            cx_ = ex + sx * r * 0.38
            s.s(poly((cx_ - r * 0.26, ey - r * 0.16), (cx_ + r * 0.26, ey - r * 0.16), (cx_ + r * 0.22, ey + r * 0.12),
                     (cx_, ey + r * 0.26), (cx_ - r * 0.22, ey + r * 0.12), (cx_ - r * 0.26, ey - r * 0.16)), INK, 5, 1)
        s.s(poly((ex - r * 0.12, ey - r * 0.12), (ex + r * 0.12, ey - r * 0.12)), INK, 5, 1)
    for sx in (-1, 1):
        s.s(poly((ex + sx * r * 0.38 - 3, ey + 2), (ex + sx * r * 0.38 + 3, ey + 2)), INK, 9, 0.6)
    if mood == "awkward":
        s.s(poly((ex - r * 0.55, ey - r * 0.45), (ex - r * 0.2, ey - r * 0.5)), INK, 5, 1)
        s.s(poly((ex + r * 0.2, ey - r * 0.5), (ex + r * 0.55, ey - r * 0.45)), INK, 5, 1)
    if beard:
        b = np.vstack([arc(hx, cy + r * 0.2, r * 0.98, 10, 170, ry=r * 0.92)])
        s.s(b, INK, 6)
        s.s(hatch(lambda xx: (cy + r * 0.45, cy + r * 0.2 + r * 0.9 * math.sqrt(max(0, 1 - ((xx - hx) / r) ** 2))),
                  hx - r * 0.85, hx + r * 0.85, 10), DEEP, 5, 1)
    if mood == "big":
        s.s(np.vstack([arc(ex, cy + r * 0.42, r * 0.35, 10, 170, ry=r * 0.25), poly((ex - r * 0.34, cy + r * 0.46))]), INK, 5)
    elif mood == "awkward":
        s.s(poly((ex - r * 0.2, cy + r * 0.55), (ex + r * 0.2, cy + r * 0.52)), INK, 5, 1)
    else:
        s.s(arc(ex, cy + r * 0.3, r * 0.3, 30, 150), INK, 5, 1)
    if bindi:
        s.s(circle(ex, cy - r * 0.35, 3.5, n=10), RED, 8, 0.4)
    # body
    sw = 0.14 * h
    s.s(poly((x - 6, cy + r), (x - 6, sh_y)))
    if outfit == "suit":
        body = poly((x - sw * 0.8, sh_y), (x + sw * 0.8, sh_y), (x + sw * 1.75, hem), (x - sw * 1.75, hem),
                    (x - sw * 0.8, sh_y))
    else:
        body = poly((x - sw, sh_y), (x + sw, sh_y), (x + sw * 1.3, hem), (x - sw * 1.3, hem), (x - sw, sh_y))
    s.s(body)
    if outfit == "suit":
        s.s(poly((x - sw * 0.9, sh_y + 4), (x + sw * 1.2, hem - 30)), DEEP, 9, 1.6)        # dupatta
    else:
        s.s(poly((x, sh_y + 6), (x, sh_y + 0.14 * h)), INK, 4, 1)
    wid = 1.75 if outfit == "suit" else 1.3
    s.s(hatch(lambda xx: (sh_y + 16 + max(0, abs(xx - x) - sw * 0.8) * (hem - sh_y) / (sw * (wid - 0.8) + 1e-6) * 0.9,
                          hem - 10), x - sw * wid + 14, x + sw * wid - 14, 18), LILAC, 6, 1.4)
    s.s(poly((x - sw * 0.45, hem), (x - sw * 0.5, fy)))
    s.s(poly((x + sw * 0.45, hem), (x + sw * 0.5, fy)))
    arms = arms or {}
    for side in (-1, 1):
        pts = arms.get(side) or [(x + side * sw * 1.3, sh_y + 0.18 * h), (x + side * sw * 1.35, sh_y + 0.32 * h)]
        s.s(np.vstack([[(x + side * sw, sh_y + 4)], pts]))
    return dict(cy=cy, r=r, sh_y=sh_y, hem=hem)


def diya(s, x, y, sz=1.0, rays=True):
    s.s(np.vstack([arc(x, y, 60 * sz, 0, 180, ry=34 * sz), poly((x - 60 * sz, y), (x + 60 * sz, y))]), INK, 7)
    s.s(hatch(lambda xx: (y + 4, y + 28 * sz * math.sqrt(max(0, 1 - ((xx - x) / (60 * sz)) ** 2))),
              x - 52 * sz, x + 52 * sz, 14), WARM, 6, 1.2)
    s.s(np.vstack([poly((x, y - 6)), arc(x, y - 38 * sz, 14 * sz, 90, 200, ry=32 * sz)[::-1],
                   poly((x, y - 80 * sz)), arc(x, y - 38 * sz, 14 * sz, -20, 90, ry=32 * sz)[::-1]]), WARM, 6)
    if rays:
        for a in range(200, 341, 35):
            aa = math.radians(a)
            s.s(line(x + 70 * sz * math.cos(aa), y - 45 * sz + 70 * sz * math.sin(aa),
                     x + 105 * sz * math.cos(aa), y - 45 * sz + 105 * sz * math.sin(aa), 5), DEEP, 5, 1)


def bulbs(s, path, every=70):
    s.s(path, INK, 5)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    for i, dist in enumerate(np.arange(30, d[-1], every)):
        k = np.searchsorted(d, dist)
        x, y = path[min(k, len(path) - 1)]
        s.s(circle(x, y + 16, 11, n=16), INK, 5, 1)
        s.s(hatch_circle(x, y + 16, 9, 6), WARM if i % 2 else LILAC, 4, 0.6)


def phone(s, x0, y0, x1, y1):
    s.s(rect(x0, y0, x1, y1), INK, 8)
    s.s(poly((x0 + (x1 - x0) * 0.38, y0 + 26), (x0 + (x1 - x0) * 0.62, y0 + 26)), INK, 6, 1)


# ---------------------------------------------------------------- story
def build_scenes():
    sc = []

    s = Scene("Lilac Tinted Chapters. Chapter two: Diwali, from far away.", header=False,
              draw_frac=0.8, draw_max=3.6)
    diya(s, 540, 1110, 1.3)
    s.t("Diwali,", 540, 520, 180, INK, -4, True)
    s.t("from far away", 540, 720, 140, INK, -2, True)
    s.s(wavy(250, 830, 820, 9, 2), DEEP, 7)
    s.t("chapter two", 540, 930, 80, DEEP, 0)
    sc.append(s)

    # 1 kitchen -----------------------------------------------------------
    s = Scene("A week before Diwali, my mumma turns our kitchen into a sweet shop. Laddoos, shakkarpare, "
              "and one very strict rule: not until the bhog.", draw_max=4.6)
    s.say = ("A week before Diwali, my mumma turns our kitchen into a sweet shop. Ladoos, shukker-paaray, "
             "and one very strict rule. Not until the bhog.")
    person(s, 330, 1080, 560, "wavy", bindi=True, outfit="suit",
           arms={1: [(470, 830), (560, 790)], -1: [(240, 820), (230, 900)]})
    s.s(rect(90, 940, 990, 1110), INK, 7)
    s.s(hatch_rect(100, 950, 980, 1100, 34), SOFT, 5, 1)
    s.s(np.vstack([arc(640, 900, 130, 0, 180, ry=60), poly((510, 900), (770, 900))]), INK, 8)   # kadhai
    s.s(arc(495, 905, 22, 90, 270), INK, 6).s(arc(785, 905, 22, -90, 90), INK, 6)
    s.s(poly((560, 790), (620, 880)), INK, 7)                                                  # ladle
    for x in (590, 640, 690):
        s.s(np.vstack([poly((x, 840)), arc(x + 10, 810, 10, 90, 270), arc(x - 5, 780, 10, -90, 90)]), DEEP, 4, 1)
    for i, (x, y) in enumerate([(850, 900), (900, 900), (950, 900), (875, 858), (925, 858), (900, 816)]):
        s.s(circle(x, y, 24, n=24), INK, 5, 1.2)
        s.s(hatch_circle(x, y, 20, 8), WARM, 4, 0.8)
    s.s(circle(900, 935, 95, 16, n=40), INK, 6)
    s.s(rect(600, 420, 920, 590, ang=-5), INK, 6)
    s.t("not until", 760, 480, 70, RED, -5, True)
    s.t("the bhog!", 760, 550, 70, RED, -5, True)
    sparkle(s, 960, 760, 20)
    sc.append(s)

    # 2 lights ------------------------------------------------------------
    s = Scene("Then the whole house gets wrapped in lights. Every year, the same tangled string. "
              "Every year, someone promises to buy a new one.", draw_max=4.4)
    s.s(rect(220, 640, 860, 1120))
    s.s(poly((180, 650), (540, 380), (900, 650)))
    s.s(rect(470, 880, 610, 1120))
    s.s(circle(590, 1010, 8, n=12), INK, 6, 1)
    for (x0, y0) in [(280, 720), (680, 720)]:
        s.s(rect(x0, y0, x0 + 120, y0 + 110))
        s.s(hatch_rect(x0 + 8, y0 + 8, x0 + 112, y0 + 102, 18), WARM, 6, 1.4)
    bulbs(s, np.array([(190, 660), (360, 530), (540, 400), (720, 530), (890, 660)], float), 60)
    bulbs(s, np.array([(220, 860), (380, 890), (540, 870), (700, 890), (860, 860)], float), 64)
    for i in range(3):
        s.s(circle(150 + i * 12, 1150 - i * 8, 40 - i * 8, n=28), INK, 5, 1.6)
    s.s(poly((130, 1160), (180, 1120), (110, 1110), (170, 1180), (150, 1105)), INK, 5, 1.6)
    s.t("?!", 210, 1040, 70, DEEP, 10, True)
    sc.append(s)

    # 3 mumma + tall little brother ----------------------------------------
    s = Scene("On Diwali evening, mumma gets everyone dressed. Including my little brother, "
              "who is younger than me, but somehow, a whole head taller.", draw_max=4.6)
    person(s, 690, 1130, 820, "curly", glasses="aviator", beard=True, mood="awkward",
           arms={1: [(800, 520), (760, 400)], -1: [(590, 520), (585, 650)]})
    person(s, 400, 1130, 560, "wavy", bindi=True, outfit="suit", look=1,
           arms={1: [(520, 670), (640, 440)], -1: [(320, 700), (560, 600), (680, 450)]})
    s.s(poly((900, 1130), (900, 330)), DEEP, 5)
    s.s(poly((880, 360), (900, 330), (920, 360)), DEEP, 5)
    s.t("younger??", 880, 300, 50, DEEP, 0, True)
    for i in range(4):
        s.s(poly((920, 1120 - i * 200), (945, 1120 - i * 200)), DEEP, 4, 1)
    s.s(np.vstack([poly((780, 360)), arc(790, 345, 12, 180, 360), poly((802, 360), (790, 380), (780, 360))]),
        SOFT, 4, 1)
    sc.append(s)

    # 4 papa's pooja mission ------------------------------------------------
    s = Scene("Papa runs the pooja like a mission. Thaali, diyas, flowers, sweets. "
              "Everything on time. Everything perfect.", draw_max=4.4)
    person(s, 330, 1130, 620, "bald", glasses="round", mood="big",
           arms={1: [(420, 760), (470, 800)], -1: [(240, 760), (240, 800)]})
    s.s(circle(360, 810, 160, 34, n=50), INK, 7)
    s.s(circle(360, 810, 130, 24, n=40), DEEP, 4, 1)
    diya(s, 300, 800, 0.45, rays=False)
    for (x, y) in [(400, 795), (425, 805), (380, 812), (410, 820)]:
        s.s(circle(x, y, 10, n=12), WARM, 5, 1)
    s.s(circle(450, 808, 8, n=10), RED, 7, 0.6)
    s.s(rect(610, 430, 980, 900, ang=3), INK, 7)
    for i, word in enumerate(["thaali", "diyas", "flowers", "sweets", "on time"]):
        y = 520 + i * 80
        s.t(word, 820, y, 64, INK, 3, False)
        s.s(rect(650, y - 22, 690, y + 18), INK, 5, 1)
        s.s(poly((654, y - 2), (668, y + 14), (700, y - 34)), RED, 7, 1)
    sc.append(s)

    # 5 chole bhature ----------------------------------------------------
    s = Scene("And after the pooja? Chole bhature. In our house, that's the real prasad.", draw_max=3.8)
    s.say = "And after the pooja? Cho-lay bha-too-ray. In our house, that's the real pra-saad."
    s.s(circle(540, 900, 400, 130, n=70), INK, 8)
    s.s(circle(540, 900, 340, 100, n=60), DEEP, 4, 1.4)
    for (x, y, rx, ry) in [(400, 840, 170, 110), (590, 800, 150, 100)]:
        s.s(circle(x, y, rx, ry, n=50), INK, 7)
        s.s(hatch(lambda xx, x=x, y=y, rx=rx, ry=ry:
                  (y - ry * 0.8 * math.sqrt(max(0, 1 - ((xx - x) / rx) ** 2)) + 10,
                   y + ry * 0.8 * math.sqrt(max(0, 1 - ((xx - x) / rx) ** 2)) - 10), x - rx + 20, x + rx - 20, 26),
            WARM, 6, 1.4)
    s.s(circle(720, 960, 110, 60, n=40), INK, 7)
    s.s(hatch_circle(720, 960, 55, 10), (150, 80, 60, 210), 5, 1)
    for i in range(10):
        s.s(circle(670 + (i % 5) * 25, 945 + (i // 5) * 25, 10, n=12), (230, 180, 120, 230), 5, 0.8)
    for (x, y) in [(300, 990), (360, 1010)]:
        s.s(circle(x, y, 30, 18, n=24), (210, 110, 170, 230), 5, 1)
    s.s(np.vstack([poly((820, 870)), arc(880, 840, 60, 160, 250)]), (70, 150, 80, 230), 9)
    for x in (460, 540, 620):
        s.s(np.vstack([poly((x, 700)), arc(x + 12, 660, 12, 90, 270), arc(x - 6, 620, 12, -90, 90)]), DEEP, 4, 1)
    s.t("the real prasad", 540, 1180, 70, DEEP, -3, True)
    sc.append(s)

    # 6 this year, far away ------------------------------------------------
    s = Scene("This year, I'm not there. I'm watching it all through a phone screen.", draw_max=3.6)
    s.s(rect(180, 360, 900, 1000))
    s.s(poly((540, 360), (540, 1000))).s(poly((180, 680), (900, 680)))
    s.s(hatch_rect(190, 370, 890, 990, 40), SOFT, 5, 1)
    for (x, y) in [(260, 450), (420, 520), (700, 430), (820, 560), (330, 820), (760, 800)]:
        sparkle(s, x, y, 14, DEEP)
    s.s(rect(140, 1000, 940, 1040))
    diya(s, 790, 990, 0.6, rays=True)
    person(s, 420, 1230, 470, "bob", look=0.5,
           arms={1: [(500, 980), (470, 920)], -1: [(340, 1020), (340, 1080)]})
    phone(s, 450, 870, 500, 950)
    for i in range(3):
        s.s(arc(475, 910, 50 + i * 20, -60, 0), WARM, 5, 1)
    sc.append(s)

    # 7 this one's yours ----------------------------------------------------
    s = Scene("On the video call, mumma held the first bhatura up to the camera and said: this one's yours.",
              draw_max=4.2)
    s.say = "On the video call, mumma held the first bha-too-ra up to the camera, and said: this one's yours."
    phone(s, 230, 300, 850, 1230)
    person(s, 500, 1300, 760, "wavy", bindi=True, outfit="suit", mood="big",
           arms={1: [(640, 780), (680, 640)], -1: [(400, 800), (400, 900)]})
    s.s(circle(700, 560, 120, 80, n=50), INK, 7)
    s.s(hatch(lambda xx: (500, 620), 600, 800, 26), WARM, 6, 1.4)
    s.s(poly((300, 410), (360, 430)), DEEP, 5, 1)
    s.s(rect(560, 330, 830, 430, ang=-3), INK, 5)
    s.t("tera wala!", 695, 380, 58, RED, -3, True)
    sc.append(s)

    # 8 ending -------------------------------------------------------------
    s = Scene("Diwali from far away feels a little smaller. But home always finds a way to reach you.",
              draw_max=3.6)
    diya(s, 540, 930, 1.7)
    for (x, y) in [(250, 520), (830, 500), (180, 900), (900, 880), (540, 420)]:
        sparkle(s, x, y, 22)
    s.s(arc(540, 1010, 300, 20, 160, ry=40), DEEP, 5)
    sc.append(s)

    # 9 end card -----------------------------------------------------------
    s = Scene("Happy Diwali. To everyone far from home.", header=False, draw_frac=0.7, draw_max=2.6)
    lilac_sprig(s, 300, 760, 0.9)
    diya(s, 700, 720, 0.9)
    s.t("happy diwali", 540, 920, 140, INK, -3, True)
    s.t("to everyone far from home", 540, 1060, 72, DEEP, 0)
    s.s(arc(540, 1100, 260, 20, 160, ry=20), DEEP, 5)
    sc.append(s)
    return sc


m.build_scenes = build_scenes

if __name__ == "__main__":
    m.main()
