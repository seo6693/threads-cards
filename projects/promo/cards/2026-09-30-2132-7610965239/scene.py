"""창고 셔터 롤업 -> 외풍 부는 창문 -> 커튼이 닫히며 바람 차단 -> 재고 꼬리표가 흔들리며 가격 공개."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

CONCEPT = {
    "name": "창고 셔터 롤업 + 외풍 차단 커튼",
    "idea": "덜컹거리는 창고 철제 셔터에 '창고 대방출' 스텐실이 쾅 찍히고 셔터가 말려 올라가며 행사 배너가 드러난 뒤, "
            "찬바람 줄이 새어드는 밤 창문에 실제 커튼이 양쪽에서 닫혀 바람을 끊고, 마지막에 크라프트 재고 꼬리표가 "
            "진자처럼 흔들리다 멈추며 가격이 박힌다",
}
END = 11.0
POSTER_AT = 9.0

T_ROLL, T_WIN, T_CLOSE, T_TAG = 1.25, 2.5, 4.3, 5.9

STEEL_A, STEEL_B = (58, 62, 70), (38, 41, 48)
STENCIL = (255, 204, 0)
KRAFT = (214, 178, 124)
INK = (40, 28, 18)
NIGHT = (14, 22, 44)


def _cache(ctx):
    c = ctx.get("_c")
    if c:
        return c
    mm, W, H = ctx["mm"], ctx["W"], ctx["H"]
    c = {}
    # corrugated shutter texture (taller than the screen so it can roll)
    sh = Image.new("RGBA", (W, H), STEEL_B)
    d = ImageDraw.Draw(sh)
    slat = 54
    for y in range(0, H, slat):
        d.rectangle([0, y, W, y + slat - 10], fill=STEEL_A)
        d.line([0, y + 4, W, y + 4], fill=(92, 97, 108), width=3)
        d.line([0, y + slat - 10, W, y + slat - 10], fill=(24, 26, 30), width=4)
    for x in (70, W - 70):
        for y in range(27, H, slat):
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(120, 124, 132))
    d.rectangle([0, H - 70, W, H], fill=(28, 30, 36))
    d.rounded_rectangle([W / 2 - 110, H - 58, W / 2 + 110, H - 30], radius=12, fill=(150, 154, 162))
    c["shutter"] = sh
    c["st1"] = mm.text_img("창고", "Black", 300, STENCIL, 10, (20, 20, 20))
    c["st2"] = mm.text_img("대방출", "Black", 250, STENCIL, 10, (20, 20, 20))
    c["st3"] = mm.text_img("문 열어요", "Black", 92, (240, 240, 240), 6, (20, 20, 20))
    ban = ctx["banner"]
    bw = 940
    c["banner_big"] = ban.resize((bw, int(bw * ban.height / ban.width)), Image.LANCZOS) if ban else None
    bw2 = 560
    c["banner_small"] = ban.resize((bw2, int(bw2 * ban.height / ban.width)), Image.LANCZOS) if ban else None
    spec = ctx["spec"]
    c["ev"] = mm.text_img(spec["event_name"], "Black", mm.fit_size(spec["event_name"], "Black", 70, 960), (255, 255, 255))
    if spec.get("event_period"):
        c["per"] = mm.text_img(spec["event_period"], "Bold", 48, (255, 214, 120))
    # curtain panel fabric from the product photo (the fabric area on the left of the photo)
    raw = ctx["product_raw"]
    fw, fh = raw.size
    fabric = raw.crop((int(fw * 0.29), 0, int(fw * 0.82), int(fh * 0.52))).resize((380, 360), Image.LANCZOS)
    panel = Image.new("RGBA", (380, 800))
    for k, yy in enumerate(range(0, 800, 350)):
        tile = fabric if k % 2 == 0 else fabric.transpose(Image.FLIP_TOP_BOTTOM)
        panel.paste(tile.convert("RGBA"), (0, yy))
    c["panel"] = panel
    c["q1"] = mm.text_img("창가만 유독", "Black", 96, (255, 255, 255), 6, (10, 14, 30))
    c["q2"] = mm.text_img("서늘하다면?", "Black", 96, (140, 210, 255), 6, (10, 14, 30))
    c["a1"] = mm.text_img("커튼으로 바람막이", "Black", 92, STENCIL, 6, (10, 14, 30))
    # price tag
    c["tag"] = _tag(ctx)
    c["prod"] = ctx["product"].resize((360, 360), Image.LANCZOS)
    c["name"] = mm.text_img(spec["name"], "Black", mm.fit_size(spec["name"], "Black", 58, 960), (255, 255, 255))
    c["cta"] = _pill(mm, spec.get("cta", "첫 댓글에 링크"), ctx["P"]["a"])
    c["stamp"] = _stamp(mm, spec.get("stamp", ""))
    rnd = random.Random(7)
    c["wind"] = [(rnd.uniform(0, 1), rnd.uniform(300, 960), rnd.uniform(0.6, 1.4), rnd.uniform(0, 6.28)) for _ in range(26)]
    ctx["_c"] = c
    return c


def _pill(mm, text, col):
    tx = mm.text_img(text, "Black", 50, (20, 20, 20))
    im = Image.new("RGBA", (tx.width + 90, 76), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, 75], radius=38, fill=col)
    im.paste(tx, ((im.width - tx.width) // 2, (76 - tx.height) // 2), tx)
    return im


def _stamp(mm, text):
    s = 260
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([6, 6, s - 6, s - 6], outline=(214, 30, 40), width=12)
    d.ellipse([26, 26, s - 26, s - 26], outline=(214, 30, 40), width=4)
    tx = mm.text_img(text, "Black", 60, (214, 30, 40))
    im.paste(tx, ((s - tx.width) // 2, (s - tx.height) // 2), tx)
    return im.rotate(-14, resample=Image.BICUBIC, expand=True)


def _tag(ctx):
    mm, spec = ctx["mm"], ctx["spec"]
    tw, th = 900, 400
    im = Image.new("RGBA", (tw, th + 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # string loop at the top
    d.line([tw / 2, 0, tw / 2, 70], fill=(235, 235, 235), width=6)
    d.polygon([(0, 150), (70, 90), (tw - 70, 90), (tw, 150), (tw, 90 + th), (0, 90 + th)], fill=KRAFT)
    d.ellipse([tw / 2 - 26, 104, tw / 2 + 26, 156], fill=(40, 30, 22))
    d.ellipse([tw / 2 - 16, 114, tw / 2 + 16, 146], fill=(235, 235, 235))
    for i in range(0, tw, 6):  # subtle paper grain
        d.line([i, 170, i + 3, 90 + th], fill=(206, 170, 116), width=1)
    lab = mm.text_img(spec.get("price_label", "행사가"), "Black", 44, (255, 255, 255))
    lx, ly = 60, 180
    d.rounded_rectangle([lx, ly, lx + lab.width + 36, ly + 64], radius=14, fill=(214, 30, 40))
    im.paste(lab, (lx + 18, ly + (64 - lab.height) // 2), lab)
    if spec.get("from_price"):
        old = mm.text_img(mm.won(spec["from_price"]) + "원", "Bold", 50, (110, 86, 60))
        ox, oy = lx + lab.width + 70, ly + (64 - old.height) // 2
        im.paste(old, (ox, oy), old)
        ImageDraw.Draw(im).line([ox, oy + old.height / 2, ox + old.width, oy + old.height / 2], fill=(214, 30, 40), width=6)
    big = mm.text_img(spec["badge_price"], "Black", 140, INK)
    im.paste(big, (54, 258), big)
    st = spec.get("stats") or []
    line = "  ·  ".join(f"{a} {mm.won(b)}{u}" for a, b, u in st)
    if line:
        sl = mm.text_img(line, "Bold", 42, (70, 50, 32))
        im.paste(sl, (62, 90 + th - sl.height - 22), sl)
    return im


def _wind(im, c, t, strength):
    if strength <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (ph, y0, sp, wv) in c["wind"]:
        x = ((t * sp * 0.9 + ph) % 1.0) * 1400 - 250
        pts = [(x + k * 18, y0 + 14 * math.sin(k * 0.35 + wv + t * 5)) for k in range(12)]
        d.line(pts, fill=(200, 230, 255, int(170 * strength)), width=5)
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    im.alpha_composite(layer)


def _thermo(d, level, x=985, top=330, bot=930):
    d.rounded_rectangle([x - 22, top, x + 22, bot], radius=22, fill=(235, 240, 250))
    d.ellipse([x - 42, bot - 30, x + 42, bot + 54], fill=(235, 240, 250))
    col = (60, 150, 255) if level < 0.5 else (240, 70, 60)
    y = bot - 10 - (bot - top - 40) * level
    d.rounded_rectangle([x - 11, y, x + 11, bot], radius=11, fill=col)
    d.ellipse([x - 30, bot - 18, x + 30, bot + 42], fill=col)


def frame(t, ctx):
    mm, W, H = ctx["mm"], ctx["W"], ctx["H"]
    c = _cache(ctx)
    ease, clamp = mm.ease, mm.clamp
    sx = sy = 0

    if t < T_WIN:
        # ---------- warehouse: shutter + banner ----------
        im = Image.new("RGBA", (W, H), (22, 20, 18, 255))
        d = ImageDraw.Draw(im)
        # spotlight cone
        cone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cone).polygon([(W / 2 - 90, 0), (W / 2 + 90, 0), (W + 120, H), (-120, H)], fill=(255, 230, 170, 40))
        im.alpha_composite(cone)
        # shelves with boxes
        for row, y in enumerate((1000, 1180)):
            d.rectangle([40, y, W - 40, y + 14], fill=(90, 70, 50))
            for k in range(6):
                bx = 70 + k * 160 + (row * 60)
                if bx > W - 180:
                    continue
                d.rectangle([bx, y - 120, bx + 130, y], fill=(176, 132, 84))
                d.line([bx + 65, y - 120, bx + 65, y - 70], fill=(150, 110, 68), width=10)
        if c["banner_big"] is not None:
            b = c["banner_big"]
            k = 0.92 + 0.08 * ease((t - T_ROLL) / 0.9)
            mm.paste_center(im, b, W / 2, 470, k)
        mm.paste_center(im, c["ev"].copy(), W / 2, 790, 1, 0, clamp((t - T_ROLL - 0.3) / 0.3))
        if c.get("per"):
            mm.paste_center(im, c["per"].copy(), W / 2, 870, 1, 0, clamp((t - T_ROLL - 0.4) / 0.3))
        # the shutter on top, rolling up
        roll = ease((t - T_ROLL) / 1.05) if t > T_ROLL else 0.0
        off = int(-H * roll)
        sh = c["shutter"].copy()
        if t < T_ROLL + 0.2:
            s = mm.slam(t / 0.35)
            mm.paste_center(sh, c["st1"], W / 2, 420, s, -4)
            if t > 0.18:
                mm.paste_center(sh, c["st2"], W / 2, 740, mm.slam((t - 0.18) / 0.35), 3)
            if t > 0.55:
                mm.paste_center(sh, c["st3"].copy(), W / 2, 1010, 1, 0, clamp((t - 0.55) / 0.2))
            # padlock that snaps open
            ld = ImageDraw.Draw(sh)
            lx, ly = W / 2, 1180
            ld.rounded_rectangle([lx - 60, ly - 40, lx + 60, ly + 60], radius=14, fill=(200, 160, 40))
            lift = 0 if t < 0.8 else min(40, (t - 0.8) * 260)
            ld.arc([lx - 40, ly - 110 - lift, lx + 40, ly - 10 - lift], 180, 360, fill=(170, 172, 180), width=14)
            ld.line([lx + 40, ly - 60 - lift, lx + 40, ly - 30 - (lift and lift)], fill=(170, 172, 180), width=14)
            ld.line([lx - 40, ly - 60 - lift, lx - 40, ly - 30], fill=(170, 172, 180), width=14)
        im.paste(sh, (0, off), sh)
        if t < 0.55:
            sx, sy = mm.shake(t, 0.0, 22, 0.55)
        elif T_ROLL <= t < T_ROLL + 0.2:
            sx, sy = mm.shake(t, T_ROLL, 12, 0.2)
        return im, sx, sy

    if t < T_TAG:
        # ---------- window at night: draft, then curtains close ----------
        im = Image.new("RGBA", (W, H), NIGHT + (255,))
        d = ImageDraw.Draw(im)
        wx0, wy0, wx1, wy1 = 110, 300, 910, 1100
        d.rectangle([wx0, wy0, wx1, wy1], fill=(30, 48, 86))
        for i in range(40):  # stars / city lights
            rx = wx0 + (i * 197) % (wx1 - wx0)
            ry = wy0 + (i * 131) % (wy1 - wy0 - 200)
            d.ellipse([rx, ry, rx + 5, ry + 5], fill=(230, 235, 255))
        d.rectangle([wx0, wy0, wx1, wy1], outline=(210, 214, 224), width=22)
        d.line([(wx0 + wx1) / 2, wy0, (wx0 + wx1) / 2, wy1], fill=(210, 214, 224), width=16)
        d.rectangle([wx0 - 40, wy1, wx1 + 40, wy1 + 34], fill=(190, 194, 204))
        d.rectangle([wx0 - 50, wy0 - 60, wx1 + 50, wy0 - 44], fill=(170, 150, 120))  # rail
        close = ease((t - T_CLOSE) / 0.9) if t > T_CLOSE else 0.0
        wind = 1.0 - close
        _wind(im, c, t, wind if t > T_WIN + 0.15 else clamp((t - T_WIN) / 0.15))
        d = ImageDraw.Draw(im)
        level = 0.75 - 0.5 * ease((t - T_WIN) / 1.4) + 0.55 * close
        _thermo(d, clamp(level))
        # curtains
        p = c["panel"]
        half = (wx1 - wx0 + 100) / 2
        lx = int(wx0 - 50 - p.width + (half + 10) * close + 40 * (1 - close) * 0 + 40)
        rx = int(wx1 + 50 - (half + 10) * close - 40)
        sway = int(8 * math.sin(t * 7) * wind)
        im.paste(p, (lx + sway, wy0 - 44), p)
        im.paste(p.transpose(Image.FLIP_LEFT_RIGHT), (rx - sway, wy0 - 44), p.transpose(Image.FLIP_LEFT_RIGHT))
        # captions (top area, below the safe margin)
        if t < T_CLOSE + 0.3:
            a = clamp((t - T_WIN) / 0.25)
            mm.paste_center(im, c["q1"].copy(), W / 2, 110, 1, 0, a)
            mm.paste_center(im, c["q2"].copy(), W / 2, 220, 1, 0, clamp((t - T_WIN - 0.3) / 0.25))
        else:
            mm.paste_center(im, c["a1"], W / 2, 170, min(1.12, mm.slam((t - T_CLOSE - 0.3) / 0.4)))
        if c["banner_small"] is not None:
            b = c["banner_small"].resize((420, int(420 * c["banner_small"].height / c["banner_small"].width)))
            mm.paste_center(im, b.copy(), W / 2, 1230, 1, 0, 0.95)
        return im

    # ---------- inventory tag swings in with the price ----------
    im = Image.new("RGBA", (W, H), (26, 24, 30, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 54):  # faint shutter lines behind: we are back in the warehouse
        d.line([0, y, W, y], fill=(40, 38, 46), width=8)
    u = t - T_TAG
    if c["banner_small"] is not None:
        mm.paste_center(im, c["banner_small"].copy(), W / 2, 36 + c["banner_small"].height / 2 + 10, 1, 0, clamp(u / 0.3))
    ptop = 36 + (c["banner_small"].height if c["banner_small"] is not None else 0) + 24
    pk = mm.slam(u / 0.45)
    zoom = 1 + 0.03 * clamp((u - 1) / 4)
    mm.paste_center(im, c["prod"], W / 2, ptop + 180, pk * zoom)
    # tag: pendulum swing that settles
    if u > 0.35:
        v = u - 0.35
        drop = ease(v / 0.35)
        ang = 16 * math.exp(-2.4 * v) * math.cos(v * 9)
        tag = c["tag"]
        cy = (ptop + 360 + 10) + tag.height / 2 - 40 + (1 - drop) * -500
        mm.paste_center(im, tag, W / 2, cy, 1, ang)
        if u > 1.6 and c["stamp"] is not None:
            mm.paste_center(im, c["stamp"], W / 2 + 250, ptop + 250, mm.slam((u - 1.6) / 0.35))
            if u < 1.85:
                sx, sy = mm.shake(u, 1.6, 14, 0.2)
    mm.paste_center(im, c["name"].copy(), W / 2, H - 160, 1, 0, clamp((u - 1.0) / 0.3))
    if u > 1.3:
        pulse = 1 + 0.04 * math.sin((u - 1.3) * 6)
        mm.paste_center(im, c["cta"], W / 2, H - 78, pulse)
    return im, sx, sy
