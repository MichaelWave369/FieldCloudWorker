"""Validate public-safe artifacts before entering a write-permitted job."""
import json
from pathlib import Path
import re
import sys

TASKS = {"heartbeat", "repo_layout", "github_repo_metrics"}


def validate(status_file, history_file):
    a, b = Path(status_file), Path(history_file)
    if a.stat().st_size > 30000 or b.stat().st_size > 30000:
        raise ValueError("artifact too large")
    status = json.loads(a.read_text(encoding="utf-8"))
    if set(status) != {
        "schema", "receipt_kind", "run_at", "run_id", "trigger",
        "sha", "run_url", "overall", "results",
    }:
        raise ValueError("unknown receipt fields")
    if status["schema"] != "fielddeck.cloud-observation.v1":
        raise ValueError("unknown receipt schema")
    if status["receipt_kind"] != "observation_not_authorization":
        raise ValueError("invalid receipt kind")
    if status["overall"] not in ("ok", "error"):
        raise ValueError("invalid overall")
    if not isinstance(status["run_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", status["run_id"]):
        raise ValueError("invalid run id")
    if status["run_url"] and not re.fullmatch(
        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+",
        status["run_url"],
    ):
        raise ValueError("invalid run URL")
    results = status["results"]
    if not isinstance(results, list) or len(results) != len(TASKS):
        raise ValueError("unexpected number of tasks")
    seen = set()
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("invalid task")
        name = item.get("task")
        if name not in TASKS or name in seen or item.get("kind") != "observation":
            raise ValueError("unreviewed or repeated task")
        seen.add(name)
        if item.get("status") not in ("ok", "error"):
            raise ValueError("invalid task status")
        duration = item.get("duration_s")
        if type(duration) not in (int, float) or not 0 <= duration <= 600:
            raise ValueError("invalid task duration")
        if item["status"] == "error":
            if set(item) != {"task", "kind", "status", "error_code", "duration_s"}:
                raise ValueError("unsafe error payload")
            if not isinstance(item["error_code"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,50}", item["error_code"]):
                raise ValueError("invalid error code")
            continue
        if set(item) != {"task", "kind", "status", "output", "duration_s"}:
            raise ValueError("unsafe success payload")
        out = item["output"]
        if not isinstance(out, dict):
            raise ValueError("invalid output")
        if name == "heartbeat" and out != {"signal": "alive"}:
            raise ValueError("heartbeat payload invalid")
        if name == "repo_layout" and out != {"required_files": 3, "present_files": 3}:
            raise ValueError("layout payload invalid")
        if name == "github_repo_metrics":
            if out != {"state": "skipped_local"}:
                if set(out) != {"repository", "stars", "open_issues_and_prs"}:
                    raise ValueError("metrics fields invalid")
                if not isinstance(out["repository"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", out["repository"]):
                    raise ValueError("repository name invalid")
                if not all(type(out[key]) is int and 0 <= out[key] < 1000000000 for key in ("stars", "open_issues_and_prs")):
                    raise ValueError("metrics invalid")
    expected = "ok" if all(x["status"] == "ok" for x in results) else "error"
    if status["overall"] != expected:
        raise ValueError("inconsistent task state")
    rows = [json.loads(line) for line in b.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not 1 <= len(rows) <= 30:
        raise ValueError("invalid history size")
    for row in rows:
        if set(row) != {"schema", "run_id", "run_at", "overall", "ok_count", "error_count"}:
            raise ValueError("unsafe history row")
        if row["schema"] != "fielddeck.cloud-history.v1":
            raise ValueError("unknown history schema")
    if rows[-1]["run_id"] != status["run_id"] or rows[-1]["overall"] != status["overall"]:
        raise ValueError("latest history does not match receipt")


def main():
    try:
        validate(sys.argv[1], sys.argv[2])
    except Exception:
        print("Receipt failed public-schema validation")
        return 1
    print("Public-safe receipt validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
