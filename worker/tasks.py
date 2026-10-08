"""Fixed, reviewed, read-only observation tasks. No dynamic code loading."""
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def heartbeat():
    return {"signal": "alive"}


def repo_layout():
    required = ("docs/index.html", "worker/runner.py", ".github/workflows/worker.yml")
    if not all((ROOT / filename).is_file() for filename in required):
        raise RuntimeError("required file missing")
    return {"required_files": 3, "present_files": 3}


def github_repo_metrics():
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo:
        return {"state": "skipped_local"}
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid repository identifier")
    headers = {"User-Agent": "fieldcloudworker/0.2", "Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = Request("https://api.github.com/repos/" + repo, headers=headers)
    with urlopen(request, timeout=10) as response:
        payload = response.read(200001)
    if len(payload) > 200000:
        raise ValueError("API response too large")
    data = json.loads(payload)
    return {
        "repository": repo,
        "stars": int(data["stargazers_count"]),
        "open_issues_and_prs": int(data["open_issues_count"]),
    }


TASKS = [heartbeat, repo_layout, github_repo_metrics]
