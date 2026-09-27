"""Render a 3-card Threads carousel (1080x1350) from a JSON spec.

usage: python scripts/make_cards.py spec.json out_dir

spec = {
  "theme": "navy" | "teal" | "orange",
  "product_image": "path/to/product.jpg",
  "hook":    {"kicker": "...", "big1": "...", "big2": "...", "line1": "...", "line2": "..."},
  "product": {"pill": "...", "brand": "...", "name": "...", "sub": "...",
              "badge_top": "34% 할인", "badge_price": "256,630원"},
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


def main(spec_path, out_dir):
    s = json.load(open(spec_path))
    t = THEMES[s.get("theme", "navy")]
    os.makedirs(out_dir, exist_ok=True)
    img = s["product_image"]
    if not os.path.isabs(img):
        img = os.path.join(os.path.dirname(os.path.abspath(spec_path)), img)
    hook_card(s["hook"], t).save(os.path.join(out_dir, "card1_hook.jpg"), quality=92)
    product_card(s["product"], t, img).save(os.path.join(out_dir, "card2_product.jpg"), quality=92)
    review_card(s["reviews"], t).save(os.path.join(out_dir, "card3_reviews.jpg"), quality=92)
    print("wrote", out_dir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
