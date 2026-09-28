"""Extra video styles for make_motion.render (spec["style"]).

Every style reads the same spec as the original "slam" style, so drafts do not change:
  receipt - typewriter hook, a store receipt prints the per-unit prices, a red stamp hits,
            then a slow zoom over the product photo and a CTA
  slot    - words slide up, the per-unit price rolls down like a slot machine and locks,
            the product swipes in with a pulsing badge, review bars grow, CTA
  split   - split-screen hook, side-by-side price bars (정가 vs 지금) with the drop %,
            a polaroid of the product drops in, two stat tiles, CTA
"""
import math

from PIL import Image, ImageDraw, ImageFilter

import make_motion as mm
from make_cards import font

W, H = mm.W, mm.H
BLACK, WHITE, RED = mm.BLACK, mm.WHITE, mm.RED
ease, clamp, slam, won = mm.ease, mm.clamp, mm.slam, mm.won
text_img, paste_center, fit_size, shake = mm.text_img, mm.paste_center, mm.fit_size, mm.shake

END = {"receipt": 8.4, "slot": 8.5, "split": 8.4}
POSTER_AT = {"receipt": 4.3, "slot": 4.9, "split": 5.3}


def pct_off(spec):
    return max(1, round((1 - spec["to_price"] / spec["from_price"]) * 100))


