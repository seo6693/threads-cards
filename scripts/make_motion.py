"""Render a punchy motion-graphic MP4 (1080x1350, 30fps, ~8.5s) for a Threads post.

usage: python scripts/make_motion.py spec.json out.mp4

spec = {
  "product_image": "product.jpg",                 # relative to spec file
  "hook": ["밀크씨슬", "아직도", "237원에", "드세요?"],  # 3-4 short words, slammed in one by one
  "unit": "한 알",
  "from_price": 237, "to_price": 118,             # per-unit price: old → now (원)
  "stamp": "반값",                                  # word stamped over the product (e.g. 반값, 50%↓)
  "name": "나우푸드 밀크씨슬 200정",
  "badge_price": "23,660원",
  "stats": [["리뷰", 73428, "개"], ["'복용 아주 편해요'", 74, "%"]],
  "cta": "첫 댓글에 링크",
  "deadline": "9/29(화) 오전 7시까지",                # optional; deals account adds it automatically
  "palette": "yellow"                              # yellow | lime | pink | cyan
}
Design: loud contrasting backgrounds that change every scene, words that slam in with
overshoot and screen shake, rotating light rays, a rubber stamp, a count-up, a top
progress bar (keeps people watching) and a bouncing arrow toward the comments.
"""
import json
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_cards import font  # noqa: E402

W, H, FPS = 1080, 1350, 30
BLACK, WHITE, RED = (14, 14, 18), (255, 255, 255), (235, 48, 48)
PALETTES = {
    "yellow": {"a": (255, 214, 10), "b": (18, 18, 24), "c": (255, 255, 255), "hi": (255, 214, 10)},
    "lime":   {"a": (190, 242, 60), "b": (16, 22, 16), "c": (255, 255, 255), "hi": (190, 242, 60)},
    "pink":   {"a": (255, 92, 150), "b": (22, 14, 24), "c": (255, 255, 255), "hi": (255, 214, 10)},
    "cyan":   {"a": (40, 220, 235), "b": (10, 20, 32), "c": (255, 255, 255), "hi": (255, 214, 10)},
}
# scene boundaries (seconds)
S1, S2, S3, S4, END = 1.3, 3.0, 4.8, 6.6, 8.5


def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):
    return 1 - (1 - clamp(x)) ** 3


def slam(x):
    """Scale factor: starts big (2.6x), lands at 1 with a small bounce."""
    x = clamp(x)
    if x < 0.55:
        return 2.6 - 1.7 * ease(x / 0.55) - 0.0
    y = (x - 0.55) / 0.45
    return 0.9 + 0.1 * (1 - math.cos(y * math.pi)) / 2 * 1.0 + 0.0 * y


def won(n):
    return f"{int(round(n)):,}"


def text_img(text, weight, size, fill, stroke=0, stroke_fill=BLACK):
    f = font(weight, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def paste_center(base, im, cx, cy, scale=1.0, angle=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    base.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)


def fit_size(text, weight, size, max_w):
    while size > 30:
        im = text_img(text, weight, size, WHITE)
        if im.width <= max_w:
            return size
        size -= 6
    return size


def rays(base, cx, cy, color, angle, n=18, alpha=70):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    R = 1600
    for k in range(n):
        a0 = math.radians(angle + k * 360 / n)
        a1 = a0 + math.radians(360 / n / 2)
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=color + (alpha,))
    base.paste(layer, (0, 0), layer)


class Confetti:
    def __init__(self, seed, colors):
        rnd = random.Random(seed)
        self.p = [(rnd.uniform(0, W), rnd.uniform(-300, -20), rnd.uniform(-3, 3), rnd.uniform(9, 17),
                   rnd.uniform(0, 360), rnd.choice(colors), rnd.randint(14, 26)) for _ in range(70)]

    def draw(self, base, t):
        d = ImageDraw.Draw(base)
        for x, y, vx, vy, rot, col, sz in self.p:
            yy = y + vy * t * FPS
            xx = x + vx * t * FPS + 20 * math.sin(t * 6 + rot)
            if -40 < yy < H + 40:
                a = math.radians(rot + t * 400)
                w, h = sz, sz * 0.45
                pts = [(xx + w * math.cos(a) - h * math.sin(a), yy + w * math.sin(a) + h * math.cos(a)),
                       (xx - w * math.cos(a) - h * math.sin(a), yy - w * math.sin(a) + h * math.cos(a)),
                       (xx - w * math.cos(a) + h * math.sin(a), yy - w * math.sin(a) - h * math.cos(a)),
                       (xx + w * math.cos(a) + h * math.sin(a), yy + w * math.sin(a) - h * math.cos(a))]
                d.polygon(pts, fill=col)


