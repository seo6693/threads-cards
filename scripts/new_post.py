"""Helpers for the scheduled per-project runs.

  python scripts/new_post.py next  <project>
      Prints the keyword to search this run, the product ids posted in
      the last N days (skip these), and the project's selection/copy rules.

  python scripts/new_post.py queue <project> <draft.json>
      Validates the draft, renders the 3 cards into
      projects/<project>/cards/<slug>/, writes the queue file and advances
      the keyword rotation. Commit and push afterwards to publish.

draft.json:
{
  "product_id": "8720424912",
  "product_name": "젠스테 무선 터치 USB 무드등",
  "keyword": "무드등",
  "link": "https://link.coupang.com/a/xxxx",
  "image": "/abs/path/product.jpg",
  "cards": {"hook": {...}, "product": {...}, "reviews": {...}},   # see make_cards.py
  "text": "본문 (<=500자, 고지 문구 포함)",
  "reply_note": "※ 가격·쿠폰은 시점마다 달라질 수 있어요"          # optional
}
"""
import datetime as dt
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_cards  # noqa: E402

DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
RAW = "https://raw.githubusercontent.com/seo6693/threads-cards/main/"
KST = dt.timezone(dt.timedelta(hours=9))


def load(project):
    proj = ROOT / "projects" / project
    if not (proj / "config.json").exists():
        sys.exit(f"unknown project '{project}' (expected one of: "
                 f"{', '.join(p.name for p in (ROOT / 'projects').iterdir())})")
    cfg = json.loads((proj / "config.json").read_text())
    state_path = proj / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"next_keyword": 0}
    return proj, cfg, state, state_path


def recent_ids(proj, days):
    cutoff = dt.datetime.now(KST) - dt.timedelta(days=days)
    ids = set()
    for folder in ("done", "queue"):
        for f in (proj / folder).glob("*.json"):
            d = json.loads(f.read_text())
            if not d.get("product_id"):
                continue
            when = d.get("published_at")
            if folder == "queue" or not when:
                ids.add(d["product_id"])
                continue
            t = dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S%z")
            if t >= cutoff:
                ids.add(d["product_id"])
    return sorted(ids)


def cmd_next(project):
    proj, cfg, state, _ = load(project)
    kws = cfg["keywords"]
    i = state["next_keyword"] % len(kws)
    print(json.dumps({
        "project": project,
        "account": cfg["account"],
        "threads": cfg["threads"],
        "keyword": kws[i],
        "backup_keywords": [kws[(i + k) % len(kws)] for k in (1, 2)],
        "skip_product_ids": recent_ids(proj, cfg["selection"]["skip_if_posted_within_days"]),
        "selection": cfg["selection"],
        "copy_rules": cfg["copy_rules"],
        "tone": cfg["tone"],
        "theme": cfg["theme"],
    }, ensure_ascii=False, indent=2))


def cmd_queue(project, draft_path):
    proj, cfg, state, state_path = load(project)
    d = json.loads(pathlib.Path(draft_path).read_text())

    errors = []
    for k in ("product_id", "product_name", "keyword", "link", "image", "cards", "text"):
        if not d.get(k):
            errors.append(f"missing '{k}'")
    text = d.get("text", "")
    if len(text) > 500:
        errors.append(f"text is {len(text)} chars (max 500)")
    if DISCLOSURE not in text:
        errors.append("text must contain the exact disclosure line: " + DISCLOSURE)
    if "http" in text:
        errors.append("text must not contain links (the link goes in the first comment)")
    if not re.match(r"^https://link\.coupang\.com/a/\w+$", d.get("link", "")):
        errors.append("link must be a partner short link https://link.coupang.com/a/...")
    if str(d.get("product_id")) in recent_ids(proj, cfg["selection"]["skip_if_posted_within_days"]):
        errors.append(f"product {d.get('product_id')} was already posted recently")
    if errors:
        sys.exit("draft rejected:\n- " + "\n- ".join(errors))

    stamp = dt.datetime.now(KST).strftime("%Y-%m-%d-%H%M")
    slug = f"{stamp}-{d['product_id']}"
    card_dir = proj / "cards" / slug
    card_dir.mkdir(parents=True, exist_ok=True)
    img = card_dir / ("product" + pathlib.Path(d["image"]).suffix)
    shutil.copy(d["image"], img)
    spec = dict(d["cards"], theme=cfg["theme"], product_image=img.name)
    (card_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    make_cards.main(str(card_dir / "spec.json"), str(card_dir))

    base = RAW + str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
    note = d.get("reply_note") or "※ 가격·쿠폰은 시점마다 달라질 수 있어요"
    post = {
        "account": cfg["account"],
        "product_id": str(d["product_id"]),
        "product_name": d["product_name"],
        "keyword": d["keyword"],
        "text": text,
        "images": [base + f for f in ("card1_hook.jpg", "card2_product.jpg", "card3_reviews.jpg")],
        "reply": f"🛒 구매 링크 → {d['link']}\n{note}",
    }
    qfile = proj / "queue" / f"{slug}.json"
    qfile.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")

    state["next_keyword"] = (state["next_keyword"] + 1) % len(cfg["keywords"])
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({"queued": str(qfile.relative_to(ROOT)), "cards": str(card_dir.relative_to(ROOT))},
                     ensure_ascii=False, indent=2))


def current_slot(cfg, now=None):
    """Latest scheduled slot start at or before now (KST), allowing runs that start a bit early."""
    now = now or dt.datetime.now(KST)
    starts = []
    for day in (now.date() - dt.timedelta(days=1), now.date()):
        for hm in cfg.get("schedule_kst", []):
            h, m = map(int, hm.split(":"))
            starts.append(dt.datetime(day.year, day.month, day.day, h, m, tzinfo=KST))
    past = [s for s in starts if s <= now + dt.timedelta(minutes=5)]
    return max(past) if past else None


def cmd_slot(project):
    proj, cfg, _, _ = load(project)
    slot = current_slot(cfg)
    posted = []
    if slot:
        guard = slot - dt.timedelta(minutes=5)
        for folder in ("done", "queue"):
            for f in (proj / folder).glob("*.json"):
                d = json.loads(f.read_text())
                if d.get("reply_to_media_id"):
                    continue
                when = d.get("published_at")
                t = (dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S%z") if when
                     else dt.datetime.strptime(f.name[:15], "%Y-%m-%d-%H%M").replace(tzinfo=KST)
                     if re.match(r"\d{4}-\d{2}-\d{2}-\d{4}", f.name) else None)
                if t and t >= guard:
                    posted.append(f.name)
    print(json.dumps({"slot": slot.isoformat() if slot else None,
                      "already_posted": bool(posted), "posted_files": posted}, ensure_ascii=False))


def cmd_skip(project, reason):
    proj, cfg, _, _ = load(project)
    now = dt.datetime.now(KST)
    slot = current_slot(cfg)
    rec = {"account": cfg["account"], "skipped_at": now.isoformat(timespec="seconds"),
           "slot": slot.isoformat() if slot else None, "reason": reason}
    out = proj / "skipped" / f"{now.strftime('%Y-%m-%d-%H%M')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"recorded": str(out.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "next":
        cmd_next(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "queue":
        cmd_queue(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "slot":
        cmd_slot(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "skip":
        cmd_skip(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        sys.exit(__doc__)
