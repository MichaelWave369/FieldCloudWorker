import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import runner
import tasks
import verify_receipt

class TestWorker(unittest.TestCase):
    def test_task_allowlist(self):
        self.assertEqual([fn.__name__ for fn in tasks.TASKS], ["heartbeat", "repo_layout", "github_repo_metrics"])

    def test_heartbeat(self):
        self.assertEqual(runner.task_result(tasks.heartbeat)["output"], {"signal": "alive"})

    def test_exception_content_is_not_public(self):
        def error():
            raise RuntimeError("SECRET_DO_NOT_PUBLISH")
        result = runner.task_result(error)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("SECRET_DO_NOT_PUBLISH", json.dumps(result))

    def test_bounded_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for _ in range(39):
                runner.write_receipt(runner.build_receipt(task_functions=[tasks.heartbeat]), path)
            rows = (path / "history.jsonl").read_text().splitlines()
            self.assertEqual(len(rows), 30)

    def test_local_receipt_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            with patch.dict("os.environ", {"GITHUB_REPOSITORY": "", "GITHUB_RUN_ID": ""}):
                receipt = runner.build_receipt()
            runner.write_receipt(receipt, path)
            verify_receipt.validate(path / "status.json", path / "history.jsonl")

    def test_disallowed_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            with patch.dict("os.environ", {"GITHUB_REPOSITORY": "", "GITHUB_RUN_ID": ""}):
                receipt = runner.build_receipt()
            receipt["results"][0]["output"]["token"] = "must-not-publish"
            runner.write_receipt(receipt, path)
            with self.assertRaises(ValueError):
                verify_receipt.validate(path / "status.json", path / "history.jsonl")

if __name__ == "__main__":
    unittest.main()