def deadline_pill(text, size=54):
    """Red '⏰-less' pill with the deal end time (fonts have no emoji)."""
    tx = text_img("특가 " + text, "Black", size, WHITE)
    bw, bh = tx.width + 70, tx.height + 44
    pill = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=RED,
                                           outline=WHITE, width=6)
    pill.paste(tx, (35, 22), tx)
    return pill


def shake(t, t0, amp=26, dur=0.25):
    if t0 <= t < t0 + dur:
        k = 1 - (t - t0) / dur
        return (int(amp * k * math.sin(t * 90)), int(amp * k * math.cos(t * 77)))
    return (0, 0)


def render(spec, spec_dir, out_path):
    P = PALETTES[spec.get("palette", "yellow")]
    prod = Image.open(os.path.join(spec_dir, spec["product_image"])).convert("RGB")
    side = min(prod.size)
    prod = prod.crop(((prod.width - side) // 2, (prod.height - side) // 2,
                      (prod.width + side) // 2, (prod.height + side) // 2)).resize((720, 720), Image.LANCZOS)
    card = Image.new("RGBA", (760, 760), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, 759, 759], radius=56, fill=WHITE)
    m = Image.new("L", (720, 720), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 719, 719], radius=40, fill=255)
    card.paste(prod, (20, 20), m)

    words = spec["hook"][:4]
    wsizes = [fit_size(w, "Black", 250, 980) for w in words]
    confetti = Confetti(7, [P["a"], RED, WHITE, (80, 160, 255)])

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "96k", out_path],
        stdin=subprocess.PIPE)

    for i in range(int(END * FPS)):
        t = i / FPS
        frame = Image.new("RGB", (W + 80, H + 80), BLACK)  # oversize for shake
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        sx, sy = 0, 0

        if t < S1:  # 1. words slam in on loud background
            im.paste(P["a"] + (255,), [0, 0, W, H])
            per = S1 / (len(words) + 0.6)
            ys = [300 + k * 250 for k in range(len(words))]
            for k, w in enumerate(words):
                t0 = k * per
                if t >= t0:
                    x = (t - t0) / (per * 0.9)
                    sc = slam(x)
                    col = RED if k == len(words) - 1 else BLACK
                    paste_center(im, text_img(w, "Black", wsizes[k], col), W / 2, ys[k], sc, 0, clamp(x * 3))
                    dx, dy = shake(t, t0 + per * 0.5, 18, 0.18)
                    sx, sy = sx + dx, sy + dy

        elif t < S2:  # 2. old price struck, new price slams with rays + confetti
            im.paste(P["b"] + (255,), [0, 0, W, H])
            tt = t - S1
            rays(im, W // 2, 700, P["a"], tt * 60, alpha=45 if tt > 0.55 else 0)
            paste_center(im, text_img(f"{spec['unit']} 가격", "Black", 84, WHITE), W / 2, 230)
            old = text_img(f"{won(spec['from_price'])}원", "Black", 170, (150, 150, 160))
            paste_center(im, old, W / 2, 440, 1.0 - 0.25 * ease((tt - 0.5) / 0.3))
            if tt > 0.25:  # red strike
                d = ImageDraw.Draw(im)
                k = ease((tt - 0.25) / 0.2)
                d.line([W / 2 - 260, 470, W / 2 - 260 + 520 * k, 410], fill=RED, width=22)
            if tt > 0.55:
                x = (tt - 0.55) / 0.35
                new = text_img(f"{won(spec['to_price'])}원", "Black", 300, P["a"], stroke=10, stroke_fill=BLACK)
                paste_center(im, new, W / 2, 780, slam(x), -4 * (1 - clamp(x)))
                dx, dy = shake(t, S1 + 0.75, 30, 0.3)
                sx, sy = dx, dy
                if tt < 0.62:  # white flash
                    im.paste((255, 255, 255, 255), [0, 0, W, H])
            if tt > 0.9:
                paste_center(im, text_img("이 가격 실화?", "Black", 80, WHITE), W / 2, 1120, ease((tt - 0.9) / 0.3))
            confetti.draw(im, max(0, tt - 0.55)) if tt > 0.55 else None

        elif t < S3:  # 3. product spins in, stamp hits
            tt = t - S2
            im.paste(P["a"] + (255,), [0, 0, W, H])
            rays(im, W // 2, 690, WHITE, -tt * 50, alpha=90)
            k = ease(tt / 0.45)
            paste_center(im, card, W / 2, 690, 0.35 + 0.65 * k, -25 * (1 - k))
            paste_center(im, text_img(spec["name"], "Black", fit_size(spec["name"], "Black", 64, 960), BLACK), W / 2, 150 if spec.get("deadline") else 200, 1, 0, ease(tt / 0.3))
            if tt > 0.6:
                x = (tt - 0.6) / 0.3
                stamp = text_img(spec.get("stamp", "특가"), "Black", 170, WHITE)
                bw, bh = stamp.width + 80, stamp.height + 50
                badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
                bd = ImageDraw.Draw(badge)
                bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=30, fill=RED, outline=WHITE, width=10)
                badge.paste(stamp, (40, 25), stamp)
                paste_center(im, badge, 800, 1000, slam(x), -14)
                dx, dy = shake(t, S2 + 0.78, 26, 0.25)
                sx, sy = dx, dy
            if spec.get("deadline"):
                paste_center(im, deadline_pill(spec["deadline"], 46), W / 2, 250, 1, 0, ease((tt - 0.2) / 0.3))
            if tt > 1.0:
                pr = text_img(spec["badge_price"], "Black", 110, BLACK)
                paste_center(im, pr, 330, 1180, ease((tt - 1.0) / 0.3))

        elif t < S4:  # 4. social proof count-up
            tt = t - S3
            im.paste(P["b"] + (255,), [0, 0, W, H])
            d = ImageDraw.Draw(im)
            for k, (label, num, unit) in enumerate(spec["stats"][:2]):
                t0 = k * 0.75
                if tt < t0:
                    continue
                c = ease((tt - t0) / 0.7)
                y = 380 + k * 460
                paste_center(im, text_img(label, "Black", fit_size(label, "Black", 70, 960), WHITE), W / 2, y - 120, 1, 0, clamp((tt - t0) * 4))
                val = won(num * c) + unit
                big = text_img(val, "Black", fit_size(val, "Black", 220, 980), P["hi"])
                paste_center(im, big, W / 2, y + 60, 1.0 + 0.15 * (1 - c))
                if unit == "%":
                    d.rounded_rectangle([140, y + 200, 940, y + 232], radius=16, fill=(60, 60, 70))
                    d.rounded_rectangle([140, y + 200, 140 + int(800 * num / 100 * c), y + 232], radius=16, fill=P["hi"])
            paste_center(im, text_img("쿠팡 구매자 기준", "Bold", 40, (170, 170, 180)), W / 2, 1250)

        else:  # 5. CTA with bouncing arrow
            tt = t - S4
            im.paste(P["a"] + (255,), [0, 0, W, H])
            paste_center(im, card, W / 2, 470, 0.62)
            if spec.get("deadline"):
                paste_center(im, deadline_pill(spec["deadline"], 58), W / 2, 110, 1 + 0.04 * math.sin(tt * 7))
            paste_center(im, text_img(spec["badge_price"], "Black", 150, BLACK), W / 2, 870, slam(tt / 0.35))
            cta = text_img(spec.get("cta", "첫 댓글에 링크"), "Black", 90, WHITE)
            bw, bh = cta.width + 120, cta.height + 70
            pill = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=BLACK)
            pill.paste(cta, (60, 35), cta)
            paste_center(im, pill, W / 2, 1060, 1 + 0.05 * math.sin(tt * 9))
            bounce = abs(math.sin(tt * 6)) * 40
            paste_center(im, text_img("↓", "Black", 150, RED), W / 2, 1210 + bounce)

        # progress bar on top (story style)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 14], fill=(0, 0, 0, 90))
        d.rectangle([0, 0, int(W * t / END), 14], fill=RED)

        frame.paste(im.convert("RGB"), (40 + sx, 40 + sy))
        ff.stdin.write(frame.crop((40, 40, 40 + W, 40 + H)).tobytes())
    ff.stdin.close()
    ff.wait()
    return out_path


def poster(video_path, jpg_path, at=4.2):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(at), "-i", video_path,
                    "-frames:v", "1", "-q:v", "3", jpg_path], check=True)
    return jpg_path


if __name__ == "__main__":
    sp = sys.argv[1]
    render(json.load(open(sp)), os.path.dirname(os.path.abspath(sp)), sys.argv[2])
    print("wrote", sys.argv[2])
