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
  "reply_note": "※ 가격·쿠폰은 시점마다 달라질 수 있어요",         # optional
  "deal_until": {"end": "2026-09-29T07:00:00+09:00",                # required when config
                 "seen": "17:40:00 남음 @ 2026-09-28 13:20 골드박스"}  # has require_deal_until
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
import make_motion  # noqa: E402

DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
RAW = "https://raw.githubusercontent.com/seo6693/threads-cards/main/"
# Videos must be served with a video content type; GitHub Pages does that, raw does not.
PAGES = "https://seo6693.github.io/threads-cards/"
KST = dt.timezone(dt.timedelta(hours=9))
FORMATS = json.loads((ROOT / "scripts" / "formats.json").read_text())
# Random delay between preparing a post and publishing it (minutes).
DELAY_MIN, DELAY_MAX = 4, 42
# Deal posts (config "require_deal_until") must be live at least this long after posting.
DEAL_MIN_LEFT_MIN = 120
WEEKDAYS = "월화수목금토일"


def deal_label(end):
    """'2026-09-29T07:00:00+09:00' -> '9/29(화) 오전 7시까지'. Times within 2 minutes
    of the hour (goldbox timers read 06:59:01) are shown as that hour."""
    t = dt.datetime.fromisoformat(end).astimezone(KST)
    if t.minute >= 58:
        t = (t + dt.timedelta(hours=1)).replace(minute=0)
    elif t.minute <= 2:
        t = t.replace(minute=0)
    ampm = "오전" if t.hour < 12 else ("낮" if t.hour == 12 else "오후")
    h = t.hour % 12 or 12
    hm = f"{h}시" if t.minute == 0 else f"{h}시 {t.minute}분"
    if t.hour == 0 and t.minute == 0:  # midnight belongs to the previous day
        y = t - dt.timedelta(days=1)
        return f"{y.month}/{y.day}({WEEKDAYS[y.weekday()]}) 자정까지"
    return f"{t.month}/{t.day}({WEEKDAYS[t.weekday()]}) {ampm} {hm}까지"


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
            pids = [d["product_id"], *d.get("more_product_ids", [])]
            when = d.get("published_at")
            if folder == "queue" or not when:
                ids.update(pids)
                continue
            t = dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S%z")
            if t >= cutoff:
                ids.update(pids)
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
        **_post_plan(cfg, state),
        "source": cfg.get("source", "search"),
        "source_note": cfg.get("source_note", ""),
        "formats": FORMATS,
        "avoid_openings": [first_line(d["text"]) for d in recent_posts(proj)],
        "recent_formats": state.get("recent_formats", [])[-4:],
        "linkbank_unused": _bank_unused(proj, cfg),
    }, ensure_ascii=False, indent=2))


TYPE_FORMAT = {"curation": "curation", "tip": "tip_post", "story": "scene_story", "deal_story": "deal_story"}


def _post_plan(cfg, state):
    """What this run should make. Each slot has a post type (config slot_types):
    curation = 3-5 products compared in one post, tip = useful info + related product,
    hero = one product in a strong single format (often video). "rotate" cycles the three."""
    slot = current_slot(cfg)
    hm = slot.strftime("%H:%M") if slot else None
    ptype = (cfg.get("slot_types") or {}).get(hm, "hero")
    if ptype == "rotate":
        recent = state.get("recent_post_types", [])
        options = [k for k in ("story", "curation", "tip", "hero") if k in (cfg.get("rotate_types") or ["curation", "tip", "hero"])]
        ptype = min(options, key=lambda k: max((i for i, r in enumerate(recent) if r == k), default=-1))
    allowed = cfg.get("formats") or list(FORMATS)
    if ptype in TYPE_FORMAT and TYPE_FORMAT[ptype] in allowed:
        fmt = TYPE_FORMAT[ptype]
    else:
        ptype = "hero"
        fmt = pick_format(state, [f for f in allowed if f not in TYPE_FORMAT.values()])
    return {"post_type": ptype, "format": fmt,
            "more_products_wanted": {"curation": "2-4 (required)", "deal_story": "2-4 (required)", "tip": "0-1", "story": "0",
                                     "hero": cfg.get("hero_more_products", "0")}[ptype],
            "hook_formulas": cfg.get("hook_formulas", []),
            "avoid_hook_formulas": state.get("recent_hook_formulas", [])[-2:],
            **_learned(cfg, state),
            "season_topics": (cfg.get("season_topics") or {}).get(str(dt.datetime.now(KST).month), [])}


