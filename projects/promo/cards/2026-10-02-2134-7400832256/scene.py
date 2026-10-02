"""Dusty floor: finger-written '닦아줘' in a thick dust layer, then one mop pass wipes the whole
screen clean top-to-bottom and the event + product are what was hiding underneath."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

CONCEPT = {
    "name": "먼지 바닥 손글씨 + 밀대 한 번에 싹",
    "idea": "화면 전체가 회색 먼지로 덮여 있고 손가락으로 '닦아줘'가 써지는 첫 장면(더러운 차 유리 낙서 느낌), "
            "밀대 헤드가 위에서 아래로 한 번 쓸고 내려가며 먼지 덩어리를 밀어내면 깨끗한 타일 위에 행사 배너·상품·가격이 드러난다",
}
END = 9.5
POSTER_AT = 6.6

_C = {}
TILE = (236, 246, 244)
GROUT = (210, 228, 226)
INK = (20, 40, 60)
NAVY = (34, 52, 92)
ACC = (0, 168, 150)


def _tiles(W, H):
    im = Image.new("RGBA", (W, H), TILE + (255,))
    d = ImageDraw.Draw(im)
    s = 135
    for x in range(0, W + 1, s):
        d.line([(x, 0), (x, H)], fill=GROUT, width=4)
    for y in range(0, H + 1, s):
        d.line([(0, y), (W, y)], fill=GROUT, width=4)
    return im


def _dust(W, H):
    rnd = random.Random(7)
    base = Image.new("RGBA", (W, H), (118, 112, 104, 246))
    d = ImageDraw.Draw(base)
    for _ in range(9000):  # specks
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.choice([1, 1, 2, 2, 3])
        c = rnd.randint(80, 170)
        d.ellipse([x, y, x + r, y + r], fill=(c, c - 4, c - 10, 255))
    for _ in range(70):  # hairs
        x, y = rnd.randrange(W), rnd.randrange(H)
        pts = []
        a = rnd.random() * 6.28
        for k in range(14):
            a += rnd.uniform(-0.5, 0.5)
            x += 9 * math.cos(a)
            y += 9 * math.sin(a)
            pts.append((x, y))
        d.line(pts, fill=(52, 46, 42, 255), width=2)
    for _ in range(40):  # fluffy clumps
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.randint(8, 22)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 144, 136, 255))
    return base.filter(ImageFilter.GaussianBlur(0.8))


def _writing(mm, W):
    """'닦아줘' as a finger-trace mask (white = wiped), one syllable at a time."""
    full = mm.text_img("닦아줘", "Black", 300, (255, 255, 255, 255))
    out, x = [], int(W / 2 - full.width / 2)
    for ch in "닦아줘":
        g = mm.text_img(ch, "Black", 300, (255, 255, 255, 255))
        out.append((g.getchannel("A").filter(ImageFilter.GaussianBlur(3)), x))
        x += g.width - 8
    return out


def _mop(W):
    im = Image.new("RGBA", (W + 160, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 70, W + 120, 190], radius=30, fill=(200, 204, 210, 255))
    d.rounded_rectangle([60, 60, W + 100, 170], radius=28, fill=NAVY + (255,))
    d.line([(100, 115), (W + 60, 115)], fill=(58, 80, 124, 255), width=6)
    cx = (W + 160) // 2
    d.rounded_rectangle([cx - 46, 80, cx + 46, 150], radius=18, fill=(26, 40, 74, 255))
    d.ellipse([cx - 18, 97, cx + 18, 133], fill=(225, 228, 235, 255))
    return im


def _put(mm, base, im, cx, cy, scale=1.0, angle=0.0, alpha=1.0):
    """paste_center on a copy, so cached layers never lose alpha."""
    mm.paste_center(base, im.copy(), cx, cy, scale, angle, alpha)


def _setup(ctx):
    if _C:
        return
    mm, W, H = ctx["mm"], ctx["W"], ctx["H"]
    _C["tiles"] = _tiles(W, H)
    _C["dust"] = _dust(W, H)
    _C["write"] = _writing(mm, W)
    _C["mop"] = _mop(W)
    b = ctx["banner"]
    _C["banner"] = b
    sp = ctx["spec"]
    _C["kicker"] = mm.text_img("쿠팡 기획전 진행 중", "Bold", 42, ACC)
    ev = sp.get("event_name", "")
    _C["event"] = mm.text_img(ev, "Black", mm.fit_size(ev, "Black", 78, 960), INK)
    per = sp.get("event_period", "")
    _C["period"] = mm.text_img(per, "Bold", 40, (80, 96, 110)) if per else None
    _C["from"] = mm.text_img(f"{mm.won(sp['from_price'])}원", "Bold", 52, (130, 140, 150))
    _C["to"] = mm.text_img(sp["badge_price"], "Black", 120, (225, 40, 60))
    _C["name"] = mm.text_img(sp["name"], "Bold", mm.fit_size(sp["name"], "Bold", 44, 960), INK)
    st = sp.get("stats", [])
    line = "  ·  ".join(f"{a} {b:,}{c}" for a, b, c in st)
    _C["stats"] = mm.text_img(line, "Bold", mm.fit_size(line, "Bold", 42, 980), (40, 70, 90))
    _C["cta"] = mm.text_img(sp.get("cta", "첫 댓글에 링크"), "Black", 64, (255, 255, 255))
    _C["stamp_txt"] = mm.text_img(sp.get("stamp", ""), "Black", 70, (255, 255, 255))


def _banner_at(im, mm, cx, cy, w, alpha=1.0):
    b = _C["banner"]
    if b is None:
        return
    h = int(w * b.height / b.width)
    bb = b.resize((int(w), h), Image.LANCZOS)
    card = Image.new("RGBA", (bb.width + 16, bb.height + 16), (255, 255, 255, 255))
    m = Image.new("L", card.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, card.width - 1, card.height - 1], radius=26, fill=255)
    card.paste(bb, (8, 8))
    card.putalpha(m)
    _put(mm, im, card, cx, cy, 1.0, 0, alpha)


def _clean_scene(t, ctx):
    mm, W, H = ctx["mm"], ctx["W"], ctx["H"]
    im = _C["tiles"].copy()
    if t < 1.4:
        return im
    d = ImageDraw.Draw(im)
    _put(mm, im, _C["kicker"], W / 2, 96)
    _put(mm, im, _C["event"], W / 2, 168)
    if _C["period"] is not None:
        _put(mm, im, _C["period"], W / 2, 232)
    # banner: big first, then moves up and shrinks
    k = mm.ease((t - 3.5) / 0.7)
    bw = 900 - 360 * k
    by = 600 - 215 * k
    _banner_at(im, mm, W / 2, by, bw)
    if t > 3.8:  # product rises
        a = mm.ease((t - 3.8) / 0.6)
        _put(mm, im, ctx["product"], W / 2, 800 + 120 * (1 - a), 0.58 * (0.8 + 0.2 * a), 0, a)
    if t > 4.5:
        a = mm.ease((t - 4.5) / 0.4)
        fr = _C["from"]
        _put(mm, im, fr, W / 2, 1065, 1, 0, a)
        if t > 4.8:
            lk = mm.ease((t - 4.8) / 0.25)
            x0 = W / 2 - fr.width / 2
            d.line([(x0, 1068), (x0 + fr.width * lk, 1068)], fill=(225, 40, 60), width=6)
    if t > 5.0:
        _put(mm, im, _C["to"], W / 2, 1155, mm.slam((t - 5.0) / 0.45))
    if t > 5.3 and _C["stamp_txt"].width > 10:  # discount stamp on the product corner
        s = mm.slam((t - 5.3) / 0.4)
        st = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
        ImageDraw.Draw(st).ellipse([4, 4, 216, 216], fill=(225, 40, 60, 255), outline=(255, 255, 255, 255), width=8)
        mm.paste_center(st, _C["stamp_txt"], 110, 110)
        _put(mm, im, st, 770, 610, 0.8 * s, -14)
    if 5.8 < t < 7.9:
        a = mm.ease((t - 5.8) / 0.4) * (1 - mm.ease((t - 7.6) / 0.3))
        _put(mm, im, _C["stats"], W / 2, 1262, 1, 0, a)
    if t > 7.8:
        a = mm.ease((t - 7.8) / 0.35)
        pulse = 1 + 0.04 * math.sin((t - 7.8) * 7)
        bar = Image.new("RGBA", (_C["cta"].width + 120, 104), (0, 0, 0, 0))
        ImageDraw.Draw(bar).rounded_rectangle([0, 0, bar.width - 1, 103], radius=52, fill=ACC + (255,))
        mm.paste_center(bar, _C["cta"], bar.width / 2, 52)
        _put(mm, im, bar, W / 2, 1258, pulse, 0, a)
    return im


def frame(t, ctx):
    _setup(ctx)
    mm, W, H = ctx["mm"], ctx["W"], ctx["H"]
    im = _clean_scene(t, ctx)
    sweep0, sweep1 = 1.45, 2.9
    if t < sweep1 + 0.05:
        # dust alpha mask: full, minus finger writing, minus area the mop already passed
        mask = _C["dust"].getchannel("A").copy()
        hole = Image.new("L", (W, H), 0)
        for i, (g, gx) in enumerate(_C["write"]):
            r = mm.clamp((t + 0.25 - i * 0.38) / 0.3)
            if r <= 0:
                continue
            cut = g.crop((0, 0, g.width, max(1, int(g.height * r))))  # traced top-down
            hole.paste(cut, (gx, 470))
        mask = Image.composite(Image.new("L", (W, H), 40), mask, hole)
        mop_y = -140 + (H + 280) * mm.clamp((t - sweep0) / (sweep1 - sweep0)) if t > sweep0 else -400
        if mop_y > 0:
            ImageDraw.Draw(mask).rectangle([0, 0, W, int(mop_y)], fill=0)
        dust = _C["dust"].copy()
        dust.putalpha(mask)
        im.alpha_composite(dust)
        if t < sweep0:  # small caption in the dust, under the writing
            a = mm.ease((t - 0.7) / 0.4)
            cap = mm.text_img("바닥이 보내는 신호", "Bold", 54, (235, 230, 220))
            _put(mm, im, cap, W / 2, 900, 1, 0, a)
        if mop_y > -200:
            d = ImageDraw.Draw(im)
            # pushed dust pile in front of the head
            rnd = random.Random(int(t * 30))
            for _ in range(120):
                x = rnd.randrange(0, W)
                y = mop_y + 70 + rnd.randrange(0, 40)
                r = rnd.randint(4, 14)
                c = rnd.randint(95, 150)
                d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c - 5, c - 10, 255))
            # handle toward the viewer
            wob = 18 * math.sin(t * 9)
            d.line([(W / 2 + wob, mop_y + 20), (W / 2 + 120 + wob, H + 40)], fill=(200, 205, 214), width=34)
            d.line([(W / 2 + wob, mop_y + 20), (W / 2 + 120 + wob, H + 40)], fill=(240, 242, 246), width=12)
            _put(mm, im, _C["mop"], W / 2 + wob, mop_y - 30)
    elif t < 3.6:  # sparkle right after the wipe
        d = ImageDraw.Draw(im)
        rnd = random.Random(3)
        for _ in range(14):
            x, y = rnd.randrange(80, W - 80), rnd.randrange(260, 1200)
            k = math.sin(mm.clamp((t - sweep1 - rnd.random() * 0.3) / 0.4) * math.pi)
            r = 26 * k
            if r > 1:
                d.polygon([(x, y - r), (x + r / 4, y), (x, y + r), (x - r / 4, y)], fill=(255, 255, 255))
                d.polygon([(x - r, y), (x, y + r / 4), (x + r, y), (x, y - r / 4)], fill=(255, 255, 255))
    return im
