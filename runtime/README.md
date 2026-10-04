# Running experiments

This folder contains the runnable project. The `geoexp` command submits experiments asynchronously on the Windows workstation, so they continue after SSH disconnects.

| Folder | Contents |
| --- | --- |
| [experiments](experiments/README.md) | Experiment notebooks, presets, environment locks and generated runs |
| `datasets/<dataset>/<version>/` | Local downloaded data, ignored by Git |
| [src/geoexp](src/geoexp) | The `geoexp` command and Windows worker |
| [tests](tests) | Runner checks; live notebook and process-stop tests are opt-in |
| [scripts](scripts) | Repository reference checker |

See [SSH installation and usage](../docs/geoexp.md) and [baseline setup](experiments/sen1floods11/README.md).

From this directory, after installing uv:

```powershell
uv tool install --editable .
geoexp host install
geoexp prepare sen1floods11-fcnn
geoexp submit sen1floods11-fcnn train variant=permanent_water
geoexp status --follow
```

Installation is done once per execution host; preparation is done per preset. After installation, `geoexp` works from anywhere inside the thesis checkout. Paths passed to `submit-file` are relative to this directory. The baseline requires a compatible CUDA GPU.

The existing manual CUDA environment stays at `../.venv/`. Per-preset environments live in `experiments/<preset>/.venv/`. Neither is tracked. The preserved `legacy_remote_training/` folder contains only old local diagnostics and state.

After this folder move, reinstall the CLI with `uv tool install --force --editable .`, rerun `geoexp host install`, and prepare any preset before submitting it. No scheduled task is changed merely by moving these files.

Run static references from the checkout root with `python runtime/scripts/check_references.py`. Run runner tests from here with `python -m unittest discover -s tests` in an environment containing the installed package.
