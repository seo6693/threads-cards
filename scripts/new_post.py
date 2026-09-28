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
import difflib
import json
import pathlib
import random
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_cards  # noqa: E402

DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
RAW = "https://raw.githubusercontent.com/seo6693/threads-cards/main/"
KST = dt.timezone(dt.timedelta(hours=9))
FORMATS = json.loads((ROOT / "scripts" / "formats.json").read_text())
# Random delay between preparing a post and publishing it (minutes).
DELAY_MIN, DELAY_MAX = 4, 42


def recent_posts(proj, n=12):
    posts = []
    for f in (proj / "done").glob("*.json"):
        d = json.loads(f.read_text())
        if d.get("text"):
            posts.append((d.get("published_at", ""), d))
    posts.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in posts[:n]]


def first_line(text):
    return next((ln.strip() for ln in text.splitlines() if ln.strip()), "")


def body_only(text):
    return text.replace(DISCLOSURE, "").strip()


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
        "theme_variants": cfg.get("theme_variants", [cfg["theme"]]),
        "topic_tags": cfg.get("topic_tags", []),
        "format": pick_format(state),
        "formats": FORMATS,
        "avoid_openings": [first_line(d["text"]) for d in recent_posts(proj)],
        "recent_formats": state.get("recent_formats", [])[-4:],
    }, ensure_ascii=False, indent=2))


def pick_format(state):
    """Least recently used format, never one of the last two posts' formats."""
    recent = state.get("recent_formats", [])
    last_used = {k: max((i for i, r in enumerate(recent) if r == k), default=-1) for k in FORMATS}
    options = [k for k in FORMATS if k not in recent[-2:]] or list(FORMATS)
    oldest = min(last_used[k] for k in options)
    return random.choice([k for k in options if last_used[k] == oldest])


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
    fmt = d.get("format")
    if fmt not in FORMATS:
        errors.append(f"'format' must be one of {list(FORMATS)}")
    elif fmt in state.get("recent_formats", [])[-2:]:
        errors.append(f"format '{fmt}' was used in one of the last 2 posts; pick another")
    # Anti-copy: the opening and the body must not look like recent posts.
    fl = first_line(text)
    for old_post in recent_posts(proj):
        ofl = first_line(old_post["text"])
        if difflib.SequenceMatcher(None, fl, ofl).ratio() > 0.6:
            errors.append(f"first line is too close to a recent post: '{ofl}'")
            break
    for old_post in recent_posts(proj):
        r = difflib.SequenceMatcher(None, body_only(text), body_only(old_post["text"])).ratio()
        if r > 0.5:
            errors.append(f"body is {r:.0%} similar to a recent post ({old_post.get('product_name')}); restructure it")
            break
    if text.count("✔️") >= 3 and sum(o["text"].count("✔️") >= 3 for o in recent_posts(proj, 2)) >= 1:
        errors.append("the previous post already used a ✔️ bullet list; use a different structure")
    if not re.search(r"[?？]\s*$|[?？]\s*\n", body_only(text)):
        errors.append("end the body (before the disclosure) with a question to invite replies")
    if errors:
        sys.exit("draft rejected:\n- " + "\n- ".join(errors))

    stamp = dt.datetime.now(KST).strftime("%Y-%m-%d-%H%M")
    slug = f"{stamp}-{d['product_id']}"
    card_dir = proj / "cards" / slug
    card_dir.mkdir(parents=True, exist_ok=True)
    img = card_dir / ("product" + pathlib.Path(d["image"]).suffix)
    shutil.copy(d["image"], img)
    fcards = FORMATS[fmt]["cards"]
    spec = dict(d["cards"], theme=d.get("theme") or random.choice(cfg.get("theme_variants", [cfg["theme"]])),
                product_image=img.name, order=fcards["order"])
    if "hook" in fcards["order"]:
        spec["hook"] = dict(spec.get("hook", {}), layout=fcards["hook_layout"])
    (card_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    names = make_cards.main(str(card_dir / "spec.json"), str(card_dir))

    base = RAW + str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
    note = d.get("reply_note") or "※ 가격·쿠폰은 시점마다 달라질 수 있어요"
    post = {
        "account": cfg["account"],
        "product_id": str(d["product_id"]),
        "product_name": d["product_name"],
        "keyword": d["keyword"],
        "text": text,
        "images": [base + f for f in names],
        "reply": d.get("reply_text") and f"{d['reply_text']}\n{d['link']}\n{note}" or f"🛒 구매 링크 → {d['link']}\n{note}",
        "format": fmt,
        "publish_after": (dt.datetime.now(KST) + dt.timedelta(
            minutes=random.randint(DELAY_MIN, DELAY_MAX))).isoformat(timespec="seconds"),
    }
    if d.get("topic_tag"):
        post["topic_tag"] = re.sub(r"[.&\s]", "", d["topic_tag"])[:50]
    qfile = proj / "queue" / f"{slug}.json"
    qfile.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")

    state["next_keyword"] = (state["next_keyword"] + 1) % len(cfg["keywords"])
    state["recent_formats"] = (state.get("recent_formats", []) + [fmt])[-8:]
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({"queued": str(qfile.relative_to(ROOT)), "cards": str(card_dir.relative_to(ROOT)),
                      "format": fmt, "publish_after": post["publish_after"]},
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
    blocked = proj / "BLOCKED.json"
    if blocked.exists():
        print(json.dumps({"blocked": True, "already_posted": True,
                          "detail": json.loads(blocked.read_text())}, ensure_ascii=False))
        return
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
