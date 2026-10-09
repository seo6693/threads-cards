"""Build shop/<project>/index.html: the account's 'profile link' page listing the products
posted in the last 14 days (newest first), each with its partner link.
Runs in GitHub Actions after publishing; served by GitHub Pages at
https://seo6693.github.io/threads-cards/shop/<project>/"""
import datetime as dt
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/seo6693/threads-cards/main/"
DISCLOSURE = "이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
KST = dt.timezone(dt.timedelta(hours=9))

PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f6f5f1;--card:#fff;--ink:#16181d;--muted:#6b7078;--accent:{accent};--line:#e6e3dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121316;--card:#1c1e22;--ink:#f2f2f2;--muted:#a2a6ad;--line:#2b2e33}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:640px;margin:0 auto;padding:20px 16px 48px}}
h1{{font-size:24px;margin:8px 0 4px}}.sub{{color:var(--muted);font-size:14px;margin:0 0 6px}}
.disc{{font-size:12.5px;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin:10px 0 18px}}
.day{{font-weight:700;margin:22px 0 8px;color:var(--muted);font-size:14px}}
a.item{{display:flex;gap:12px;align-items:center;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;margin:0 0 10px}}
a.item img{{width:76px;height:76px;object-fit:cover;border-radius:10px;background:#eee;flex:none}}
.ph{{width:76px;height:76px;border-radius:10px;background:var(--accent);opacity:.18;flex:none}}
.name{{font-weight:650;line-height:1.35}}.price{{color:var(--accent);font-weight:800;margin-top:2px}}
.go{{margin-left:auto;font-weight:700;color:var(--accent);white-space:nowrap;padding-left:6px}}
footer{{color:var(--muted);font-size:12px;margin-top:28px}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">{sub}</p>
<div class="disc">{disc} 가격·쿠폰은 시점마다 달라질 수 있어요.</div>
{body}
<footer>마지막 업데이트 {updated}</footer>
</main></body></html>"""

ACCENT = {"nutri": "#2f6fd6", "deals": "#e8590c", "fresh": "#0f9d8a", "promo": "#7048e8"}


def img_for(proj, slug, name):
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        f = proj / "cards" / slug / (name + ext)
        if f.exists():
            return RAW + str(f.relative_to(ROOT)).replace("\\", "/")
    return ""


def build(proj):
    cfg = json.loads((proj / "config.json").read_text())
    cutoff = dt.datetime.now(KST) - dt.timedelta(days=14)
    rows = []
    for f in sorted((proj / "done").glob("*.json"), reverse=True):
        d = json.loads(f.read_text())
        if d.get("reply_to_media_id") or not d.get("published_at") or not ((d.get("result") or {}).get("media_id") or (d.get("result") or {}).get("manual")):
            continue
        t = dt.datetime.strptime(d["published_at"], "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
        if t < cutoff:
            continue
        slug = f.stem
        link = d.get("link") or next((w for w in (d.get("reply") or "").split() if w.startswith("https://link.coupang.com/")), "")
        if not link:
            continue
        items = [{"name": d.get("product_name", ""), "price": d.get("price", ""), "link": link,
                  "img": img_for(proj, slug, "product")}]
        for i, mp in enumerate(d.get("more_products") or [], 2):
            items.append({"name": mp["product_name"], "price": mp.get("price", ""), "link": mp["link"],
                          "img": img_for(proj, slug, f"p{i}")})
        deal = d.get("deal_label")
        if deal and d.get("deal_until") and dt.datetime.fromisoformat(d["deal_until"]) < dt.datetime.now(KST):
            deal = "특가 마감 · 지금 가격은 들어가서 확인"
        rows.append((t, items, deal))
    days = {}
    for t, items, deal in rows:
        days.setdefault(t.strftime("%m/%d"), []).append((items, deal))
    parts = []
    for day, groups in days.items():
        parts.append(f'<div class="day">{day}</div>')
        for items, deal in groups:
            for it in items:
                pic = f'<img src="{html.escape(it["img"])}" alt="" loading="lazy">' if it["img"] else '<div class="ph"></div>'
                price = f'<div class="price">{html.escape(it["price"])}</div>' if it["price"] else ""
                dl = f'<div class="sub">⏰ {html.escape(deal)}</div>' if deal else ""
                parts.append(f'<a class="item" href="{html.escape(it["link"])}" target="_blank" rel="noopener sponsored">'
                             f'{pic}<div><div class="name">{html.escape(it["name"])}</div>{price}{dl}</div>'
                             f'<span class="go">보기 ›</span></a>')
    if not parts:
        parts.append('<p class="sub">곧 첫 상품이 올라와요.</p>')
    title = f'{cfg.get("label", proj.name)} 모음'
    out = PAGE.format(title=html.escape(title), sub=f'{html.escape(cfg.get("threads") or "인스타")} 에 올라온 상품 (최근 2주)',
                      disc=DISCLOSURE, body="\n".join(parts), accent=ACCENT.get(proj.name, "#2f6fd6"),
                      updated=(max(t for t, _, _ in rows) if rows else dt.datetime.now(KST)).strftime("%m/%d %H:%M"))
    dest = ROOT / "shop" / proj.name / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.read_text() != out:  # avoid a commit every 10 minutes
        dest.write_text(out)
    return dest, sum(len(i) for _, i, _ in rows)


if __name__ == "__main__":
    for proj in sorted((ROOT / "projects").iterdir()):
        if (proj / "config.json").exists():
            dest, n = build(proj)
            print(dest.relative_to(ROOT), n, "products")
