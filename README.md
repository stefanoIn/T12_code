# Earth observation thesis

Evaluating geospatial foundation models across several datasets, with an emphasis on geographic generalisation, explicit geographic splits and reproducible model comparisons.

## Repository layout

```text
research/                 Papers, literature analysis and thesis writing
  literature/
  reports/
  notes/
  notebooks/
runtime/                  Experiment code and execution tools
  experiments/            Notebooks, presets, locks and generated runs
  datasets/               Local data organised by dataset and version
  src/geoexp/             Windows asynchronous experiment runner
  scripts/
  tests/
  pyproject.toml
docs/                     Setup instructions, migration records and audits
.venv/                    Existing local CUDA environment (untracked)
```

- [Research material](research/README.md)
- [Running experiments](runtime/README.md)
- [SSH setup and geoexp commands](docs/geoexp.md)
- [Sen1Floods11 baseline](runtime/experiments/sen1floods11/README.md)
- [Experiment conventions](runtime/experiments/README.md)
- [Benchmark shortlist](research/reports/shortlist/sources/shortlisted_benchmark_datasets_portrait_cover.tex)
- [Benchmarking protocols](research/notes/benchmarking_protocols.md)

Downloaded data lives under `runtime/datasets/<dataset>/<version>/`. Generated artifacts stay under `runtime/experiments/<study>/runs/` and are ignored, except for the existing curated baseline metric/history JSONs. Papers and report exports under `research/` remain tracked.

The baseline's data is at `runtime/datasets/Sen1Floods11/v1.1/`; its existing checkpoints and results are at `runtime/experiments/sen1floods11/runs/`. Training computation and notebook outputs are preserved. The original CUDA environment remains at `.venv/` because Python environments are not safely relocatable.

## Local utilities

From the checkout root:

```powershell
python runtime/scripts/check_references.py
python runtime/scripts/paper_renamer.py --folder research/literature/datasets --dry-run
```

Use an environment with the dependencies needed by the utility. The reference checker validates local document links and Python/notebook syntax without running experiments. Add `--strict` to fail on documented missing figures too. The paper renamer requires PyMuPDF, requests and watchdog; without `--folder` it watches Downloads and moves processed PDFs to `research/literature/papers/`.

Report versions and historical notebooks are preserved. Five missing figures are recorded in [missing assets](docs/missing_assets.json); the PDF audit also retains a pre-existing missing Corley PDF link. See the [migration record](docs/reorganization.md) for previous layouts.
