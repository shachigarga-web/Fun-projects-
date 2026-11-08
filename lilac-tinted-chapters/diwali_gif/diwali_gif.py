"""
Happy Diwali greeting: seamless looping GIF + MP4 for WhatsApp / Instagram.

Diyas with flickering flames, fireworks, marigold toran, twinkling stars,
shimmering gold text. Everything loops perfectly (all motion has period LOOP).

  python diwali_gif.py            # writes happy_diwali.gif and happy_diwali.mp4
"""
import math, os, subprocess, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "YatraOne-Regular.ttf")
SCRIPT_FONT = os.path.join(HERE, "..", "Caveat.ttf")
S = 600                      # square canvas
FPS, LOOP = 20, 4.0          # 80 frames, seamless
N = int(FPS * LOOP)
rng = np.random.default_rng(8)

GOLD = np.array([255, 196, 84], np.float32)
FLAME_OUT = np.array([255, 140, 40], np.float32)
FLAME_IN = np.array([255, 236, 170], np.float32)


def blob(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(x ** 2 + y ** 2) / (2 * (r / 3.3) ** 2)).astype(np.float32)


_blobs = {}


def add_glow(img, x, y, r, col, a):
    r = max(1, int(r))
    if r not in _blobs:
        _blobs[r] = blob(r)
    b = _blobs[r]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = x - r, y - r, x + r + 1, y + r + 1
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(S, x1), min(S, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return
    img[cy0:cy1, cx0:cx1] += b[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0, None] * col * a


def add_ellipse_glow(img, x, y, rx, ry, col, a):
    """Soft vertical ellipse (flames)."""
    xs = np.arange(int(x - rx * 3), int(x + rx * 3) + 1)
    ys = np.arange(int(y - ry * 3), int(y + ry * 3) + 1)
    xs, ys = xs[(xs >= 0) & (xs < S)], ys[(ys >= 0) & (ys < S)]
    if not len(xs) or not len(ys):
        return
    X, Y = np.meshgrid(xs, ys)
    g = np.exp(-(((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2) / 2).astype(np.float32)
    img[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] += g[..., None] * col * a


# ------------------------------------------------------------------ static layers
def background():
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    d = np.sqrt(((x - S / 2) / S) ** 2 + ((y - S * 0.42) / S) ** 2)
    inner, outer = np.array([82, 46, 132], np.float32), np.array([16, 9, 38], np.float32)
    k = np.clip(d / 0.75, 0, 1)[..., None] ** 0.9
    return inner * (1 - k) + outer * k


def static_overlay():
    """Things that don't move: toran, diya bodies, rangoli, text base (drawn at 2x)."""
    Z = 2
    lay = Image.new("RGBA", (S * Z, S * Z), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # marigold toran: three swags
    for i in range(3):
        x0, x1 = i * S / 3, (i + 1) * S / 3
        for k, t in enumerate(np.linspace(0, 1, 13)):
            px = x0 + (x1 - x0) * t
            py = 14 + 34 * math.sin(math.pi * t)
            col = (255, 150, 30) if k % 2 else (255, 205, 50)
            r = 11
            d.ellipse([(px - r) * Z, (py - r) * Z, (px + r) * Z, (py + r) * Z], fill=col)
            d.ellipse([(px - 4) * Z, (py - 5) * Z, (px + 3) * Z, (py + 2) * Z], fill=(255, 230, 140))
        for t in (0.25, 0.5, 0.75):                        # mango leaves
            px, py = x0 + (x1 - x0) * t, 14 + 34 * math.sin(math.pi * t) + 18
            d.polygon([(px * Z, (py - 6) * Z), ((px + 7) * Z, (py + 10) * Z), (px * Z, (py + 24) * Z),
                       ((px - 7) * Z, (py + 10) * Z)], fill=(70, 150, 70))
    # rangoli under the diyas
    cx, cy = S / 2, 508
    for r, col in [(225, (226, 70, 120)), (185, (255, 170, 40)), (145, (120, 200, 220)), (105, (176, 140, 226))]:
        d.ellipse([(cx - r) * Z, (cy - r * 0.2) * Z, (cx + r) * Z, (cy + r * 0.2) * Z], outline=col, width=5 * Z)
    for k in range(16):
        a = 2 * math.pi * k / 16
        px, py = cx + 205 * math.cos(a), cy + 205 * 0.2 * math.sin(a)
        d.ellipse([(px - 6) * Z, (py - 3) * Z, (px + 6) * Z, (py + 3) * Z], fill=(255, 236, 200))
    # diya bodies
    for x in DIYAS:
        y = DIYA_Y
        d.chord([(x - 34) * Z, (y - 22) * Z, (x + 34) * Z, (y + 22) * Z], 0, 180, fill=(196, 92, 52))
        d.ellipse([(x - 34) * Z, (y - 7) * Z, (x + 34) * Z, (y + 7) * Z], fill=(150, 62, 36))
        d.polygon([((x + 26) * Z, (y - 4) * Z), ((x + 46) * Z, (y - 16) * Z), ((x + 36) * Z, y * Z)],
                  fill=(196, 92, 52))
        for k in range(5):                                  # painted dots
            px = x - 20 + k * 10
            d.ellipse([(px - 2.5) * Z, (y + 9) * Z, (px + 2.5) * Z, (y + 14) * Z], fill=(255, 214, 120))
        d.line([(x - 26) * Z, (y + 4) * Z, (x + 26) * Z, (y + 4) * Z], fill=(255, 200, 90), width=2 * Z)
    lay = lay.resize((S, S), Image.LANCZOS)
    return lay


def text_masks():
    Z = 2
    out = []
    for txt, font, size, y in [("शुभ दीपावली", FONT, 46, 108), ("Happy Diwali", FONT, 78, 192)]:
        m = Image.new("L", (S * Z, S * Z), 0)
        ImageDraw.Draw(m).text((S * Z / 2, y * Z), txt, font=ImageFont.truetype(font, size * Z), fill=255, anchor="mm")
        out.append(np.asarray(m.resize((S, S), Image.LANCZOS), np.float32) / 255)
    m = Image.new("L", (S * Z, S * Z), 0)
    f = ImageFont.truetype(SCRIPT_FONT, 40 * Z)
    f.set_variation_by_name("Bold")
    ImageDraw.Draw(m).text((S * Z / 2, 588 * Z - 16 * Z), "light, love & lots of laddoos", font=f, fill=255,
                           anchor="ms")
    out.append(np.asarray(m.resize((S, S), Image.LANCZOS), np.float32) / 255)
    return out


DIYAS = [110, 205, 300, 395, 490]
DIYA_Y = 470

STARS = [(rng.uniform(0, S), rng.uniform(60, 400), rng.uniform(0.6, 1.6), rng.integers(1, 4), rng.uniform(0, 6.28))
         for _ in range(70)]

# fireworks: (x, y, colour, start time, particle count)
BURSTS = [
    (130, 300, (255, 120, 170), 0.2, 46),
    (470, 280, (255, 210, 90), 1.5, 52),
    (300, 330, (140, 220, 255), 2.7, 48),
    (520, 140 + 200, (190, 150, 255), 3.4, 40),
]
LIFE = 1.7


def frame(i, bg, overlay, masks):
    t = i / FPS
    ph = 2 * math.pi * t / LOOP
    img = bg.copy()
    # stars
    for x, y, r, k, p in STARS:
        a = 0.5 + 0.5 * math.sin(ph * k + p)
        add_glow(img, x, y, 3, np.array([255, 240, 220], np.float32), 0.6 * a * r)
    # fireworks (loop-safe: time wraps)
    for bx, by, col, st, n in BURSTS:
        tau = (t - st) % LOOP
        if tau > LIFE:
            continue
        col = np.array(col, np.float32)
        fade = (1 - tau / LIFE) ** 1.6
        R = 95 * (1 - math.exp(-tau * 3.2))
        if tau < 0.12:
            add_glow(img, bx, by, 30, col, 1.2 * (1 - tau / 0.12))
        for k in range(n):
            a = 2 * math.pi * k / n + 0.3 * math.sin(k * 7.1)
            rr = R * (0.85 + 0.15 * math.sin(k * 3.3))
            for trail, w in ((0, 1.0), (0.07, 0.45), (0.14, 0.2)):
                tt = max(0, tau - trail)
                rt = 95 * (1 - math.exp(-tt * 3.2)) * (0.85 + 0.15 * math.sin(k * 3.3))
                px = bx + rt * math.cos(a)
                py = by + rt * math.sin(a) + 28 * tt * tt
                add_glow(img, px, py, 7, col, 1.0 * fade * w)
            sparkle = 0.5 + 0.5 * math.sin(tau * 40 + k)
            add_glow(img, bx + rr * math.cos(a), by + rr * math.sin(a) + 28 * tau * tau, 2,
                     np.array([255, 255, 255], np.float32), 0.5 * fade * sparkle)
    # diya glow (behind bodies)
    for j, x in enumerate(DIYAS):
        fl = 1 + 0.12 * math.sin(ph * 3 + j * 1.7) + 0.06 * math.sin(ph * 7 + j)
        add_glow(img, x, DIYA_Y - 30, 70, GOLD, 0.35 * fl)
    # composite static overlay
    o = np.asarray(overlay, np.float32)
    a = o[..., 3:4] / 255
    img = img * (1 - a) + o[..., :3] * a
    # flames on top
    for j, x in enumerate(DIYAS):
        fl = 1 + 0.12 * math.sin(ph * 3 + j * 1.7) + 0.06 * math.sin(ph * 7 + j)
        sway = 2.2 * math.sin(ph * 2 + j)
        fx, fy = x + sway, DIYA_Y - 22 - 10 * fl
        add_ellipse_glow(img, fx, fy, 7 * fl, 15 * fl, FLAME_OUT, 0.95)
        add_ellipse_glow(img, fx - sway * 0.3, fy + 4, 3.5, 8 * fl, FLAME_IN, 1.0)
        add_glow(img, fx, fy, 26, GOLD, 0.25 * fl)
    # text: gold with a moving shimmer
    hindi, eng, sub = masks
    xs = np.arange(S, dtype=np.float32)[None, :]
    band = (((t / LOOP) * (S + 400)) - 200)
    shimmer = np.exp(-((xs - band) / 45) ** 2)[..., None]
    for m, base, boost in [(hindi, np.array([255, 214, 140], np.float32), 0.6),
                           (eng, GOLD, 0.8)]:
        sh = np.clip(m - np.roll(np.roll(m, 3, 0), 2, 1), 0, 1)              # tiny shadow trick
        img = img * (1 - np.roll(np.roll(m, 3, 0), 2, 1)[..., None] * 0.6)
        col = base + (np.array([255, 250, 230], np.float32) - base) * shimmer * boost
        img = img * (1 - m[..., None]) + col * m[..., None]
    img = img * (1 - sub[..., None]) + np.array([246, 232, 255], np.float32) * sub[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    bg = background()
    overlay = static_overlay()
    masks = text_masks()
    tmp = tempfile.mkdtemp(dir=HERE)
    try:
        for i in range(N):
            Image.fromarray(frame(i, bg, overlay, masks)).save(os.path.join(tmp, f"f{i:03d}.png"))
        pat = os.path.join(tmp, "f%03d.png")
        gif = os.path.join(HERE, "happy_diwali.gif")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pat,
                        "-vf", "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
                               "[b][p]paletteuse=dither=sierra2_4a", "-loop", "0", gif], check=True)
        mp4 = os.path.join(HERE, "happy_diwali.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-framerate", str(FPS),
                        "-i", pat, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", mp4], check=True)
        Image.open(os.path.join(tmp, "f010.png")).save(os.path.join(HERE, "preview.png"))
        print("wrote", gif, os.path.getsize(gif) // 1024, "KB;", mp4)
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
