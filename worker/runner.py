"""Produce bounded public-safe observation receipts."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tasks import TASKS

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MAX_HISTORY = 30


def task_result(fn):
    started = monotonic()
    entry = {"task": fn.__name__, "kind": "observation"}
    try:
        output = fn()
        encoded = json.dumps(output, ensure_ascii=True, allow_nan=False)
        if len(encoded) > 1600:
            raise ValueError("task output too large")
        entry.update(status="ok", output=output)
    except Exception as exc:
        # Exception texts and stack traces must not enter public data.
        entry.update(status="error", error_code=type(exc).__name__)
    entry["duration_s"] = round(monotonic() - started, 3)
    return entry


def build_receipt(now=None, task_functions=None):
    now = now or datetime.now(timezone.utc)
    results = [task_result(fn) for fn in (TASKS if task_functions is None else task_functions)]
    run_id = str(os.getenv("GITHUB_RUN_ID") or "local")[:30]
    repo = os.getenv("GITHUB_REPOSITORY", "")
    return {
        "schema": "fielddeck.cloud-observation.v1",
        "receipt_kind": "observation_not_authorization",
        "run_at": now.isoformat(timespec="seconds"),
        "run_id": run_id,
        "trigger": str(os.getenv("GITHUB_EVENT_NAME", "local"))[:40],
        "sha": str(os.getenv("GITHUB_SHA", ""))[:7],
        "run_url": ("https://github.com/" + repo + "/actions/runs/" + run_id) if run_id != "local" else "",
        "overall": "ok" if all(x["status"] == "ok" for x in results) else "error",
        "results": results,
    }


def write_receipt(receipt, docs=DOCS):
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "status.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    history_file = docs / "history.jsonl"
    rows = []
    if history_file.exists():
        for line in history_file.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                if item.get("schema") == "fielddeck.cloud-history.v1":
                    rows.append(item)
            except (ValueError, TypeError):
                continue
    rows.append({
        "schema": "fielddeck.cloud-history.v1",
        "run_id": receipt["run_id"],
        "run_at": receipt["run_at"],
        "overall": receipt["overall"],
        "ok_count": sum(x["status"] == "ok" for x in receipt["results"]),
        "error_count": sum(x["status"] != "ok" for x in receipt["results"]),
    })
    history_file.write_text(
        "".join(json.dumps(x, separators=(",", ":")) + "\n" for x in rows[-MAX_HISTORY:]),
        encoding="utf-8",
    )


def main():
    receipt = build_receipt()
    write_receipt(receipt)
    print("observation:", receipt["overall"], "task-count:", len(receipt["results"]))
    # Fail the workflow only after the publish job publishes the error receipt.
    return 0


if __name__ == "__main__":
    sys.exit(main())
