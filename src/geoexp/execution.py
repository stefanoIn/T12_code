"""Child entry point, executed only inside a prepared preset environment."""
from __future__ import annotations

import dataclasses
import importlib.metadata
import runpy
import sys
import traceback
from pathlib import Path

from .api import ExperimentContext, Tracker, contained
from .config import convert
from .discovery import load, preset_path
from .storage import atomic_json, read_json, utc_now


def execute(root: Path, run: Path):
    request = read_json(run / "request.json")
    spec = load(root, request["preset"])
    preset = preset_path(root, spec.name)
    context = ExperimentContext(root, preset, run, run / "artifacts", request["device"], Tracker(run))
    config = convert(read_json(run / "config.json"), spec.config_type)
    provenance = read_json(run / "provenance.json")
    provenance.update(started_at=utc_now(), interpreter=sys.executable,
                      packages={d.metadata["Name"]: d.version for d in importlib.metadata.distributions()})
    atomic_json(run / "provenance.json", provenance)
    try:
        if request["file"]:
            source = contained(root, request["file"])
            if source.suffix == ".ipynb":
                context.notebook(source, dataclasses.asdict(config))
            else:
                sys.argv = [str(source)]
                sys.path.insert(0, str(source.parent))
                runpy.run_path(str(source), run_name="__main__", init_globals={
                    "GEOEXP_CONTEXT": context, "GEOEXP_CONFIG": config})
        else:
            spec.actions[request["action"]](context, config)
    finally:
        provenance = read_json(run / "provenance.json")
        provenance["finished_at"] = utc_now()
        atomic_json(run / "provenance.json", provenance)


if __name__ == "__main__":
    try:
        execute(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
