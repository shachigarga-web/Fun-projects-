"""
Style test: one scene in a looser hand-drawn look.
Fills sit slightly off the line art, fills have a dry-brush texture,
outlines are thin, tapered, broken strokes, and the line art "boils" gently.

Scene: Diwali evening. Mumma fixes the collar of her (very tall) younger son,
Papa gets the pooja thaali ready behind them.

  python style_test.py --still out.png
  python style_test.py --clip out.mp4      # 6s with text write-on, glow flicker
"""
import argparse, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "ShadowsIntoLightTwo-Regular.ttf")
W, H, SS, FPS = 1080, 1920, 2, 24

INK = (40, 24, 62)
HAIR = (34, 22, 50)
GREYHAIR = (78, 70, 92)
SKIN = (214, 160, 124)
SKIN_SH = (190, 132, 100)
CHEEK = (226, 128, 120)
KURTA_W, KURTA_W_SH = (240, 236, 246), (204, 196, 230)
RUST, RUST_SH, RUST_LT = (192, 90, 50), (158, 68, 42), (214, 116, 70)
CREAM = (240, 226, 204)
TEAL, TEAL_SH = (40, 136, 146), (28, 106, 118)
PYJAMA = (232, 228, 240)
STEEL = (206, 208, 222)
WARM = (255, 204, 110)

rng = np.random.default_rng(21)


def P(*p):
    return np.array(p, float)


def curve(*pts, n=24, closed=False):
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


def ell(cx, cy, rx, ry, rot=0, a0=0, a1=360, n=48):
    a = np.radians(np.linspace(a0, a1, n))
    pts = np.stack([rx * np.cos(a), ry * np.sin(a)], 1)
    r = math.radians(rot)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return pts @ R.T + [cx, cy]


def resample(pts, step=5.0):
    pts = np.asarray(pts, float)
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    c = np.concatenate([[0], np.cumsum(d)])
    if c[-1] < 1e-6:
        return pts[:1].repeat(2, 0)
    s = np.append(np.arange(0, c[-1], step), c[-1])
    return np.stack([np.interp(s, c, pts[:, 0]), np.interp(s, c, pts[:, 1])], 1)


# ------------------------------------------------------------------ items
ITEMS = []


def paint(pts, col, line=True, lw=3.6, off=(-5, 5), dry=True, gaps=True):
    """Painted fill shifted off its line art, plus a broken sketchy outline."""
    pts = np.asarray(pts, float)
    ITEMS.append(dict(k="fill", pts=pts + off + rng.normal(0, 1.4, pts.shape), col=col, dry=dry))
    if line:
        ITEMS.append(dict(k="line", pts=resample(np.vstack([pts, pts[:1]])), w=lw, closed=True, gaps=gaps))


def shade(pts, col):
    ITEMS.append(dict(k="fill", pts=np.asarray(pts, float), col=col, dry=True))


def line(pts, w=3.6, col=INK, gaps=False):
    ITEMS.append(dict(k="line", pts=resample(pts), w=w, col=col, closed=False, gaps=gaps))


def limb(pts, w, col, sh=None):
    path = resample(curve(*pts, n=16))
    ITEMS.append(dict(k="limb", pts=path, w=w, col=col, sh=sh))


def glow(x, y, r, col=WARM, s=0.8, fl=0.2):
    ITEMS.append(dict(k="glow", x=x, y=y, r=r, col=col, s=s, fl=fl, ph=rng.uniform(0, 6)))


def dots(cx, cy, n, spread, col, r=5):
    for _ in range(n):
        x, y = cx + rng.normal(0, spread[0]), cy + rng.normal(0, spread[1])
        ITEMS.append(dict(k="fill", pts=ell(x, y, r, r * 0.8, n=10), col=col, dry=False))


