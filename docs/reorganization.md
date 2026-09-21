# Repository reorganization

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
- Python/notebook syntax and local document references are checked by [check_references.py](../scripts/check_references.py). The checker checks filename case even on Windows.
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
