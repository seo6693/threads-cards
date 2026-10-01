"""숟가락 돌리기 룰렛 — a real spoon-spinning game on a dinner table decides 'replace the spoons?'"""
import math

from PIL import Image, ImageDraw, ImageFilter

CONCEPT = {
    "name": "숟가락 돌리기 결정 룰렛",
    "idea": "나무 식탁 한가운데서 큰 숟가락이 팽이처럼 빙글빙글 돌고 사방 접시에 '아직 멀쩡해/다음 달에/이번엔 바꾸기/몰라 그냥 써'가 적혀 있다가, "
            "숟가락이 '이번엔 바꾸기'에 탁 멈추며 도장이 찍히고, 식탁보가 걷히듯 행사 배너가 올라온 뒤 실제 수저세트와 가격이 차려진다",
}
END = 10.0
POSTER_AT = 8.2

CX, CY = 540, 720
TABLE = (214, 178, 136)
TABLE_D = (190, 150, 108)
INK = (46, 34, 26)
CREAM = (252, 246, 236)
OPTIONS = [(0, "아직 멀쩡해"), (90, "다음 달에"), (180, "이번엔 바꾸기"), (270, "몰라 그냥 써")]
TARGET = 180
SPIN_END = 2.6


def _table():
    im = Image.new("RGBA", (1080, 1350), TABLE + (255,))
    d = ImageDraw.Draw(im)
    for k in range(0, 1350, 150):  # wood planks
        d.line([(0, k), (1080, k)], fill=TABLE_D + (255,), width=5)
        for j in range(6):
            y = k + 25 + j * 20
            d.arc([-200 + j * 90, y - 30, 1300 - j * 70, y + 30], 180, 360, fill=(204, 166, 124, 255), width=2)
    return im


_BG = None


