# Repository reorganization

This document retains earlier migration history. The current layout separates `research/` and `runtime/`; see the final section. Earlier paths describe the layout at the time of each migration.

## Layout changes

| Previous location | New location |
| --- | --- |
| `preliminary report/` | `reports/preliminary/`, split into sources, figures, and notes |
| `benchmarking report/` | `reports/benchmarking/`, split into sources, tables, exports, figures, and notes |
| `benchmark shortlist/` | `reports/shortlist/sources/` and `reports/shortlist/intermediate/` |
| `Readings/` | `literature/papers/`, `literature/datasets/`, and `notes/literature/` |
| `AUTONAME/paper_renamer.py` | `scripts/paper_renamer.py` |
| `TorchGeo/torchgeo.ipynb` | `notebooks/torchgeo/torchgeo.ipynb` |
| `preliminary report/py/references.ipynb` | `notebooks/literature/references.ipynb` |
| `CROMA/croma.ipynb` and `SAR_encoder.pdf` | `notebooks/croma/` and its `figures/` folder |
| Root research Markdown files | `notes/benchmarking_protocols.md` and `notes/benchmarking_limitations.md` |
| Root benchmark PDF and image | `reports/benchmarking/exports/` and `figures/` |

[reorganization.json](reorganization.json) records every original path, destination, action, and original SHA-256 hash: 132 moved files and seven removed duplicate copies. Hashes describe the contents **before** path edits and notebook output clearing. All 137 files in the initial move batch were verified against their original hashes immediately after relocation; the two standalone CROMA files were subsequently moved separately.

## Removed material

Only byte-identical duplicate copies and the root Windows `desktop.ini` were removed. Duplicate contents were checked before deletion, and a surviving copy was verified at its destination. The manifest maps each removed duplicate to that copy. Unique drafts, different PDF versions, and existing user changes were preserved. Empty former directories were removed.

The virtual environment and the nested `CROMA/CROMA/` checkout remain in place. No Git changes were staged or committed, and pre-existing deletions were not restored. The CROMA gitlink already lacked a `.gitmodules` entry; the root README documents how to populate it in a fresh checkout.

## Reference repairs

- Preliminary LaTeX figure paths now use `../figures/`, relative to the `sources/` directory. References to classification, image captioning, and semantic segmentation were matched to the existing figures after inspecting them and their captions.
- Benchmarking LaTeX input snippets and their target tables remain together in `sources/`.
- The paper renamer uses a repository-relative default destination; examples use the new literature directory.
- Literature notebook outputs use an explicit repository-relative figures directory. The CROMA notebook resolves its upstream checkout independently of the notebook working directory.
- Python/notebook syntax and local document references are checked by [check_references.py](../runtime/scripts/check_references.py). The checker checks filename case even on Windows.
- DOCX relationship records were inspected: no local external file links needed updating.
- Ignore rules for raw datasets are anchored at the repository root, so `literature/datasets/` is visible to Git. Notebook source files are no longer hidden by the old blanket CROMA ignore rule. LaTeX intermediates and Windows metadata are ignored.

## Missing source assets

Five assets referenced in older preliminary report drafts were absent before cleanup:

- `reflectance_plot.jpg`
- `sentinel1_sar_london.jpg`
- `biomass_regression.png`
- `lst_downscaling.png`
- `reconstruction_enhancement.png`

These account for 15 source/target pairs in [missing_assets.json](missing_assets.json). They were not replaced with unrelated images. In particular, the available grayscale SAR image does not match the caption's artificial-colour Sentinel-1 image of London. Existing conditional placeholders are preserved. The checker reports these gaps; strict mode fails until they are fixed.

## Verification results

- Static checks: 68 local references and five Python/notebook files checked, with zero new broken references or syntax errors. Strict mode fails on the 15 documented references to the five pre-existing missing images.
- Both modified notebooks' path setup was executed from the repository root and their respective notebook directories; all resolved the intended folders.
- The renamer's `--help` command ran successfully in the existing virtual environment and reported the new default destination.
- All surviving non-code/non-LaTeX files match their original hashes. The upstream CROMA checkout retains its local checkpoint and cache.
- Full notebook workloads and LaTeX builds were not run. Static reference validation does not establish that every historical draft compiles.

After its move and initial hash verification, `reports/benchmarking/figures/Bini_benchmarks.png` disappeared in a separate change. This possible concurrent deletion was preserved rather than reverted. The original bytes are recoverable from `HEAD:Bini_benchmarks.png`, and their Git hash was checked against the manifest. No document references this image.

## Experiment portability update — 2026-10-03

