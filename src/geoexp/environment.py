from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .storage import atomic_json, digest, read_json, utc_now


def uv() -> str:
    candidate = Path(sys.executable).parent / ("uv.exe" if os.name == "nt" else "uv")
    found = str(candidate) if candidate.is_file() else shutil.which("uv")
    if not found:
        raise ValueError("Install uv and put it on PATH before preparing or submitting experiments.")
    return found


def python(preset: Path) -> Path:
    return preset / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def isolated_env(preset: Path) -> dict:
    env = os.environ.copy()
    # Never sync the caller's activated environment or an external project override.
    for key in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_WORKING_DIRECTORY"):
        env.pop(key, None)
    env["UV_PROJECT_ENVIRONMENT"] = str(preset / ".venv")
    env["PYTHONNOUSERSITE"] = "1"
    return env


def fingerprint(root: Path, preset: Path) -> dict:
    return {"lock_sha256": digest(preset / "uv.lock"),
            "project_sha256": digest(preset / "pyproject.toml"),
            "runner_project_sha256": digest(root / "pyproject.toml")}


def prepare(root: Path, preset: Path) -> None:
    if not (preset / "uv.lock").is_file():
        raise ValueError(f"{preset.name} has no uv.lock. Generate and review one with uv lock --project {preset}.")
    marker = preset / ".venv" / "geoexp-prepared.json"
    marker.unlink(missing_ok=True)
    subprocess.run([uv(), "sync", "--locked", "--project", str(preset)],
                   env=isolated_env(preset), check=True)
    atomic_json(marker, {**fingerprint(root, preset), "prepared_at": utc_now(),
                         "python": str(python(preset).resolve())})


def ensure_prepared(root: Path, preset: Path) -> None:
    if not (preset / "uv.lock").is_file():
        raise ValueError(f"{preset.name} has no uv.lock. Generate and review one with uv lock --project {preset}.")
    marker = preset / ".venv" / "geoexp-prepared.json"
    if not marker.is_file() or not python(preset).is_file():
        raise ValueError(f"Run geoexp prepare {preset.name} first.")
    prepared = read_json(marker)
    if any(prepared.get(k) != v for k, v in fingerprint(root, preset).items()) or prepared.get("python") != str(python(preset).resolve()):
        raise ValueError(f"Environment or lock changed. Rerun geoexp prepare {preset.name}.")


def select_device(supported: tuple[str, ...], available: list[str], requested: str = "auto") -> str:
    if requested != "auto":
        if requested not in supported or requested not in available:
            raise ValueError(f"Device {requested} unavailable: preset supports {supported}, host has {available}")
        return requested
    for candidate in ("cuda", "mps", "cpu"):
        if candidate in supported and candidate in available:
            return candidate
    raise ValueError(f"No supported device: preset supports {supported}, host has {available}")


def probe(preset: Path) -> dict:
    code = '''import importlib.util, json, platform, sys
devices = ["cpu"]
details = {"python": sys.version, "platform": platform.platform(), "machine": platform.machine()}
if importlib.util.find_spec("torch"):
    import torch
    details["torch"] = torch.__version__
    details["cuda_runtime"] = torch.version.cuda
    if torch.cuda.is_available():
        devices.append("cuda")
        details["gpu"] = torch.cuda.get_device_name(0)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        devices.append("mps")
details["available_devices"] = devices
print(json.dumps(details))'''
    result = subprocess.run([str(python(preset)), "-c", code], env=isolated_env(preset),
                            capture_output=True, text=True, check=True, timeout=90)
    return json.loads(result.stdout)


def command(root: Path, preset: Path, run: Path) -> list[str]:
    # Both offline and no-sync: submitting never resolves or installs dependencies.
    return [uv(), "run", "--offline", "--frozen", "--no-sync", "--no-python-downloads",
            "--project", str(preset), str(python(preset)), "-m", "geoexp.execution", str(root), str(run)]
