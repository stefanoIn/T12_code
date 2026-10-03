from __future__ import annotations

import dataclasses
import json
import math
import re
from pathlib import Path
from typing import Any, Callable


def contained(root: Path, path: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Path must remain inside {root}: {path}")
    return candidate


def component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


@dataclasses.dataclass(frozen=True)
class DatasetRef:
    name: str
    version: str

    def resolve(self, repository: Path) -> Path:
        return contained(repository, Path("datasets") / component(self.name) / component(self.version))


class Tracker:
    def __init__(self, run: Path):
        self.run = run

    def log(self, metrics: dict[str, float], step: int | None = None) -> None:
        from .storage import utc_now
        for key, value in metrics.items():
            if not isinstance(key, str) or type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Metrics must map names to finite numbers")
        if step is not None and (type(step) is not int or step < 0):
            raise ValueError("step must be a nonnegative integer")
        with (self.run / "metrics.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"timestamp": utc_now(), "step": step, "metrics": metrics}, allow_nan=False) + "\n")


@dataclasses.dataclass
class ExperimentContext:
    repository: Path
    experiment: Path
    run: Path
    artifacts: Path
    device: str
    tracker: Tracker

    def dataset(self, reference: DatasetRef) -> Path:
        path = reference.resolve(self.repository)
        if not path.is_dir():
            raise FileNotFoundError(f"Place {reference.name} {reference.version} at {path}")
        return path

    def notebook(self, path: str | Path, parameters: dict[str, Any] | None = None) -> Path:
        """Use the preset's interpreter, never a globally registered CUDA kernel."""
        import os
        import sys
        import papermill
        from .storage import atomic_json
        source = contained(self.repository, path)
        output = self.run / "executed" / source.name
        output.parent.mkdir(parents=True, exist_ok=True)
        kernel_root = self.run / "jupyter"
        kernel = kernel_root / "kernels" / "geoexp"
        atomic_json(kernel / "kernel.json", {
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "GeoExp prepared environment", "language": "python",
        })
        old = os.environ.get("JUPYTER_PATH")
        os.environ["JUPYTER_PATH"] = str(kernel_root) + (os.pathsep + old if old else "")
        try:
            papermill.execute_notebook(
                str(source), str(output), parameters=parameters or {}, kernel_name="geoexp",
                cwd=str(self.repository), log_output=True, progress_bar=False,
                stdout_file=sys.stdout, stderr_file=sys.stderr,
            )
        finally:
            if old is None:
                os.environ.pop("JUPYTER_PATH", None)
            else:
                os.environ["JUPYTER_PATH"] = old
        return output


@dataclasses.dataclass(frozen=True)
class ExperimentSpec:
    name: str
    config_type: type
    actions: dict[str, Callable[[ExperimentContext, Any], None]]
    datasets: tuple[DatasetRef, ...] = ()
    supported_devices: tuple[str, ...] = ("cpu",)
    protocol: dict[str, Any] = dataclasses.field(default_factory=dict)
    sources: tuple[str, ...] = ()

    def __post_init__(self):
        component(self.name)
        if not dataclasses.is_dataclass(self.config_type):
            raise ValueError("config_type must be a dataclass")
        if not self.actions or any(not callable(action) for action in self.actions.values()):
            raise ValueError("Provide at least one callable action")
        for action in self.actions:
            component(action)
        if not self.supported_devices or set(self.supported_devices) - {"cuda", "mps", "cpu"}:
            raise ValueError("supported_devices must contain cuda, mps and/or cpu")