- Moved the active Sen1Floods11 baseline from the ignored dataset folder to [experiments/sen1floods11](../runtime/experiments/sen1floods11/README.md). Updated the launcher and current instructions together. The notebook locates the repository using README.md and scripts/check_references.py and keeps relative filesystem paths without changing its working directory.
- Kept datasets/v1.1 and Sen1Floods11_runs in place. Preserved training settings, computation, notebook outputs, and existing checkpoint files. New resume checkpoints use best-model filenames; old Windows/POSIX references resolve within the experiment checkpoint directory.
- Made Windows control scripts derive the project root from their script location. Registered scheduled tasks were not changed. Task setup must be rerun after moving the repository.
- Kept selected metric/history JSONs tracked. Added exclusions for machine metadata, runtime state, diagnostic output, checkpoints, executed notebooks and ZIP bundles; removed tracked generated artifacts from the index while retaining local files. Git history was not rewritten.
- Removed the CROMA notebook, diagram, local checkout and downloaded weights at the user's explicit request. Earlier descriptions of CROMA in this historical record describe the prior layout, not the current repository.
- Added experiment/setup documentation and extended the static checker to experiment code, notebook Markdown links, and IPython syntax. The pre-existing PDF-audit link to the absent Corley _3.pdf and the 15 documented references to five missing figures remain separate baseline issues.

Future studies follow the [experiment conventions](../runtime/experiments/README.md). No shared benchmarking framework or new training protocol was introduced.

## Dataset and run folder follow-up ? 2026-10-03

Moved `datasets/v1.1/` to `datasets/Sen1Floods11/v1.1/` and `Sen1Floods11_runs/` to `experiments/sen1floods11/runs/`. The earlier sections describe the layout at the time of those migrations.

Updated the active baseline, local legacy notebook path strings, launcher, status script, setup instructions, and Git exclusions. Dataset versions now live under their dataset name; generated runs live alongside their study code. The baseline's eight metric/history JSONs remain tracked in their new location. Existing run artifacts and saved outputs retain their historical contents. Resume loading resolves legacy best-model references by filename in the new checkpoint directory.

Generated runs are excluded from source/reference checking. Training was not launched, and registered scheduled tasks were not changed.

## Windows experiment runner follow-up — 2026-10-03

Added the `geoexp` Python CLI and Windows Task Scheduler adapter. Named presets now live under `experiments/<preset>/` with their own environment manifests. The CUDA-only `sen1floods11-fcnn` preset wraps the preserved baseline notebook; the CPU `runner-smoke` preset exercises scheduling and tracking. Notebook execution uses an isolated Papermill kernel and writes executed copies into per-run folders. The old Sen1-specific PowerShell controls were removed from source. Registered tasks were not changed; migration is an explicit `geoexp host migrate` command. Mac host execution was subsequently removed at the user's request.

The baseline notebook's install cell became a Papermill parameters cell. The existing variant selection, resume behavior, training computation, checkpoints, and saved outputs are otherwise retained. Its legacy best-checkpoint references still resolve by filename in the current checkpoint directory. The new job records capture environment, source and split identity without moving existing results.

Automatic approval review initially rejected installing isolated test tools under the prior dependency-installation restriction. After the user directed continued implementation, uv and Papermill were installed only into an ignored development-tools folder. Genuine `uv.lock` files were generated and checked for both presets. The CPU smoke preset was prepared in its own `.venv`; real Python and Papermill notebook jobs completed, including expected failures. Twelve behavioral tests passed, including the live process stop test; future live tests are opt-in. The CUDA baseline environment and actual Windows scheduled task were not installed or launched during this migration. The reference checker still reports the pre-existing Corley PDF-audit link and five documented missing figures.


## Research and runtime separation — 2026-10-04

Moved papers, reports, notes and literature notebooks into `research/`. Moved the experiment code, local datasets, runs, runner package, tests, utilities and package manifest into `runtime/`. The directory-level moves are appended to `reorganization.json`; earlier audit inventories and migration entries remain historical records.

The baseline is now `runtime/experiments/sen1floods11/Sen1Floods11_FCNN_Baselines.ipynb`. Data is at `runtime/datasets/Sen1Floods11/v1.1/`, and existing checkpoints/results are at `runtime/experiments/sen1floods11/runs/`. All 41,228 inventoried local files remain present; 41,111 data, run artifact, environment and PDF files retained their sizes and modification times. Baseline training cells and saved outputs were compared with the pre-move notebook and are unchanged; only discovery and explanatory text changed. The user's pre-existing deletion of the TorchGeo notebook was preserved.

The existing CUDA `.venv/` remains at the checkout root. No package was installed or replaced. Moved per-preset environments are rejected until prepared again; preparation refreshes the editable runner import after relocation. From `runtime/`, reinstall the CLI with `uv tool install --force --editable .`, rerun `geoexp host install`, and then `geoexp prepare <preset>`. Registered tasks and local host state were not modified. `geoexp` commands work from the checkout root and nested directories; exploratory file arguments are relative to `runtime/`.

Updated notebook discovery, literature figure output, paper-renamer destination, documentation links, the reference checker and Git exclusions. Eight curated baseline JSONs remain eligible for publication; data, weights, generated runs and environments stay ignored. Old local remote-control files were preserved under ignored `runtime/legacy_remote_training/`.

Validation: 12 runner tests passed and three opt-in live tests were skipped. Both preset locks passed offline checks. Baseline discovery was checked from the checkout root, runtime root, experiment directory and research directory without executing training. Static checks introduced no new missing references: the existing Corley PDF-audit link and 15 documented references to five missing figures remain. No training, model downloads, dependency installation, OS-service changes, commits or history rewrites were performed.
