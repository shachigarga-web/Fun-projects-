"""
Chapter 3 reel from ready-made illustrations: slow camera moves, crossfades,
one handwritten line at the turn of the story, small sign-off at the end.

The song is added inside Instagram (licensed audio library), so the video is silent.
Also writes one clip per image into clips/ for beat-syncing in Instagram or CapCut.

  python make_ch3.py
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "ShadowsIntoLightTwo-Regular.ttf")
BOLD = os.path.join(HERE, "..", "Caveat.ttf")
W, H, FPS = 1080, 1920, 30
XF = 0.3                                     # crossfade seconds

# (file, seconds, camera move)  moves: zin, zout, up, down, left, right
SHOTS = [
    ("01.png", 2.6, "soft"),     # then slowly... the labels appear
    ("02.png", 2.4, "up"),      # don't be so demanding / too picky
    ("03.png", 2.6, "zout"),    # household responsibility...
    ("04.png", 2.2, "zin"),     # the turn: she works on her own goals
    ("05.png", 1.9, "right"),   # moodboard
    ("06.png", 1.9, "zin"),     # painting
    ("07.png", 1.9, "down"),    # hiking
    ("08.png", 1.9, "zout"),    # terrace dinner
    ("09.png", 1.9, "zin"),     # cheers
    ("10.png", 3.2, "up"),      # coffee, eyes closed: the ending
]
TURN_TEXT = (3, "so she did what a girl's gotta do.")
SIGN_OFF = "lilac tinted chapters"


def cover(im, fit=False):
    s = max(W / im.width, H / im.height)
    if not fit:
        return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    # fit the whole image (text must not be cropped); fill the rest with a blurred copy
    bw, bh = W, H
    bg = im.resize((round(im.width * s * 1.1), round(im.height * s * 1.1)), Image.LANCZOS)
    bg = bg.crop(((bg.width - bw) // 2, (bg.height - bh) // 2, (bg.width - bw) // 2 + bw, (bg.height - bh) // 2 + bh))
    bg = bg.filter(ImageFilter.GaussianBlur(30))
    k = bw / im.width
    fg = im.resize((bw, round(im.height * k)), Image.LANCZOS)
    bg.paste(fg, (0, (bh - fg.height) // 2))
    return bg


def move(im, move, p):
    """Crop a 9:16 window from the cover-fitted image; p in 0..1 over the shot."""
    p = p * p * (3 - 2 * p)                               # ease in-out
    z = {"zin": 1.0 + 0.09 * p, "zout": 1.09 - 0.09 * p, "soft": 1.0 + 0.025 * p}.get(move, 1.06)
    cw, ch = W / z, H / z
    ex, ey = im.width - cw, im.height - ch               # spare room to pan in
    cx, cy = ex / 2, ey / 2
    if move == "up":
        cy = ey * (0.85 - 0.7 * p)
    elif move == "down":
        cy = ey * (0.15 + 0.7 * p)
    elif move == "left":
        cx = ex * (0.85 - 0.7 * p)
    elif move == "right":
        cx = ex * (0.15 + 0.7 * p)
    return im.resize((W, H), Image.BICUBIC, box=(cx, cy, cx + cw, cy + ch))


def text_layer(txt, size, y, alpha, reveal=1.0, bold=False):
    f = ImageFont.truetype(BOLD if bold else FONT, size)
    if bold:
        f.set_variation_by_name("Bold")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = txt[:max(0, int(len(txt) * reveal))]
    x = W / 2 - f.getlength(txt) / 2
    a = int(255 * alpha)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x + 2, y + 4), s, font=f, fill=(25, 12, 35, int(a * 0.85)), anchor="lm")
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    sh.alpha_composite(sh)
    d = ImageDraw.Draw(sh)
    d.text((x, y), s, font=f, fill=(255, 250, 244, a), anchor="lm")
    return sh


def shot_frame(i, t, imgs):
    fn, dur, mv = SHOTS[i]
    fr = move(imgs[i], mv, min(1, t / dur)).convert("RGBA")
    if i == TURN_TEXT[0]:
        rv = min(1, max(0, (t - 0.25) / 1.0))
        fr.alpha_composite(text_layer(TURN_TEXT[1], 88, 300, 1.0, rv, bold=True))
    if i == len(SHOTS) - 1:
        a = min(1, max(0, (t - 1.2) / 0.6))
        fr.alpha_composite(text_layer(SIGN_OFF, 64, 1500, a, bold=True))
    return fr.convert("RGB")


def ffmpeg(out):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                             "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                            stdin=subprocess.PIPE)


def main():
    imgs = [cover(Image.open(os.path.join(HERE, "src", s[0])).convert("RGB"), fit=(s[0] == "01.png")) for s in SHOTS]
    starts, t = [], 0.0
    for _, dur, _ in SHOTS:
        starts.append(t)
        t += dur
    total = t + XF
    out = os.path.join(HERE, "chapter3_labels.mp4")
    ff = ffmpeg(out)
    for fi in range(int(total * FPS)):
        tt = fi / FPS
        i = max(k for k, s in enumerate(starts) if s <= tt) if tt < starts[-1] + SHOTS[-1][1] else len(SHOTS) - 1
        lt = tt - starts[i]
        fr = shot_frame(i, lt, imgs)
        if i + 1 < len(SHOTS) and lt > SHOTS[i][1] - XF:            # crossfade into next shot
            k = (lt - (SHOTS[i][1] - XF)) / XF
            fr = Image.blend(fr, shot_frame(i + 1, 0.0, imgs), k)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", out, f"({total:.1f}s)")

    os.makedirs(os.path.join(HERE, "clips"), exist_ok=True)
    for i, (fn, dur, mv) in enumerate(SHOTS):
        ff = ffmpeg(os.path.join(HERE, "clips", f"{i + 1:02d}.mp4"))
        n = int(3.0 * FPS)
        for fi in range(n):
            fr = move(imgs[i], mv, fi / n).convert("RGBA")
            if i == TURN_TEXT[0]:
                fr.alpha_composite(text_layer(TURN_TEXT[1], 88, 300, 1.0, min(1, fi / FPS / 1.0), bold=True))
            ff.stdin.write(fr.convert("RGB").tobytes())
        ff.stdin.close()
        ff.wait()
    print("wrote clips/01..10.mp4 (3s each)")


if __name__ == "__main__":
    main()