# ------------------------------------------------------------------ scene
def build():
    # back wall details ---------------------------------------------------
    shade(P((0, 1590), (1080, 1560), (1080, 1920), (0, 1920)), (122, 112, 204))
    for x in range(40, 1080, 140):                                    # floor tiles, faint
        line(P((x, 1575), (x - 60, 1920)), 2.2, (108, 98, 190))
    # mandir shelf at back-left
    paint(P((24, 1080), (190, 1080), (190, 1340), (24, 1340)), (150, 96, 92))
    paint(curve((20, 1085), (60, 1010), (107, 985), (154, 1010), (194, 1085), n=10), (176, 112, 100))
    paint(ell(107, 1290, 30, 12), (200, 110, 60), lw=3)
    paint(curve((105, 1285), (98, 1262), (106, 1240), (114, 1262), (107, 1285), n=6), (255, 170, 60), lw=2)
    glow(107, 1255, 150, WARM, 0.7, 0.25)
    # string lights + marigold toran
    path = curve((-10, 640), (270, 700), (540, 660), (810, 705), (1090, 645), n=30)
    line(path, 3, INK)
    cols = [(255, 214, 96), (255, 128, 150), (150, 220, 255), (255, 176, 80)]
    pr = resample(path, 54)
    for i, (x, y) in enumerate(pr[1:-1]):
        c = cols[i % 4]
        paint(ell(x, y + 12, 8, 11, n=12), c, lw=2.4, off=(-2, 2), dry=False)
        glow(x, y + 12, 50, c, 0.5, 0.45)
    tor = curve((-10, 590), (300, 625), (540, 600), (800, 628), (1090, 590), n=30)
    for i, (x, y) in enumerate(resample(tor, 24)):
        paint(ell(x, y, 13, 12, n=14), (255, 150, 40) if i % 2 else (255, 200, 60), lw=2.4, off=(-2, 2))
    # rangoli
    for r, c in [(300, (240, 110, 150)), (215, (255, 196, 70)), (130, (120, 200, 210)), (55, (250, 246, 255))]:
        paint(ell(540, 1800, r, r * 0.22, n=60), c, lw=2.6, off=(-3, 3))

    # ----------------------------------------------------- PAPA (back left)
    px = 228
    limb([(196, 1430), (194, 1540), (196, 1640)], 44, PYJAMA)
    limb([(258, 1430), (262, 1540), (262, 1640)], 44, PYJAMA)
    paint(ell(190, 1652, 26, 11), (110, 60, 50), lw=3)
    paint(ell(268, 1652, 26, 11), (110, 60, 50), lw=3)
    paint(curve((168, 1112), (152, 1220), (150, 1330), (156, 1440), (300, 1440), (306, 1330),
                (300, 1220), (286, 1112), (228, 1098), n=10, closed=True), TEAL)
    shade(curve((160, 1300), (230, 1330), (300, 1300), (302, 1436), (158, 1436), n=8, closed=True), TEAL_SH)
    line(P((228, 1110), (228, 1200)), 2.6)
    paint(P((246, 1168), (284, 1168), (284, 1200), (246, 1200)), TEAL_SH, lw=2.6, off=(-2, 2))
    paint(P((254, 1140), (276, 1140), (276, 1172), (254, 1172)), (40, 32, 52), lw=2.6, off=(-1, 1))   # phone in pocket
    limb([(170, 1128), (160, 1210), (188, 1262)], 30, TEAL, TEAL_SH)
    limb([(286, 1128), (298, 1210), (270, 1262)], 30, TEAL, TEAL_SH)
    paint(ell(228, 1268, 84, 22), STEEL, lw=3.2)
    line(ell(228, 1266, 66, 15, a0=200, a1=340, n=14), 2, (150, 150, 172))
    paint(ell(205, 1258, 20, 8), (200, 110, 60), lw=2.4)
    paint(curve((205, 1255), (199, 1236), (205, 1220), (212, 1236), (206, 1255), n=6), (255, 170, 60), lw=2)
    glow(205, 1235, 130, WARM, 0.75, 0.3)
    dots(250, 1258, 9, (14, 4), (255, 160, 40), 6)
    paint(ell(272, 1262, 9, 5), (210, 40, 60), lw=2)
    paint(ell(184, 1266, 15, 11), SKIN, lw=2.6)
    paint(ell(272, 1268, 15, 11), SKIN, lw=2.6)
    limb([(228, 1080), (228, 1108)], 30, SKIN)
    paint(ell(px, 1040, 47, 54), SKIN)                                   # bald head
    shade(ell(px - 6, 1006, 22, 12, rot=-10), (234, 188, 156))           # shine
    paint(curve((184, 1012), (180, 1046), (190, 1080), (204, 1086), (196, 1050), (196, 1016), n=6, closed=True), GREYHAIR, lw=2.2, off=(-2, 2))
    paint(curve((272, 1012), (276, 1046), (266, 1080), (252, 1086), (260, 1050), (260, 1016), n=6, closed=True), GREYHAIR, lw=2.2, off=(-2, 2))
    paint(ell(181, 1052, 7, 12), SKIN, lw=2.2, off=(-1, 1))
    paint(ell(275, 1052, 7, 12), SKIN, lw=2.2, off=(-1, 1))
    for x in (210, 247):
        line(np.vstack([ell(x, 1040, 15, 11, n=20)]), 2.8)
        ITEMS.append(dict(k="fill", pts=ell(x, 1041, 3.5, 4, n=8), col=INK, dry=False))
    line(P((225, 1040), (232, 1040)), 2.6)
    line(P((207, 1024), (221, 1022)), 3, GREYHAIR)
    line(P((236, 1022), (251, 1024)), 3, GREYHAIR)
    line(curve((228, 1044), (224, 1058), (230, 1062), n=6), 2.4, SKIN_SH)
    paint(curve((204, 1070), (228, 1084), (252, 1070), (228, 1076), n=8, closed=True), (252, 248, 246), lw=2.6, off=(-1, 1))
    shade(ell(197, 1066, 9, 5), CHEEK + (120,))
    shade(ell(259, 1066, 9, 5), CHEEK + (120,))

    # ----------------------------------------------------- MUMMA (middle)
    mx = 450
    paint(curve((400, 930), (378, 980), (372, 1040), (392, 1078), (420, 1060), (480, 1060),
                (508, 1078), (520, 1030), (506, 970), (480, 925), n=10, closed=True), HAIR)      # hair back
    paint(curve((388, 1060), (350, 1200), (338, 1340), (352, 1440), (402, 1430), (400, 1300),
                (420, 1150), (420, 1070), n=10, closed=True), RUST_LT)                           # dupatta behind
    dots(372, 1250, 10, (16, 80), CREAM, 4)
    limb([(424, 1480), (422, 1600), (424, 1708)], 42, CREAM)
    limb([(484, 1480), (488, 1600), (492, 1708)], 42, CREAM)
    paint(ell(418, 1716, 24, 10), (214, 168, 70), lw=3)
    paint(ell(498, 1716, 24, 10), (214, 168, 70), lw=3)
    paint(curve((404, 1045), (388, 1150), (374, 1300), (366, 1486), (540, 1486), (526, 1300),
                (512, 1150), (500, 1045), (452, 1036), n=10, closed=True), RUST)
    shade(curve((372, 1360), (450, 1390), (534, 1360), (538, 1480), (368, 1480), n=8, closed=True), RUST_SH)
    for x in np.linspace(380, 528, 10):
        ITEMS.append(dict(k="fill", pts=ell(x, 1462, 5, 5, n=10), col=CREAM, dry=False))
    paint(curve((432, 1044), (452, 1110), (474, 1044), (464, 1046), (452, 1086), (442, 1046), n=6, closed=True),
          CREAM, lw=2.6, off=(-2, 2))
    paint(curve((470, 1046), (500, 1046), (508, 1120), (470, 1300), (432, 1430), (420, 1300), (452, 1140), n=10,
                closed=True), RUST_LT)                                                          # dupatta front drape
    dots(470, 1200, 9, (12, 60), CREAM, 4)
    limb([(492, 1070), (560, 1040)], 34, RUST, RUST_SH)                 # right arm (near brother)
    limb([(412, 1080), (500, 1092)], 34, RUST, RUST_SH)                 # left arm across body
    paint(ell(452, 1028, 14, 18), SKIN, lw=2.4, off=(-1, 1))            # neck
    paint(ell(mx, 972, 45, 53, rot=12), SKIN)
    paint(curve((404, 955), (412, 918), (448, 905), (486, 916), (500, 952), (474, 935), (440, 940),
                (416, 962), n=8, closed=True), HAIR, lw=3)                                         # front hair
    paint(curve((404, 950), (392, 1000), (398, 1040), (412, 1012), (414, 966), n=6, closed=True), HAIR, lw=2.6)
    line(curve((470, 920), (488, 940), (494, 980)), 2.4, (70, 54, 90))
    for x, y in [(444, 970), (476, 964)]:
        ITEMS.append(dict(k="fill", pts=ell(x, y, 4.5, 6, n=10), col=INK, dry=False))
    line(P((434, 952), (452, 948)), 3, HAIR)
    line(P((468, 944), (486, 944)), 3, HAIR)
    ITEMS.append(dict(k="fill", pts=ell(462, 946, 4.5, 4.5, n=10), col=(214, 30, 50), dry=False))   # bindi
    line(curve((460, 976), (456, 990), (463, 994), n=6), 2.4, SKIN_SH)
    line(curve((448, 1006), (462, 1014), (476, 1004), n=6), 3)
    shade(ell(434, 996, 9, 5), CHEEK + (120,))
    shade(ell(486, 990, 9, 5), CHEEK + (120,))
    paint(ell(410, 996, 4, 4), (240, 196, 80), lw=1.6, off=(0, 0))       # earring

    # ----------------------------------------------------- BROTHER (tall, right)
    limb([(628, 1400), (624, 1560), (622, 1700)], 54, PYJAMA)
    limb([(732, 1400), (738, 1560), (736, 1700)], 54, PYJAMA)
    paint(ell(612, 1712, 30, 12), (96, 54, 62), lw=3)
    paint(ell(748, 1712, 30, 12), (96, 54, 62), lw=3)
    paint(curve((604, 880), (586, 960), (580, 1100), (576, 1260), (578, 1404), (680, 1410), (782, 1404),
                (780, 1260), (774, 1100), (768, 960), (750, 880), (677, 866), n=8, closed=True), KURTA_W)
    shade(curve((574, 1240), (680, 1270), (788, 1240), (786, 1410), (576, 1410), n=8, closed=True), KURTA_W_SH)
    shade(curve((600, 900), (590, 1060), (610, 1060), (616, 920), n=6, closed=True), KURTA_W_SH)
    line(P((676, 892), (676, 1020)), 2.4)
    for y in (920, 955, 990):
        ITEMS.append(dict(k="fill", pts=ell(676, y, 3.5, 3.5, n=8), col=INK, dry=False))
    limb([(600, 900), (580, 1060), (590, 1220)], 40, KURTA_W, KURTA_W_SH)
    paint(ell(592, 1234, 17, 21), SKIN, lw=2.6)
    limb([(752, 902), (808, 830), (744, 742)], 40, KURTA_W, KURTA_W_SH)     # hand behind head, awkward
    paint(ell(736, 738, 20, 17), SKIN, lw=2.6)
    paint(P((646, 856), (708, 856), (712, 890), (642, 890)), KURTA_W, lw=3, off=(-2, 2))   # collar
    limb([(560, 1040), (600, 960), (630, 896)], 26, SKIN)                  # mumma's forearms + hands
    limb([(500, 1092), (590, 1000), (668, 900)], 26, SKIN)
    paint(curve((616, 880), (640, 872), (650, 890), (632, 904), (616, 898), n=6, closed=True), SKIN, lw=2.6)
    paint(curve((656, 884), (684, 876), (694, 894), (674, 908), (656, 902), n=6, closed=True), SKIN, lw=2.6)
    paint(ell(676, 850, 22, 16), SKIN, lw=2.4, off=(-1, 1))                 # neck
    paint(ell(672, 774, 50, 62, rot=-8), SKIN)
    paint(ell(722, 784, 9, 14), SKIN, lw=2.4, off=(-1, 1))
    paint(curve((622, 790), (612, 730), (630, 690), (672, 672), (716, 684), (736, 724), (730, 782),
                (716, 742), (690, 728), (654, 734), (630, 760), n=8, closed=True), HAIR)     # big hair
    line(curve((640, 704), (668, 690), (700, 698)), 2.2, (70, 52, 92))
    paint(curve((622, 776), (626, 826), (648, 854), (676, 862), (704, 850), (722, 816), (722, 776),
                (706, 810), (676, 818), (644, 808), n=8, closed=True), HAIR, lw=3)            # beard
    line(curve((660, 826), (674, 830), (688, 826), n=6), 3, (150, 96, 92))
    for x in (650, 692):                                                     # aviator glasses
        line(curve((x - 20, 768), (x + 18, 766), (x + 16, 784), (x, 794), (x - 16, 788), (x - 20, 768), n=6), 2.8)
        ITEMS.append(dict(k="fill", pts=ell(x - 2, 778, 4, 5.5, n=10), col=INK, dry=False))
    line(P((668, 770), (674, 770)), 2.4)
    line(P((634, 752), (656, 748)), 3.2, HAIR)                               # raised awkward brows
    line(P((684, 746), (706, 752)), 3.2, HAIR)
    line(curve((672, 782), (668, 800), (676, 804), n=6), 2.4, SKIN_SH)
    paint(curve((748, 700), (742, 716), (748, 724), (754, 716), n=6, closed=True), (200, 230, 255), lw=2, off=(0, 0))


