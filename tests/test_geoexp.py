"""Offline behavioral checks; no training, service installation or downloads."""
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from geoexp import DatasetRef
from geoexp import ExperimentContext, Tracker
from geoexp.api import contained
from geoexp.config import configuration
from geoexp.discovery import load, repository
from geoexp.environment import select_device
from geoexp import jobs
from geoexp import environment, hosts
from geoexp.storage import atomic_json, digest, identity, lock, matching_process, read_json, transition

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".geoexp-validation").mkdir(exist_ok=True)

    def test_discovery_and_typed_overrides(self):
        self.assertEqual(repository(ROOT / "experiments/runner-smoke"), ROOT)
        self.assertEqual(repository(ROOT / "datasets/Sen1Floods11/v1.1"), ROOT)
        self.assertRaises(ValueError, repository, Path(Path(__file__).resolve().anchor))
        smoke = load(ROOT, "runner-smoke")
        config = configuration(smoke.config_type, ["seed=3", "seconds=0.1"])
        self.assertEqual(dataclasses.asdict(config), {"seed": 3, "seconds": 0.1, "fail": False})
        for override in ("seed=true", "seconds=-1", "missing=1", "seed=3", "bad"):
            if override == "seed=3":
                self.assertRaises(ValueError, configuration, smoke.config_type, [override, override])
            else:
                self.assertRaises(ValueError, configuration, smoke.config_type, [override])
        baseline = load(ROOT, "sen1floods11-fcnn")
        self.assertRaises(ValueError, configuration, baseline.config_type, ["variant=unknown"])
        self.assertEqual(configuration(baseline.config_type, ["variant=s1_weak"]).variant, "s1_weak")

    def test_paths_and_devices(self):
        self.assertEqual(DatasetRef("Sen1Floods11", "v1.1").resolve(ROOT), ROOT / "datasets/Sen1Floods11/v1.1")
        self.assertRaises(ValueError, DatasetRef("../secret", "v1").resolve, ROOT)
        self.assertRaises(ValueError, contained, ROOT, "../elsewhere")
        self.assertEqual(select_device(("mps", "cpu"), ["cpu", "mps"]), "mps")
        self.assertEqual(select_device(("cuda", "mps"), ["cuda", "mps"]), "cuda")
        self.assertRaises(ValueError, select_device, ("cuda",), ["mps", "cpu"])
        self.assertRaises(ValueError, select_device, ("cuda", "cpu"), ["cuda", "cpu"], "mps")

    def test_checkpoint_compatibility_without_loading_weights(self):
        notebook = json.loads((ROOT / "experiments/sen1floods11/Sen1Floods11_FCNN_Baselines.ipynb").read_text(encoding="utf-8"))
        source = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
        self.assertIn("PureWindowsPath(saved_best).name", source)
        self.assertIn('best_checkpoint.name if best_checkpoint is not None', source)
        self.assertIn('"Sen1Floods11" / "v1.1"', source)
        self.assertIn('"sen1floods11" / "runs"', source)
        self.assertTrue(any("parameters" in c.get("metadata", {}).get("tags", []) for c in notebook["cells"]))
        self.assertNotIn("%pip install", source)
        from pathlib import PureWindowsPath
        for variant in ("hand_labeled", "s1_weak", "s2_weak", "permanent_water"):
            folder = ROOT / "experiments/sen1floods11/runs/checkpoints" / variant
            resume = folder / "resume_checkpoint.pt"
            self.assertTrue(resume.is_file(), variant)
            self.assertTrue(any(folder.glob("*.cp")), variant)
            self.assertEqual(PureWindowsPath("C:\\old\\best.pt").name, "best.pt")
        import importlib.util
        path = ROOT / "experiments/sen1floods11-fcnn/experiment.py"
        spec = importlib.util.spec_from_file_location("_baseline_adapter_test", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        for variant in ("hand_labeled", "s1_weak", "s2_weak", "permanent_water"):
            result = json.loads((ROOT / "experiments/sen1floods11/runs/results" / variant / "common_test_results.json").read_text())
            metrics = dict(module.result_metrics(result))
            self.assertIn("bolivia_test.iou", metrics)
            self.assertIn("hand_labeled_test.accuracy", metrics)

    def test_state_transitions_and_atomic_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".geoexp-validation") as directory:
            run = Path(directory)
            atomic_json(run / "status.json", {"state": "queued"})
            transition(run, "starting")
            transition(run, "running")
            self.assertRaises(ValueError, transition, run, "queued")
            transition(run, "completed")
            self.assertRaises(ValueError, transition, run, "running")
            self.assertEqual(read_json(run / "status.json")["state"], "completed")
            with lock(run / "lock"):
                self.assertRaises(RuntimeError, self._contend, run / "lock")

    @staticmethod
    def _contend(path):
        with lock(path, timeout=0):
            pass

    def test_stale_pid_does_not_match(self):
        current = identity(os.getpid())
        self.assertIsNotNone(matching_process(current))
        self.assertIsNone(matching_process({"pid": current["pid"], "create_time": current["create_time"] - 1}))

    def test_generated_host_configuration_is_parseable(self):
        state = ROOT / ".geoexp-validation" / "host with spaces"
        script = hosts.windows_install_script(ROOT, state)
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
            "$text=[Console]::In.ReadToEnd(); $null=$tokens=$errors=$null; "
            "$null=[System.Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors); "
            "if($errors.Count){$errors|ForEach-Object{Write-Error $_}; exit 1}"],
            input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        agent = hosts.launch_agent(ROOT, state)
        self.assertEqual(agent["ProgramArguments"][3], "_worker")
        self.assertEqual(agent["WorkingDirectory"], str(ROOT))

    def test_prepare_requires_lock_and_no_sync_on_submit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".geoexp-validation") as directory:
            preset = Path(directory)
            self.assertRaises(ValueError, environment.prepare, ROOT, preset)
            (preset / "uv.lock").write_text("fixture", encoding="utf-8")
            (preset / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
            with patch("geoexp.environment.uv", return_value="uv"), patch("geoexp.environment.python", return_value=Path(sys.executable)):
                command = environment.command(ROOT, preset, preset / "run")
                self.assertIn("--offline", command)
                self.assertIn("--frozen", command)
                self.assertIn("--no-sync", command)
                self.assertIn("--no-python-downloads", command)
                with patch("geoexp.environment.subprocess.run") as run:
                    environment.prepare(ROOT, preset)
                    self.assertIn("--locked", run.call_args.args[0])
                environment.ensure_prepared(ROOT, preset)
                (preset / "pyproject.toml").write_text("changed", encoding="utf-8")
                self.assertRaises(ValueError, environment.ensure_prepared, ROOT, preset)

    def test_notebook_execution_preserves_source_and_uses_prepared_kernel(self):
        with tempfile.TemporaryDirectory(prefix="notebook with spaces ", dir=ROOT / ".geoexp-validation") as directory:
            run = Path(directory)
            source = ROOT / "experiments/runner-smoke/smoke.ipynb"
            before = digest(source)
            calls = []
            def execute_notebook(input_path, output_path, **kwargs):
                calls.append((input_path, output_path, kwargs))
                Path(output_path).write_text("executed fixture", encoding="utf-8")
            context = ExperimentContext(ROOT, ROOT / "experiments/runner-smoke", run,
                                        run / "artifacts", "cpu", Tracker(run))
            with patch.dict(sys.modules, {"papermill": types.SimpleNamespace(execute_notebook=execute_notebook)}):
                output = context.notebook(source.relative_to(ROOT), {"seed": 17})
            self.assertEqual(digest(source), before)
            self.assertEqual(output.read_text(encoding="utf-8"), "executed fixture")
            self.assertEqual(calls[0][2]["parameters"], {"seed": 17})
            kernel = read_json(run / "jupyter/kernels/geoexp/kernel.json")
            self.assertEqual(kernel["argv"][0], sys.executable)
            self.assertEqual(calls[0][2]["cwd"], str(ROOT))


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".geoexp-validation").mkdir(exist_ok=True)

    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(dir=ROOT / ".geoexp-validation")
        self.addCleanup(self.sandbox.cleanup)
        self.state = Path(self.sandbox.name) / "host"
        self.state.mkdir()
        atomic_json(self.state / "host.json", {"repository": str(ROOT)})
        self.preset = ROOT / "experiments/runner-smoke"
        self.created_runs = []
        self.addCleanup(self._remove_created_runs)
        self.prepared = patch("geoexp.environment.ensure_prepared")
        self.fingerprint = patch("geoexp.environment.fingerprint", return_value={"lock_sha256": "fixture", "project_sha256": "fixture", "runner_project_sha256": "fixture"})
        self.probe = patch("geoexp.environment.probe", return_value={"available_devices": ["cpu"]})
        self.activate = patch("geoexp.hosts.activate")
        for item in (self.prepared, self.fingerprint, self.probe, self.activate):
            item.start()
            self.addCleanup(item.stop)

    def _submit(self, state=None, overrides=None, file=None):
        run = jobs.submit(ROOT, state or self.state, "runner-smoke", "test", overrides or [], file=file)
        self.created_runs.append(run)
        return run

    def _remove_created_runs(self):
        root = (ROOT / "experiments/runner-smoke/runs/jobs").resolve()
        for run in self.created_runs:
            target = run.resolve()
            if target.parent != root:
                raise RuntimeError(f"Unexpected test run path: {target}")
            shutil.rmtree(target)

    def _execute(self, run):
        from geoexp.execution import execute
        execute(ROOT, run)

    def test_submission_records_and_host_exclusivity(self):
        first = self._submit(overrides=["seed=9"])
        self.assertEqual(read_json(first / "config.json")["seed"], 9)
        request = read_json(first / "request.json")
        provenance = read_json(first / "provenance.json")
        self.assertEqual(request["schema_version"], 1)
        self.assertEqual(request["device"], "cpu")
        self.assertEqual(provenance["seed"], 9)
        self.assertEqual(provenance["environment"]["lock_sha256"], "fixture")
        self.assertIn("revision", provenance["git"])
        self.assertTrue((first / "metrics.jsonl").exists())
        self.assertRaises(ValueError, self._submit)
        second_state = Path(self.sandbox.name) / "mac"
        second_state.mkdir()
        atomic_json(second_state / "host.json", {"repository": str(ROOT)})
        second = self._submit(state=second_state)
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(read_json(first / "status.json")["state"], "queued")
        self.assertEqual(read_json(second / "status.json")["state"], "queued")
        self.assertEqual(jobs.stop(self.state), first)
        self.assertEqual(read_json(first / "status.json")["state"], "stopped")

    def test_python_success_and_failure(self):
        source = "experiments/runner-smoke/smoke.py"
        run = self._submit(file=source)
        self._execute(run)
        self.assertIn('"fixture": 1', (run / "metrics.jsonl").read_text())
        self.assertEqual(read_json(run / "request.json")["benchmark"], False)
        self.assertRaises(ValueError, self._submit, file="../outside.py")
        jobs.stop(self.state)
        run = self._submit(overrides=["fail=true"])
        self.assertRaises(RuntimeError, self._execute, run)

    def test_worker_success_failure_and_stale_state(self):
        with patch("geoexp.environment.command", side_effect=lambda root, preset, run: [sys.executable, "-m", "geoexp.execution", str(root), str(run)]):
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            with patch("geoexp.environment.isolated_env", return_value=env):
                run = self._submit()
                self.assertTrue(jobs.work_once(ROOT, self.state))
                self.assertEqual(read_json(run / "status.json")["state"], "completed")
                run = self._submit(overrides=["fail=true"])
                self.assertTrue(jobs.work_once(ROOT, self.state))
                self.assertEqual(read_json(run / "status.json")["state"], "failed")
                run = self._submit()
                status = read_json(run / "status.json")
                status.update(state="running", process={"pid": os.getpid(), "create_time": time.time() - 100})
                atomic_json(run / "status.json", status)
                with lock(self.state / "host.lock"):
                    self.assertIsNone(jobs.reconcile(self.state))
                self.assertEqual(read_json(run / "status.json")["state"], "failed")

    @unittest.skipUnless(os.environ.get("GEOEXP_RUN_PROCESS_TEST") == "1",
                         "Set GEOEXP_RUN_PROCESS_TEST=1 to start and stop a live child")
    def test_stop_terminates_live_job_tree(self):
        run = self._submit()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            transition(run, "starting")
            transition(run, "running", process=identity(child.pid))
            self.assertEqual(jobs.stop(self.state), run)
            self.assertEqual(read_json(run / "status.json")["state"], "stopped")
            self.assertIsNotNone(child.poll())
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()


if __name__ == "__main__":
    unittest.main()