def _spoon():
    sp = Image.new("RGBA", (220, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    # handle (bottom) + bowl (top): spoon points "up" = bowl direction
    d.rounded_rectangle([92, 250, 128, 740], radius=18, fill=(150, 150, 158, 255))
    d.rounded_rectangle([98, 256, 112, 736], radius=8, fill=(220, 220, 228, 255))
    d.ellipse([20, 10, 200, 300], fill=(160, 160, 168, 255))
    d.ellipse([36, 26, 184, 282], fill=(205, 205, 214, 255))
    d.ellipse([60, 50, 120, 150], fill=(245, 245, 250, 255))
    return sp


_SPOON = None


def heading(t):
    x = min(1.0, t / SPIN_END)
    total = 360 * 6 + TARGET
    return total * (1 - (1 - x) ** 3)


def plate(label, hot, mm, scale=1.0):
    w, h = 300, 130
    p = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    d.ellipse([10, 16, w + 10, h + 16], fill=(0, 0, 0, 50))
    d.ellipse([0, 0, w, h], fill=(255, 92, 70, 255) if hot else CREAM + (255,), outline=INK, width=5)
    d.ellipse([22, 14, w - 22, h - 14], outline=(255, 255, 255, 160) if hot else (220, 205, 185, 255), width=3)
    size = mm.fit_size(label, "Black", 50, w - 50)
    mm.paste_center(p, mm.text_img(label, "Black", size, mm.WHITE if hot else INK), w / 2, h / 2)
    return p


def pill(text, mm, fg, bg, size=46, pad=34):
    tx = mm.text_img(text, "Black", size, fg)
    p = Image.new("RGBA", (tx.width + pad * 2, tx.height + 30), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=p.height // 2, fill=bg)
    p.paste(tx, (pad, 15), tx)
    return p


def frame(t, ctx):
    global _BG, _SPOON
    mm, spec = ctx["mm"], ctx["spec"]
    if _BG is None:
        _BG = _table()
        _SPOON = _spoon()
    im = _BG.copy()
    sx = sy = 0

    # ---------- 1. spinning spoon decides (0 - 2.9s)
    if t < 3.3:
        fade = 1 - mm.clamp((t - 2.9) / 0.4)
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        q = mm.text_img("수저, 바꿀 때 됐나?", "Black", 92, INK)
        mm.paste_center(layer, q, 540, 150, 1.0 + 0.04 * math.sin(t * 9) * (t < SPIN_END))
        sub = "숟가락이 정해줌" if t < SPIN_END else "결론 나왔습니다"
        mm.paste_center(layer, mm.text_img(sub, "Bold", 50, (120, 70, 40)), 540, 250)
        h = heading(t)
        for ang, label in OPTIONS:
            r = math.radians(ang)
            px, py = CX + 360 * math.sin(r), CY - 360 * math.cos(r)
            if ang == 90:
                px -= 40
            if ang == 270:
                px += 40
            hot = ang == TARGET and t >= SPIN_END
            pulse = 1 + (0.12 * math.sin((t - SPIN_END) * 14) * math.exp(-(t - SPIN_END) * 3) if hot else 0)
            mm.paste_center(layer, plate(label, hot, mm), px, py, pulse)
        # motion-blur ghosts while fast
        speed = (1 - min(1.0, t / SPIN_END)) ** 2
        for g in range(4 if speed > 0.05 else 0):
            mm.paste_center(layer, _SPOON, CX, CY, 0.78, -(h - g * 18 * speed * 3), 0.18)
        mm.paste_center(layer, _SPOON, CX, CY, 0.78, -h)
        d = ImageDraw.Draw(layer)
        d.ellipse([CX - 14, CY - 14, CX + 14, CY + 14], fill=INK)
        if t >= SPIN_END:  # stamp
            k = (t - SPIN_END) / 0.25
            st = pill("결정!", mm, mm.WHITE, (220, 40, 40, 255), size=64)
            mm.paste_center(layer, st, 760, 1230, mm.slam(k) if k < 1 else 1.0, -8)
            sx, sy = mm.shake(t, SPIN_END, 22, 0.3)
        if fade < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * fade)))
        im.alpha_composite(layer)

    # ---------- 2. tablecloth pulls up revealing the event banner (2.9 - 5.4s)
    if 2.9 <= t < 5.8:
        k = mm.ease((t - 2.9) / 0.6)
        out = mm.ease((t - 5.3) / 0.5)
        cloth = Image.new("RGBA", (1080, 1350), CREAM + (255,))
        cd = ImageDraw.Draw(cloth)
        for x in range(0, 1080, 90):  # gingham
            cd.rectangle([x, 0, x + 44, 1350], fill=(244, 222, 214, 255))
        for y in range(0, 1350, 90):
            cd.rectangle([0, y, 1080, y + 44], fill=(240, 212, 204, 180))
        top = int(1350 * (1 - k) - 1350 * out)
        im.alpha_composite(cloth, (0, max(-1350, top)))
        y0 = top
        mm.paste_center(im, pill("쿠팡 기획전", mm, mm.WHITE, (220, 40, 40, 255), 48), 540, y0 + 230)
        ev = spec["event_name"]
        mm.paste_center(im, mm.text_img(ev, "Black", mm.fit_size(ev, "Black", 96, 960), INK), 540, y0 + 360)
        if spec.get("event_period"):
            mm.paste_center(im, mm.text_img(spec["event_period"], "Bold", 48, (110, 80, 60)), 540, y0 + 450)
        b = ctx["banner"]
        if b is not None:
            bw = 940
            bb = b.resize((bw, int(bw * b.height / b.width)), Image.LANCZOS)
            card = Image.new("RGBA", (bb.width + 24, bb.height + 24), (255, 255, 255, 255))
            card.paste(bb, (12, 12))
            sh = Image.new("RGBA", (card.width + 60, card.height + 60), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle([30, 40, card.width + 30, card.height + 40], 20, fill=(0, 0, 0, 90))
            sh = sh.filter(ImageFilter.GaussianBlur(14))
            mm.paste_center(im, sh, 540, y0 + 800)
            mm.paste_center(im, card, 540, y0 + 780, 1.0, -2 + 2 * k)
        mm.paste_center(im, mm.text_img("여기서 하나 골라봤어요", "Bold", 52, (120, 70, 40)), 540, y0 + 1120)

    # ---------- 3. the table is set: product + price (5.4 - 10s)
    if t >= 5.4:
        a = mm.ease((t - 5.4) / 0.5)
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        hd = pill(spec["event_name"], mm, mm.WHITE, INK + (255,), 42)
        mm.paste_center(layer, hd, 540, 110)
        # placemat
        ImageDraw.Draw(layer).rounded_rectangle([110, 190, 970, 900], radius=60, fill=CREAM + (255,), outline=INK, width=6)
        drop = 1 - mm.ease((t - 5.6) / 0.6)
        mm.paste_center(layer, ctx["product"], 540, 545 - 260 * drop, 0.82, 4 * drop)
        name = spec["name"]
        mm.paste_center(layer, mm.text_img(name, "Black", mm.fit_size(name, "Black", 54, 980), INK), 540, 960)
        if t > 6.3:
            k = mm.ease((t - 6.3) / 0.4)
            old = mm.text_img(spec["from_label"], "Bold", 60, (120, 100, 90))
            ImageDraw.Draw(old).line([(0, old.height // 2 + 2), (old.width, old.height // 2 + 2)], fill=(200, 40, 40), width=6)
            mm.paste_center(layer, old, 225, 1075, 1, 0, k)
            mm.paste_center(layer, mm.text_img("→", "Black", 70, INK), 435, 1072, 1, 0, k)
        if t > 6.8:
            k = (t - 6.8) / 0.35
            new = mm.text_img(spec["badge_price"], "Black", 112, (215, 35, 35), 6, mm.WHITE)
            mm.paste_center(layer, new, 772, 1068, mm.slam(k) if k < 1 else 1.0)
        if t > 7.5:
            k = mm.ease((t - 7.5) / 0.4)
            mm.paste_center(layer, mm.text_img(spec["stat_line"], "Bold", 44, INK), 540, 1170, 1, 0, k)
        if t > 8.0:
            k = mm.ease((t - 8.0) / 0.4)
            c = pill(spec["cta"], mm, mm.WHITE, (215, 35, 35, 255), 52)
            mm.paste_center(layer, c, 540, 1262 + 30 * (1 - k), 1 + 0.04 * math.sin(t * 8), 0, k)
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        im.alpha_composite(layer)
    return im, sx, sy