def bleed_image(prod_raw):
    """Product photo filling the 4:5 frame: blurred cover behind, sharp square in front."""
    side = min(prod_raw.size)
    sq = prod_raw.crop(((prod_raw.width - side) // 2, (prod_raw.height - side) // 2,
                        (prod_raw.width + side) // 2, (prod_raw.height + side) // 2))
    bg = sq.resize((H, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda v: int(v * 0.55))
    out = Image.new("RGB", (W, H))
    out.paste(bg, ((W - H) // 2, 0))
    out.paste(sq.resize((W, W), Image.LANCZOS), (0, (H - W) // 2 - 60))
    return out.convert("RGBA")


def ken_burns(img, k):
    s = 1.0 + 0.12 * k
    w, h = int(W / s), int(H / s)
    x, y = (W - w) // 2, int((H - h) * 0.4)
    return img.crop((x, y, x + w, y + h)).resize((W, H), Image.BILINEAR)


def gradient_bottom(im, top=750):
    g = Image.new("L", (1, H), 0)
    for y in range(top, H):
        g.putpixel((0, y), int(230 * ((y - top) / (H - top)) ** 1.2))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    layer.putalpha(g.resize((W, H)))
    im.alpha_composite(layer)


def pill(text, size, fg, bg, outline=None):
    tx = text_img(text, "Black", size, fg)
    bw, bh = tx.width + 110, tx.height + 60
    p = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=bg,
                                        outline=outline, width=6 if outline else 0)
    p.paste(tx, (55, 30), tx)
    return p


def arrows(im, x, y, t, color):
    for k in range(3):
        a = clamp(0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 7 - k * 1.1)))
        paste_center(im, text_img("⌄" if False else "▼", "Black", 60, color), x, y + k * 52, 1, 0, a)


def deadline(im, spec, y, size=50):
    if spec.get("deadline"):
        paste_center(im, mm.deadline_pill(spec["deadline"], size), W / 2, y)


# ---------------------------------------------------------------- receipt
def receipt_frame(t, c):
    spec, P = c["spec"], c["P"]
    im = Image.new("RGBA", (W, H), (30, 30, 36, 255))
    sx = sy = 0
    if t < 1.6:  # typewriter hook
        words = spec["hook"][:4]
        lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else [" ".join(words)]
        lines = [l for l in lines if l]
        total = sum(len(l) for l in lines)
        n = int(total * clamp(t / 1.25))
        y = 520 if len(lines) > 1 else 640
        for i, line in enumerate(lines):
            vis = line[:max(0, n)]
            n -= len(line)
            size = fit_size(line, "Black", 170, 960)
            if vis:
                ti = text_img(vis, "Black", size, P["a"] if i == len(lines) - 1 else WHITE)
                x0 = (W - text_img(line, "Black", size, WHITE).width) / 2
                im.paste(ti, (int(x0), int(y - ti.height / 2)), ti)
                if 0 <= n < len(lines[i + 1] if i + 1 < len(lines) else "") or (i == len(lines) - 1 and n <= 0):
                    if int(t * 4) % 2 == 0:
                        ImageDraw.Draw(im).rectangle([x0 + ti.width + 8, y - size * 0.45, x0 + ti.width + 30, y + size * 0.45], fill=WHITE)
            y += 230
        return im, 0, 0
    if t < 4.6:  # receipt prints
        tt = t - 1.6
        pw, ph = 860, 1060
        paper = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(paper)
        d.rectangle([0, 0, pw, ph - 30], fill=(250, 248, 240))
        for x in range(0, pw, 40):  # torn bottom
            d.polygon([(x, ph - 30), (x + 20, ph), (x + 40, ph - 30)], fill=(250, 248, 240))
        ink, mute = (30, 30, 30), (120, 120, 120)
        def center(y, s, f, col):
            d.text(((pw - d.textlength(s, font=f)) / 2, y), s, font=f, fill=col)
        def dash(y):
            for x in range(50, pw - 50, 28):
                d.line([x, y, x + 14, y], fill=mute, width=4)
        def row(y, l, r, f, col):
            d.text((60, y), l, font=f, fill=col)
            d.text((pw - 60 - d.textlength(r, font=f), y), r, font=f, fill=col)
        center(40, "영 수 증", font("Black", 58), ink)
        nm = spec["name"]
        center(130, nm, font("Bold", fit_size(nm, "Bold", 46, pw - 120)), mute)
        dash(215)
        f1, f2 = font("Bold", 54), font("Black", 60)
        if tt > 0.55:
            row(260, f"{spec['unit']} 정가", f"{won(spec['from_price'])}원", f1, mute)
        if tt > 0.9:
            row(360, f"{spec['unit']} 지금", f"{won(spec['to_price'])}원", f2, RED)
        if tt > 1.25:
            row(465, "차이", f"-{won(spec['from_price'] - spec['to_price'])}원", f1, ink)
        dash(575)
        if tt > 1.6:
            row(620, "결제가", spec["badge_price"], font("Black", 74), ink)
        drop = ease(tt / 0.5)
        top = int(-ph + (ph + 170) * drop)
        im.paste(paper, ((W - pw) // 2, top), paper)
        deadline(im, spec, 95, 46)
        if tt > 2.0:
            x = (tt - 2.0) / 0.35
            st = text_img(spec.get("stamp", "특가"), "Black", 120, RED)
            r = max(st.width, st.height) // 2 + 60
            badge = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge)
            bd.ellipse([6, 6, 2 * r - 6, 2 * r - 6], outline=RED, width=14)
            bd.ellipse([30, 30, 2 * r - 30, 2 * r - 30], outline=RED, width=5)
            badge.paste(st, (r - st.width // 2, r - st.height // 2), st)
            paste_center(im, badge, 700, 1110, slam(x), -16, 0.92)
            sx, sy = shake(t, 3.75, 24, 0.22)
        return im, sx, sy
    if t < 6.4:  # slow zoom over the product
        tt = t - 4.6
        im = ken_burns(c["bleed"], tt / 1.8)
        gradient_bottom(im)
        chip = pill(spec.get("stamp", "특가"), 56, WHITE, RED)
        paste_center(im, chip, 60 + chip.width / 2, 110, 1, 0, ease(tt / 0.3))
        nm = spec["name"]
        paste_center(im, text_img(nm, "Black", fit_size(nm, "Black", 66, 960), WHITE), W / 2, 1010, 1, 0, ease(tt / 0.3))
        for k, (label, num, unit) in enumerate(spec["stats"][:2]):
            a = ease((tt - 0.4 - 0.4 * k) / 0.3)
            s = f"{label} {won(num)}{unit}"
            paste_center(im, text_img(s, "Bold", fit_size(s, "Bold", 54, 960), P["hi"] if k == 0 else WHITE), W / 2, 1110 + 90 * k, 1, 0, a)
        paste_center(im, text_img("쿠팡 구매자 기준", "Bold", 34, (200, 200, 205)), W / 2, 1300, 1, 0, ease((tt - 0.8) / 0.3))
        return im, 0, 0
    tt = t - 6.4  # CTA
    im.paste(P["a"] + (255,), [0, 0, W, H])
    deadline(im, spec, 100, 52)
    paste_center(im, c["card"], W / 2, 470 + 10 * math.sin(tt * 3), 0.6, 3 * math.sin(tt * 2))
    paste_center(im, text_img(spec["badge_price"], "Black", 140, BLACK), W / 2, 860, slam(tt / 0.35))
    paste_center(im, pill(spec.get("cta", "첫 댓글에 링크"), 84, WHITE, BLACK), W / 2, 1030)
    arrows(im, W / 2, 1160, tt, BLACK)
    return im, 0, 0


# ---------------------------------------------------------------- slot
def slot_frame(t, c):
    spec, P = c["spec"], c["P"]
    im = Image.new("RGBA", (W, H), P["a"] + (255,))
    sx = sy = 0
    if t < 1.3:  # words slide up
        words = spec["hook"][:4]
        per = 1.3 / (len(words) + 0.5)
        for k, w in enumerate(words):
            x = (t - k * per) / (per * 0.9)
            if x <= 0:
                continue
            y = 300 + k * 250 + 140 * (1 - ease(x))
            col = RED if k == len(words) - 1 else BLACK
            paste_center(im, text_img(w, "Black", fit_size(w, "Black", 230, 980), col), W / 2, y, 1, 0, clamp(x * 2))
        return im, 0, 0
    if t < 3.8:  # slot-machine price roll
        tt = t - 1.3
        im.paste(P["b"] + (255,), [0, 0, W, H])
        paste_center(im, text_img(f"{spec['unit']} 가격", "Black", 80, WHITE), W / 2, 220)
        old = text_img(f"{won(spec['from_price'])}원", "Black", 110, (140, 140, 150))
        paste_center(im, old, W / 2, 390)
        d = ImageDraw.Draw(im)
        d.line([W / 2 - old.width / 2 - 10, 395, W / 2 + old.width / 2 + 10, 385], fill=RED, width=14)
        k = ease((tt - 0.2) / 1.4)
        v = spec["from_price"] + (spec["to_price"] - spec["from_price"]) * k
        speed = 1 - clamp((tt - 0.2) / 1.4)
        big = text_img(f"{won(v)}원", "Black", 250, P["hi"], stroke=8, stroke_fill=BLACK)
        if speed > 0.05:
            for off in (-90, 90, -170, 170):
                paste_center(im, big, W / 2, 720 + off * speed, 1, 0, 0.25 * speed)
        sc = 1.0 + (0.18 * (1 - ease((tt - 1.6) / 0.35)) if tt > 1.6 else 0)
        paste_center(im, big, W / 2, 720, sc)
        if tt > 1.6:
            sx, sy = shake(t, 2.95, 26, 0.25)
            chip = pill(f"-{pct_off(spec)}%", 90, WHITE, RED)
            paste_center(im, chip, W / 2, 990, slam((tt - 1.65) / 0.35))
        if tt > 1.95:
            s = f"{spec['unit']}마다 {won(spec['from_price'] - spec['to_price'])}원 덜 내요"
            paste_center(im, text_img(s, "Bold", fit_size(s, "Bold", 60, 960), WHITE), W / 2, 1160, 1, 0, ease((tt - 1.95) / 0.3))
        return im, sx, sy
    if t < 5.8:  # product swipes in
        tt = t - 3.8
        nm = spec["name"]
        paste_center(im, text_img(nm, "Black", fit_size(nm, "Black", 62, 960), BLACK), W / 2, 150, 1, 0, ease(tt / 0.3))
        deadline(im, spec, 250, 44)
        k = ease(tt / 0.45)
        paste_center(im, c["card"], W / 2 + (W) * (1 - k), 700, 0.85, 10 * (1 - k))
        if tt > 0.5:
            st = text_img(spec.get("stamp", "특가"), "Black", 96, WHITE)
            r = max(st.width, st.height) // 2 + 50
            b = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
            ImageDraw.Draw(b).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=RED, outline=WHITE, width=10)
            b.paste(st, (r - st.width // 2, r - st.height // 2), st)
            paste_center(im, b, 850, 580, slam((tt - 0.5) / 0.3) * (1 + 0.05 * math.sin(tt * 8)), 12)
        paste_center(im, text_img(spec["badge_price"], "Black", 120, BLACK), W / 2, 1170, 1, 0, ease((tt - 0.7) / 0.3))
        return im, 0, 0
    if t < 7.4:  # review bars
        tt = t - 5.8
        im.paste(WHITE + (255,), [0, 0, W, H])
        d = ImageDraw.Draw(im)
        for k, (label, num, unit) in enumerate(spec["stats"][:2]):
            y = 300 + k * 480
            a = ease((tt - 0.35 * k) / 0.5)
            paste_center(im, text_img(label, "Black", fit_size(label, "Black", 64, 960), BLACK), W / 2, y - 110, 1, 0, clamp(a * 3))
            frac = num / 100 if unit == "%" else 1.0
            d.rounded_rectangle([90, y, W - 90, y + 110], radius=55, fill=(236, 236, 240))
            if a > 0:
                d.rounded_rectangle([90, y, 90 + max(110, int((W - 180) * frac * a)), y + 110], radius=55, fill=P["a"], outline=BLACK, width=6)
            val = f"{won(num * a)}{unit}"
            paste_center(im, text_img(val, "Black", 120, BLACK), W / 2, y + 200)
        paste_center(im, text_img("쿠팡 구매자 기준", "Bold", 40, (130, 130, 140)), W / 2, 1260)
        return im, 0, 0
    tt = t - 7.4  # CTA
    im.paste(P["b"] + (255,), [0, 0, W, H])
    deadline(im, spec, 100, 52)
    paste_center(im, c["card"], W / 2, 480, 0.58, 4 * math.sin(tt * 3))
    paste_center(im, text_img(spec["badge_price"], "Black", 140, WHITE), W / 2, 870, slam(tt / 0.3))
    paste_center(im, pill(spec.get("cta", "첫 댓글에 링크"), 84, BLACK, P["a"]), W / 2, 1040, 1 + 0.04 * math.sin(tt * 9))
    arrows(im, W / 2, 1170, tt, P["a"])
    return im, 0, 0


# ---------------------------------------------------------------- split
def split_frame(t, c):
    spec, P = c["spec"], c["P"]
    im = Image.new("RGBA", (W, H), WHITE + (255,))
    sx = sy = 0
    if t < 1.4:  # split-screen hook
        words = spec["hook"][:4]
        top, bot = " ".join(words[:len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])
        im.paste(BLACK + (255,), [0, H // 2, W, H])
        k1, k2 = ease(t / 0.45), ease((t - 0.35) / 0.45)
        paste_center(im, text_img(top, "Black", fit_size(top, "Black", 180, 980), BLACK), W / 2 - W * (1 - k1), H * 0.27)
        if bot:
            paste_center(im, text_img(bot, "Black", fit_size(bot, "Black", 180, 980), P["a"]), W / 2 + W * (1 - k2), H * 0.73)
        return im, 0, 0
    if t < 4.2:  # side-by-side price bars
        tt = t - 1.4
        im.paste((52, 52, 62, 255), [0, 0, W // 2, H])
        im.paste(P["a"] + (255,), [W // 2, 0, W, H])
        paste_center(im, text_img(f"{spec['unit']} 기준", "Black", 56, WHITE), W / 4, 130)
        paste_center(im, text_img("정가", "Black", 90, WHITE), W / 4, 240)
        paste_center(im, text_img("지금", "Black", 90, BLACK), W * 3 / 4, 240)
        d = ImageDraw.Draw(im)
        base, full = 1230, 760
        h1 = full * ease(tt / 0.4)
        ratio = spec["to_price"] / spec["from_price"]
        h2 = full * (1 - (1 - ratio) * ease((tt - 0.5) / 0.8)) * ease(tt / 0.4)
        d.rounded_rectangle([W / 4 - 150, base - h1, W / 4 + 150, base], radius=26, fill=(150, 150, 165))
        d.rounded_rectangle([W * 3 / 4 - 150, base - h2, W * 3 / 4 + 150, base], radius=26, fill=BLACK)
        v = spec["from_price"] + (spec["to_price"] - spec["from_price"]) * ease((tt - 0.5) / 0.8)
        paste_center(im, text_img(f"{won(spec['from_price'])}원", "Black", fit_size(f"{won(spec['from_price'])}원", "Black", 84, 500), WHITE), W / 4, base - h1 - 60, 1, 0, clamp(tt * 3))
        paste_center(im, text_img(f"{won(v)}원", "Black", fit_size(f"{won(spec['from_price'])}원", "Black", 84, 500), BLACK), W * 3 / 4, base - h2 - 60, 1, 0, clamp(tt * 3))
        if tt > 1.5:
            paste_center(im, pill(f"{pct_off(spec)}% ↓", 96, WHITE, RED, outline=WHITE), W * 3 / 4, 560, slam((tt - 1.5) / 0.35), -8)
            sx, sy = shake(t, 3.05, 22, 0.22)
        return im, sx, sy
    if t < 6.2:  # polaroid drop
        tt = t - 4.2
        im.paste(P["b"] + (255,), [0, 0, W, H])
        d = ImageDraw.Draw(im)
        for x in range(0, W, 90):
            d.line([x, 0, x, H], fill=tuple(min(255, v + 18) for v in P["b"]), width=2)
        deadline(im, spec, 90, 46)
        pol = c["polaroid"]
        k = ease(tt / 0.55)
        bounce = 30 * math.sin(clamp((tt - 0.55) / 0.3) * math.pi) if tt > 0.55 else 0
        paste_center(im, pol, W / 2, -500 + 1150 * k - bounce, 0.9, -4 * k)
        if tt > 0.7:
            st = text_img(spec["badge_price"], "Black", 78, BLACK)
            r = max(st.width, st.height) // 2 + 40
            b = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
            ImageDraw.Draw(b).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=P["hi"], outline=BLACK, width=8)
            b.paste(st, (r - st.width // 2, r - st.height // 2), st)
            paste_center(im, b, 840, 1170, slam((tt - 0.7) / 0.3), 10)
        return im, 0, 0
    if t < 7.4:  # stat tiles
        tt = t - 6.2
        im.paste(P["a"] + (255,), [0, 0, W, H])
        d = ImageDraw.Draw(im)
        for k, (label, num, unit) in enumerate(spec["stats"][:2]):
            y0 = 200 + k * 520
            a = ease((tt - 0.3 * k) / 0.45)
            if a <= 0:
                continue
            d.rounded_rectangle([80, y0, W - 80, y0 + 450], radius=40, fill=BLACK)
            paste_center(im, text_img(label, "Bold", fit_size(label, "Bold", 60, 860), WHITE), W / 2, y0 + 100)
            val = f"{won(num * a)}{unit}"
            paste_center(im, text_img(val, "Black", fit_size(val, "Black", 200, 860), P["hi"] if P["hi"] != P["a"] else WHITE), W / 2, y0 + 280)
        paste_center(im, text_img("쿠팡 구매자 기준", "Bold", 40, BLACK), W / 2, 1275)
        return im, 0, 0
    tt = t - 7.4  # CTA
    deadline(im, spec, 100, 52)
    paste_center(im, c["card"], W / 2, 480, 0.6)
    paste_center(im, text_img(spec["badge_price"], "Black", 140, BLACK), W / 2, 870, slam(tt / 0.3))
    paste_center(im, pill(spec.get("cta", "첫 댓글에 링크"), 84, WHITE, RED), W / 2, 1040, 1 + 0.04 * math.sin(tt * 9))
    arrows(im, W / 2, 1170, tt, BLACK)
    return im, 0, 0


FRAMES = {"receipt": receipt_frame, "slot": slot_frame, "split": split_frame}


def context(spec, card, prod_raw):
    pol = Image.new("RGBA", (820, 980), (0, 0, 0, 0))
    ImageDraw.Draw(pol).rectangle([0, 0, 819, 979], fill=(252, 252, 248))
    ph = card.crop((20, 20, 740, 740))
    pol.paste(ph, (50, 50), ph)
    nm = spec["name"]
    t = text_img(nm, "Bold", fit_size(nm, "Bold", 52, 720), (40, 40, 40))
    pol.paste(t, ((820 - t.width) // 2, 820), t)
    return {"spec": spec, "P": mm.PALETTES[spec.get("palette", "yellow")], "card": card,
            "bleed": bleed_image(prod_raw), "polaroid": pol}
