"""Render Threads carousel cards (1080x1350) from a JSON spec.

"order" picks which cards to draw and in what order (default hook, product, reviews).
Hook layouts: "number" (default), "question", "checklist", "versus".
  question:  {"layout":"question","kicker":"...","question":"줄바꿈은 \\n","answer":"..."}
  checklist: {"layout":"checklist","title":"...","items":["...","...","..."],"note":"..."}
  versus:    {"layout":"versus","kicker":"...","left_label":"정가","left":"59,700원",
              "right_label":"지금","right":"22,000원","saving":"37,700원 아껴요","note":"..."}

usage: python scripts/make_cards.py spec.json out_dir

spec = {
  "theme": "navy" | "teal" | "orange",
  "product_image": "path/to/product.jpg",
  "hook":    {"kicker": "...", "big1": "...", "big2": "...", "line1": "...", "line2": "..."},
  "product": {"pill": "...", "brand": "...", "name": "...", "sub": "...",
              "badge_top": "34% 할인", "badge_price": "256,630원",
              "deadline": "9/29(화) 오전 7시까지"},          # optional, deals account
  "reviews": {"title": "...", "big": "91%", "caption": "...",
              "quotes": [["“...”", "..."], ...3], "footer": "..."}
}
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
FD = "/usr/share/fonts/opentype/noto/"

THEMES = {
    "navy":   {"bg": (16, 32, 72),  "glow": (40, 70, 150), "accent": (255, 214, 0), "main": (37, 99, 235),
               "soft": (190, 205, 235), "card": (241, 245, 252), "paper": (246, 244, 238)},
    "teal":   {"bg": (10, 60, 60),  "glow": (20, 110, 105), "accent": (255, 214, 0), "main": (13, 148, 136),
               "soft": (180, 225, 218), "card": (236, 248, 246), "paper": (244, 246, 243)},
    "navy2":  {"bg": (28, 24, 64),  "glow": (72, 58, 150), "accent": (255, 196, 64), "main": (91, 76, 219),
               "soft": (205, 198, 240), "card": (243, 241, 252), "paper": (245, 244, 240)},
    "navy3":  {"bg": (18, 40, 52),  "glow": (34, 92, 118), "accent": (255, 224, 102), "main": (20, 116, 160),
               "soft": (186, 216, 230), "card": (237, 246, 250), "paper": (244, 246, 245)},
    "teal2":  {"bg": (22, 52, 30),  "glow": (46, 110, 62), "accent": (255, 210, 80), "main": (34, 139, 76),
               "soft": (196, 228, 204), "card": (238, 248, 240), "paper": (245, 246, 240)},
    "teal3":  {"bg": (58, 36, 20),  "glow": (122, 78, 36), "accent": (255, 220, 120), "main": (190, 106, 30),
               "soft": (240, 218, 190), "card": (252, 245, 236), "paper": (248, 245, 239)},
    "orange": {"bg": (70, 30, 10),  "glow": (140, 70, 20), "accent": (255, 214, 0), "main": (234, 88, 12),
               "soft": (245, 210, 185), "card": (253, 243, 235), "paper": (248, 244, 238)},
}
WHITE, INK, MUTED = (255, 255, 255), (20, 24, 33), (100, 110, 125)


def font(weight, size):
    return ImageFont.truetype(FD + f"NotoSansCJK-{weight}.ttc", size, index=1)  # KR


def fit(d, text, weight, size, max_w):
    f = font(weight, size)
    while d.textlength(text, font=f) > max_w and size > 20:
        size -= 4
        f = font(weight, size)
    return f


def center(d, y, text, f, fill):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def hook_card(s, t):
    c = Image.new("RGB", (W, H), t["bg"])
    glow = Image.new("RGB", (W, H), t["bg"])
    ImageDraw.Draw(glow).ellipse([140, 330, 940, 1130], fill=t["glow"])
    c.paste(glow.filter(ImageFilter.GaussianBlur(160)), (0, 0))
    d = ImageDraw.Draw(c)
    center(d, 150, s["kicker"], fit(d, s["kicker"], "Bold", 58, 960), t["soft"])
    center(d, 330, s["big1"], fit(d, s["big1"], "Black", 150, 980), WHITE)
    center(d, 510, s["big2"], fit(d, s["big2"], "Black", 240, 1000), t["accent"])
    d.rounded_rectangle([200, 860, 880, 866], radius=3, fill=t["glow"])
    center(d, 910, s["line1"], fit(d, s["line1"], "Bold", 56, 980), WHITE)
    center(d, 1000, s["line2"], fit(d, s["line2"], "Regular", 46, 980), t["soft"])
    center(d, 1180, "넘겨서 보기  →", font("Bold", 44), t["accent"])
    return c


def wrap(d, text, f, max_w):
    """Break at spaces (Korean words stay whole); fall back to characters for a too-long word."""
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            cand = (line + " " + word).strip()
            if d.textlength(cand, font=f) <= max_w:
                line = cand
                continue
            if line:
                out.append(line)
            line = ""
            for ch in word:
                if d.textlength(line + ch, font=f) > max_w and line:
                    out.append(line)
                    line = ch
                else:
                    line += ch
        out.append(line)
    return out


def _dark_base(t):
    c = Image.new("RGB", (W, H), t["bg"])
    glow = Image.new("RGB", (W, H), t["bg"])
    ImageDraw.Draw(glow).ellipse([140, 330, 940, 1130], fill=t["glow"])
    c.paste(glow.filter(ImageFilter.GaussianBlur(160)), (0, 0))
    return c, ImageDraw.Draw(c)


def question_card(s, t):
    c, d = _dark_base(t)
    center(d, 150, s.get("kicker", ""), fit(d, s.get("kicker", ""), "Bold", 50, 960), t["soft"])
    size = 110
    while size > 60:
        f = font("Black", size)
        lines = wrap(d, s["question"], f, 940)
        if len(lines) <= 4:
            break
        size -= 8
    lh = int(size * 1.28)
    y = 640 - len(lines) * lh // 2
    for ln in lines:
        center(d, y, ln, f, WHITE)
        y += lh
    ans = s.get("answer", "")
    if ans:
        fa = fit(d, ans, "Bold", 58, 900)
        w = d.textlength(ans, font=fa)
        d.rounded_rectangle([(W - w) / 2 - 36, 1010, (W + w) / 2 + 36, 1110], radius=50, fill=t["accent"])
        d.text(((W - w) / 2, 1024), ans, font=fa, fill=INK)
    center(d, 1200, "넘겨서 보기  →", font("Bold", 40), t["accent"])
    return c


def checklist_card(s, t):
    c = Image.new("RGB", (W, H), t["paper"])
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, W, 16], fill=t["main"])
    title_f = font("Black", 76)
    lines = wrap(d, s["title"], title_f, 940)
    y = 110
    for ln in lines[:3]:
        d.text((70, y), ln, font=title_f, fill=INK)
        y += 98
    y += 40
    for i, item in enumerate(s["items"][:4], 1):
        d.rounded_rectangle([70, y, W - 70, y + 168], radius=26, fill=WHITE, outline=(222, 226, 230), width=2)
        d.ellipse([100, y + 44, 180, y + 124], fill=t["main"])
        n = str(i)
        fn = font("Black", 48)
        d.text((140 - d.textlength(n, font=fn) / 2, y + 50), n, font=fn, fill=WHITE)
        fi = font("Bold", 46)
        il = wrap(d, item, fi, 800)[:2]
        iy = y + 84 - len(il) * 30
        for ln in il:
            d.text((212, iy), ln, font=fi, fill=INK)
            iy += 60
        y += 190
    if s.get("note"):
        center(d, max(y + 20, 1200), s["note"], fit(d, s["note"], "Bold", 42, 960), t["main"])
    return c


def versus_card(s, t):
    c, d = _dark_base(t)
    center(d, 130, s.get("kicker", ""), fit(d, s.get("kicker", ""), "Bold", 56, 960), t["soft"])
    # left: old price, struck through
    fl, fv = font("Bold", 44), font("Black", 110)
    for x0, lab, val, col, strike in ((70, s["left_label"], s["left"], t["soft"], True),
                                      (560, s["right_label"], s["right"], t["accent"], False)):
        d.rounded_rectangle([x0, 360, x0 + 450, 760], radius=36,
                            fill=t["glow"] if strike else (255, 255, 255))
        tc = t["soft"] if strike else INK
        d.text((x0 + 225 - d.textlength(lab, font=fl) / 2, 410), lab, font=fl, fill=tc)
        fvv = fit(d, val, "Black", 96, 400)
        vw = d.textlength(val, font=fvv)
        d.text((x0 + 225 - vw / 2, 530), val, font=fvv, fill=tc if strike else t["main"])
        if strike:
            d.line([x0 + 225 - vw / 2 - 10, 590, x0 + 225 + vw / 2 + 10, 590], fill=(255, 120, 110), width=8)
    if s.get("saving"):
        center(d, 850, s["saving"], fit(d, s["saving"], "Black", 110, 980), t["accent"])
    if s.get("note"):
        center(d, 1010, s["note"], fit(d, s["note"], "Regular", 42, 960), t["soft"])
    center(d, 1200, "넘겨서 보기  →", font("Bold", 40), t["accent"])
    return c


def product_card(s, t, img_path):
    c = Image.new("RGB", (W, H), t["paper"])
    d = ImageDraw.Draw(c)
    f = font("Bold", 38)
    w = d.textlength(s["pill"], font=f)
    d.rounded_rectangle([70, 70, 70 + w + 56, 70 + 72], radius=40, fill=t["main"])
    d.text((98, 78), s["pill"], font=f, fill=WHITE)
    d.text((70, 170), s["brand"], font=fit(d, s["brand"], "Bold", 52, 940), fill=MUTED)
    d.text((70, 235), s["name"], font=fit(d, s["name"], "Black", 92, 940), fill=INK)
    d.text((70, 350), s["sub"], font=fit(d, s["sub"], "Regular", 46, 940), fill=MUTED)
    card = Image.new("RGB", (820, 820), WHITE)
    card.paste(Image.open(img_path).convert("RGB").resize((780, 780), Image.LANCZOS), (20, 20))
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 820, 820], radius=40, fill=255)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([140, 460, 960, 1280], radius=40, fill=(0, 0, 0, 60))
    c.paste(shadow.filter(ImageFilter.GaussianBlur(25)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(25)))
    c.paste(card, (130, 440), mask)
    d = ImageDraw.Draw(c)
    bx, by, bw = 645, 1080, 390
    d.ellipse([bx, by, bx + bw, by + 230], fill=t["accent"])
    f1 = font("Bold", 40)
    f2 = fit(d, s["badge_price"], "Black", 72, bw - 50)
    d.text((bx + (bw - d.textlength(s["badge_top"], font=f1)) / 2, by + 38), s["badge_top"], font=f1, fill=INK)
    d.text((bx + (bw - d.textlength(s["badge_price"], font=f2)) / 2, by + 95), s["badge_price"], font=f2, fill=INK)
    if s.get("deadline"):  # deal end time, e.g. "9/29(화) 오전 7시까지"
        txt = "특가 " + s["deadline"]
        f3 = fit(d, txt, "Black", 40, 560)
        w3 = d.textlength(txt, font=f3)
        x0 = W - 70 - w3 - 60
        d.rounded_rectangle([x0, 70, W - 70, 142], radius=36, fill=(214, 40, 40))
        d.text((x0 + 30, 80), txt, font=f3, fill=WHITE)
    return c


def review_card(s, t):
    c = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, W, 470], fill=t["main"])
    center(d, 70, s["title"], font("Bold", 54), WHITE)
    center(d, 130, s["big"], font("Black", 170), WHITE)
    center(d, 380, s["caption"], fit(d, s["caption"], "Bold", 42, 980), WHITE)
    y = 520
    for q, sub in s["quotes"]:
        d.rounded_rectangle([70, y, W - 70, y + 190], radius=28, fill=t["card"])
        d.rectangle([70, y + 30, 80, y + 160], fill=t["main"])
        d.text((115, y + 35), q, font=fit(d, q, "Bold", 46, 860), fill=INK)
        d.text((115, y + 110), sub, font=fit(d, sub, "Regular", 38, 860), fill=MUTED)
        y += 212
    center(d, 1180, s["footer"], fit(d, s["footer"], "Bold", 44, 980), t["main"])
    center(d, 1250, "구매자 리뷰를 요약한 내용이에요", font("Regular", 30), (160, 168, 180))
    return c


def cover_card(s, t):
    """Curation cover: title + numbered list of the products inside."""
    c, d = _dark_base(t)
    center(d, 110, s.get("kicker", ""), fit(d, s.get("kicker", ""), "Bold", 50, 960), t["soft"])
    tf = font("Black", 92)
    y = 200
    for ln in wrap(d, s["title"], tf, 960)[:2]:
        center(d, y, ln, tf, WHITE)
        y += 118
    y += 40
    items = s.get("items") or [{"name": r.get("short") or r["name"], "price": r.get("cover_value") or r.get("price", "")}
                               for r in s.get("_ranks", [])]
    items = items[:5]
    rowh = min(150, (1160 - y) // max(1, len(items)))
    for i, it in enumerate(items, 1):
        d.rounded_rectangle([70, y, W - 70, y + rowh - 18], radius=28, fill=t["card"] if "card" in t else (40, 46, 60))
        d.ellipse([96, y + (rowh - 18) / 2 - 38, 172, y + (rowh - 18) / 2 + 38], fill=t["accent"])
        fn = font("Black", 46)
        d.text((134 - d.textlength(str(i), font=fn) / 2, y + (rowh - 18) / 2 - 30), str(i), font=fn, fill=INK)
        fnm = fit(d, it["name"], "Bold", 44, 560)
        d.text((196, y + (rowh - 18) / 2 - 28), it["name"], font=fnm, fill=INK if "card" in t else WHITE)
        fp = fit(d, it.get("price", ""), "Black", 46, 260)
        d.text((W - 96 - d.textlength(it.get("price", ""), font=fp), y + (rowh - 18) / 2 - 28), it.get("price", ""), font=fp, fill=t["main"] if "card" in t else t["accent"])
        y += rowh
    center(d, 1230, s.get("note", "넘겨서 하나씩 보기  →"), fit(d, s.get("note", "넘겨서 하나씩 보기  →"), "Bold", 42, 960), t["accent"])
    return c


def rank_card(s, t, img_path):
    """One product of a curation: rank badge, photo, name, price and one fact."""
    c = Image.new("RGB", (W, H), t["paper"])
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, W, 16], fill=t["main"])
    d.ellipse([60, 60, 220, 220], fill=t["main"])
    rn = str(s["rank"])
    fr = font("Black", 96)
    d.text((140 - d.textlength(rn, font=fr) / 2, 78), rn, font=fr, fill=WHITE)
    if s.get("badge"):
        fb = fit(d, s["badge"], "Black", 46, 680)
        bw = d.textlength(s["badge"], font=fb)
        d.rounded_rectangle([250, 100, 250 + bw + 64, 180], radius=40, fill=t["accent"])
        d.text((282, 112), s["badge"], font=fb, fill=INK)
    card = Image.new("RGB", (760, 760), WHITE)
    card.paste(Image.open(img_path).convert("RGB").resize((720, 720), Image.LANCZOS), (20, 20))
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 760, 760], radius=40, fill=255)
    c.paste(card, (160, 250), mask)
    d = ImageDraw.Draw(c)
    nm = s["name"]
    center(d, 1040, nm, fit(d, nm, "Black", 64, 960), INK)
    if s.get("sub"):
        center(d, 1125, s["sub"], fit(d, s["sub"], "Regular", 44, 960), MUTED)
    pr = s.get("price", "")
    fp = fit(d, pr, "Black", 74, 700)
    pw = d.textlength(pr, font=fp)
    d.rounded_rectangle([(W - pw) / 2 - 44, 1190, (W + pw) / 2 + 44, 1300], radius=55, fill=t["main"])
    d.text(((W - pw) / 2, 1200), pr, font=fp, fill=WHITE)
    return c


def scene_card(s, t, img_path):
    """Stop-the-scroll cover: a real-life situation photo with a big hook burned in.
    s = {"lines": [["오후 3시만 되면", false], ["눈이 감기는 사람?", true]], "sub": "넘겨서 확인 →", "ai": true}"""
    im = Image.open(img_path).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - W) // 2, int((im.height - H) * 0.35)
    im = im.crop((x, y, x + W, y + H)).convert("RGBA")
    g = Image.new("L", (1, H))
    for j in range(H):
        g.putpixel((0, j), int(225 * max(0.0, 1 - j / 640) ** 1.4 + 120 * max(0.0, (j - H + 260) / 260) ** 2))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(g.resize((W, H)))
    im.alpha_composite(shade)
    d = ImageDraw.Draw(im)
    accent = s.get("accent") or t["accent"]
    if isinstance(accent, list):
        accent = tuple(accent)
    y = 110
    for ln, hi in s["lines"][:3]:
        f = fit(d, ln, "Black", 118, 960)
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=accent if hi else WHITE,
               stroke_width=6, stroke_fill=(0, 0, 0))
        y += f.size + 26
    sub = s.get("sub", "넘겨서 확인 →")
    fs = fit(d, sub, "Bold", 44, 900)
    tw = d.textlength(sub, font=fs)
    d.rounded_rectangle([(W - tw) / 2 - 34, H - 150, (W + tw) / 2 + 34, H - 72], radius=40, fill=(255, 255, 255, 235))
    d.text(((W - tw) / 2, H - 140), sub, font=fs, fill=INK)
    if s.get("ai", True):
        fa = font("Bold", 26)
        d.rounded_rectangle([28, H - 58, 28 + d.textlength("AI 이미지", font=fa) + 28, H - 20], radius=19, fill=(0, 0, 0, 150))
        d.text((42, H - 54), "AI 이미지", font=fa, fill=(235, 235, 235))
    return im.convert("RGB")


def main(spec_path, out_dir):
    s = json.load(open(spec_path))
    t = THEMES[s.get("theme", "navy")]
    os.makedirs(out_dir, exist_ok=True)
    img = s["product_image"]
    if not os.path.isabs(img):
        img = os.path.join(os.path.dirname(os.path.abspath(spec_path)), img)
    hooks = {"number": hook_card, "question": question_card,
             "checklist": checklist_card, "versus": versus_card}
    names = []
    for i, part in enumerate(s.get("order", ["hook", "product", "reviews"]), 1):
        if part == "hook":
            h = s["hook"]
            im = hooks[h.get("layout", "number")](h, t)
        elif part == "product":
            im = product_card(s["product"], t, img)
        elif part == "reviews":
            im = review_card(s["reviews"], t)
        elif part == "scene":
            sp = s["scene_image"] if os.path.isabs(s["scene_image"]) else os.path.join(os.path.dirname(os.path.abspath(spec_path)), s["scene_image"])
            im = scene_card(s["scene"], t, sp)
        elif part == "cover":
            im = cover_card(dict(s["cover"], _ranks=s.get("ranks", [])), t)
        elif part.startswith("rank"):
            r = s["ranks"][int(part[4:]) - 1]
            ip = r["image"] if os.path.isabs(r["image"]) else os.path.join(os.path.dirname(os.path.abspath(spec_path)), r["image"])
            im = rank_card(r, t, ip)
        else:
            raise SystemExit(f"unknown card '{part}'")
        name = f"card{i}_{part}.jpg"
        im.save(os.path.join(out_dir, name), quality=92)
        names.append(name)
    print("wrote", out_dir, names)
    return names


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
