"""Learn from the numbers: per project, which hook formulas, topics, post types and hours get views.

Reads checks/insights.json (collected daily) and the done/ files, writes projects/<p>/learning.json:
  formula_weights  - selection weights for hook formulas (more views -> picked more often;
                     every formula keeps a floor weight so new ideas still get tested)
  formulas / types / hours - average views per group with sample sizes
  top_posts        - best recent posts (topic_source, hook, views) to imitate
`new_post.py next` uses formula_weights to suggest the next hook formula.
"""
import collections
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
KST = dt.timezone(dt.timedelta(hours=9))
FLOOR = 0.15


def avg(xs):
    return round(sum(xs) / len(xs), 1) if xs else 0


def main():
    ins = json.loads((ROOT / "checks" / "insights.json").read_text())
    for name, v in ins["projects"].items():
        proj = ROOT / "projects" / name
        if not (proj / "config.json").exists() or not isinstance(v.get("posts"), list):
            continue
        cfg = json.loads((proj / "config.json").read_text())
        by_f, by_t, by_h = (collections.defaultdict(list) for _ in range(3))
        rows = []
        for p in v["posts"]:
            views = p.get("views")
            if views is None or not p.get("published_at"):
                continue
            t = dt.datetime.strptime(p["published_at"], "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
            if t < dt.datetime.now(KST) - dt.timedelta(days=28):
                continue
            by_t[{"curation": "비교", "tip_post": "꿀팁", "scene_story": "이야기"}.get(p.get("format"), "대표")].append(views)
            by_h[f"{t.hour:02d}시"].append(views)
            if p.get("hook_formula"):
                by_f[p["hook_formula"]].append(views)
            rows.append({"views": views, "hook_formula": p.get("hook_formula", ""), "topic_source": p.get("topic_source", ""),
                         "product": p.get("product"), "format": p.get("format"), "when": t.strftime("%m/%d %H:%M"),
                         "permalink": p.get("permalink")})
        formulas = cfg.get("hook_formulas", [])
        overall = avg([r["views"] for r in rows]) or 1
        weights = {}
        for f in formulas:
            xs = by_f.get(f, [])
            # few samples -> stay near 1 (keep testing); more samples -> trust the average
            score = (sum(xs) + 3 * overall) / (len(xs) + 3) / overall
            weights[f] = round(max(FLOOR, score), 2)
        out = {"updated": dt.datetime.now(KST).isoformat(timespec="minutes"), "posts_28d": len(rows),
               "avg_views_28d": overall if rows else 0,
               "formula_weights": weights,
               "formulas": {k: {"avg": avg(x), "n": len(x)} for k, x in by_f.items()},
               "types": {k: {"avg": avg(x), "n": len(x)} for k, x in by_t.items()},
               "hours": {k: {"avg": avg(x), "n": len(x)} for k, x in sorted(by_h.items())},
               "top_posts": sorted(rows, key=lambda r: -r["views"])[:5]}
        (proj / "learning.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print(name, out["posts_28d"], "posts, weights", weights)


if __name__ == "__main__":
    main()
