from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .api import ExperimentSpec, component, contained


def repository(start: Path | None = None) -> Path:
    """Find the runnable project from anywhere inside the thesis checkout."""
    start = (start or Path.cwd()).resolve()
    for path in (start, *start.parents):
        if (path / "README.md").is_file() and (path / "runtime/scripts/check_references.py").is_file():
            return path / "runtime"
    raise ValueError("Start geoexp from the repository root or a directory inside it.")


def preset_path(root: Path, name: str) -> Path:
    path = contained(root, Path("experiments") / component(name))
    for filename in ("experiment.py", "pyproject.toml"):
        if not contained(root, path / filename).is_file():
            raise ValueError(f"Preset {name} is missing {filename}")
    return path


def names(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "experiments").iterdir()
                  if p.is_dir() and (p / "experiment.py").is_file())


def load(root: Path, name: str) -> ExperimentSpec:
    path = preset_path(root, name)
    for local in (path, path / "src"):
        if local.is_dir() and str(local) not in sys.path:
            sys.path.insert(0, str(local))
    module_name = "_geoexp_preset_" + name.replace("-", "_")
    module_spec = importlib.util.spec_from_file_location(module_name, path / "experiment.py")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    spec = module.EXPERIMENT
    if not isinstance(spec, ExperimentSpec) or spec.name != name:
        raise ValueError(f"{path}/experiment.py must export EXPERIMENT with name={name!r}")
    return spec
