"""Baby-monitor night cam: a green night-vision nursery feed with a flashing '칭얼거림 감지' alert and spiking
sound bars grabs the first second; a picture book glides into the crib, the noise meter calms down, the
camera flips from night-vision to day colour and the monitor screen turns into the event banner, the book
and its price, all inside the same monitor bezel."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

CONCEPT = {
    "name": "베이비 모니터 야간 카메라",
    "idea": "초록 야간투시 아기방 홈캠 화면에 빨간 '칭얼거림 감지' 알림과 요동치는 소리 막대가 번쩍이는 첫 장면, "
            "그림책이 아기 침대 쪽으로 쓱 들어오면 소리 막대가 잦아들고 상태가 '자장자장 모드'로 바뀐 뒤, "
            "카메라가 야간→주간 컬러로 전환되며 모니터 화면이 행사 배너·그림책·가격으로 바뀐다",
}
END = 10.0
POSTER_AT = 7.6

BG = (14, 18, 16)
NV = (120, 255, 150)       # night-vision green
NV_D = (18, 52, 30)
ALERT = (255, 64, 64)
CALM = (70, 220, 140)
CREAM = (255, 248, 236)
INK = (30, 26, 34)
PINK = (255, 112, 150)

T_BOOK = 1.5     # book glides in
T_CALM = 2.6     # meter calms
T_SWITCH = 4.2   # night -> day switch
T_INFO = 5.0     # price block

SCR = (60, 150, 1020, 1170)  # monitor screen box
_C = {}


def _e(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _back(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _nightvision(im):
    g = ImageOps.grayscale(im.convert("RGB"))
    g = ImageOps.autocontrast(g, cutoff=1)
    return ImageOps.colorize(g, black=NV_D, white=NV).convert("RGBA")


def _nursery(ctx):
    """the static nursery scene (drawn in colour, tinted later): wall, crib bars, mobile, star lamp"""
    if "room" in _C:
        return _C["room"]
    w, h = SCR[2] - SCR[0], SCR[3] - SCR[1]
    im = Image.new("RGBA", (w, h), (200, 190, 175, 255))
    d = ImageDraw.Draw(im)
    for y in range(h):  # wall gradient
        k = y / h
        d.line([(0, y), (w, y)], fill=(int(214 - 40 * k), int(204 - 40 * k), int(190 - 40 * k)))
    d.rectangle([0, int(h * 0.78), w, h], fill=(150, 120, 96))
    rnd = random.Random(7)
    for _ in range(26):  # wallpaper stars
        x, y = rnd.randint(20, w - 20), rnd.randint(20, int(h * 0.55))
        r = rnd.randint(5, 10)
        d.polygon([(x, y - r), (x + r * 0.3, y - r * 0.3), (x + r, y), (x + r * 0.3, y + r * 0.3),
                   (x, y + r), (x - r * 0.3, y + r * 0.3), (x - r, y), (x - r * 0.3, y - r * 0.3)],
                  fill=(236, 226, 206))
    # crib
    cx0, cx1, cy0, cy1 = 110, w - 110, int(h * 0.44), int(h * 0.86)
    d.rounded_rectangle([cx0, cy0 - 26, cx1, cy0], radius=12, fill=(236, 230, 220))
    d.rounded_rectangle([cx0, cy1 - 10, cx1, cy1 + 18], radius=10, fill=(236, 230, 220))
    d.rectangle([cx0 + 20, cy0 + 120, cx1 - 20, cy1 - 10], fill=(250, 246, 240))  # mattress/blanket
    d.ellipse([cx0 + 80, cy0 + 70, cx0 + 260, cy0 + 170], fill=(255, 252, 248))   # pillow
    for x in range(cx0, cx1 + 1, 54):
        d.rectangle([x, cy0, x + 14, cy1], fill=(236, 230, 220))
    # mobile string + three hanging stars
    mx = w // 2
    d.line([(mx, 0), (mx, 70)], fill=(120, 110, 100), width=4)
    d.line([(mx - 160, 70), (mx + 160, 70)], fill=(120, 110, 100), width=4)
    _C["room"] = (im, (cx0, cy0, cx1, cy1))
    return _C["room"]


def _scanlines(w, h):
    if ("scan", w, h) not in _C:
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        for y in range(0, h, 4):
            d.line([(0, y), (w, y)], fill=(0, 0, 0, 46))
        _C[("scan", w, h)] = s
    return _C[("scan", w, h)]


def _noise(w, h, seed):
    key = ("noise", seed % 6)
    if key not in _C:
        rnd = random.Random(seed % 6)
        small = Image.new("L", (w // 6, h // 6))
        small.putdata([rnd.randint(0, 255) for _ in range(small.width * small.height)])
        n = small.resize((w, h), Image.NEAREST)
        lay = Image.new("RGBA", (w, h), (180, 255, 200, 0))
        lay.putalpha(n.point(lambda v: int(v * 0.12)))
        _C[key] = lay
    return _C[key]


def _book(ctx, size):
    key = ("book", size)
    if key not in _C:
        raw = ctx["product_raw"]
        # crop the white margin around the cover
        g = ImageOps.invert(ImageOps.grayscale(raw)).point(lambda v: 255 if v > 18 else 0)
        box = g.getbbox() or (0, 0, raw.width, raw.height)
        cov = raw.crop(box)
        r = size / max(cov.size)
        cov = cov.resize((int(cov.width * r), int(cov.height * r)), Image.LANCZOS).convert("RGBA")
        sh = Image.new("RGBA", (cov.width + 40, cov.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([16, 22, cov.width + 24, cov.height + 30], radius=10, fill=(0, 0, 0, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        sh.paste(cov, (20, 16), cov)
        _C[key] = sh
    return _C[key]


def _meter_levels(t):
    """10 sound bars: wild before calm, then low breathing"""
    out = []
    for i in range(10):
        wild = 0.55 + 0.45 * abs(math.sin(t * 13 + i * 1.7)) * abs(math.cos(t * 7 + i))
        calm = 0.10 + 0.06 * (1 + math.sin(t * 2.2 + i * 0.6))
        k = _e((t - T_CALM + 0.4) / 1.0)
        out.append(wild * (1 - k) + calm * k)
    return out


def _txt(mm, s, w, size, fill, stroke=0, sf=(0, 0, 0)):
    return mm.text_img(s, w, size, fill, stroke=stroke, stroke_fill=sf)


def _screen_night(t, ctx):
    mm = ctx["mm"]
    w, h = SCR[2] - SCR[0], SCR[3] - SCR[1]
    room, (cx0, cy0, cx1, cy1) = _nursery(ctx)
    im = room.copy()
    d = ImageDraw.Draw(im)
    # mobile stars swing
    sw = math.sin(t * 2.6) * 10
    for k, dx in enumerate((-160, 0, 160)):
        x = w // 2 + dx + sw
        y = 70 + 60 + 20 * (k % 2)
        d.line([(w // 2 + dx, 70), (x, y - 22)], fill=(120, 110, 100), width=3)
        d.regular_polygon((x, y, 26), 5, rotation=sw * 2, fill=(250, 236, 180))
    # book glides into the crib
    if t >= T_BOOK:
        k = _back((t - T_BOOK) / 0.8)
        b = _book(ctx, 380)
        bx = int((cx0 + cx1) / 2 - b.width / 2)
        by = int(cy0 + 30 + (1 - k) * (h - cy0 + 80))
        im.paste(b, (bx, by), b)
    im = _nightvision(im)
    im.alpha_composite(_noise(w, h, int(t * 30)))
    im.alpha_composite(_scanlines(w, h))
    # vignette
    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse([-200, -160, w + 200, h + 160], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    im = Image.composite(im, dark, v)
    return im


def _screen_day(t, ctx):
    """day mode: cream nursery card with banner, book and price"""
    mm = ctx["mm"]
    spec = ctx["spec"]
    w, h = SCR[2] - SCR[0], SCR[3] - SCR[1]
    im = Image.new("RGBA", (w, h), CREAM + (255,))
    d = ImageDraw.Draw(im)
    rnd = random.Random(3)
    for _ in range(40):  # soft confetti hearts/dots
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        c = rnd.choice([(255, 214, 224), (210, 236, 214), (255, 236, 190)])
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=c)
    # banner across the top
    ban = ctx["banner"]
    bw = w - 240
    bh = int(ban.height * bw / ban.width)
    bimg = ban.resize((bw, bh), Image.LANCZOS)
    m = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=28, fill=255)
    kb = _e((t - T_SWITCH) / 0.6)
    BT = 96
    im.paste(bimg, ((w - bw) // 2, int(BT - (1 - kb) * 60)), m)
    bh = bh + BT - 30
    # book + price block
    k2 = _back((t - T_INFO) / 0.7)
    b = _book(ctx, 330)
    if t >= T_INFO:
        mm.paste_center(im, b, 250, bh + 40 + 175, scale=max(0.01, k2), angle=(1 - k2) * -12 + 3)
    k3 = _e((t - T_INFO - 0.35) / 0.6)
    if k3 > 0:
        x0 = 480
        y0 = bh + 40
        lines = [
            (_txt(mm, spec["short"], "Black", 52, INK), 0),
            (_txt(mm, spec["sub"], "Medium", 34, (110, 100, 110)), 72),
            (_txt(mm, f"정가 {spec['from_price']}원", "Medium", 36, (140, 130, 140)), 142),
        ]
        for img, dy in lines:
            im.paste(img, (int(x0 + (1 - k3) * 80), y0 + dy), img)
        # strike through the list price
        s = lines[2][0]
        sy = y0 + 142 + s.height // 2
        d.line([(int(x0 + (1 - k3) * 80) + 8, sy), (int(x0 + (1 - k3) * 80) + s.width - 6, sy)], fill=(140, 130, 140), width=4)
        pr = _txt(mm, spec["badge_price"], "Black", 96, PINK, stroke=0)
        im.paste(pr, (int(x0 + (1 - k3) * 80) - 4, y0 + 196), pr)
        pill = _txt(mm, spec["stamp"], "Black", 40, (255, 255, 255))
        pw, ph = pill.width + 36, pill.height + 18
        px, py = int(x0 + (1 - k3) * 80), y0 + 330
        d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=INK)
        im.paste(pill, (px + 18, py + 9), pill)
    # stats row
    k4 = _e((t - T_INFO - 0.9) / 0.6)
    if k4 > 0:
        y = h - 172
        st = spec["stats"]
        colw = (w - 90) // len(st)
        for i, (label, val, unit) in enumerate(st):
            x = 45 + i * colw
            d.rounded_rectangle([x, y, x + colw - 20, y + 150], radius=26, fill=(255, 255, 255), outline=(236, 222, 214), width=3)
            n = int(val * _e((t - T_INFO - 0.9) / 1.0))
            v = _txt(mm, f"{n:,}{unit}", "Black", 58, INK)
            lab = _txt(mm, label, "Bold", 32, (120, 110, 120))
            mm.paste_center(im, v, x + (colw - 20) / 2, y + 54, alpha=k4)
            mm.paste_center(im, lab, x + (colw - 20) / 2, y + 116, alpha=k4)
    return im


def _hud(base, t, ctx, day):
    mm = ctx["mm"]
    d = ImageDraw.Draw(base)
    x0, y0, x1, y1 = SCR
    col = (255, 255, 255)
    # top-left camera label + REC dot
    lab = _txt(mm, "CAM 1 · 아기방", "Bold", 34, col, stroke=3, sf=(0, 0, 0))
    base.paste(lab, (x0 + 26, y0 + 22), lab)
    if int(t * 2) % 2 == 0:
        d.ellipse([x1 - 150, y0 + 32, x1 - 126, y0 + 56], fill=ALERT)
    rec = _txt(mm, "REC", "Black", 30, col, stroke=3, sf=(0, 0, 0))
    base.paste(rec, (x1 - 116, y0 + 26), rec)
    if day:
        return
    # clock
    sec = 12 + int(t)
    clk = _txt(mm, f"21:47:{sec:02d}", "Bold", 34, col, stroke=3, sf=(0, 0, 0))
    base.paste(clk, (x0 + 26, y0 + 70), clk)
    mode = _txt(mm, "야간 모드", "Bold", 30, NV, stroke=3, sf=(0, 0, 0))
    base.paste(mode, (x1 - mode.width - 26, y0 + 72), mode)
    # sound meter (right edge)
    lv = _meter_levels(t)
    mx, my = x1 - 70, y1 - 60
    for i, l in enumerate(lv):
        hgt = int(18 + 300 * l)
        c = ALERT if l > 0.5 else (CALM if l < 0.3 else (255, 200, 60))
        d.rounded_rectangle([mx - i * 0 - 0, my - (i + 1) * 32, mx + 40, my - (i + 1) * 32 + 22], radius=6,
                            fill=c if (i + 1) / 10 <= l + 0.05 else (60, 70, 66))
    # alert banner (center) – red & flashing, then calm green
    calm_k = _e((t - T_CALM) / 0.4)
    if calm_k < 1:
        flash = 0.65 + 0.35 * (1 if int(t * 6) % 2 == 0 else 0)
        s = mm.slam(t / 0.45) if t < 0.45 else 1.0
        txt = _txt(mm, "칭얼거림 감지!", "Black", 92, (255, 255, 255))
        box = Image.new("RGBA", (txt.width + 80, txt.height + 44), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([0, 0, box.width - 1, box.height - 1], radius=30,
                                              fill=ALERT + (int(235 * flash),))
        box.paste(txt, (40, 22), txt)
        mm.paste_center(base, box, (x0 + x1) / 2, y0 + 250, scale=s, alpha=1 - calm_k)
    if t >= T_CALM:
        k = _back((t - T_CALM) / 0.5)
        txt = _txt(mm, "자장자장 모드", "Black", 80, INK)
        box = Image.new("RGBA", (txt.width + 80, txt.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([0, 0, box.width - 1, box.height - 1], radius=30, fill=CALM + (240,))
        box.paste(txt, (40, 20), txt)
        mm.paste_center(base, box, (x0 + x1) / 2, y0 + 250, scale=max(0.01, k))
        sub = _txt(mm, "소리 레벨 ▼ 낮음", "Bold", 40, (255, 255, 255), stroke=4, sf=(0, 0, 0))
        mm.paste_center(base, sub, (x0 + x1) / 2, y0 + 350, alpha=_e((t - T_CALM - 0.3) / 0.4))


def frame(t, ctx):
    mm = ctx["mm"]
    spec = ctx["spec"]
    W, H = ctx["W"], ctx["H"]
    base = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(base)
    # monitor bezel
    d.rounded_rectangle([SCR[0] - 26, SCR[1] - 26, SCR[2] + 26, SCR[3] + 26], radius=54, fill=(38, 42, 48))
    d.rounded_rectangle([SCR[0] - 10, SCR[1] - 10, SCR[2] + 10, SCR[3] + 10], radius=44, fill=(8, 10, 12))
    # top caption above the monitor
    if t < T_SWITCH:
        cap = _txt(mm, "밤 9시 47분, 아기방 홈캠", "Black", 56, (255, 255, 255))
    else:
        cap = _txt(mm, spec["event_name"], "Black", 60, (255, 230, 120))
    mm.paste_center(base, cap, W / 2, 84)

    w, h = SCR[2] - SCR[0], SCR[3] - SCR[1]
    if t < T_SWITCH:
        scr = _screen_night(t, ctx)
    else:
        scr = _screen_day(t, ctx)
    # switch transition: white flash + horizontal wipe from night to day
    if T_SWITCH - 0.25 <= t < T_SWITCH + 0.35:
        night = _screen_night(min(t, T_SWITCH - 0.01), ctx)
        day = _screen_day(max(t, T_SWITCH), ctx)
        k = _e((t - (T_SWITCH - 0.25)) / 0.6)
        cut = int(w * k)
        scr = night.copy()
        scr.paste(day.crop((0, 0, cut, h)), (0, 0))
        dd = ImageDraw.Draw(scr)
        dd.rectangle([cut - 6, 0, cut + 6, h], fill=(255, 255, 255))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=36, fill=255)
    base.paste(scr, (SCR[0], SCR[1]), m)
    _hud(base, t, ctx, day=t >= T_SWITCH)
    if T_SWITCH - 0.3 <= t < T_SWITCH + 0.3:
        lab = _txt(mm, "주간 모드 전환", "Black", 64, INK)
        box = Image.new("RGBA", (lab.width + 70, lab.height + 36), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([0, 0, box.width - 1, box.height - 1], radius=26, fill=(255, 255, 255, 235))
        box.paste(lab, (35, 18), lab)
        mm.paste_center(base, box, W / 2, (SCR[1] + SCR[3]) / 2)

    # bottom strip: below the monitor
    if t < T_SWITCH:
        line = _txt(mm, "오늘 밤 처방은?", "Black", 64, (255, 255, 255)) if t < T_BOOK + 0.3 else \
            _txt(mm, "그림책 한 권 투입", "Black", 64, NV)
    else:
        line = _txt(mm, spec["cta"], "Black", 66, (255, 230, 120))
        pulse = 1 + 0.05 * math.sin(t * 7) if t > T_INFO + 1.5 else 1.0
        mm.paste_center(base, line, W / 2, 1258, scale=pulse)
        line = None
    if line is not None:
        mm.paste_center(base, line, W / 2, 1258)
    # first second shake on the alert
    sx = sy = 0
    if t < 0.6:
        sx = int(math.sin(t * 90) * 14 * (1 - t / 0.6))
        sy = int(math.cos(t * 70) * 8 * (1 - t / 0.6))
    return base, sx, sy
