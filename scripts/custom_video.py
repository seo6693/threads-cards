"""Render a one-off video from a scene script written for a single post (이벤트·프로모션 account).

A scene script is a small Python file that defines
    CONCEPT  = {"name": "스크래치 복권", "idea": "one line: what happens on screen and why it grabs attention"}
    END      = 9.0          # seconds, 6..15
    POSTER_AT = 5.0         # a moment where the product, price and event name are all visible
    def frame(t, ctx): ... -> RGBA image (1080x1350), or (image, shake_x, shake_y)

ctx (dict) gives you everything already loaded:
    spec        the draft's "motion" dict (hook, name, badge_price, from_price, to_price, unit, stamp,
                stats, cta, event_name, event_period (may be ""), ...)
    product     RGBA product photo, square 720x720, rounded white card around it (760x760)
    product_raw RGB original product photo
    banner      RGBA promotion thumbnail from the 기획전 list (original size), or None
    bleed       RGBA 1080x1350 full-frame version of the product photo
    P           colour palette {"a","b","c","hi"} (random per video), plus mm.RED/WHITE/BLACK
    mm          scripts/make_motion helpers: text_img, paste_center, fit_size, ease, slam, clamp,
                shake, rays, Confetti, won, deadline_pill, font (make_cards.font)
    W, H, FPS   1080, 1350, 30
Anything else (PIL drawing, math, random with a fixed seed) is fine. No network, no files outside the
post folder, no audio.
"""
import difflib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_motion as mm  # noqa: E402
import motion_styles as ms  # noqa: E402
from make_cards import font  # noqa: E402

W, H, FPS = mm.W, mm.H, mm.FPS
ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_scene(path):
    spec = importlib.util.spec_from_file_location("scene_" + pathlib.Path(path).parent.name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for k in ("CONCEPT", "END", "POSTER_AT", "frame"):
        if not hasattr(mod, k):
            raise SystemExit(f"scene script must define {k}")
    if not 6 <= float(mod.END) <= 15:
        raise SystemExit("END must be between 6 and 15 seconds")
    if not 0 < float(mod.POSTER_AT) < float(mod.END):
        raise SystemExit("POSTER_AT must be inside the video")
    c = mod.CONCEPT
    if not (isinstance(c, dict) and c.get("name") and c.get("idea")):
        raise SystemExit('CONCEPT must be {"name": ..., "idea": ...}')
    return mod


def context(spec, spec_dir):
    prod_raw = Image.open(pathlib.Path(spec_dir) / spec["product_image"]).convert("RGB")
    side = min(prod_raw.size)
    sq = prod_raw.crop(((prod_raw.width - side) // 2, (prod_raw.height - side) // 2,
                        (prod_raw.width + side) // 2, (prod_raw.height + side) // 2)).resize((720, 720), Image.LANCZOS)
    card = Image.new("RGBA", (760, 760), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, 759, 759], radius=56, fill=mm.WHITE)
    m = Image.new("L", (720, 720), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 719, 719], radius=40, fill=255)
    card.paste(sq, (20, 20), m)
    banner = None
    if spec.get("banner_image"):
        banner = Image.open(pathlib.Path(spec_dir) / spec["banner_image"]).convert("RGBA")
    mm.font = font
    return {"spec": spec, "product": card, "product_raw": prod_raw, "banner": banner,
            "bleed": ms.bleed_image(prod_raw), "P": mm.PALETTES[spec.get("palette", "yellow")],
            "mm": mm, "W": W, "H": H, "FPS": FPS}


def _frame(mod, t, ctx):
    r = mod.frame(t, ctx)
    im, sx, sy = (r if isinstance(r, tuple) else (r, 0, 0))
    if im.size != (W, H):
        raise SystemExit(f"frame() must return a {W}x{H} image, got {im.size}")
    return im.convert("RGBA"), int(sx), int(sy)


def render(scene_path, spec, spec_dir, out_path):
    mod = load_scene(scene_path)
    ctx = context(spec, spec_dir)
    end = float(mod.END)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "96k", out_path], stdin=subprocess.PIPE)
    for i in range(int(end * FPS)):
        im, sx, sy = _frame(mod, i / FPS, ctx)
        frame = Image.new("RGB", (W + 80, H + 80), mm.BLACK)
        frame.paste(im.convert("RGB"), (40 + sx, 40 + sy))
        ff.stdin.write(frame.crop((40, 40, 40 + W, 40 + H)).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
    return mod


def contact_sheet(video_path, out_jpg, end, n=6):
    """n frames side by side, to look at before posting."""
    tmp = pathlib.Path(out_jpg).with_suffix("")
    ims = []
    for k in range(n):
        t = end * (k + 0.5) / n
        f = f"{tmp}_{k}.jpg"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", video_path,
                        "-frames:v", "1", f], check=True)
        ims.append(Image.open(f).resize((360, 450)))
        pathlib.Path(f).unlink()
    sheet = Image.new("RGB", (360 * n, 450))
    for k, im in enumerate(ims):
        sheet.paste(im, (360 * k, 0))
    sheet.save(out_jpg, quality=85)
    return out_jpg


def _norm(code):
    code = re.sub(r"#.*", "", code)
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    return re.sub(r"\s+", " ", code)


def novelty_errors(project, scene_path):
    """New video must be a new idea: new concept name and code not a copy of an earlier scene."""
    errors = []
    mod = load_scene(scene_path)
    reg = json.loads((ROOT / "projects" / project / "video_patterns.json").read_text())
    name = mod.CONCEPT["name"].strip().lower()
    cards = ROOT / "projects" / project / "cards"
    for r in reg:
        if r.get("slug") and not (cards / r["slug"]).exists():
            continue  # that attempt was deleted and redone
        if r["name"].strip().lower() == name:
            errors.append(f"concept '{mod.CONCEPT['name']}' was already used on {r['date']}; design a new one")
    code = _norm(pathlib.Path(scene_path).read_text())
    others = [p for p in (ROOT / "projects" / project / "cards").glob("*/scene.py")
              if p.resolve() != pathlib.Path(scene_path).resolve()]
    others.append(ROOT / "scripts" / "scene_example.py")
    for p in others:
        r = difflib.SequenceMatcher(None, code, _norm(p.read_text())).ratio()
        if r > 0.6:
            errors.append(f"scene code is {r:.0%} the same as {p.relative_to(ROOT)}; write a new scene, not a variation")
    return errors


def register(project, mod, slug, date):
    path = ROOT / "projects" / project / "video_patterns.json"
    reg = json.loads(path.read_text())
    reg.append({"name": mod.CONCEPT["name"], "idea": mod.CONCEPT["idea"], "slug": slug, "date": date})
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")
