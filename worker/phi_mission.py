"""FCW-03: a frozen PhiBot Scout mission observation, NOT a PhiBot runtime.

Derive one public, advisory, no-authority mission record from the already
executed github_repo_metrics observation. Does NOT run a model, start PhiBot,
accept mission requests, obtain credentials, call tools or perform additional GETs.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MISSION_ID = "phibot.scout.public-repo-health.v1"
BOT_ID = "phibot.scout.cloud-review.v1"
SOURCE_REPO = "MichaelWave369/FieldCloudWorker"
TASK_ID = "github_repo_metrics"
TTL_SECONDS = 28800
DOMAIN = b"PHIBOT-CLOUD-OBSERVATION-V1\0"
SCHEMA = "phibot.cloud-mission-observation.v0.1"

def fail(condition, code):
    if not condition:
        raise ValueError("phi_mission: " + code)

def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def strict_json(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            fail(key not in obj, "DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    def no_nonfinite(value):
        raise ValueError("phi_mission: NONFINITE")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=no_nonfinite)

def mission_from_status(status_raw):
    fail(type(status_raw) is bytes and 0 < len(status_raw) <= 30000, "STATUS_BYTES")
    status = strict_json(status_raw)
    fail(type(status) is dict and set(status) == {
        "schema", "receipt_kind", "run_at", "run_id", "trigger",
        "sha", "run_url", "overall", "results"}, "STATUS_FIELDS")
    fail(status["schema"] == "fielddeck.cloud-observation.v1" and
         status["receipt_kind"] == "observation_not_authorization", "STATUS_SCHEMA")
    fail(status["overall"] in ("ok", "error"), "STATUS_OUTCOME")
    run_id = status["run_id"]
    fail(type(run_id) is str and
         (run_id == "local" or re.fullmatch(r"[1-9][0-9]{0,18}", run_id) is not None), "RUN_ID")
    sha = status["sha"]
    url = status["run_url"]
    if run_id == "local":
        fail(url == "", "LOCAL_URL")
    else:
        fail(type(sha) is str and re.fullmatch(r"[0-9a-f]{7}", sha) is not None, "RUN_SHA")
        fail(url == f"https://github.com/{SOURCE_REPO}/actions/runs/{run_id}", "RUN_URL")
        fail(status["trigger"] in ("push", "schedule", "workflow_dispatch", "pull_request"), "RUN_EVENT")
    time_value = status["run_at"]
    fail(type(time_value) is str and re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", time_value
    ) is not None, "RUN_TIME")
    observed = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
    fail(observed.tzinfo is not None, "TIMEZONE_REQUIRED")
    fail(type(status["results"]) is list and len(status["results"]) == 3, "TASK_COUNT")
    seen = set()
    task = None
    for row in status["results"]:
        fail(type(row) is dict and row.get("task") in
             ("heartbeat", "repo_layout", TASK_ID), "UNAPPROVED_TASK")
        fail(row["task"] not in seen and row.get("kind") == "observation", "TASK_DUPLICATE")
        seen.add(row["task"])
        fail(row.get("status") in ("ok", "error"), "BAD_TASK_STATUS")
        if row["task"] == TASK_ID:
            task = row
    fail(len(seen) == 3 and task is not None, "TASK_SET")
    # Public worker receipt verifier separately validates the exact task
    # output shapes. This mission adapter only projects ID and result state.
    record = {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "agent_identity_ref": BOT_ID,
        "source_repository": SOURCE_REPO,
        "source_status_sha256": hashlib.sha256(status_raw).hexdigest(),
        "task_id": TASK_ID,
        "execution_class": "DELEGATED_FIXED_OBSERVER_NOT_PHIBOT_RUNTIME",
        "run_id": run_id,
        "run_sha": sha,
        "run_url": url,
        "observed_at": time_value,
        "expires_at": (observed + timedelta(seconds=TTL_SECONDS)).isoformat(timespec="seconds"),
        "outcome": "OBSERVED_OK" if task["status"] == "ok" else "OBSERVED_ERROR",
        "budget": {"max_observations": 1, "model_calls": 0, "network_writes": 0},
        "epistemic": "UNVERIFIED_PUBLIC",
        "worker_observation_executed": True,
        "phibot_runtime_executed": False,
        "model_inference_executed": False,
        "authority_granted": False,
        "network_write_executed": False,
        "memory_admitted": False,
    }
    record["receipt_sha256"] = hashlib.sha256(DOMAIN + canonical(record)).hexdigest()
    return record

def validate_mission(status_raw, mission_raw, require_cloud_run=True):
    fail(type(mission_raw) is bytes and 0 < len(mission_raw) <= 16000, "MISSION_BYTES")
    found = strict_json(mission_raw)
    fail(type(found) is dict, "MISSION_SHAPE")
    expected = mission_from_status(status_raw)
    fail(found == expected, "MISSION_DRIFT")
    if require_cloud_run:
        fail(expected["run_id"] != "local", "LOCAL_NOT_PUBLISHABLE")
    return expected

def main(argv):
    if len(argv) not in (3, 4):
        print("usage: phi_mission.py [verify] <status> <mission>", file=sys.stderr)
        return 2
    verifying = len(argv) == 4 and argv[1] == "verify"
    if len(argv) == 4 and not verifying:
        return 2
    source, output = (Path(argv[2]), Path(argv[3])) if verifying else (Path(argv[1]), Path(argv[2]))
    try:
        raw = source.read_bytes()
        if verifying:
            validate_mission(raw, output.read_bytes(), require_cloud_run=True)
        else:
            # A published artifact is generated only from an existing status,
            # after the original tasks have completed.
            record = mission_from_status(raw)
            output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        print("PhiBot cloud mission evidence refused", file=sys.stderr)
        return 1
    print("PhiBot delegated observation:", "verified" if verifying else "created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
