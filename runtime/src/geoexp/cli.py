from __future__ import annotations

import argparse
import dataclasses
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from . import environment, hosts, jobs
from .discovery import load, names, preset_path, repository
from .storage import TERMINAL, host_directory, lock, matching_process, read_json


def parser():
    p = argparse.ArgumentParser(prog="geoexp", description="Submit independent experiments on this host.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List presets without importing ML packages")
    for name in ("describe", "prepare"):
        sub.add_parser(name).add_argument("preset")
    for name in ("submit", "submit-file"):
        s = sub.add_parser(name)
        s.add_argument("preset")
        s.add_argument("action" if name == "submit" else "file")
        s.add_argument("overrides", nargs="*")
        s.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    sub.add_parser("stop")
    sub.add_parser("runs")
    s = sub.add_parser("status")
    s.add_argument("--follow", action="store_true")
    s = sub.add_parser("doctor")
    s.add_argument("preset", nargs="?")
    s = sub.add_parser("host")
    s.add_argument("operation", choices=["install", "migrate"])
    s = sub.add_parser("_worker", help=argparse.SUPPRESS)
    s.add_argument("--repository", type=Path, required=True)
    s.add_argument("--state", type=Path, required=True)
    s.add_argument("--once", action="store_true", help=argparse.SUPPRESS)
    return p


def status(state: Path, follow: bool):
    positions = {"stdout.log": 0, "stderr.log": 0}
    selected = None
    previous = None
    while True:
        with lock(state / "host.lock"):
            jobs.reconcile(state)
            if selected is None:
                latest = state / "latest.json"
                if not latest.exists():
                    print("No jobs on this host.")
                    return
                selected = Path(read_json(latest)["run"])
            record = read_json(selected / "status.json")
        if record != previous:
            print(json.dumps(record, indent=2), flush=True)
            previous = record
        if follow:
            for filename, position in positions.items():
                path = selected / filename
                if path.exists():
                    with path.open("rb") as stream:
                        stream.seek(position)
                        chunk = stream.read()
                        positions[filename] = stream.tell()
                    if chunk:
                        print(chunk.decode("utf-8", errors="replace"), end="", flush=True)
        if not follow or record["state"] in TERMINAL:
            return
        time.sleep(1)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "_worker":
            jobs.worker(repository(args.repository), args.state, args.once)
            return 0
        root, state = repository(), host_directory()
        if args.command == "list":
            for name in names(root):
                spec = load(root, name)
                print(f"{name}: {', '.join(spec.actions)} [{', '.join(spec.supported_devices)}]")
        elif args.command == "describe":
            spec = load(root, args.preset)
            print(json.dumps({"name": spec.name, "actions": list(spec.actions),
                              "defaults": dataclasses.asdict(spec.config_type()),
                              "datasets": [dataclasses.asdict(ref) for ref in spec.datasets],
                              "devices": spec.supported_devices, "protocol": spec.protocol}, indent=2))
        elif args.command == "prepare":
            with lock(state / "host.lock", timeout=1):
                if jobs.reconcile(state):
                    raise ValueError("Stop or finish the active job before preparing environments.")
                environment.prepare(root, preset_path(root, args.preset))
            print(f"Prepared {args.preset}.")
        elif args.command in {"submit", "submit-file"}:
            run = jobs.submit(root, state, args.preset, getattr(args, "action", "file"),
                              args.overrides, args.device, getattr(args, "file", None))
            print(f"Queued {run.name}\n{run}")
        elif args.command == "status":
            hosts.require_host(root, state)
            status(state, args.follow)
        elif args.command == "stop":
            hosts.require_host(root, state)
            run = jobs.stop(state)
            print(f"Stopped {run.name}" if run else "No active job.")
        elif args.command == "runs":
            for path in sorted((root / "experiments").glob("*/runs/jobs/*/status.json")):
                record = read_json(path)
                print(f"{record['run_id']}  {record['state']:10}  {path.parents[3].name}")
        elif args.command == "host":
            with lock(state / "host.lock"):
                if jobs.reconcile(state):
                    raise ValueError("Stop or finish the active job before changing the host service.")
                if args.operation == "migrate":
                    hosts.legacy_must_be_inactive()
                existing = state / "worker.json"
                if existing.exists() and matching_process(read_json(existing)):
                    from .storage import terminate_tree
                    terminate_tree(read_json(existing))
                hosts.install(root, state)
                if args.operation == "migrate":
                    hosts.remove_legacy()
            print("Installed host worker. Rerun this command after relocating the checkout.")
        elif args.command == "doctor":
            info = {"repository": str(root), "platform": platform.platform(), "host_state": str(state)}
            errors = []
            try:
                hosts.require_host(root, state)
                info["service"] = read_json(state / "host.json")
                worker_record = state / "worker.json"
                info["worker_running"] = worker_record.exists() and bool(matching_process(read_json(worker_record)))
                if not info["worker_running"]:
                    errors.append("Worker is not running; reinstall or start the host service")
            except ValueError as exc:
                errors.append(str(exc))
            try:
                info["uv"] = environment.uv()
                if args.preset:
                    preset = preset_path(root, args.preset)
                    environment.ensure_prepared(root, preset)
                    spec = load(root, args.preset)
                    info["hardware"] = environment.probe(preset)
                    info["selected_device"] = environment.select_device(spec.supported_devices, info["hardware"]["available_devices"])
                    info["missing_datasets"] = [str(r.resolve(root)) for r in spec.datasets if not r.resolve(root).is_dir()]
                    if info["missing_datasets"]:
                        errors.append("Dataset setup is incomplete")
            except (ValueError, subprocess.SubprocessError) as exc:
                errors.append(str(exc))
            info["errors"] = errors
            print(json.dumps(info, indent=2))
            return int(bool(errors))
        return 0
    except KeyboardInterrupt:
        print("Detached from display; submitted jobs keep running.", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"geoexp: {exc}", file=sys.stderr)
        return 1
