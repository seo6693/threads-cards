"""Refresh long-lived Threads tokens and store them back as repo secrets.

Runs in GitHub Actions (see .github/workflows/token-refresh.yml).

  python scripts/refresh_tokens.py            # refresh every account
  python scripts/refresh_tokens.py --dry-run  # only check tokens + secret write access

Needs:
  THREADS_TOKEN_<X>  current tokens (from repo secrets)
  GH_TOKEN           fine-grained PAT with "Secrets: Read and write" on this repo
                     (secret SECRETS_PAT); the default GITHUB_TOKEN cannot write secrets
  GITHUB_REPOSITORY  set by Actions

Threads rules: a long-lived token can be refreshed once it is >= 24h old
and not yet expired; each refresh gives another 60 days and (for public
profiles) extends the permission grant. Token values are never printed
or written to the repo — only status (expiry dates) goes to
checks/token_status.json.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://graph.threads.net"
KST = dt.timezone(dt.timedelta(hours=9))


def get(path, **params):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # Never echo the URL: it contains the token.
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')}") from None


def set_secret(name, value):
    subprocess.run(["gh", "secret", "set", name, "--repo", os.environ["GITHUB_REPOSITORY"]],
                   input=value.encode(), check=True, capture_output=True)


def main():
    dry = "--dry-run" in sys.argv
    if not os.environ.get("GH_TOKEN"):
        sys.exit("SECRETS_PAT is not set: create a fine-grained token with "
                 "'Secrets: Read and write' on this repo and save it as secret SECRETS_PAT. "
                 "Nothing was refreshed.")

    # Prove we can write secrets before touching any token, so a new token
    # is never obtained without a place to store it.
    set_secret("TOKEN_REFRESH_CHECK", dt.datetime.now(KST).isoformat())

    accounts = json.loads((ROOT / "accounts.json").read_text())
    status_path = ROOT / "checks" / "token_status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    now = dt.datetime.now(KST)
    failed = []

    for key, acc in accounts.items():
        token = os.environ.get(acc["token_env"])
        entry = status.get(key, {})
        entry["checked_at"] = now.isoformat(timespec="seconds")
        try:
            if not token:
                raise RuntimeError(f"secret {acc['token_env']} is not set")
            me = get("v1.0/me", fields="id,username", access_token=token)
            if me.get("id") != acc["user_id"]:
                raise RuntimeError(f"token belongs to {me.get('username')} ({me.get('id')}), "
                                   f"expected {acc['user_id']}")
            entry["username"] = me.get("username")
            if not dry:
                new = get("refresh_access_token", grant_type="th_refresh_token", access_token=token)
                print(f"::add-mask::{new['access_token']}")
                set_secret(acc["token_env"], new["access_token"])
                entry["refreshed_at"] = now.isoformat(timespec="seconds")
                entry["expires_at"] = (now + dt.timedelta(seconds=int(new["expires_in"]))).isoformat(timespec="seconds")
            entry["ok"] = True
            entry.pop("error", None)
            print(f"OK   {key} (@{entry['username']})" + ("" if dry else f" -> expires {entry['expires_at']}"))
        except Exception as e:
            entry["ok"] = False
            entry["error"] = str(e)
            failed.append(key)
            print(f"FAIL {key}: {e}")
        status[key] = entry

    status_path.parent.mkdir(exist_ok=True)
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
