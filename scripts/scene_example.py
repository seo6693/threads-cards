"""EXAMPLE ONLY — shows the scene API. Never post this pattern; queue rejects copies of it.

Concept: a phone lock-screen notification drops in announcing the event, then the product.
"""
import math

from PIL import Image, ImageDraw

CONCEPT = {"name": "예시: 잠금화면 알림", "idea": "잠금화면에 행사 알림이 뜨고, 눌러서 열면 상품과 가격이 나온다"}
END = 7.0
POSTER_AT = 4.5


def frame(t, ctx):
    mm, P, spec, W, H = ctx["mm"], ctx["P"], ctx["spec"], ctx["W"], ctx["H"]
    im = Image.new("RGBA", (W, H), (20, 24, 40, 255))
    d = ImageDraw.Draw(im)
    mm.paste_center(im, mm.text_img("9:41", "Black", 200, mm.WHITE), W / 2, 260)
    if t > 0.4:  # notification drops in
        k = mm.ease((t - 0.4) / 0.4)
        y = -200 + 650 * k
        d.rounded_rectangle([60, y, W - 60, y + 220], radius=40, fill=(245, 245, 250, 255))
        mm.paste_center(im, mm.text_img(spec.get("event_name", "쿠팡 행사"), "Black", 56, mm.BLACK), W / 2, y + 80)
        if spec.get("event_period"):
            mm.paste_center(im, mm.text_img(spec["event_period"], "Bold", 44, (90, 90, 100)), W / 2, y + 160)
    if t > 3.0:  # opened: product + price
        a = mm.ease((t - 3.0) / 0.5)
        mm.paste_center(im, ctx["product"], W / 2, 820, 0.7 * a)
        mm.paste_center(im, mm.text_img(spec["badge_price"], "Black", 120, P["a"]), W / 2, 1200, 1, 0, a)
    if ctx["banner"] is not None and t < 3.0:
        mm.paste_center(im, ctx["banner"].resize((600, int(600 * ctx["banner"].height / ctx["banner"].width))), W / 2, 1000, 1, 0, 0.9)
    return im
