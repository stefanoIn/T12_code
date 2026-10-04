# Running experiments asynchronously on Windows

`geoexp` runs a thesis experiment on the Windows workstation after SSH disconnects. It discovers studies in `runtime/experiments/<preset>/` and permits one active job. The Windows workstation holds the checkout, datasets, weights and generated results. Installing the CLI or scheduled task does not start training.

## Connect by SSH

The connecting computer can be a Mac, Windows PC or any SSH client. Execution always happens on the Windows workstation. Use the same remote Windows account because the scheduled task and job state belong to that user. Changing the computer from which you connect does not require reinstalling anything.

Connect from your local terminal, replacing the placeholders with the execution computer's login and hostname or IP address:

```text
ssh <remote-user>@<remote-host>
```

After connecting, enter PowerShell if SSH opens another shell, then enter the checkout:

```powershell
powershell
cd "<path-to-checkout>\runtime"
```

SSH access must already be configured on the Windows workstation.

## One-time Windows setup

After the research/runtime reorganization, run setup from `runtime/`: reinstall the editable CLI with `uv tool install --force --editable .`, run `geoexp host install`, then `geoexp prepare <preset>` for any preset you use. Preparation refreshes the runner's editable import if its environment moved. The original manual CUDA environment stays at the checkout root in `.venv/`. Existing tasks have not been modified automatically.

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). From `runtime/` inside the checkout, install the CLI into an isolated tool environment:

```text
uv tool install --editable .
geoexp list
geoexp host install
```

If `geoexp` is not found after installation, run `uv tool update-shell`, reconnect SSH, and return to the repository.

On the current Windows checkout, uv is also available in the ignored development-tools folder created during validation. You can use it for the initial installation:

```powershell
..\.geoexp-devtools\bin\uv.exe tool install --editable . --python 3.12
..\.geoexp-devtools\bin\uv.exe tool update-shell
```

Reconnect SSH, return to `runtime/`, and run `geoexp host migrate` to replace the old Windows task, or `geoexp host install` for a fresh host. The development-tools folder is local and is not included in a fresh Git clone; on other computers, install uv using the linked instructions first.

After moving the checkout, run `uv tool install --force --editable .` from its new `runtime/` directory, then `geoexp host install`. Also rerun host installation after changing the CLI's interpreter. This registers the `GeoExpWorker` Windows scheduled task. It runs under the current interactive user and survives closing SSH or locking the desktop; signing out ends the session. If the service does not start, run `geoexp doctor` and inspect the local worker logs in the host state directory it prints.

To remove the old Windows `Sen1Floods11-Training` task and install the generic worker explicitly, use `geoexp host migrate`. It refuses while the legacy task is running. A checkout or `prepare` does not modify registered OS services.

## Prepare and submit

After the initial Windows setup, each new SSH session only needs a connection and `cd` into the checkout before using `geoexp`. The commands work from anywhere inside the checkout; filesystem commands shown below assume you are in `runtime/`. Prepare each preset once, then repeat preparation when its dependency manifest or lock changes. You do not need to prepare again because you disconnected or switched the computer from which you connect.

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

`geoexp status --follow` streams the most recently submitted job until it finishes; interrupting the display leaves the job running. `geoexp stop` stops the active process tree. A second submission is rejected while one is active. `geoexp describe <preset>` shows typed defaults, actions, datasets, devices and protocol. Use `--device cuda|cpu` to request a specific device. The default selects CUDA and then CPU among devices allowed by the preset. Unsupported hardware is rejected.

An exploratory file uses the same prepared environment:

```text
geoexp submit-file runner-smoke experiments/runner-smoke/smoke.py
geoexp submit-file runner-smoke experiments/runner-smoke/smoke.ipynb
```

File paths for `submit-file` are relative to `runtime/`, regardless of the directory from which you invoke the command. The source file is preserved; executed notebooks appear under `runs/jobs/<run-id>/executed/`. Exploratory `submit-file` jobs are marked `benchmark=false`; a named action is required for a benchmark result.

## Sen1Floods11 baseline

The existing notebook lives in [the legacy study](../runtime/experiments/sen1floods11/README.md). Its runner preset is [sen1floods11-fcnn](../runtime/experiments/sen1floods11-fcnn/experiment.py). It is CUDA only and expects `datasets/Sen1Floods11/v1.1` on the host. Its separate environment targets the locally observed CUDA PyTorch version; inspect the host's supported PyTorch index before preparing it. The original `.venv` remains at the checkout root, one level above `runtime/`, and is separate.

```text
geoexp prepare sen1floods11-fcnn
geoexp doctor sen1floods11-fcnn
geoexp submit sen1floods11-fcnn train variant=permanent_water
geoexp submit sen1floods11-fcnn train variant=hand_labeled resume=true
```

Valid variants are `hand_labeled`, `s1_weak`, `s2_weak`, and `permanent_water`. `resume=true` and `preflight=true` are notebook defaults. The original notebook remains editable and runnable in Jupyter. Runs of the same variant share the historical checkpoint directory, so never copy another run's checkpoint into it during a job. The adapter writes logs and an executed notebook to its own run directory and copies curated result JSONs into that directory on success. It records the legacy checkpoint path and split CSV hashes. Resuming uses the notebook's existing filename based compatibility for moved checkpoint references. The baseline retains its historical unseeded behavior; a `seed` override is unavailable until RNG and data loading behavior are adapted and validated.

## Records and new presets

Run artifacts go to `experiments/<preset>/runs/jobs/<run-id>/` and stay out of Git. `request.json`, `status.json`, `config.json`, and `provenance.json` record the run ID, state, selected hardware, Git revision and dirty state, lock hash, dataset and split identity, seed if defined, timestamps and package versions. `metrics.jsonl`, stdout/stderr, executed notebooks and artifacts stay in the same folder. Curate selected summaries into a tracked `results/` directory when ready to publish. The host service configuration stores the runtime directory's absolute path outside the repository in the local application state folder.

Add `experiments/<name>/` with a dataclass and exported `EXPERIMENT: ExperimentSpec`, callable named actions, dataset references, supported devices and protocol fields. Action functions receive `ExperimentContext`, including paths, selected device and a metric tracker. Compose model, dataset, task and geographic split in `experiment.py` or its own `src/`; keep different model stacks in separate uv projects. The [smoke preset](../runtime/experiments/runner-smoke/experiment.py) is an executable contract example. A research preset should record the model/checkpoint, dataset version, split and held-out geography, preprocessing, training settings, seed, and metric definitions before comparative results are published.
