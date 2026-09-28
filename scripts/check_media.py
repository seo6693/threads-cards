"""Check that Threads accepts a video URL — WITHOUT publishing anything.

Creates a VIDEO media container for one account and polls its status until
FINISHED or ERROR. It never calls threads_publish, so nothing appears on the
profile; unpublished containers simply expire.

  python scripts/check_media.py <account> <video_url>
Writes checks/media_result.json.
"""
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import publish as P  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(account, url):
    acc = json.loads((ROOT / "accounts.json").read_text())[account]
    token = os.environ[acc["token_env"]]
    out = {"account": account, "url": url, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "served_as_video": P.url_ready(url)}
    try:
        cid = P.call("POST", f"{acc['user_id']}/threads", token, media_type="VIDEO",
                     video_url=url, text="(검사용 · 게시하지 않음)")["id"]
        start = time.time()
        while time.time() - start < 600:
            st = P.call("GET", cid, token, fields="status,error_message")
            if st.get("status") in ("FINISHED", "ERROR", "EXPIRED"):
                break
            time.sleep(6)
        out.update(container_status=st.get("status"), error_message=st.get("error_message"),
                   seconds=round(time.time() - start))
    except Exception as e:
        out["error"] = str(e)[:500]
    (ROOT / "checks" / "media_result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
