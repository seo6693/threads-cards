"""Make Instagram-safe square copies of a post's cards: <card_dir>/ig/<card>.jpg (1080x1080).
Instagram crops a carousel to the first photo's frame, and on many phones that frame is a
square no matter what. A 4:5 card is scaled to fit inside the square and the sides are
filled with a blurred, darkened copy of the same card, so nothing (hook, price, AI label)
gets cut. Run: python3 scripts/insta_square.py <card_dir> [...]   (new_post.py calls it
for instagram_manual projects)."""
import pathlib
import sys

from PIL import Image, ImageEnhance, ImageFilter

SIZE = 1080


def square(src, dst):
    im = Image.open(src).convert("RGB")
    bg = im.resize((SIZE, SIZE)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    scale = min(SIZE / im.width, SIZE / im.height)
    fg = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    bg.paste(fg, ((SIZE - fg.width) // 2, (SIZE - fg.height) // 2))
    dst.parent.mkdir(exist_ok=True)
    bg.save(dst, quality=92)


def run(card_dir):
    card_dir = pathlib.Path(card_dir)
    out = []
    for f in sorted(card_dir.glob("card*.jpg")):
        square(f, card_dir / "ig" / f.name)
        out.append(f.name)
    return out


if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(d, run(d))
