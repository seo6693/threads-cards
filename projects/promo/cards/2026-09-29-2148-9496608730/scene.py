"""가스레인지 점화: a stovetop burner clicks on with a flame burst, the promotion banner lands on the
grate like a pan, then the real pan drops on and the price is 'cooked' as the flame turns up."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

CONCEPT = {
    "name": "가스레인지 점화 다이얼",
    "idea": "위에서 내려다본 가스레인지가 '딱' 점화되며 불꽃이 터지고, 행사 배너가 팬처럼 화구에 얹혔다가 "
            "실제 프라이팬이 올라가며 화력이 '강'으로 올라갈 때 가격이 익어 튀어나온다",
}
END = 10.0
POSTER_AT = 8.2

CX, CY = 540, 735
_cache = {}


def pc(mm, base, img, *a):
    mm.paste_center(base, img.copy(), *a)


def T(mm, key, text, weight, size, fill, stroke=0, sf=(0, 0, 0)):
    k = (key, text, size)
    if k not in _cache:
        _cache[k] = mm.text_img(text, weight, size, fill, stroke, sf)
    return _cache[k]


def stovetop(W, H):
    if "bg" in _cache:
        return _cache["bg"].copy()
    bg = Image.new("RGBA", (W, H), (22, 22, 26, 255))
    d = ImageDraw.Draw(bg)
    for y in range(H):  # glass top gradient
        v = int(18 + 16 * (1 - abs(y - H * 0.45) / (H * 0.6)))
        d.line([(0, y), (W, y)], fill=(v, v, v + 4, 255))
    # glossy diagonal reflection
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(0, 180), (W, -120), (W, 40), (0, 340)], fill=(255, 255, 255, 14))
    bg.alpha_composite(gl)
    # burner base rings
    d.ellipse([CX - 250, CY - 250, CX + 250, CY + 250], fill=(38, 38, 42, 255), outline=(70, 70, 76, 255), width=6)
    d.ellipse([CX - 120, CY - 120, CX + 120, CY + 120], fill=(55, 55, 60, 255))
    d.ellipse([CX - 60, CY - 60, CX + 60, CY + 60], fill=(30, 30, 34, 255))
    _cache["bg"] = bg
    return bg.copy()


def flames(im, power, t):
    """ring of flame tongues; power 0..1.4 sets height."""
    if power <= 0.02:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    n = 28
    r0 = 128
    for k in range(n):
        a = 2 * math.pi * k / n
        flick = 0.75 + 0.25 * math.sin(t * 23 + k * 1.7) + 0.1 * math.sin(t * 41 + k)
        h = (40 + 120 * power) * flick
        w = 0.085
        pts = [(CX + r0 * math.cos(a - w), CY + r0 * math.sin(a - w)),
               (CX + (r0 + h) * math.cos(a), CY + (r0 + h) * math.sin(a)),
               (CX + r0 * math.cos(a + w), CY + r0 * math.sin(a + w))]
        d.polygon(pts, fill=(60, 140, 255, 210))
        inner = [(CX + r0 * math.cos(a - w * 0.5), CY + r0 * math.sin(a - w * 0.5)),
                 (CX + (r0 + h * 0.55) * math.cos(a), CY + (r0 + h * 0.55) * math.sin(a)),
                 (CX + r0 * math.cos(a + w * 0.5), CY + r0 * math.sin(a + w * 0.5))]
        d.polygon(inner, fill=(190, 230, 255, 235))
        if power > 1.0:  # orange tips at full power
            tip = [(CX + (r0 + h * 0.8) * math.cos(a - w * 0.4), CY + (r0 + h * 0.8) * math.sin(a - w * 0.4)),
                   (CX + (r0 + h * 1.05) * math.cos(a), CY + (r0 + h * 1.05) * math.sin(a)),
                   (CX + (r0 + h * 0.8) * math.cos(a + w * 0.4), CY + (r0 + h * 0.8) * math.sin(a + w * 0.4))]
            d.polygon(tip, fill=(255, 150, 40, 200))
    glow = layer.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(glow)
    im.alpha_composite(layer)


def grate(im):
    d = ImageDraw.Draw(im)
    for a in (0, 90, 180, 270):
        r = math.radians(a + 45)
        x0, y0 = CX + 150 * math.cos(r), CY + 150 * math.sin(r)
        x1, y1 = CX + 330 * math.cos(r), CY + 330 * math.sin(r)
        d.line([(x0, y0), (x1, y1)], fill=(12, 12, 14, 255), width=30)
        d.line([(x0, y0), (x1, y1)], fill=(60, 60, 66, 255), width=8)
    d.ellipse([CX - 335, CY - 335, CX + 335, CY + 335], outline=(12, 12, 14, 255), width=22)


def knob(im, mm, t, level):
    """control knob bottom-left with 약/중/강 marks."""
    kx, ky = 118, 1222
    d = ImageDraw.Draw(im)
    for lab, ang in (("약", -60), ("중", 0), ("강", 60)):
        r = math.radians(ang - 90)
        pc(mm, im, T(mm, "k", lab, "Bold", 30, (200, 200, 205)), kx + 84 * math.cos(r), ky + 84 * math.sin(r))
    d.ellipse([kx - 54, ky - 54, kx + 54, ky + 54], fill=(210, 210, 214, 255), outline=(120, 120, 126, 255), width=6)
    ang = -150 + 90 * level  # off=-150, 약=-60, 중=0(level 1.67), 강=60
    r = math.radians(ang - 90)
    d.line([(kx, ky), (kx + 42 * math.cos(r), ky + 42 * math.sin(r))], fill=(235, 48, 48, 255), width=14)


def pill(mm, text, size, bg, fg):
    k = ("pill", text, size, bg)
    if k not in _cache:
        ti = mm.text_img(text, "Black", size, fg)
        im = Image.new("RGBA", (ti.width + 64, ti.height + 34), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=bg)
        im.alpha_composite(ti, (32, 17))
        _cache[k] = im
    return _cache[k]


def frame(t, ctx):
    mm, spec, W, H = ctx["mm"], ctx["spec"], ctx["W"], ctx["H"]
    YEL, RED, WHITE = (255, 206, 40), mm.RED, mm.WHITE
    im = stovetop(W, H)
    sx = sy = 0

    # --- knob level / flame power timeline
    if t < 0.3:
        level, power = 0.0, 0.0
    elif t < 4.8:
        level, power = 1.0, 0.75 + (0.9 if t < 0.55 else 0.0) * (1 - (t - 0.3) / 0.25)
    elif t < 6.2:
        k = mm.ease((t - 4.8) / 0.6)
        level, power = 1.0 + k * 1.34, 0.75 + 0.65 * k
    else:
        level, power = 2.34, 1.4

    flames(im, power, t)
    grate(im)

    # click flash
    if 0.3 <= t < 0.5:
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(160 * (1 - (t - 0.3) / 0.2))))
        im.alpha_composite(fl)
        sx, sy = mm.shake(t, 0.3, 20, 0.25) if hasattr(mm, "shake") else (0, 0)

    # --- phase A: hook question (0.2 .. 2.7)
    if t < 2.9:
        a = 1 - mm.clamp((t - 2.6) / 0.3)
        s = mm.slam((t - 0.15) / 0.5)
        pc(mm, im, T(mm, "h0", "딱!", "Black", 120, YEL, 8, (0, 0, 0)), 880, 470, 1.0, -12,
                        mm.clamp((t - 0.3) / 0.1) * (1 - mm.clamp((t - 1.3) / 0.3)))
        pc(mm, im, T(mm, "h1", "프라이팬 코팅,", "Black", 92, WHITE, 6), W / 2, 190, s, 0, a)
        if t > 0.55:
            s2 = mm.slam((t - 0.55) / 0.5)
            pc(mm, im, T(mm, "h2", "벗겨졌나요?", "Black", 118, YEL, 7), W / 2, 315, s2, 0, a)

    # --- phase B: banner lands on the grate like a pan (2.7 .. 4.8)
    ban = ctx["banner"]
    if ban is not None and 2.6 <= t < 5.1:
        if "ban" not in _cache:
            bw = 900
            b = ban.resize((bw, int(bw * ban.height / ban.width)), Image.LANCZOS)
            card = Image.new("RGBA", (b.width + 24, b.height + 24), (0, 0, 0, 0))
            ImageDraw.Draw(card).rounded_rectangle([0, 0, card.width - 1, card.height - 1], radius=30, fill=WHITE)
            m = Image.new("L", b.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, b.width - 1, b.height - 1], radius=22, fill=255)
            card.paste(b, (12, 12), m)
            _cache["ban"] = card
        k = mm.ease((t - 2.7) / 0.45)
        out = mm.ease((t - 4.75) / 0.35)
        scale = 1.5 - 0.5 * k
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([CX - 430, CY - 170 + 40, CX + 430, CY + 230], fill=(0, 0, 0, int(120 * k)))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30)))
        pc(mm, im, _cache["ban"], CX - 1100 * out, CY, scale, -4 * (1 - k), k)
        if 3.0 < t < 3.25:
            sx, sy = mm.shake(t, 3.0, 16, 0.22)
        # steam lines
        for j in range(5):
            ph = (t * 0.9 + j * 0.21) % 1.0
            x = CX - 280 + j * 140
            y = CY - 250 - ph * 200
            pc(mm, im, T(mm, "st", "~", "Bold", 70, (230, 230, 235)), x + 12 * math.sin(t * 5 + j), y,
                            1.0, 90, 0.5 * (1 - ph) * k * (1 - out))
        a2 = mm.clamp((t - 3.1) / 0.3) * (1 - out)
        pc(mm, im, T(mm, "b1", "쿠팡 기획전 진행 중", "Black", 86, WHITE, 6), W / 2, 250, 1, 0, a2)
        pc(mm, im, T(mm, "b2", "화구 위에 뭐가 올라갈까요?", "Bold", 48, (210, 210, 215)), W / 2, 1110, 1, 0, a2)

    # event name chip stays from 2.9
    if t >= 2.9:
        ev = spec.get("event_name", "")
        if spec.get("event_period"):
            ev = ev + " · " + spec["event_period"]
        a = mm.clamp((t - 2.9) / 0.3)
        y = 108 if t < 3.1 else 108
        pc(mm, im, pill(mm, ev, 46, (235, 48, 48, 255), WHITE), W / 2, y, 1, 0, a)

    # --- phase C: pan drops on, flame to 강, price cooks (4.9 .. END)
    if t >= 4.9:
        k = mm.ease((t - 4.9) / 0.45)
        prod = ctx["product"]
        scale = 0.74 * (1.35 - 0.35 * k)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([CX - 300, CY - 260, CX + 320, CY + 330], fill=(0, 0, 0, int(140 * k)))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)))
        pc(mm, im, prod, CX, CY + 40 * (1 - k), scale, 0, k)
        if 5.3 < t < 5.55:
            sx, sy = mm.shake(t, 5.3, 18, 0.22)
        # 정가 strike
        if spec.get("from_price") and t >= 5.4:
            a = mm.clamp((t - 5.4) / 0.3)
            fp = T(mm, "fp", "정가 " + mm.won(spec["from_price"]) + "원", "Bold", 54, (190, 190, 196))
            pc(mm, im, fp, W / 2, 205, 1, 0, a)
            if t >= 5.8:
                p = mm.clamp((t - 5.8) / 0.25)
                d = ImageDraw.Draw(im)
                x0 = W / 2 - fp.width / 2
                d.line([(x0, 205), (x0 + fp.width * p, 205)], fill=RED, width=7)
        if t >= 6.2:
            s = mm.slam((t - 6.2) / 0.55)
            price = T(mm, "pr", spec["badge_price"], "Black", 132, YEL, 8)
            pc(mm, im, price, W / 2, 315, s)
            if 6.45 < t < 6.7:
                sx, sy = mm.shake(t, 6.45, 22, 0.22)
        if t >= 6.5:
            pc(mm, im, T(mm, "nm", spec["name"], "Bold", 42, (235, 235, 240)), W / 2, 418, 1, 0, mm.clamp((t - 6.5) / 0.3))
        if spec.get("stamp") and t >= 6.8:
            s = mm.slam((t - 6.8) / 0.45)
            pc(mm, im, pill(mm, spec["stamp"], 64, (235, 48, 48, 255), WHITE), 865, 520, s, 10)
        # stats
        stats = spec.get("stats") or []
        for i, st in enumerate(stats[:2]):
            t0 = 7.2 + 0.35 * i
            if t >= t0:
                a = mm.ease((t - t0) / 0.3)
                val = st[1] * a
                txt = f"{st[0]} {mm.won(val)}{st[2]}"
                pc(mm, im, pill(mm, txt, 44, (255, 255, 255, 235), (20, 20, 24)) if a >= 1 else
                                mm.text_img(txt, "Black", 44, WHITE, 4), 300 + 480 * i if len(stats) > 1 else W / 2,
                                1080, 1, 0, a)
        # CTA
        if t >= 7.9:
            pul = 1 + 0.05 * math.sin((t - 7.9) * 8)
            pc(mm, im, pill(mm, spec.get("cta", "첫 댓글에 링크") + " ↓", 56, YEL + (255,), (20, 20, 24)),
                            W / 2 + 60, 1215, pul * mm.slam((t - 7.9) / 0.4))

    knob(im, mm, t, level)
    return im, sx, sy
