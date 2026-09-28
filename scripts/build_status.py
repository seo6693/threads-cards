"""Write dashboard/status.json so the dashboard never calls the GitHub API.

The GitHub API allows only 60 anonymous requests per hour per network, which the
dashboard kept hitting. This runs inside GitHub Actions (with the workflow token,
which has a far higher limit) and saves what the dashboard needs:
  paths  - every file under projects/ (to find queue/done/failed/skipped posts)
  runs   - recent workflow runs worth showing (routine scheduled successes left out
           so the file only changes when something actually happens)
  issues - open issues (token refresh failures)
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def api(path):
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo or not os.environ.get("GH_TOKEN"):
        return None
    try:
        out = subprocess.run(["gh", "api", f"repos/{repo}/{path}"], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print("api failed:", path, e)
        return None


def main():
    paths = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "projects").rglob("*")
                   if p.is_file() and p.name != ".gitkeep")
    this_run = os.environ.get("GITHUB_RUN_ID")
    runs = api("actions/runs?per_page=40")
    keep = []
    for r in (runs or {}).get("workflow_runs", []):
        if str(r["id"]) == this_run or r["status"] != "completed":
            continue
        if r["event"] == "dynamic":  # GitHub Pages deploys; every commit makes one
            continue
        if r["event"] == "schedule" and r["conclusion"] == "success":
            continue
        keep.append({k: r[k] for k in ("name", "status", "conclusion", "created_at", "html_url", "event")})
        if len(keep) == 8:
            break
    issues = api("issues?state=open&per_page=10")
    old_path = ROOT / "dashboard" / "status.json"
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    status = {
        "paths": paths,
        "runs": keep if runs is not None else old.get("runs", []),
        "issues": ([{"title": i["title"], "html_url": i["html_url"]} for i in issues if "pull_request" not in i]
                   if issues is not None else old.get("issues", [])),
    }
    old_path.write_text(json.dumps(status, ensure_ascii=False, indent=1) + "\n")
    print(f"status.json: {len(paths)} files, {len(status['runs'])} runs, {len(status['issues'])} issues")


if __name__ == "__main__":
    main()
