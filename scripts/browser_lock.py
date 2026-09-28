"""One browser, many accounts: make scheduled runs take turns.

All projects use the same built-in browser pane on the user's computer. Two runs
driving it at once would click on each other's pages. This keeps a small lock
file in the repo (locks/browser.json); git push rejects a racing second writer,
so only one run holds it. A lock expires by itself after TTL minutes, so a run
that crashes never blocks the others for long.

  python3 scripts/browser_lock.py acquire <project>   # waits (up to WAIT min) for its turn
  python3 scripts/browser_lock.py release <project>   # call as soon as browser work is done

acquire prints {"ok": true, ...} when the lock is held, or {"ok": false, ...} after
waiting WAIT minutes (then record a skip and stop).
Run it only while the working tree has no other uncommitted changes.
"""
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCK = ROOT / "locks" / "browser.json"
TTL, WAIT = 35, 45  # minutes
KST = dt.timezone(dt.timedelta(hours=9))


def git(*a, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=check)


def now():
    return dt.datetime.now(KST)


def current():
    if not LOCK.exists():
        return None
    d = json.loads(LOCK.read_text())
    return d if dt.datetime.fromisoformat(d["expires"]) > now() else None


def push(msg):
    git("add", "locks")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return True
    git("commit", "-m", msg + " [skip ci]")
    if git("push", check=False).returncode == 0:
        return True
    git("reset", "--hard", "HEAD~1")  # someone else pushed first; re-read and retry
    return False


def acquire(project):
    deadline = time.time() + WAIT * 60
    while True:
        git("pull", "--rebase", "-q", "origin", "main", check=False)
        held = current()
        if held and held["owner"] != project:
            if time.time() > deadline:
                print(json.dumps({"ok": False, "held_by": held}, ensure_ascii=False))
                return 1
            print(f"browser in use by {held['owner']} until {held['expires'][11:16]}, waiting…", file=sys.stderr)
            time.sleep(60)
            continue
        LOCK.parent.mkdir(exist_ok=True)
        t = now()
        lock = {"owner": project, "since": t.isoformat(timespec="seconds"),
                "expires": (t + dt.timedelta(minutes=TTL)).isoformat(timespec="seconds")}
        LOCK.write_text(json.dumps(lock) + "\n")
        if push(f"Browser lock: {project}"):
            print(json.dumps({"ok": True, **lock}, ensure_ascii=False))
            return 0
        time.sleep(5)


def release(project):
    for _ in range(5):
        git("pull", "--rebase", "-q", "origin", "main", check=False)
        if not LOCK.exists() or json.loads(LOCK.read_text()).get("owner") != project:
            print(json.dumps({"released": False, "reason": "not held"}))
            return 0
        LOCK.unlink()
        if push(f"Browser unlock: {project}"):
            print(json.dumps({"released": True}))
            return 0
        time.sleep(3)
    return 1


if __name__ == "__main__":
    cmd, project = sys.argv[1], sys.argv[2]
    sys.exit(acquire(project) if cmd == "acquire" else release(project))
