"""Publish queued Threads posts.

Each project (projects/<name>/) posts to exactly one Threads account,
set in projects/<name>/config.json ("account"). Each file in
projects/<name>/queue/*.json describes one post:
{
  "account": "nutri",                 # optional; must match the project's account
  "text": "본문",                      # max 500 chars
  "images": ["https://...jpg", ...],  # 0 = text post, 1 = image, 2-20 = carousel
  "reply": "첫 댓글 (선택)"
}
To add only a comment to an already published post, use
{"account": ..., "reply_to_media_id": "<id>", "reply": "..."}.

Tokens come from environment variables named in accounts.json
(GitHub Actions secrets). After publishing, the file is moved to the
project's done/ (or failed/) folder with the result added.
"""
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.threads.net/v1.0"
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"


def call(method, path, token, **params):
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    # Threads sometimes answers 5xx / "is_transient": true; retry those
    # with backoff instead of failing the whole post.
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            transient = e.code >= 500 or '"is_transient":true' in body.replace(" ", "")
            if transient and attempt < 4:
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4:
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"{method} {path} -> {e}") from None


def wait_ready(cid, token, timeout=300):
    """Poll a media container until it is ready to publish."""
    start = time.time()
    while time.time() - start < timeout:
        st = call("GET", cid, token, fields="status,error_message")
        status = st.get("status")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} {status}: {st.get('error_message')}")
        time.sleep(5)
    raise RuntimeError(f"container {cid} not ready after {timeout}s")


def create_and_publish(uid, token, retries=1, **params):
    cid = call("POST", f"{uid}/threads", token, **params)["id"]
    wait_ready(cid, token)
    for attempt in range(retries):
        try:
            return call("POST", f"{uid}/threads_publish", token, creation_id=cid)["id"]
        except RuntimeError as e:
            # "Media Not Found" right after creating a container is usually
            # transient on Threads' side; wait and retry.
            if "4279009" not in str(e) or attempt == retries - 1:
                raise
            time.sleep(20)


def reply(uid, token, media_id, text):
    # Replying immediately after the parent is published often fails with
    # "Media Not Found"; give Threads time to finish processing the parent.
    time.sleep(30)
    return create_and_publish(uid, token, retries=4, media_type="TEXT",
                              text=text, reply_to_id=media_id)


def publish(spec, accounts):
    acc = accounts[spec["account"]]
    uid = acc["user_id"]
    token = os.environ.get(acc["token_env"])
    if not token:
        raise RuntimeError(f"secret {acc['token_env']} is not set")

    # Reply-only job: attach a comment to an already published post.
    if spec.get("reply_to_media_id"):
        return {"reply_id": reply(uid, token, spec["reply_to_media_id"], spec["reply"])}

    text = spec.get("text", "")
    if len(text) > 500:
        raise RuntimeError(f"text is {len(text)} chars (max 500)")
    images = spec.get("images", [])

    if not images:
        media_id = create_and_publish(uid, token, media_type="TEXT", text=text)
    elif len(images) == 1:
        media_id = create_and_publish(uid, token, media_type="IMAGE",
                                      image_url=images[0], text=text)
    else:
        children = []
        for url in images:
            cid = call("POST", f"{uid}/threads", token, media_type="IMAGE",
                       image_url=url, is_carousel_item="true")["id"]
            wait_ready(cid, token)
            children.append(cid)
        media_id = create_and_publish(uid, token, media_type="CAROUSEL",
                                      children=",".join(children), text=text)

    result = {"media_id": media_id}
    result["permalink"] = call("GET", media_id, token, fields="permalink").get("permalink")

    if spec.get("reply"):
        try:
            result["reply_id"] = reply(uid, token, media_id, spec["reply"])
        except Exception as e:  # post is already live; record and continue
            result["reply_error"] = str(e)
    return result


def main():
    accounts = json.loads((ROOT / "accounts.json").read_text())
    jobs = []
    for proj in sorted(p for p in PROJECTS.iterdir() if p.is_dir()):
        account = json.loads((proj / "config.json").read_text())["account"]
        jobs += [(proj, account, f) for f in sorted((proj / "queue").glob("*.json"))]
    if not jobs:
        print("queue empty")
        return 0
    failures = 0
    for proj, account, f in jobs:
        spec = json.loads(f.read_text())
        spec["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        try:
            # A project only ever posts to its own account, so a post
            # dropped in the wrong folder fails instead of going live.
            if spec.setdefault("account", account) != account:
                raise RuntimeError(f"post is for '{spec['account']}' but sits in "
                                   f"projects/{proj.name} ('{account}')")
            spec["result"] = publish(spec, accounts)
            dest = proj / "done"
            print(f"OK   {proj.name}/{f.name}: {spec['result']}")
        except Exception as e:
            spec["error"] = str(e)
            dest = proj / "failed"
            failures += 1
            print(f"FAIL {proj.name}/{f.name}: {e}")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f.name).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        f.unlink()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
