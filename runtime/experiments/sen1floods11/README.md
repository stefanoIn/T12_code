# Sen1Floods11 FCN baseline

[Sen1Floods11_FCNN_Baselines.ipynb](Sen1Floods11_FCNN_Baselines.ipynb) trains FCN-ResNet50 with two Sentinel-1 channels. It is one baseline experiment within the thesis on geographic generalisation of GeoFMs.

## Data and environment

Keep the downloaded dataset in this layout relative to `runtime/`:

```text
datasets/Sen1Floods11/v1.1/
  data/
    flood_events/HandLabeled/
    flood_events/WeaklyLabeled/
    perm_water/
  splits/
    flood_handlabeled/
    perm_water/
```

Select a Python kernel on the host containing the dataset and a compatible CUDA-enabled PyTorch installation. The notebook requires NumPy, rasterio, torchvision, Pillow, tqdm, and ipywidgets. Jupyter/ipykernel is needed for interactive execution; nbconvert is needed for headless execution. The first code cell declares Papermill parameters. Install dependencies before execution; the notebook does not install packages during training.

The existing environment observed during this refactor on 2026-10-03 was:

| Component | Observed version |
| --- | --- |
| Python | 3.12.10 |
| PyTorch | 2.14.0+cu130 |
| torchvision | 0.29.0+cu130 |
| NumPy | 2.5.3 |
| rasterio | 1.5.1 |
| tqdm | 4.70.0 |
| ipywidgets | 8.1.9 |
| nbconvert | 7.17.1 |
| ipykernel | 7.3.0 |

This records the local environment, not a cross-platform dependency lock or a guarantee that these exact builds are available on another host. Manage the PyTorch/CUDA installation for that host separately.

## Run locally or remotely

Start the kernel from the repository root or any directory inside it. The notebook searches parents for `README.md` and `runtime/scripts/check_references.py`, then locates `runtime/` and constructs relative paths without changing the working directory. No project-root environment variable is required. A kernel outside the repository must be restarted from inside it.

In remote-connected VS Code, select the kernel on the remote host. Paths refer to that host's filesystem. Choose `EXPERIMENT` in the notebook and run the cells in order. The retained selection is `permanent_water`; the other choices are `hand_labeled`, `s1_weak`, and `s2_weak`.

For asynchronous execution over SSH on Windows, follow the [geoexp runner setup](../../../docs/geoexp.md). The `sen1floods11-fcnn` preset supports CUDA and exposes the four existing variants as validated overrides. For direct headless execution from `runtime/`, use a kernel installed on the execution host:

```text
jupyter nbconvert --to notebook --execute experiments/sen1floods11/Sen1Floods11_FCNN_Baselines.ipynb --output Sen1Floods11_executed --output-dir experiments/sen1floods11/runs/headless/executed --ExecutePreprocessor.kernel_name=thesis-d-cuda --ExecutePreprocessor.timeout=-1
```

Create the output directory first. Replace `thesis-d-cuda` with the local kernel name when needed. These commands execute training; the repository's static checks do not.

## Outputs and resume

Artifacts remain under `experiments/sen1floods11/runs/`: `checkpoints/<experiment>/`, `results/<experiment>/`, and `logs/<experiment>/`. The experiment-specific output names and training settings are unchanged. `RESUME_IF_AVAILABLE=True` resumes from the last completed epoch in `resume_checkpoint.pt`.

New resume checkpoints store the best-model filename relative to the experiment checkpoint directory. Legacy absolute Windows or POSIX references are resolved by filename in that same directory. When transferring a run, copy both its resume checkpoint and its best-model file. No existing checkpoint is rewritten by the refactor.

Metric/history JSONs remain publishable. Runtime metadata, checkpoints, executed notebooks, and ZIP bundles remain local. Saved cell outputs were preserved; clear them before publishing. Historical notebooks under `runtime/datasets/` are preserved locally and are not maintained by this refactor.
