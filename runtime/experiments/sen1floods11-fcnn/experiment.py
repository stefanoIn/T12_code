"""Adapter around the preserved CUDA notebook; no ML imports during discovery."""
from dataclasses import dataclass
from typing import Literal

from geoexp import DatasetRef, ExperimentContext, ExperimentSpec


def result_metrics(value, prefix=""):
    """Flatten historical test result rows into named scalar metrics."""
    import math
    if isinstance(value, dict):
        for key, item in value.items():
            yield from result_metrics(item, prefix + str(key) + ".")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            label = item.get("name", index) if isinstance(item, dict) else index
            yield from result_metrics(item, prefix + str(label) + ".")
    elif type(value) in (int, float) and math.isfinite(value):
        yield prefix.rstrip("."), value


@dataclass
class Config:
    variant: Literal["hand_labeled", "s1_weak", "s2_weak", "permanent_water"] = "permanent_water"
    resume: bool = True
    preflight: bool = True


def train(context: ExperimentContext, config: Config):
    import hashlib
    import json
    import shutil
    from geoexp.storage import atomic_json, read_json

    dataset = context.dataset(DatasetRef("Sen1Floods11", "v1.1"))
    legacy = context.repository / "experiments/sen1floods11/runs"
    checkpoint = legacy / "checkpoints" / config.variant / "resume_checkpoint.pt"
    record = read_json(context.run / "provenance.json")
    record["baseline"] = {
        "model": "FCNResNet50, 2 input channels, GroupNorm",
        "variant": config.variant, "seed_policy": "Historical unseeded behavior; resume restores saved RNG state",
        "epochs": {"hand_labeled": 100, "s1_weak": 3, "s2_weak": 200, "permanent_water": 200}[config.variant],
        "learning_rate": 5e-4, "legacy_outputs": legacy.relative_to(context.repository).as_posix(),
        "resume": {"requested": config.resume, "exists": checkpoint.is_file(),
                   "path": checkpoint.relative_to(context.repository).as_posix(),
                   "size": checkpoint.stat().st_size if checkpoint.exists() else None,
                   "modified_ns": checkpoint.stat().st_mtime_ns if checkpoint.exists() else None},
        "split_sha256": {p.relative_to(dataset).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((dataset / "splits").rglob("*.csv"))},
    }
    atomic_json(context.run / "provenance.json", record)
    context.notebook("experiments/sen1floods11/Sen1Floods11_FCNN_Baselines.ipynb", {
        "EXPERIMENT": config.variant, "RESUME_IF_AVAILABLE": config.resume,
        "PREFLIGHT_VALIDATE_LABELS": config.preflight,
    })
    for name in ("common_test_results.json", "training_history.json"):
        source = legacy / "results" / config.variant / name
        if source.exists():
            shutil.copy2(source, context.artifacts / name)
            if name == "common_test_results.json":
                metrics = dict(result_metrics(json.loads(source.read_text(encoding="utf-8"))))
                if metrics:
                    context.tracker.log(metrics)


EXPERIMENT = ExperimentSpec(
    name="sen1floods11-fcnn", config_type=Config, actions={"train": train},
    datasets=(DatasetRef("Sen1Floods11", "v1.1"),), supported_devices=("cuda",),
    protocol={"name": "legacy-sen1floods11-fcnn", "split_identity": "upstream v1.1 CSV splits; SHA256 recorded per run",
              "held_out_geography": "Bolivia evaluation in preserved notebook; not a new geographic protocol",
              "preprocessing": "Preserved notebook normalization, augmentation and ignore-label behavior",
              "checkpoint_selection": "Preserved notebook best-validation and last-epoch resume logic"},
    sources=("experiments/sen1floods11/Sen1Floods11_FCNN_Baselines.ipynb",),
)
