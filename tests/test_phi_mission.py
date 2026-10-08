"""FCW-03: cloud mission sidecar negative controls, without network or agents."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import phi_mission


def sample(error=False):
    return {
      "schema":"fielddeck.cloud-observation.v1",
      "receipt_kind":"observation_not_authorization",
      "run_at":"2026-10-08T21:10:46+00:00",
      "run_id":"37844903712", "trigger":"push", "sha":"8e81ffe",
      "run_url":"https://github.com/MichaelWave369/FieldCloudWorker/actions/runs/37844903712",
      "overall":"error" if error else "ok",
      "results":[
          {"task":"heartbeat","kind":"observation","status":"ok",
           "output":{"signal":"alive"},"duration_s":0},
          {"task":"repo_layout","kind":"observation","status":"ok",
           "output":{"required_files":3,"present_files":3},"duration_s":0},
          ({"task":"github_repo_metrics","kind":"observation","status":"error",
            "error_code":"RuntimeError","duration_s":0.2} if error else
           {"task":"github_repo_metrics","kind":"observation","status":"ok",
            "output":{"repository":"MichaelWave369/FieldCloudWorker",
                      "stars":1,"open_issues_and_prs":0},"duration_s":0.2})
      ]
    }

def encode(v):
    return (json.dumps(v, indent=2) + "\n").encode()

class MissionTests(unittest.TestCase):
    def test_provenance_digest_ttl_budget(self):
        raw=encode(sample())
        mission=phi_mission.mission_from_status(raw)
        self.assertEqual(mission["source_status_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(mission["expires_at"],"2026-10-09T05:10:46+00:00")
        self.assertEqual(mission["budget"],{"max_observations":1,"model_calls":0,"network_writes":0})
        self.assertFalse(mission["phibot_runtime_executed"])
        self.assertFalse(mission["authority_granted"])
        self.assertTrue(mission["worker_observation_executed"])
        self.assertNotIn("stars",json.dumps(mission))
        phi_mission.validate_mission(raw,encode(mission))

    def test_failure_is_visible_without_exception_text(self):
        mission=phi_mission.mission_from_status(encode(sample(True)))
        self.assertEqual(mission["outcome"],"OBSERVED_ERROR")
        self.assertNotIn("RuntimeError",json.dumps(mission))

    def test_cannot_tamper_mission_budget_or_grants(self):
        raw=encode(sample()); record=phi_mission.mission_from_status(raw)
        record["budget"]["network_writes"]=1
        with self.assertRaises(ValueError): phi_mission.validate_mission(raw,encode(record))
        record=phi_mission.mission_from_status(raw);record["authority_granted"]=True
        with self.assertRaises(ValueError): phi_mission.validate_mission(raw,encode(record))

    def test_cannot_swap_source_receipt(self):
        raw=encode(sample()); other=sample();other["results"][-1]["output"]["stars"]=22
        with self.assertRaises(ValueError):
            phi_mission.validate_mission(encode(other),encode(phi_mission.mission_from_status(raw)))

    def test_no_arbitrary_task_or_duplicate(self):
        a=sample();a["results"][-1]["task"]="shell_exec"
        with self.assertRaises(ValueError): phi_mission.mission_from_status(encode(a))
        a=sample();a["results"][1]["task"]="heartbeat"
        with self.assertRaises(ValueError): phi_mission.mission_from_status(encode(a))

    def test_local_records_not_published_as_cloud(self):
        a=sample();a.update(run_id="local",run_url="",trigger="local",sha="")
        raw=encode(a);record=phi_mission.mission_from_status(raw)
        with self.assertRaises(ValueError):
            phi_mission.validate_mission(raw,encode(record),require_cloud_run=True)

    def test_extra_sidecar_fields_and_duplicate_keys_refused(self):
        raw=encode(sample()); m=phi_mission.mission_from_status(raw)
        m["shell"]="execute now"
        with self.assertRaises(ValueError):phi_mission.validate_mission(raw,encode(m))
        bad=encode(m).replace(b'"schema":',b'"schema":"fake","schema":',1)
        with self.assertRaises(ValueError):phi_mission.validate_mission(raw,bad)

    def test_cli_generates_and_verifies_without_network(self):
        raw=encode(sample())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"status.json").write_bytes(raw)
            self.assertEqual(phi_mission.main(["tool",str(p/"status.json"),str(p/"mission.json")]),0)
            self.assertEqual(phi_mission.main(["tool","verify",str(p/"status.json"),str(p/"mission.json")]),0)
            receipt=json.loads((p/"mission.json").read_text())
            self.assertEqual(receipt["mission_id"],phi_mission.MISSION_ID)

if __name__=="__main__":unittest.main()
