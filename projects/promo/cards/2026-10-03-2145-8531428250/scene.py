"""Breaker panel blackout: the screen opens in a dark room with a spark and a tripped breaker panel,
four breaker toggles snap up one by one (each one a word of the event), the lights come on and the
lit wall shows the event banner, the power strip and its price."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

CONCEPT = {
    "name": "두꺼비집 차단기 복구 + 불 켜지는 방",
    "idea": "'펑' 스파크와 함께 깜깜한 방에서 손전등 원 안에 내려간 분전반(두꺼비집)이 보이고 '또 내려갔어?'가 떠는 첫 장면, "
            "차단기 레버 4개가 '공9위크·SALE·멀티탭·전원' 순서로 딸깍딸깍 올라가며 초록 불이 켜지고, 마지막 레버에 방 조명이 확 들어오면서 "
            "밝아진 벽에 행사 배너·멀티탭·가격이 걸린다",
}
END = 10.5
POSTER_AT = 7.2

_C = {}
WALL = (246, 241, 230)
METAL = (196, 200, 206)
METAL_D = (120, 126, 134)
INK = (24, 28, 36)
GREEN = (40, 210, 110)
AMBER = (255, 176, 32)
FLIP_T = [1.3, 1.85, 2.4, 2.95]
LIGHT_T = 3.25


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _back(x):
    """overshoot ease for snapping things in"""
    x = max(0.0, min(1.0, x))
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _panel(mm, flips):
    """Breaker box 760x620, toggles up/down by flips[i] in 0..1."""
    w, h = 820, 640
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=36, fill=METAL, outline=METAL_D, width=8)
    d.rounded_rectangle([40, 40, w - 41, 120], radius=18, fill=(70, 76, 86))
    t = mm.text_img("분전반  MAIN", "Black", 44, (230, 232, 236))
    im.paste(t, (w // 2 - t.width // 2, 80 - t.height // 2), t)
    labels = ["공9위크", "SALE", "멀티탭", "전원"]
    slot_w = 170
    x0 = (w - slot_w * 4) // 2
    for i in range(4):
        cx = x0 + slot_w * i + slot_w // 2
        # breaker body
        d.rounded_rectangle([cx - 66, 160, cx + 66, 600], radius=16, fill=(236, 238, 242), outline=METAL_D, width=4)
        d.rounded_rectangle([cx - 30, 230, cx + 30, 470], radius=12, fill=(60, 64, 72))
        k = flips[i]
        # lever: down y=420, up y=280
        ly = 420 - 140 * k
        col = (240, 70, 60) if k < 0.5 else (30, 140, 255)
        d.rounded_rectangle([cx - 40, ly - 48, cx + 40, ly + 48], radius=14, fill=col, outline=INK, width=4)
        # LED
        on = k >= 0.99
        d.ellipse([cx - 16, 182, cx + 16, 214], fill=GREEN if on else (90, 30, 30), outline=INK, width=3)
        lab = mm.text_img(labels[i], "Black", 40 if len(labels[i]) > 3 else 46, INK)
        if lab.width > 124:
            lab = lab.resize((124, int(lab.height * 124 / lab.width)), Image.LANCZOS)
        im.paste(lab, (cx - lab.width // 2, 540 - lab.height // 2), lab)
        st = mm.text_img("ON" if on else "OFF", "Bold", 28, GREEN if on else (200, 60, 60))
        im.paste(st, (cx - st.width // 2, 495 - st.height // 2), st)
    return im


def _spark(base, cx, cy, t, seed):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(base)
    k = max(0.0, 1 - t / 0.45)
    if k <= 0:
        return
    for _ in range(26):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(10, 40)
        r1 = r0 + rnd.uniform(120, 320) * (1.2 - k)
        col = (255, rnd.randint(200, 255), rnd.randint(60, 160), int(255 * k))
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))],
               fill=col, width=rnd.randint(4, 9))
    d.ellipse([cx - 70 * k, cy - 70 * k, cx + 70 * k, cy + 70 * k], fill=(255, 250, 220, int(230 * k)))


def _wall(W, H):
    if "wall" not in _C:
        im = Image.new("RGBA", (W, H), WALL + (255,))
        d = ImageDraw.Draw(im)
        for y in range(0, H, 6):  # subtle wallpaper stripes
            if (y // 6) % 9 == 0:
                d.line([(0, y), (W, y)], fill=(238, 231, 216), width=3)
        d.rectangle([0, H - 70, W, H], fill=(214, 196, 168))
        _C["wall"] = im
    return _C["wall"].copy()


def _price_tag(mm, spec, P):
    name = spec["name"]
    f_sz = mm.fit_size(name, "Black", 54, 940)
    nm = mm.text_img(name, "Black", f_sz, INK)
    old = mm.text_img(mm.won(spec["from_price"]) + "원", "Bold", 50, (130, 130, 140))
    od = ImageDraw.Draw(old)
    od.line([(4, old.height // 2 + 2), (old.width - 4, old.height // 2 + 2)], fill=mm.RED, width=6)
    new = mm.text_img(spec["badge_price"], "Black", 112, mm.RED)
    return nm, old, new


def frame(t, ctx):
    mm, P, spec, W, H = ctx["mm"], ctx["P"], ctx["spec"], ctx["W"], ctx["H"]
    flips = [_back((t - ft) / 0.22) if t >= ft else 0.0 for ft in FLIP_T]
    flips = [min(1.0, f) if t < ft + 0.22 else 1.0 for f, ft in zip(flips, FLIP_T)]
    sx = sy = 0
    for ft in FLIP_T:
        dx, dy = mm.shake(t, ft + 0.12, amp=14, dur=0.18)
        sx += dx
        sy += dy
    dx, dy = mm.shake(t, 0.0, amp=30, dur=0.3)
    sx += dx
    sy += dy

    light = _ease((t - LIGHT_T) / 0.35) if t >= LIGHT_T else 0.0
    # flicker right at switch-on
    if LIGHT_T <= t < LIGHT_T + 0.3:
        light *= 0.55 + 0.45 * (1 if int(t * 30) % 3 else 0)

    im = _wall(W, H)
    if light < 1:
        dark = Image.new("RGBA", (W, H), (8, 10, 16, int(245 * (1 - light))))
        im.alpha_composite(dark)

    # ---- dark phase: flashlight on the panel
    panel_out = _ease((t - LIGHT_T - 0.3) / 0.6)
    if panel_out < 1:
        pan = _panel(mm, flips)
        py = 820 + 900 * panel_out
        if light < 1:
            # flashlight circle reveals the panel
            beam = Image.new("L", (W, H), 0)
            bx = W / 2 + 40 * math.sin(t * 2.3)
            by = 800 + 25 * math.cos(t * 1.7)
            r = 470 + 30 * math.sin(t * 5)
            ImageDraw.Draw(beam).ellipse([bx - r, by - r, bx + r, by + r], fill=255)
            beam = beam.filter(ImageFilter.GaussianBlur(40))
            lit = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            mm.paste_center(lit, pan, W / 2, py)
            glow = Image.new("RGBA", (W, H), (255, 236, 180, 40))
            lit.alpha_composite(glow)
            vis = lit.getchannel("A").point(lambda v: v)
            m = Image.composite(vis, Image.new("L", (W, H), 0), beam)
            if light > 0:
                m = Image.blend(m, vis, light)
            lit.putalpha(m)
            im.alpha_composite(lit)
        else:
            mm.paste_center(im, pan, W / 2, py)

    if t < LIGHT_T + 0.2:
        # hook text, trembling
        jit = 6 if t < 1.3 else 2
        a = 1.0 if t < LIGHT_T else max(0.0, 1 - (t - LIGHT_T) / 0.2)
        rnd = random.Random(int(t * 30))
        hx = W / 2 + rnd.uniform(-jit, jit)
        hy = 250 + rnd.uniform(-jit, jit)
        txt = "또 내려갔어?" if t < FLIP_T[0] else "딸깍, 딸깍…"
        mm.paste_center(im, mm.text_img(txt, "Black", 118, mm.WHITE, stroke=6, stroke_fill=(0, 0, 0)), hx, hy, 1, 0, a)
        sub = "차단기 또 떨어진 집" if t < FLIP_T[0] else "하나씩 올려볼게요"
        mm.paste_center(im, mm.text_img(sub, "Bold", 52, AMBER), W / 2, 390, 1, 0, a)
        _spark(im, W / 2 + 230, 700, t, 3)

    # ---- lit phase
    if t >= LIGHT_T + 0.25:
        k = _ease((t - LIGHT_T - 0.25) / 0.5)
        # event chip
        chip_txt = "쿠팡 기획전 · " + spec["event_name"]
        if spec.get("event_period"):
            chip_txt += " · " + spec["event_period"]
        ct = mm.text_img(chip_txt, "Black", 44, mm.WHITE)
        chip = Image.new("RGBA", (ct.width + 60, ct.height + 30), (0, 0, 0, 0))
        ImageDraw.Draw(chip).rounded_rectangle([0, 0, chip.width - 1, chip.height - 1], radius=chip.height // 2,
                                               fill=(30, 110, 230))
        chip.paste(ct, (30, 15), ct)
        mm.paste_center(im, chip, W / 2, 72 - 120 * (1 - k))
        # banner hanging like a frame on the wall
        if ctx["banner"] is not None:
            bw = 700
            b = ctx["banner"].resize((bw, int(bw * ctx["banner"].height / ctx["banner"].width)), Image.LANCZOS)
            fr = Image.new("RGBA", (b.width + 24, b.height + 24), INK + (255,))
            fr.paste(b, (12, 12), b)
            sw = 3 * math.sin((t - LIGHT_T) * 6) * max(0.0, 1 - (t - LIGHT_T) / 1.6)
            by = 290 - 500 * (1 - _back((t - LIGHT_T - 0.25) / 0.6))
            mm.paste_center(im, fr, W / 2, by, 1, sw)

    if t >= 4.3:
        k = _back((t - 4.3) / 0.45)
        # glow behind product (power is on)
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        r = 330 * min(1.0, k)
        ImageDraw.Draw(g).ellipse([W / 2 - r, 720 - r, W / 2 + r, 720 + r], fill=(255, 220, 120, 120))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(50)))
        mm.paste_center(im, ctx["product"], W / 2, 720, 0.58 * k)
        if t >= 4.9:
            feat = spec.get("feature")
            if feat:
                kk = _ease((t - 4.9) / 0.3)
                ft = mm.text_img(feat, "Black", 40, INK)
                pill = Image.new("RGBA", (ft.width + 44, ft.height + 24), (0, 0, 0, 0))
                ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=24,
                                                       fill=AMBER, outline=INK, width=4)
                pill.paste(ft, (22, 12), pill.crop((22, 12, 22 + ft.width, 12 + ft.height)) if False else ft)
                mm.paste_center(im, pill, W / 2 + 250, 520, kk, -8)

    if t >= 5.4:
        nm, old, new = _price_tag(mm, spec, P)
        k = _ease((t - 5.4) / 0.35)
        mm.paste_center(im, nm, W / 2, 1010, 1, 0, k)
        tot = old.width + 36 + new.width
        x_old = (W - tot) / 2 + old.width / 2
        x_new = (W - tot) / 2 + old.width + 36 + new.width / 2
        mm.paste_center(im, old, x_old, 1112, 1, 0, k)
        if t >= 5.9:
            mm.paste_center(im, new, x_new, 1100, mm.slam((t - 5.9) / 0.4))
            if spec.get("stamp") and t >= 6.3:
                st = mm.text_img(spec["stamp"], "Black", 52, mm.WHITE)
                bub = Image.new("RGBA", (st.width + 40, st.height + 24), (0, 0, 0, 0))
                ImageDraw.Draw(bub).rounded_rectangle([0, 0, bub.width - 1, bub.height - 1], radius=20, fill=mm.RED)
                bub.paste(st, (20, 12), st)
                mm.paste_center(im, bub, W / 2 - 330, 560, mm.slam((t - 6.3) / 0.35), 10)

    if t >= 6.8:
        k = _ease((t - 6.8) / 0.4)
        stats = spec.get("stats") or []
        line = "   ".join(f"{s[0]} {mm.won(s[1])}{s[2]}" for s in stats[:2])
        if line:
            mm.paste_center(im, mm.text_img(line, "Bold", 40, (70, 70, 80)), W / 2, 1182, 1, 0, k)

    if t >= 7.6:
        k = _back((t - 7.6) / 0.4)
        ct = mm.text_img(spec.get("cta", "첫 댓글에 링크"), "Black", 50, mm.WHITE)
        pill = Image.new("RGBA", (ct.width + 70, ct.height + 30), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=pill.height // 2,
                                               fill=INK)
        pill.paste(ct, (35, 15), ct)
        pulse = 1 + 0.04 * math.sin((t - 7.6) * 8)
        mm.paste_center(im, pill, W / 2, 1255, k * pulse)

    return im, sx, sy
