"""Pre-made partner links, so a run can still post when Coupang Partners has logged out.

Partner short links never expire, but making one needs a signed-in Partners page. While
signed in, links for many good candidates are made in one go and kept in
projects/<project>/linkbank.json:
  {"<productId>": {"title": "...", "link": "https://link.coupang.com/a/...",
                   "note": "why it is a candidate", "added": "2026-09-29"}}
Everything else a post needs (price, reviews, image) comes from the public product page
https://www.coupang.com/vp/products/<productId>, which works without Partners.

  python3 scripts/linkbank.py add <project> <file.json>   # list of {pid,title,link,note}
  python3 scripts/linkbank.py pick <project>              # unused entries, best first
"""
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import new_post  # noqa: E402


def path(project):
    return ROOT / "projects" / project / "linkbank.json"


def load(project):
    p = path(project)
    return json.loads(p.read_text()) if p.exists() else {}


def add(project, file):
    bank = load(project)
    today = dt.date.today().isoformat()
    n = 0
    for e in json.loads(pathlib.Path(file).read_text()):
        if not re.match(r"^https://link\.coupang\.com/a/\w+$", e.get("link", "")) or not str(e.get("pid", "")).isdigit():
            print("skip bad entry:", e)
            continue
        bank[str(e["pid"])] = {"title": e.get("title", ""), "link": e["link"], "note": e.get("note", ""), "added": today}
        n += 1
    path(project).write_text(json.dumps(bank, ensure_ascii=False, indent=1) + "\n")
    print(f"{n} links added, {len(bank)} in bank")


def pick(project):
    proj, cfg, _, _ = new_post.load(project)
    recent = set(new_post.recent_ids(proj, cfg["selection"]["skip_if_posted_within_days"]))
    bank = load(project)
    unused = [{"pid": k, **v, "product_url": f"https://www.coupang.com/vp/products/{k}"}
              for k, v in bank.items() if k not in recent]
    print(json.dumps({"unused": len(unused), "total": len(bank), "entries": unused}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd, project = sys.argv[1], sys.argv[2]
    add(project, sys.argv[3]) if cmd == "add" else pick(project)