# ------------------------------------------------------------------ rendering
_tex = None


def texture():
    global _tex
    if _tex is None:
        n = rng.random((H * SS // 4, W * SS // 4)).astype(np.float32)
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((W * SS, H * SS), Image.BILINEAR)
        im = im.filter(ImageFilter.BoxBlur(3)).resize((W * SS // 8, H * SS)).resize((W * SS, H * SS), Image.BILINEAR)
        a = np.asarray(im, np.float32) / 255
        a = (a - a.mean()) / (a.std() + 1e-6)
        _tex = np.clip(0.93 + 0.09 * a, 0.74, 1.0)
    return _tex


def background():
    w, h = W // 4, H // 4
    t = np.linspace(0, 1, h)[:, None, None]
    g = np.array((100, 106, 212), float) * (1 - t) + np.array((156, 146, 228), float) * t
    img = Image.fromarray(np.broadcast_to(g, (h, w, 3)).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x, y, rx, ry, c in [(220, 260, 160, 220, (130, 132, 226)), (60, 140, 120, 90, (150, 120, 210)),
                            (240, 420, 130, 60, (176, 150, 230))]:
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=c + (130,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(26)))
    return img.convert("RGB").resize((W * SS, H * SS), Image.BICUBIC)


def brush(pts, w, seed, taper=0.35):
    n = len(pts)
    tg = np.gradient(pts, axis=0)
    nm = np.stack([-tg[:, 1], tg[:, 0]], 1) / (np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9)
    t = np.linspace(0, 1, n)
    r = np.random.default_rng(seed)
    prof = 0.25 + 0.75 * np.clip(np.minimum(t, 1 - t) / taper, 0, 1) ** 0.8 if taper else np.ones(n)
    prof = prof * (1 + 0.2 * np.sin(2 * np.pi * t * r.uniform(1, 2.5) + r.uniform(0, 6)))
    hw = (w * prof / 2)[:, None]
    return np.vstack([pts + nm * hw, (pts - nm * hw)[::-1]])


def wob(pts, seed, amp):
    r = np.random.default_rng(seed)
    n = len(pts)
    t = np.linspace(0, 1, n)
    off = np.zeros((n, 2))
    for k in (1, 2):
        fr = r.uniform(0.6, 1.4) * k * (n / 160 + 0.5)
        off[:, 0] += amp / k * np.sin(2 * np.pi * fr * t + r.uniform(0, 6))
        off[:, 1] += amp / k * np.sin(2 * np.pi * fr * t + r.uniform(0, 6))
    return pts + off


def segments(pts, seed, gaps):
    """Split an outline into strokes with small gaps, like a quick hand sketch."""
    if not gaps or len(pts) < 30:
        return [pts]
    r = np.random.default_rng(seed)
    out, i = [], 0
    while i < len(pts) - 3:
        ln = int(r.uniform(18, 55))
        out.append(pts[i:i + ln + 2])
        i += ln + int(r.uniform(1, 4))
    return out


_fill_cache = {}


def draw_fill(img, it, idx):
    if idx not in _fill_cache:
        pts = it["pts"] * SS
        x0, y0 = np.floor(pts.min(0)).astype(int) - 4
        x1, y1 = np.ceil(pts.max(0)).astype(int) + 4
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W * SS, x1), min(H * SS, y1)
        if x1 <= x0 or y1 <= y0:
            _fill_cache[idx] = None
            return
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in pts - [x0, y0]], fill=255)
        a = np.asarray(m, np.float32) / 255
        col = it["col"]
        alpha = (col[3] / 255) if len(col) == 4 else 1.0
        if it["dry"]:
            a = a * texture()[y0:y1, x0:x1]
        spr = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        spr[..., :3] = col[:3]
        spr[..., 3] = np.clip(a * alpha * 255, 0, 255).astype(np.uint8)
        _fill_cache[idx] = (Image.fromarray(spr, "RGBA"), (x0, y0))
    c = _fill_cache[idx]
    if c:
        img.alpha_composite(c[0], c[1])


def glow_sprite(r, _c={}):
    if r not in _c:
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x ** 2 + y ** 2) / r
        _c[r] = (np.exp(-(d ** 2) * 4) * (d < 1)).astype(np.float32)
    return _c[r]


