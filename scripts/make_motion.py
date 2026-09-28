"""Render a short motion-graphic MP4 (1080x1350, 30fps) for a Threads post.

usage: python scripts/make_motion.py spec.json out.mp4

spec = {
  "theme": "navy",                      # same palettes as make_cards.THEMES
  "product_image": "product.jpg",       # relative to spec file
  "kicker": "밀크씨슬 200정",            # small line on the first scene
  "from_price": 237, "to_price": 118,   # per-unit price counting down (원)
  "unit": "한 알",                        # "한 알" / "1포" / "1개"
  "brand": "NOW FOODS", "name": "실리마린 밀크시슬 300mg",
  "badge_top": "50% 할인", "badge_price": "23,660원",
  "stats": [["상품평", 73428, "개"], ["복용 편의 '아주편해요'", 74, "%"]],
  "cta": "링크는 첫 댓글에"
}
Scenes: 0-2.6s per-unit price counts down · 2.6-5.4s product slides in with price badge ·
5.4-8.2s review numbers count up with bars · 8.2-10s call to action.
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_cards import THEMES, WHITE, INK, font, fit  # noqa: E402

W, H, FPS, DUR = 1080, 1350, 30, 10.0


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def pop(x):
    """0→1 with a small overshoot."""
    x = max(0.0, min(1.0, x))
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2 if x < 1 else 1.0


def won(n):
    return f"{int(round(n)):,}"


def ctext(d, y, text, f, fill, alpha_img=None):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def render(spec, spec_dir, out_path):
    t = THEMES[spec.get("theme", "navy")]
    prod = Image.open(os.path.join(spec_dir, spec["product_image"])).convert("RGB").resize((700, 700))
    pmask = Image.new("L", (700, 700), 0)
    ImageDraw.Draw(pmask).rounded_rectangle([0, 0, 700, 700], radius=48, fill=255)

    bg = Image.new("RGB", (W, H), t["bg"])
    glow = Image.new("RGB", (W, H), t["bg"])
    ImageDraw.Draw(glow).ellipse([90, 280, 990, 1180], fill=t["glow"])
    bg.paste(glow.filter(ImageFilter.GaussianBlur(170)), (0, 0))

    f_kick = font("Bold", 56)
    f_big = font("Black", 230)
    f_unit = font("Bold", 64)
    f_mid = font("Bold", 50)
    frames = int(DUR * FPS)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "96k", out_path],
        stdin=subprocess.PIPE)

    for i in range(frames):
        s = i / FPS
        im = bg.copy()
        d = ImageDraw.Draw(im)

        if s < 2.6:  # scene 1: per-unit price counts down
            k = ease(s / 0.5)
            ctext(d, 170 + (1 - k) * 40, spec["kicker"], f_kick, t["soft"])
            ctext(d, 330, f"{spec['unit']} 가격", f_unit, WHITE)
            c = ease((s - 0.4) / 1.6)
            val = spec["from_price"] + (spec["to_price"] - spec["from_price"]) * c
            txt = won(val) + "원"
            col = t["accent"] if c >= 1 else WHITE
            ctext(d, 470, txt, fit(d, txt, "Black", 230, 1000), col)
            if s > 0.5:  # old price, struck
                old = f"원래 {won(spec['from_price'])}원"
                fo = font("Bold", 52)
                x0 = (W - d.textlength(old, font=fo)) / 2
                d.text((x0, 800), old, font=fo, fill=t["soft"])
                sw = d.textlength(old, font=fo) * ease((s - 0.6) / 0.5)
                d.line([x0 - 6, 832, x0 - 6 + sw + 12, 832], fill=(255, 110, 100), width=7)

        elif s < 5.4:  # scene 2: product slides up, badge pops
            k = ease((s - 2.6) / 0.6)
            y = int(460 + (1 - k) * 700)
            d.text((80, 130), spec["brand"], font=fit(d, spec["brand"], "Bold", 52, 920), fill=t["soft"])
            d.text((80, 200), spec["name"], font=fit(d, spec["name"], "Black", 84, 920), fill=WHITE)
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle([200, y + 30, 900, y + 730], radius=48, fill=(0, 0, 0, 90))
            sh = sh.filter(ImageFilter.GaussianBlur(24))
            im.paste(sh, (0, 0), sh)
            im.paste(prod, (190, y), pmask)
            d = ImageDraw.Draw(im)
            b = pop((s - 3.3) / 0.45)
            if b > 0:
                bw, bh = int(420 * b), int(250 * b)
                cx, cy = 820, 1120
                d.ellipse([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2], fill=t["accent"])
                if b > 0.8:
                    f1, f2 = font("Bold", 42), fit(d, spec["badge_price"], "Black", 76, 360)
                    d.text((cx - d.textlength(spec["badge_top"], font=f1) / 2, cy - 78), spec["badge_top"], font=f1, fill=INK)
                    d.text((cx - d.textlength(spec["badge_price"], font=f2) / 2, cy - 18), spec["badge_price"], font=f2, fill=INK)

        elif s < 8.2:  # scene 3: numbers from reviews
            ctext(d, 150, "구매자들이 남긴 숫자", f_mid, t["soft"])
            for j, (label, num, unit) in enumerate(spec["stats"][:2]):
                st = 5.6 + j * 0.7
                c = ease((s - st) / 1.0)
                if s < st:
                    continue
                y0 = 330 + j * 400
                ctext(d, y0, label, fit(d, label, "Bold", 54, 960), WHITE)
                val = won(num * c) + unit
                ctext(d, y0 + 80, val, fit(d, val, "Black", 150, 980), t["accent"])
                pct = min(num, 100) / 100 if unit == "%" else 1.0
                d.rounded_rectangle([140, y0 + 305, 940, y0 + 325], radius=10, fill=t["glow"])
                d.rounded_rectangle([140, y0 + 305, 140 + int(800 * pct * c), y0 + 325], radius=10, fill=t["accent"])
            ctext(d, 1180, "쿠팡 상품 페이지 기준", font("Regular", 36), t["soft"])

        else:  # scene 4: CTA
            k = ease((s - 8.2) / 0.4)
            ctext(d, 420, spec["name"], fit(d, spec["name"], "Black", 70, 960), WHITE)
            ctext(d, 540, spec["badge_price"], font("Black", 150), t["accent"])
            pulse = 1 + 0.04 * math.sin((s - 8.2) * 8)
            cta = spec.get("cta", "링크는 첫 댓글에")
            fc = font("Black", int(66 * pulse))
            w = d.textlength(cta + "  ↓", font=fc)
            d.rounded_rectangle([(W - w) / 2 - 50, 860 - 10 + (1 - k) * 60, (W + w) / 2 + 50, 980 + (1 - k) * 60],
                                radius=60, fill=WHITE)
            d.text(((W - w) / 2, 875 + (1 - k) * 60), cta + "  ↓", font=fc, fill=t["main"])

        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()
    return out_path


if __name__ == "__main__":
    sp = sys.argv[1]
    render(json.load(open(sp)), os.path.dirname(os.path.abspath(sp)), sys.argv[2])
    print("wrote", sys.argv[2])
