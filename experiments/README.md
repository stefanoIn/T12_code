# Thesis experiments

The thesis compares geospatial foundation models across several datasets, with an emphasis on geographic generalisation and reproducible benchmarking. Each study belongs in `experiments/<study>/` and contains its code, configuration, and setup instructions. Exploratory notebooks can remain under `notebooks/`.

The current [Sen1Floods11 FCN baseline](sen1floods11/README.md) reproduces an existing training procedure. Its original training settings are preserved; it does not yet implement a shared GeoFM benchmarking protocol.

The [geoexp runner](../docs/geoexp.md) discovers named presets in `experiments/<preset>/`. Each preset declares actions and typed settings in `experiment.py` and maintains its own uv project and lockfile. The [runner smoke preset](runner-smoke/experiment.py) is a small cross-platform example. The CUDA-only [Sen1Floods11 runner preset](sen1floods11-fcnn/experiment.py) wraps the preserved notebook and its existing result directories.

## Data, runs, and publication

- Keep downloaded data under ignored `datasets/<dataset>/<version>/` folders. The existing Sen1Floods11 dataset remains at `datasets/Sen1Floods11/v1.1/`.
- Put future generated artifacts under ignored `experiments/<study>/runs/<run-id>/`. Give separate configurations and seeds distinct run IDs; resume only the matching run.
- Publish selected metric tables, histories, and portable run descriptions under the study's `results/` folder. Record the originating run ID and protocol, including unsuccessful or incomplete runs when relevant to comparisons.
- Existing Sen1Floods11 artifacts remain under `experiments/sen1floods11/runs/`. Its metric and history JSONs remain tracked; checkpoints, logs, executed notebooks, and ZIP bundles remain local.
- A Git ignore rule does not remove previously committed content from Git history. This refactor does not rewrite history.

## Record for each future run

Record the model and checkpoint identity/version, code revision, dataset version, and split manifest or identifier. Describe training/validation/test regions and held-out geography explicitly, with split checks and any known pretraining overlap or uncertainty.

Record input bands, resolution, preprocessing, adaptation method, training hyperparameters, seed, environment versions, checkpoint selection rule, and metrics with their aggregation and ignore-label definitions. Distinguish in-distribution and geographically held-out evaluation. Make the configuration and split definition available alongside curated results so model comparisons use identifiable protocols.

These are record-keeping conventions. Dataset selection, geographic split design, and the shared evaluation implementation will be developed as the thesis progresses.
