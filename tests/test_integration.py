"""Real uv/Papermill smoke jobs; skipped until runner-smoke is prepared."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geoexp import jobs
from geoexp import environment
from geoexp.storage import atomic_json, read_json

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "experiments/runner-smoke"


def ready():
    try:
        environment.ensure_prepared(ROOT, PRESET)
        environment.uv()
        return True
    except (ValueError, OSError):
        return False


@unittest.skipUnless(os.environ.get("GEOEXP_RUN_INTEGRATION") == "1" and ready(),
                     "Set GEOEXP_RUN_INTEGRATION=1 after preparing runner-smoke")
class PreparedSmokeTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".geoexp-validation"
        base.mkdir(exist_ok=True)
        cache = base / "uv-cache"
        cache.mkdir(exist_ok=True)
        context = patch.dict(os.environ, {"UV_CACHE_DIR": str(cache)})
        context.start()
        self.addCleanup(context.stop)
        self.sandbox = tempfile.TemporaryDirectory(prefix="host with spaces ", dir=base)
        self.addCleanup(self.sandbox.cleanup)
        self.state = Path(self.sandbox.name)
        atomic_json(self.state / "host.json", {"repository": str(ROOT)})
        self.runs = []
        self.addCleanup(self.clean_runs)

    def clean_runs(self):
        parent = (PRESET / "runs/jobs").resolve()
        for run in self.runs:
            target = run.resolve()
            if target.parent != parent:
                raise RuntimeError(f"Unexpected generated run path: {target}")
            shutil.rmtree(target)

    def run_job(self, action, overrides=None, file=None):
        with patch("geoexp.hosts.activate"):
            run = jobs.submit(ROOT, self.state, "runner-smoke", action, overrides or [], file=file)
        self.runs.append(run)
        jobs.work_once(ROOT, self.state)
        return run, read_json(run / "status.json")

    def test_named_python_and_notebook_and_exploratory_files(self):
        run, status = self.run_job("test", ["seed=7"])
        self.assertEqual(status["state"], "completed", (run / "stderr.log").read_text(errors="replace"))
        self.assertEqual((run / "artifacts/device.txt").read_text(), "cpu")
        self.assertIn("Smoke fixture stdout", (run / "stdout.log").read_text())
        self.assertIn("Smoke fixture stderr", (run / "stderr.log").read_text())
        self.assertEqual(json.loads((run / "metrics.jsonl").read_text().splitlines()[0])["step"], 0)

        run, status = self.run_job("notebook", ["seed=11"])
        self.assertEqual(status["state"], "completed", (run / "stderr.log").read_text(errors="replace"))
        executed = json.loads((run / "executed/smoke.ipynb").read_text(encoding="utf-8"))
        self.assertTrue(any("Notebook stdout 11" in str(cell.get("outputs", "")) for cell in executed["cells"]))

        run, status = self.run_job("file", file="experiments/runner-smoke/smoke.py")
        self.assertEqual(status["state"], "completed", (run / "stderr.log").read_text(errors="replace"))
        self.assertFalse(read_json(run / "request.json")["benchmark"])
        run, status = self.run_job("file", file="experiments/runner-smoke/smoke.ipynb")
        self.assertEqual(status["state"], "completed", (run / "stderr.log").read_text(errors="replace"))
        self.assertTrue((run / "executed/smoke.ipynb").is_file())

    def test_failed_python_and_notebook(self):
        run, status = self.run_job("test", ["fail=true"])
        self.assertEqual(status["state"], "failed")
        self.assertIn("Intentional smoke failure", (run / "stderr.log").read_text(errors="replace"))
        run, status = self.run_job("notebook", ["fail=true"])
        self.assertEqual(status["state"], "failed")
        self.assertIn("Intentional notebook failure", (run / "stderr.log").read_text(errors="replace"))
