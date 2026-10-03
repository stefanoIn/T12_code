# Running experiments on Windows and macOS

`geoexp` discovers studies in `experiments/<preset>/`. After SSH login, use the same command on either host. Each host runs one job at a time; Windows and Mac queues are independent. Each host needs its own checkout and local data and weights. The Mac user must stay logged into a graphical session for the user LaunchAgent; both hosts must stay awake. Installing the CLI or service does not start training.

## One-time setup on each host

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). In the checkout, install the CLI into an isolated tool environment:

```text
uv tool install --editable .
geoexp list
geoexp host install
```

After moving the checkout, run `uv tool install --force --editable .` from its new location, then `geoexp host install`. Also rerun host installation after changing the CLI's interpreter. On Windows this registers the `GeoExpWorker` scheduled task. It runs under the current interactive user and survives closing SSH or locking the desktop; signing out ends the session. On macOS it installs `org.geoexp.worker` in the user's LaunchAgents and uses `caffeinate` while a job is active. It survives closing SSH while the graphical user remains logged in. If the service does not start, run `geoexp doctor` and inspect the local worker logs in the host state directory it prints.

To remove the old Windows `Sen1Floods11-Training` task and install the generic worker explicitly, use `geoexp host migrate`. It refuses while the legacy task is running. A checkout or `prepare` does not modify registered OS services.

## Prepare and submit

Each preset owns `experiment.py`, `pyproject.toml`, and `uv.lock`. After changing dependencies, regenerate the lock intentionally with `uv lock --project experiments/<preset>/`, review it, then commit it. `geoexp prepare <preset>` runs `uv sync --locked` in that preset's `.venv`. It checks the lock and cannot run while a job is active. `submit` requires the prepared lock and environment, then invokes uv with `--offline --frozen --no-sync --no-python-downloads`.

The two current presets have checked-in lockfiles. The CPU smoke preset was prepared and exercised on Windows. The CUDA baseline lock was checked without installing its large model stack or starting training; prepare that preset on the target Windows GPU host before submitting it.

Offline tests run with `python -m unittest discover -s tests`. After preparing `runner-smoke`, set `GEOEXP_RUN_INTEGRATION=1` to include real uv and Papermill jobs. Set `GEOEXP_RUN_PROCESS_TEST=1` to include the live process stop test. These tests create temporary jobs and remove their own run folders when finished.

```text
geoexp prepare runner-smoke
geoexp doctor runner-smoke
geoexp submit runner-smoke test seed=1
geoexp status --follow
geoexp runs
geoexp stop
```

`geoexp status --follow` streams the most recently submitted job until it finishes; interrupting the display leaves the job running. `geoexp stop` stops the active process tree on the current host. A second submission on that host is rejected while one is active. `geoexp describe <preset>` shows typed defaults, actions, datasets, devices, and protocol. Use `--device cuda|mps|cpu` to request a specific accelerator. The default selects CUDA, MPS, then CPU among devices allowed by the preset. Unsupported hardware is rejected.

An exploratory file uses the same prepared environment:

```text
geoexp submit-file runner-smoke experiments/runner-smoke/smoke.py
geoexp submit-file runner-smoke experiments/runner-smoke/smoke.ipynb
```

File paths must be repository relative. The source file is preserved; executed notebooks appear under `runs/jobs/<run-id>/executed/`. Exploratory `submit-file` jobs are marked `benchmark=false`; a named action is required for a benchmark result.

## Sen1Floods11 baseline

The existing notebook lives in [the legacy study](../experiments/sen1floods11/README.md). Its runner preset is [sen1floods11-fcnn](../experiments/sen1floods11-fcnn/experiment.py). It is CUDA only and expects `datasets/Sen1Floods11/v1.1` on the host. Its separate environment targets the locally observed CUDA PyTorch version; inspect the host's supported PyTorch index before preparing it. The original root `.venv` is separate.

```text
geoexp prepare sen1floods11-fcnn
geoexp doctor sen1floods11-fcnn
geoexp submit sen1floods11-fcnn train variant=permanent_water
geoexp submit sen1floods11-fcnn train variant=hand_labeled resume=true
```

Valid variants are `hand_labeled`, `s1_weak`, `s2_weak`, and `permanent_water`. `resume=true` and `preflight=true` are notebook defaults. The original notebook remains editable and runnable in Jupyter. Runs of the same variant share the historical checkpoint directory, so never copy another run's checkpoint into it during a job. The adapter writes logs and an executed notebook to its own run directory and copies curated result JSONs into that directory on success. It records the legacy checkpoint path and split CSV hashes. Resuming uses the notebook's existing filename based compatibility for moved Windows/POSIX checkpoint references. The baseline retains its historical unseeded behavior; a `seed` override is unavailable until RNG and data loading behavior are adapted and validated. Its CUDA code does not run on the Mac's MPS device.

## Records and new presets

Run artifacts go to `experiments/<preset>/runs/jobs/<run-id>/` and stay out of Git. `request.json`, `status.json`, `config.json`, and `provenance.json` record the run ID, state, selected hardware, Git revision and dirty state, lock hash, dataset and split identity, seed if defined, timestamps and package versions. `metrics.jsonl`, stdout/stderr, executed notebooks and artifacts stay in the same folder. Curate selected summaries into a tracked `results/` directory when ready to publish. The host service configuration stores the checkout's absolute path outside the repository in the local application state folder.

Add `experiments/<name>/` with a dataclass and exported `EXPERIMENT: ExperimentSpec`, callable named actions, dataset references, supported devices and protocol fields. Action functions receive `ExperimentContext`, including paths, selected device and a metric tracker. Compose model, dataset, task and geographic split in `experiment.py` or its own `src/`; keep different model stacks in separate uv projects. The [smoke preset](../experiments/runner-smoke/experiment.py) is an executable contract example. A research preset should record the model/checkpoint, dataset version, split and held-out geography, preprocessing, training settings, seed, and metric definitions before comparative results are published.
