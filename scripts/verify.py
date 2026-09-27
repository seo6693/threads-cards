"""Check every account's token without publishing anything.

For each account in accounts.json, calls GET /me and compares the
returned id with the configured user_id. Writes checks/result.json.
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    accounts = json.loads((ROOT / "accounts.json").read_text())
    out = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "accounts": {}}
    for key, acc in accounts.items():
        token = os.environ.get(acc["token_env"])
        if not token:
            out["accounts"][key] = {"ok": False, "error": f"secret {acc['token_env']} is not set"}
            continue
        q = urllib.parse.urlencode({"fields": "id,username", "access_token": token})
        try:
            with urllib.request.urlopen(f"https://graph.threads.net/v1.0/me?{q}", timeout=30) as r:
                me = json.load(r)
            out["accounts"][key] = {
                "ok": me.get("id") == acc["user_id"],
                "id": me.get("id"),
                "username": me.get("username"),
                "expected_id": acc["user_id"],
            }
        except urllib.error.HTTPError as e:
            out["accounts"][key] = {"ok": False, "error": f"HTTP {e.code}: {e.read().decode(errors='replace')}"}
    path = ROOT / "checks" / "result.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
