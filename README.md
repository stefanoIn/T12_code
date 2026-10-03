# Earth observation thesis

Research on how geospatial foundation models generalise geographically across several datasets. The thesis focuses on reproducible model comparisons, explicit geographic splits, and reliable evaluation protocols. Sen1Floods11 FCN training is one baseline experiment in this broader programme.

## Where things live

| Folder | Contents |
| --- | --- |
| [reports/preliminary](reports/preliminary) | Landscape review: LaTeX sources, Markdown notes, and shared figures |
| [reports/benchmarking](reports/benchmarking) | Dataset inventories and benchmark reports, grouped into `sources/`, `tables/`, `exports/`, `figures/`, and `notes/` |
| [reports/shortlist](reports/shortlist) | Shortlist source and intermediate PDF snapshots |
| [literature/papers](literature/papers) | Foundation model, survey, and benchmark papers |
| [literature/datasets](literature/datasets) | Dataset papers, including the single retained GEO-Bench paper |
| [notes](notes) | Benchmarking research notes and paper recaps |
| [experiments](experiments) | Study-specific code, setup instructions, and experiment conventions |
| [notebooks](notebooks) | TorchGeo exploration and literature plotting |
| [scripts](scripts) | PDF renamer and local reference checker |
| [docs](docs) | Reorganization record and known missing assets |
| `datasets/` | Local downloaded data and historical notebooks; ignored by Git |
| `experiments/sen1floods11/runs/` | Existing baseline artifacts; selected metric/history JSONs are tracked |
| `experiments/<study>/runs/` | Generated artifacts alongside each study; ignored by default |

## Starting points

- [Benchmark shortlist](reports/shortlist/sources/shortlisted_benchmark_datasets_portrait_cover.tex)
- [Sen1Floods11 baseline setup](experiments/sen1floods11/README.md)
- [Experiment and result conventions](experiments/README.md)
- [Windows/macOS SSH experiment runner](docs/geoexp.md)
- [38 benchmark candidates, v4](reports/benchmarking/sources/eo_benchmark_candidate_table_clean_38_v4.tex)
- [191 confirmed benchmark datasets, v4](reports/benchmarking/sources/eo_confirmed_benchmark_datasets_191_v4.tex)
- [595-dataset evidence table, v4](reports/benchmarking/sources/eo_datasets_master_benchmark_fmeval_evidence_portrait_595_v4.tex)
- [Landscape overview](reports/preliminary/notes/AI4EO_Landscape_Overview_August_2026.md)
- [Benchmarking protocols](notes/benchmarking_protocols.md) and [evaluation limitations](notes/benchmarking_limitations.md)

Distinct report versions and PDF exports are preserved. Version numbers and filenames describe existing snapshots; a PDF is not necessarily a build of the adjacent LaTeX version. No draft has been designated the final thesis report.

## Working with reports

Compile LaTeX from the relevant `sources/` directory so relative inputs and figure paths resolve. For example, from the repository root:

```powershell
Set-Location reports/shortlist/sources
pdflatex -interaction=nonstopmode -halt-on-error shortlisted_benchmark_datasets_portrait_cover.tex
pdflatex -interaction=nonstopmode -halt-on-error shortlisted_benchmark_datasets_portrait_cover.tex
```

Choose the engine required by each source (`fontspec` sources require XeLaTeX or LuaLaTeX). The benchmarking `overleaf_dataset_inventory_snippet.tex` is an inclusion snippet, not a standalone document; keep its two input tables with it. When uploading preliminary sources to Overleaf, preserve the sibling `sources/` and `figures/` directories and set the main document accordingly.

Five figure assets were already missing from preliminary drafts. Their exact references are listed in [docs/missing_assets.json](docs/missing_assets.json). Some drafts provide placeholders; others cannot build until those assets are supplied. Existing PDF exports have been retained.

## Notebooks and scripts

Start notebook kernels from the repository root or a directory inside it. The Sen1Floods11 baseline and literature notebooks locate the root automatically. The baseline uses relative paths without changing the working directory. Remote kernels resolve those paths on the remote host, where the dataset and environment must be installed. Literature plots save to `reports/preliminary/figures/`.

The baseline now lives under `experiments/sen1floods11/`. Its data remains under `datasets/Sen1Floods11/v1.1/`, and its existing checkpoints remain under `experiments/sen1floods11/runs/`. See the [cross-platform experiment runner](docs/geoexp.md) for SSH execution on Windows and macOS. Saved notebook outputs are retained; clear them before publishing if they contain machine-specific information.

Use the Python environment appropriate to each experiment; `.venv/` is preserved locally. The paper renamer imports `pymupdf`, `requests`, and `watchdog`; the literature notebook uses `pandas` and `matplotlib`. Model notebooks also require their imported ML packages and model files.

Preview dataset-paper renaming from the repository root:

```powershell
python scripts/paper_renamer.py --folder literature/datasets --dry-run
```

Without `--folder`, the renamer watches the user's Downloads folder and moves processed PDFs into this repository's `literature/papers/`. Its default destination is derived from the script location. Dataset mode is enabled automatically for a folder named `datasets`.

## Checking paths

```powershell
python scripts/check_references.py
python scripts/check_references.py --strict
```

The offline checker validates local Markdown links, LaTeX figure/input references (including filename case), Python syntax, and notebook code syntax, including experiment notebooks and IPython commands such as `%pip`. It requires IPython when notebooks contain IPython syntax. The default command fails on undocumented broken references or syntax errors and reports the documented missing assets. `--strict` fails on any missing asset. It does not validate remote URLs, execute notebooks, or compile LaTeX.

Keep downloaded datasets under root `data/` or `datasets/`, which are ignored. Literature PDFs under `literature/datasets/` are tracked. Put new report material in its topic folder, and retain distinct versions until their contents have been reviewed.

See [the cleanup record](docs/reorganization.md) for the migration map and verification details.
