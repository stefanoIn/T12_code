from __future__ import annotations

import dataclasses
import os
import platform
import subprocess
import time
from pathlib import Path

import psutil

from . import environment, hosts
from .api import contained
from .config import configuration
from .discovery import load, preset_path
from .storage import (TERMINAL, atomic_json, digest, identity, lock, matching_process,
                      read_json, run_id, terminate_tree, transition, utc_now)


def active_run(state: Path) -> Path | None:
    path = state / "active.json"
    return Path(read_json(path)["run"]) if path.exists() else None


def reconcile(state: Path) -> Path | None:
    """Caller holds host lock. Never clear a live or queued job."""
    run = active_run(state)
    if run is None:
        return None
    status = read_json(run / "status.json")
    if status["state"] in TERMINAL:
        if matching_process(status.get("process")):
            return run
        (state / "active.json").unlink(missing_ok=True)
        return None
    worker_record = state / "worker.json"
    worker_alive = worker_record.exists() and matching_process(read_json(worker_record))
    if status["state"] in {"starting", "running"} and not matching_process(status.get("process")) and not worker_alive:
        transition(run, "failed", error="Job process disappeared; inspect logs before resuming.")
        (state / "active.json").unlink(missing_ok=True)
        return None
    return run


def git_info(root: Path) -> dict:
    def call(*args):
        result = subprocess.run(["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    try:
        return {"revision": call("rev-parse", "HEAD"), "dirty": bool(call("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"revision": None, "dirty": None, "error": str(exc)}


def submit(root: Path, state: Path, name: str, action: str, overrides: list[str],
           device: str = "auto", file: str | None = None) -> Path:
    hosts.require_host(root, state)
    preset = preset_path(root, name)
    spec = load(root, name)
    if file is None and action not in spec.actions:
        raise ValueError(f"Unknown action {action!r}. Available: {', '.join(spec.actions)}")
    source = None
    if file is not None:
        if Path(file).is_absolute():
            raise ValueError("submit-file requires a repository-relative path")
        source = contained(root, file)
        if not source.is_file() or source.suffix not in {".py", ".ipynb"}:
            raise ValueError("submit-file requires an existing .py or .ipynb file")
    config = dataclasses.asdict(configuration(spec.config_type, overrides))
    with lock(state / "host.lock"):
        existing = reconcile(state)
        if existing:
            raise ValueError(f"This host already has an active job: {existing.name}")
        environment.ensure_prepared(root, preset)
        hardware = environment.probe(preset)
        selected = environment.select_device(spec.supported_devices, hardware["available_devices"], device)
        for reference in spec.datasets:
            if not reference.resolve(root).is_dir():
                raise ValueError(f"Missing dataset: {reference.resolve(root)}")
        identifier = run_id()
        run = contained(root, preset / "runs" / "jobs" / identifier)
        run.mkdir(parents=True)
        (run / "artifacts").mkdir()
        (run / "metrics.jsonl").touch()
        request = {"schema_version": 1, "run_id": identifier, "preset": name, "action": action,
                   "overrides": overrides, "device": selected, "submitted_at": utc_now(),
                   "file": source.relative_to(root).as_posix() if source else None,
                   "benchmark": source is None,
                   "experiment_sha256": digest(preset / "experiment.py"),
                   "sources_sha256": {source: digest(contained(root, source)) for source in spec.sources},
                   "source_sha256": digest(source) if source else None,
                   **environment.fingerprint(root, preset)}
        atomic_json(run / "request.json", request)
        atomic_json(run / "config.json", config)
        atomic_json(run / "provenance.json", {
            "schema_version": 1, "run_id": identifier, "git": git_info(root),
            "hardware": hardware, "device": selected, "seed": config.get("seed"),
            "datasets": [dataclasses.asdict(ref) for ref in spec.datasets],
            "protocol": spec.protocol, "environment": environment.fingerprint(root, preset),
            "submitted_at": request["submitted_at"],
        })
        atomic_json(run / "status.json", {"schema_version": 1, "run_id": identifier,
                    "state": "queued", "updated_at": utc_now()})
        atomic_json(state / "latest.json", {"run": str(run)})
        atomic_json(state / "active.json", {"run": str(run)})
        try:
            hosts.activate()
        except Exception as exc:
            transition(run, "failed", error=f"Cannot activate worker: {exc}")
            (state / "active.json").unlink(missing_ok=True)
            raise
    return run


def stop(state: Path):
    with lock(state / "host.lock"):
        run = reconcile(state)
        if run is None:
            return None
        status = read_json(run / "status.json")
        terminate_tree(status.get("process"))
        if status["state"] not in TERMINAL:
            transition(run, "stopped", reason="Stopped by user; resume is experiment-specific.")
        (state / "active.json").unlink(missing_ok=True)
        return run


def work_once(root: Path, state: Path) -> bool:
    with lock(state / "host.lock"):
        run = reconcile(state)
        if run is None:
            return False
        status = read_json(run / "status.json")
        if status["state"] != "queued":
            return False
        request = read_json(run / "request.json")
        out = err = child = inhibitor = None
        try:
            contained(root, run)
            preset = preset_path(root, request["preset"])
            environment.ensure_prepared(root, preset)
            if any(request.get(k) != v for k, v in environment.fingerprint(root, preset).items()):
                raise ValueError("Preset environment changed after submission")
            if digest(preset / "experiment.py") != request["experiment_sha256"]:
                raise ValueError("Experiment changed after submission")
            if any(digest(contained(root, path)) != value for path, value in request["sources_sha256"].items()):
                raise ValueError("Experiment source changed after submission")
            if request["file"] and digest(contained(root, request["file"])) != request["source_sha256"]:
                raise ValueError("Exploratory source changed after submission")
            transition(run, "starting", started_at=utc_now())
            out = (run / "stdout.log").open("ab", buffering=0)
            err = (run / "stderr.log").open("ab", buffering=0)
            env = environment.isolated_env(preset)
            env.update(PYTHONUNBUFFERED="1", GEOEXP_RUN_DIR=str(run), GEOEXP_DEVICE=request["device"],
                       GEOEXP_CONFIG=str(run / "config.json"))
            child = subprocess.Popen(environment.command(root, preset, run), cwd=root, env=env,
                                     stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                     start_new_session=os.name != "nt")
            process = identity(child.pid)
            if platform.system() == "Darwin":
                inhibitor = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-s", "-w", str(child.pid)],
                                             stdout=out, stderr=err)
            transition(run, "running", process=process)
        except Exception as exc:
            if child is not None:
                try:
                    process = identity(child.pid)
                    terminate_tree(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            transition(run, "failed", error=str(exc))
            (state / "active.json").unlink(missing_ok=True)
            if out:
                out.close()
            if err:
                err.close()
            return True
    try:
        code = child.wait()
        with lock(state / "host.lock"):
            if read_json(run / "status.json")["state"] not in TERMINAL:
                transition(run, "completed" if code == 0 else "failed", exit_code=code)
            if active_run(state) == run:
                (state / "active.json").unlink(missing_ok=True)
    finally:
        if inhibitor is not None and inhibitor.poll() is None:
            inhibitor.terminate()
            inhibitor.wait()
        out.close()
        err.close()
    return True


def worker(root: Path, state: Path, once: bool = False):
    with lock(state / "worker.lock", timeout=0):
        atomic_json(state / "worker.json", {**identity(os.getpid()), "repository": str(root)})
        while True:
            work_once(root, state)
            if once:
                return
            time.sleep(1)