def render(boil=0, t=0.0):
    img = background().convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    glows = []
    for i, it in enumerate(ITEMS):
        seed = i * 7919 + boil * 31
        k = it["k"]
        if k == "fill":
            draw_fill(img, it, i)
        elif k == "line":
            col = it.get("col", INK)
            pts = wob(it["pts"], seed, 1.1)
            for j, seg in enumerate(segments(pts, i * 13, it["gaps"])):
                if len(seg) < 2:
                    continue
                poly = brush(seg * SS, it["w"] * SS, seed + j)
                d.polygon([tuple(p) for p in poly], fill=col + (235,))
        elif k == "limb":
            pts = wob(it["pts"], seed, 0.8)
            off = np.array([-4, 4])
            poly = brush((pts + off) * SS, it["w"] * SS, seed, taper=0)
            d.polygon([tuple(p) for p in poly], fill=it["col"])
            for q in ((pts[0] + off) * SS, (pts[-1] + off) * SS):
                rr = it["w"] * SS / 2
                d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=it["col"])
            if it["sh"]:
                poly = brush((pts + off + [5, 0]) * SS, it["w"] * 0.35 * SS, seed + 1, taper=0.3)
                d.polygon([tuple(p) for p in poly], fill=it["sh"] + (170,))
            for s in (-1, 1):
                tg = np.gradient(pts, axis=0)
                nm = np.stack([-tg[:, 1], tg[:, 0]], 1) / (np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9)
                edge = pts + s * nm * it["w"] / 2
                for j, seg in enumerate(segments(edge, i * 17 + s, True)):
                    if len(seg) > 2:
                        poly = brush(seg * SS, 3.4 * SS, seed + j * 3 + s)
                        d.polygon([tuple(p) for p in poly], fill=INK + (230,))
        elif k == "glow":
            glows.append(it)
    small = np.asarray(img.convert("RGB").resize((W, H), Image.LANCZOS), np.float32)
    for g in glows:
        r = int(g["r"])
        spr = glow_sprite(r)
        fl = 1 + g["fl"] * (0.6 * math.sin(t * 7 + g["ph"]) + 0.4 * math.sin(t * 13.3 + g["ph"] * 2))
        x0, y0 = int(g["x"]) - r, int(g["y"]) - r
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + 2 * r + 1), min(H, y0 + 2 * r + 1)
        a = spr[ya - y0:yb - y0, xa - x0:xb - x0, None] * g["s"] * fl
        reg = small[ya:yb, xa:xb]
        small[ya:yb, xa:xb] = reg + (np.array(g["col"], np.float32) - reg * 0.35) * a * 0.75
    small += np.random.default_rng(boil).normal(0, 2.5, (H, W, 1))
    return Image.fromarray(np.clip(small, 0, 255).astype(np.uint8)).convert("RGBA")