def _learned(cfg, state):
    """Suggest the next hook formula from what has been getting views (scripts/learn.py)."""
    f = ROOT / "projects" / cfg["account"] / "learning.json"
    if not f.exists():
        return {}
    L = json.loads(f.read_text())
    w = {k: v for k, v in (L.get("formula_weights") or {}).items()
         if k not in state.get("recent_hook_formulas", [])[-2:]}
    pick = random.choices(list(w), weights=list(w.values()))[0] if w else None
    return {"suggested_hook_formula": pick, "top_posts_to_learn_from": L.get("top_posts", [])[:3],
            "best_hours": L.get("hours", {})}


def _bank_unused(proj, cfg):
    f = proj / "linkbank.json"
    if not f.exists():
        return 0
    recent = set(recent_ids(proj, cfg["selection"]["skip_if_posted_within_days"]))
    return sum(1 for k in json.loads(f.read_text()) if k not in recent)


def pick_format(state, allowed=None):
    """Least recently used format, never one of the last two posts' formats."""
    recent = state.get("recent_formats", [])
    pool = [k for k in FORMATS if not allowed or k in allowed]
    # About one post in three is a motion video.
    if "price_motion" in pool and "price_motion" not in recent[-2:]:
        return "price_motion"
    last_used = {k: max((i for i, r in enumerate(recent) if r == k), default=-1) for k in pool}
    options = [k for k in pool if k not in recent[-2:] and k != "price_motion"] or pool
    oldest = min(last_used[k] for k in options)
    return random.choice([k for k in options if last_used[k] == oldest])


