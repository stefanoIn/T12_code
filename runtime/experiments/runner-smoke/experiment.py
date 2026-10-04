"""Tiny CPU fixtures to verify a host before submitting research workloads."""
from dataclasses import dataclass

from geoexp import ExperimentContext, ExperimentSpec


@dataclass
class Config:
    seed: int = 1
    seconds: float = 0.0
    fail: bool = False

    def __post_init__(self):
        if not 0 <= self.seconds <= 3600:
            raise ValueError("seconds must be between 0 and 3600")


def test(context: ExperimentContext, config: Config):
    import random
    import sys
    import time
    print("Smoke fixture stdout", flush=True)
    print("Smoke fixture stderr", file=sys.stderr, flush=True)
    context.tracker.log({"sample": random.Random(config.seed).random()}, step=0)
    (context.artifacts / "device.txt").write_text(context.device, encoding="utf-8")
    time.sleep(config.seconds)
    if config.fail:
        raise RuntimeError("Intentional smoke failure")


def notebook(context: ExperimentContext, config: Config):
    from dataclasses import asdict
    context.notebook("experiments/runner-smoke/smoke.ipynb", asdict(config))


EXPERIMENT = ExperimentSpec(
    name="runner-smoke", config_type=Config, actions={"test": test, "notebook": notebook},
    supported_devices=("cpu",), protocol={"name": "runner validation only; no scientific results"},
    sources=("experiments/runner-smoke/smoke.ipynb",),
)