def add_text(im, text, reveal=1.0):
    f = ImageFont.truetype(HAND, 78)
    words = text.split()
    lines, cur = [], []
    for w_ in words:
        if cur and f.getlength(" ".join(cur + [w_])) > 880:
            lines.append(" ".join(cur)); cur = [w_]
        else:
            cur.append(w_)
    lines.append(" ".join(cur))
    total = sum(map(len, lines))
    n_show = int(total * reveal)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    y = 430 - (len(lines) - 1) * 48
    for ln in lines:
        k = max(0, min(len(ln), n_show))
        n_show -= len(ln)
        x = W / 2 - f.getlength(ln) / 2
        if k:
            d.text((x + 2, y + 3), ln[:k], font=f, fill=(30, 16, 50, 90), anchor="lm")
            d.text((x, y), ln[:k], font=f, fill=(250, 246, 255, 255), anchor="lm")
        y += 96
    im.alpha_composite(lay)
    return im


TEXT = "diwali ki shaam mumma sabko ready karti hai."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still")
    ap.add_argument("--clip")
    a = ap.parse_args()
    build()
    if a.still:
        add_text(render(0, 0.3), TEXT).convert("RGB").save(a.still)
        print("wrote", a.still)
    if a.clip:
        n = FPS * 6
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.clip], stdin=subprocess.PIPE)
        cache = {}
        for fi in range(n):
            t = fi / FPS
            b = fi // 4
            if b not in cache:
                cache = {b: render(b, t)}
            fr = render(b, t) if fi % 4 == 0 else cache[b].copy()
            z = 1 + 0.03 * t / 6
            cw, ch = W / z, H / z
            fr = fr.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
            fr = add_text(fr, TEXT, min(1, max(0, (t - 0.4) / 1.6)))
            ff.stdin.write(fr.convert("RGB").tobytes())
        ff.stdin.close(); ff.wait()
        print("wrote", a.clip)


if __name__ == "__main__":
    main()