def cmd_queue(project, draft_path):
    proj, cfg, state, state_path = load(project)
    d = json.loads(pathlib.Path(draft_path).read_text())

    errors = []
    need_keys = ["product_id", "product_name", "keyword", "link", "image", "text"]
    if not FORMATS.get(d.get("format"), {}).get("video"):
        need_keys.append("cards")
    if FORMATS.get(d.get("format"), {}).get("custom"):
        need_keys += ["video_script", "banner_image"]
    if d.get("format") in ("scene_story", "deal_story"):
        need_keys += ["scene_image", "hook_formula"]
        sc = (d.get("cards") or {}).get("scene") or {}
        if not sc.get("lines") or not 1 <= len(sc["lines"]) <= 3:
            errors.append("scene_story: cards.scene.lines needs 1-3 [text, highlight] lines")
        elif any(len(str(ln[0])) > 16 for ln in sc["lines"]):
            errors.append("scene_story: each hook line must be 16 characters or fewer (must read at a glance)")
        hf = cfg.get("hook_formulas", [])
        if hf and d.get("hook_formula") not in hf:
            errors.append(f"hook_formula must be one of {hf}")
        elif d.get("hook_formula") in state.get("recent_hook_formulas", [])[-2:]:
            errors.append(f"hook formula '{d.get('hook_formula')}' was used in the last 2 posts; use another")
    for k in need_keys:
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
    # Extra products: each becomes its own numbered reply with its own link.
    more = d.get("more_products") or []
    if len(more) > 4:
        errors.append("more_products: at most 4 (5 products per post)")
    seen = {str(d.get("product_id"))}
    recent_short = set(recent_ids(proj, min(7, cfg["selection"]["skip_if_posted_within_days"])))
    for i, mp in enumerate(more, 2):
        for k in ("product_id", "product_name", "link"):
            if not mp.get(k):
                errors.append(f"more_products[{i}] missing '{k}'")
        if not re.match(r"^https://link\.coupang\.com/a/\w+$", mp.get("link", "")):
            errors.append(f"more_products[{i}] link must be a partner short link")
        if str(mp.get("product_id")) in seen:
            errors.append(f"more_products[{i}] duplicates another product in this post")
        if str(mp.get("product_id")) in recent_short:
            errors.append(f"more_products[{i}] ({mp.get('product_name')}) was posted in the last 7 days")
        seen.add(str(mp.get("product_id")))
    if FORMATS.get(d.get("format"), {}).get("multi"):
        if not 2 <= len(more) <= 4:
            errors.append("curation needs 3-5 products in total (main + 2-4 more_products)")
        if any(not mp.get("image") for mp in more):
            errors.append("curation: every more_products entry needs an 'image' (its photo)")
        if not (d.get("cards") or {}).get("cover") or len((d.get("cards") or {}).get("ranks", [])) != len(more) + 1:
            errors.append("curation cards need 'cover' and one 'ranks' entry per product (main first)")
        elif (d["cards"]["cover"]).get("items"):
            errors.append("curation: leave cover.items out; the cover list is built from 'ranks' in the same order "
                          "(give each rank an optional 'short' name and 'cover_value')")
    fmt = d.get("format")
    allowed = cfg.get("formats") or list(FORMATS)
    if fmt not in FORMATS or fmt not in allowed:
        errors.append(f"'format' must be one of {allowed}")
    elif (len(allowed) > 1 and fmt in state.get("recent_formats", [])[-2:]
          and fmt != _post_plan(cfg, state)["format"]):  # the slot's own type (curation/tip) is always allowed
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
    deal = None
    if cfg.get("require_deal_until"):
        du = d.get("deal_until") or {}
        if not du.get("end") or not du.get("seen"):
            errors.append("deal_until {end, seen} is required for this account: read the item's "
                          "'HH:MM:SS 남음' timer on the goldbox page (RUNBOOK step 1). No verified end time -> pick another product")
        else:
            try:
                end = dt.datetime.fromisoformat(du["end"])
                if end.tzinfo is None:
                    raise ValueError("needs +09:00")
                left = (end - dt.datetime.now(KST)).total_seconds() / 60
                deal = {"end": end.astimezone(KST).isoformat(timespec="seconds"), "label": deal_label(du["end"])}
                if left < DELAY_MAX + DEAL_MIN_LEFT_MIN:
                    errors.append(f"deal ends in {left:.0f} min; it needs >= {DELAY_MAX + DEAL_MIN_LEFT_MIN} min left. Pick another product")
                elif left > 14 * 24 * 60:
                    errors.append("deal_until.end is more than 14 days away; that is not a timer reading")
                elif deal["label"] not in text:
                    errors.append(f"text must state the deal end exactly as '{deal['label']}'")
            except ValueError as e:
                errors.append(f"deal_until.end must be ISO time with +09:00 ({e})")
    if errors:
        sys.exit("draft rejected:\n- " + "\n- ".join(errors))

    stamp = dt.datetime.now(KST).strftime("%Y-%m-%d-%H%M")
    slug = f"{stamp}-{d['product_id']}"
    card_dir = proj / "cards" / slug
    card_dir.mkdir(parents=True, exist_ok=True)
    img = card_dir / ("product" + pathlib.Path(d["image"]).suffix)
    shutil.copy(d["image"], img)
    if FORMATS[fmt].get("custom"):
        import custom_video
        m = dict(d.get("motion") or {})
        for k in ("name", "badge_price", "event_name"):
            if not m.get(k):
                sys.exit(f"draft rejected:\n- 'motion' is missing {k}")
        ban = card_dir / ("banner" + pathlib.Path(d["banner_image"]).suffix)
        shutil.copy(d["banner_image"], ban)
        scene = card_dir / "scene.py"
        shutil.copy(d["video_script"], scene)
        errs = custom_video.novelty_errors(project, scene)
        if errs:
            shutil.rmtree(card_dir)
            sys.exit("draft rejected:\n- " + "\n- ".join(errs))
        rp = state.get("recent_palettes", [])[-2:]
        m.setdefault("palette", random.choice([c for c in make_motion.PALETTES if c not in rp]))
        state["recent_palettes"] = (state.get("recent_palettes", []) + [m["palette"]])[-6:]
        m.update(product_image=img.name, banner_image=ban.name)
        if deal:
            m["deadline"] = deal["label"]
        (card_dir / "motion.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        mod = custom_video.render(str(scene), m, str(card_dir), str(card_dir / "video.mp4"))
        make_motion.poster(str(card_dir / "video.mp4"), str(card_dir / "poster.jpg"), at=float(mod.POSTER_AT))
        custom_video.contact_sheet(str(card_dir / "video.mp4"), str(card_dir / "frames.jpg"), float(mod.END))
        custom_video.register(project, mod, card_dir.name, dt.date.today().isoformat())
        rel = str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
        media = {"video": PAGES + rel + "video.mp4", "thumb": RAW + rel + "poster.jpg", "images": [],
                 "video_concept": mod.CONCEPT["name"]}
    elif FORMATS[fmt].get("video"):
        m = d.get("motion") or {}
        need = ("hook", "unit", "from_price", "to_price", "stamp", "name", "badge_price", "stats")
        missing = [k for k in need if not m.get(k)]
        if missing:
            sys.exit("draft rejected:\n- 'motion' is missing " + ", ".join(missing))
        m = dict(m, product_image=img.name)
        if deal:
            m["deadline"] = deal["label"]
        # Rotate the video style and colour so consecutive videos never look the same:
        # least-recently-used style, and a palette different from the last two videos.
        rv = state.get("recent_video_styles", [])
        order = {st: (rv[::-1].index(st) if st in rv else 99) for st in make_motion.STYLES}
        oldest = max(order.values())
        m.setdefault("style", random.choice([st for st, v in order.items() if v == oldest]))
        rp = state.get("recent_palettes", [])[-2:]
        m.setdefault("palette", random.choice([c for c in make_motion.PALETTES if c not in rp] or list(make_motion.PALETTES)))
        state["recent_video_styles"] = (rv + [m["style"]])[-6:]
        state["recent_palettes"] = (state.get("recent_palettes", []) + [m["palette"]])[-6:]
        (card_dir / "motion.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        make_motion.render(m, str(card_dir), str(card_dir / "video.mp4"))
        make_motion.poster(str(card_dir / "video.mp4"), str(card_dir / "poster.jpg"),
                           at=make_motion.poster_time(m["style"]))
        rel = str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
        media = {"video": PAGES + rel + "video.mp4", "thumb": RAW + rel + "poster.jpg", "images": []}
    elif FORMATS[fmt].get("multi"):
        ranks = []
        for i, r in enumerate(d["cards"]["ranks"]):
            src = d["image"] if i == 0 else more[i - 1]["image"]
            name = "product" + pathlib.Path(src).suffix if i == 0 else f"p{i + 1}" + pathlib.Path(src).suffix
            if i:
                shutil.copy(src, card_dir / name)
            ranks.append(dict(r, rank=i + 1, image=name))
        spec = {"theme": d.get("theme") or random.choice(cfg.get("theme_variants", [cfg["theme"]])),
                "product_image": img.name, "cover": d["cards"]["cover"], "ranks": ranks,
                "order": ["cover"] + [f"rank{i + 1}" for i in range(len(ranks))]}
        if d.get("scene_image"):  # deal_story: a real-life scene with the hook goes in front of the cover
            sc_name = "scene" + pathlib.Path(d["scene_image"]).suffix
            shutil.copy(d["scene_image"], card_dir / sc_name)
            spec.update(scene_image=sc_name, scene=d["cards"]["scene"], order=["scene"] + spec["order"])
        (card_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        names = make_cards.main(str(card_dir / "spec.json"), str(card_dir))
        base = RAW + str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
        media = {"images": [base + f for f in names]}
    else:
        fcards = FORMATS[fmt]["cards"]
        spec = dict(d["cards"], theme=d.get("theme") or random.choice(cfg.get("theme_variants", [cfg["theme"]])),
                    product_image=img.name, order=fcards["order"])
        if d.get("scene_image"):
            sc_name = "scene" + pathlib.Path(d["scene_image"]).suffix
            shutil.copy(d["scene_image"], card_dir / sc_name)
            spec["scene_image"] = sc_name
        if deal:
            spec["product"] = dict(spec.get("product", {}), deadline=deal["label"])
        if "hook" in fcards["order"]:
            spec["hook"] = dict(spec.get("hook", {}), layout=fcards["hook_layout"])
        (card_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        names = make_cards.main(str(card_dir / "spec.json"), str(card_dir))
        base = RAW + str(card_dir.relative_to(ROOT)).replace("\\", "/") + "/"
        media = {"images": [base + f for f in names]}
    note = d.get("reply_note") or "※ 가격·쿠폰은 시점마다 달라질 수 있어요"
    if deal:
        note = f"⏰ 특가 {deal['label']} (쿠팡 골드박스 표시 기준)\n" + note
    post = {
        "account": cfg["account"],
        "product_id": str(d["product_id"]),
        "product_name": d["product_name"],
        "keyword": d["keyword"],
        "text": text,
        **media,
        "reply": d.get("reply_text") and f"{d['reply_text']}\n{d['link']}\n{note}" or f"🛒 구매 링크 → {d['link']}\n{note}",
        "format": fmt,
        "post_type": {"curation": "curation", "tip_post": "tip", "scene_story": "story", "deal_story": "deal_story"}.get(fmt, "hero"),
        "hook_formula": d.get("hook_formula", ""),
        "topic_source": d.get("topic_source", ""),
        "publish_after": (dt.datetime.now(KST) + dt.timedelta(
            minutes=random.randint(DELAY_MIN, DELAY_MAX))).isoformat(timespec="seconds"),
    }
    if more:
        intro = f"{d['reply_text']}\n" if d.get("reply_text") else ""
        price = f" {d['price']}" if d.get("price") else ""
        post["reply"] = f"{intro}1) {d['product_name']}{price}\n{d['link']}\n{note}"
        # Several link comments in a row from a new account looked like spam to Meta (two accounts
        # were checkpointed on 10/4). Only `max_link_replies` comments carry a link; the other
        # products are listed in one plain comment that points to the profile link page.
        max_links = int(cfg.get("max_link_replies", 1))
        linked = more[:max(0, max_links - 1)]
        rest = more[len(linked):]
        post["replies"] = [post["reply"]] + [
            f"{i}) {mp.get('line') or mp['product_name']}\n{mp['link']}" for i, mp in enumerate(linked, 2)]
        if rest:
            names = "\n".join(f"{i}) {mp['product_name']}" for i, mp in enumerate(rest, 2 + len(linked)))
            post["replies"].append(f"{names}\n→ 나머지 링크는 프로필 링크 '상품 모음'에 순서대로 있어요")
        post["more_product_ids"] = [str(mp["product_id"]) for mp in more]
        post["more_products"] = [{"product_id": str(mp["product_id"]), "product_name": mp["product_name"],
                                  "link": mp["link"], "price": mp.get("price", "")} for mp in more]
    post["link"] = d["link"]
    post["price"] = d.get("price", "")
    if d.get("link_source") == "bank":
        post["link_source"] = "bank"
    if deal:
        post["deal_until"] = deal["end"]
        post["deal_label"] = deal["label"]
    if d.get("topic_tag"):
        post["topic_tag"] = re.sub(r"[.&\s]", "", d["topic_tag"])[:50]
    if cfg.get("channel") == "instagram_manual":
        import insta_square  # square copies so Instagram never crops the cards
        insta_square.run(card_dir)
    qfile = proj / "queue" / f"{slug}.json"
    qfile.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")

    state["next_keyword"] = (state["next_keyword"] + 1) % len(cfg["keywords"])
    state["recent_formats"] = (state.get("recent_formats", []) + [fmt])[-8:]
    ptype = {"curation": "curation", "tip_post": "tip", "scene_story": "story", "deal_story": "deal_story"}.get(fmt, "hero")
    state["recent_post_types"] = (state.get("recent_post_types", []) + [ptype])[-8:]
    if d.get("hook_formula"):
        state["recent_hook_formulas"] = (state.get("recent_hook_formulas", []) + [d["hook_formula"]])[-8:]
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


def cmd_slot(project, mode=None):
    proj, cfg, _, _ = load(project)
    blocked = proj / "BLOCKED.json"
    if blocked.exists():
        print(json.dumps({"blocked": True, "already_posted": True,
                          "detail": json.loads(blocked.read_text())}, ensure_ascii=False))
        return
    if mode == "makeup":
        # Make-up for a slot that was skipped earlier today: allowed only while today's
        # posts are fewer than the slots whose time has already passed.
        today = dt.datetime.now(KST).date().isoformat()
        n = sum(1 for folder in ("done", "queue") for f in (proj / folder).glob(today + "-*.json")
                if not json.loads(f.read_text()).get("reply_to_media_id"))
        now = dt.datetime.now(KST)
        due = sum(1 for hm in cfg.get("schedule_kst", [])
                  if now >= now.replace(hour=int(hm[:2]), minute=int(hm[3:]), second=0, microsecond=0))
        print(json.dumps({"slot": "makeup", "already_posted": n >= due,
                          "posted_today": n, "slots_passed_today": due}, ensure_ascii=False))
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
    elif len(sys.argv) >= 4 and sys.argv[1] == "slot" and sys.argv[3] == "makeup":
        cmd_slot(sys.argv[2], "makeup")
    elif len(sys.argv) >= 3 and sys.argv[1] == "slot":
        cmd_slot(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "skip":
        cmd_skip(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        sys.exit(__doc__)
