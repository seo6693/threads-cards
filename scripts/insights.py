"""Collect Threads numbers for every published post (views, likes, replies, reposts, shares)
plus per-account totals, into checks/insights.json. Read-only; nothing is posted.
Needs the threads_manage_insights permission on each token; if it is missing the error is recorded."""
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://graph.threads.net/v1.0/"


def get(path, **q):
    url = API + path + "?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="replace")[:300]}


def main():
    accounts = json.loads((ROOT / "accounts.json").read_text())
    out = {"collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "projects": {}}
    for proj in sorted((ROOT / "projects").iterdir()):
        cfgp = proj / "config.json"
        if not cfgp.exists():
            continue
        acc = accounts.get(json.loads(cfgp.read_text())["account"])
        token = acc and os.environ.get(acc["token_env"])
        if not token:
            continue
        posts = []
        for f in sorted((proj / "done").glob("*.json")):
            d = json.loads(f.read_text())
            mid = (d.get("result") or {}).get("media_id")
            if not mid or d.get("reply_to_media_id"):
                continue
            r = get(f"{mid}/insights", metric="views,likes,replies,reposts,quotes,shares", access_token=token)
            m = {x["name"]: (x.get("values") or [{}])[0].get("value", x.get("total_value", {}).get("value"))
                 for x in r.get("data", [])}
            posts.append({"file": f.name, "product": d.get("product_name"), "format": d.get("format"),
                          "hook_formula": d.get("hook_formula", ""), "topic_source": d.get("topic_source", ""),
                          "video": bool(d.get("video")), "published_at": d.get("published_at"),
                          "permalink": d["result"].get("permalink"), **m,
                          **({"error": r["error"]} if "error" in r else {})})
        u = get(f"{acc['user_id']}/threads_insights", metric="views,likes,replies,followers_count", access_token=token)
        tot = {x["name"]: (x.get("total_value") or {}).get("value", sum(v.get("value", 0) for v in x.get("values", [])))
               for x in u.get("data", [])}
        out["projects"][proj.name] = {"account": acc.get("label"), "totals": tot or u.get("error"), "posts": posts}
    p = ROOT / "checks" / "insights.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: (v["totals"], len(v["posts"])) for k, v in out["projects"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
