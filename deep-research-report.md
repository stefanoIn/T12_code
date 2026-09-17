# Executive Summary  
Benchmarking Earth-observation foundation models (GeoFMs) demands **diverse, challenging datasets and strict protocols** to avoid over‑optimistic results.  We find four key principles: **Dataset diversity (spatial, modal, temporal)**, **rigorous split design (to avoid leakage/OOD biases)**, **consistent preprocessing**, and **reproducible evaluation protocols** (multiple seeds, fixed hyperparameters).  For each axis (geography, modality, resolution, etc.), we recommend concrete practices and cite recent benchmark sources (PANGAEA, GEO-Bench-2, EarthShift, EarthNets) as evidence.  The report includes a **recommended dataset table** (tasks, modalities, resolution, license, split notes and shift‑suitability flags) and a **protocol checklist** plus a sample Mermaid pipeline diagram.  

Key findings: Use **global, permittively-licensed datasets** with varied tasks (segmentation, classification, regression) and modalities (optical, SAR).  Avoid trivial/saturated benchmarks (e.g. tiny scene scenes with >98% accuracy).  Always separate train/test by location (e.g. spatial blocking or different countries) to measure true generalization.  In experiments, fix most hyperparameters (one optimizer, one LR), vary only a small grid or none, run several random seeds, and report **mean±std** performance.  Preprocessing should match model expectations (e.g. patch size, band selection) and use consistent normalization.  Temporal tasks need careful aggregation: simple pooling often underperforms transformer-based fusion (L-TAE).  

This report synthesizes best practices from PANGAEA, GEO-Bench-2, EarthShift, EarthNets and key dataset papers.  In the following sections we detail **selection criteria, experimental protocol, preprocessing, temporal handling, and evaluation metrics**, illustrating each with examples and references.  We conclude with a consolidated dataset comparison table, a protocol checklist, and a sample end-to-end pipeline (flowchart).  

---

## Dataset Selection Criteria  

- **Geographic Diversity:**  Choose datasets from all continents or diverse climates to avoid regional bias. Many GeoFM benchmarks (PANGAEA, GEO-Bench-2) emphasize global coverage.  For example, PANGAEA includes datasets from South America, Asia, Africa, etc., not just Europe/USA.  A diverse geographic pool stresses models’ spatial generalization.  
  - *Pitfalls:* Many older datasets focus on Europe/NA; models may overfit local features. GEO-Bench-2 explicitly selected globally representative samples and encourages filling gaps.  
  - *Recommendation:* Include at least one dataset per continent (if possible). Use global datasets (e.g. **CloudSEN12** has 5 continents) and region‑holdout tests (train on one country, test on another) to quantify generalization.

- **Spatial Independence (Leakage control):**  Ensure train/test samples are geographically separated. Simple random splits can violate spatial independence (nearby pixels are correlated). Benchmarks like EarthShift introduce explicit *in-distribution vs out-of-distribution* splits and measure robustness. Similarly, CloudSEN12 and So2Sat provide official spatial-block splits to avoid autocorrelation.  
  - *Pitfalls:* Neglecting this leads to overestimated performance. For example, PANGAEA’s cross-region tests on Five-Billion-Pixels show mIoU dropping drastically (e.g. 52% to 18%) when shifting to a new country. This demonstrates “spatial autocorrelation” and differing class sets can mask true robustness.  
  - *Recommendation:* Always use spatial or country‐level splits for evaluation. If not provided, create blocks or leave-one-region-out splits. EarthShift’s formal ID vs OOD framework is a good template.  

- **Application Diversity (Task types):**  Use a variety of tasks beyond scene classification: segmentation (semantic/instance), object detection, change detection, regression, etc. PANGAEA and GEO-Bench-2 target dense tasks (per-pixel) as more realistic and discriminative. GEO-Bench-2 notably avoids easy classification with saturated accuracy (e.g., dropping EuroSAT which yields ~98% across models).  
  - *Pitfalls:* Uniform tasks (all segmentation, or all classification) yield narrow conclusions. Also beware tasks that all models solve (like cloud masks) easily.  
  - *Recommendation:* Include tasks from multiple domains (urban, agriculture, marine, forestry) and modalities (segmentation, detection, regression). PANGAEA excludes trivial tasks and covers agriculture (PASTIS), flood mapping (KuroSiwo), biomass (BioMassters), etc.

- **Modality and Sensor Variety:**  Cover optical (multispectral), SAR, and their fusion. GeoFMs may be pretrained on specific modalities, so benchmarks should test others. PANGAEA explicitly includes optical and SAR datasets, and GEO-Bench-2 groups datasets by sensor (capability “bands”). For example, include Sentinel-1 (SAR) flood tasks and Sentinel-2 (multispectral) land-cover tasks.  
  - *Pitfalls:* A model trained on RGB-only imagery may fail on multispectral data. Ensure datasets match the intended pretraining domains of models under test. PANGAEA’s band-adaptation step standardizes inputs, but avoid feeding incompatible data.  
  - *Recommendation:* Select datasets that test each modality: e.g. Sen1Floods11 (SAR+optical), BioMassters (SAR+optical regression), FTW (optical fields), etc. If evaluating a multi-modal GFM, include purely optical and purely SAR tasks.

- **Spatial Resolution (GSD) and Scale:**  Include both high-resolution (meter-level) and low-resolution (tens of meters) data. EarthNets deliberately chose two benchmarks per task: one ~1m and one ~10m. This exposes models to scale differences. PANGAEA notes some GFMs are pre-trained at coarser GSD and underperform on very high-res data.  
  - *Pitfalls:* Using only one resolution biases toward models tuned to that scale. Also, resolution mismatch can hurt performance if not adjusted.  
  - *Recommendation:* Use datasets spanning e.g. 0.5–30m GSD. Consider “matching resolution” ablations: PANGAEA found that up/downsampling inputs to the model’s pretraining resolution can improve performance. For fair comparison, either resample images to a common GSD (and document it) or test both original and matched resolution.  

- **Temporal Coverage:**  Include static images, bi-temporal (change detection), and multi-temporal (time series) tasks. PANGAEA and GEO-Bench-2 include temporal tasks (DynamicEarthNet, PASTIS-R, BioMassters). Temporal diversity tests models’ ability to use change information.  
  - *Pitfalls:* Treating multi-date data as independent samples discards temporal cues. Also, short vs long time series pose different challenges (PANGAEA saw overfitting on 6-day series).  
  - *Recommendation:* For time-series data, use appropriate aggregation (see “Temporal Aggregation” below). Datasets like PASTIS-R (38–61 Sentinel-2 dates + S1 data) or DynamicEarthNet (daily labels) provide temporal benchmarks. When using such data, specify how sequences are handled (e.g. summation, temporal encoder).

- **Label Quality and Class Balance:**  Favor datasets with **reliable, diverse labels**. Avoid datasets that are either too easy or too noisy. GEO-Bench-2’s “challenging and discriminative” criterion picks datasets where strong vs weak models differ appreciably.  
  - *Pitfalls:* Highly imbalanced classes (like burn scars only 11% pixels) can inflate accuracy; ensure metrics like IoU account for imbalance. Also, avoid overly coarse labels that saturate (e.g. broad water mask without permanent vs flood separation, as PANGAEA suggests flood tasks require multi-class masks).  
  - *Recommendation:* Check dataset documentation for annotation quality. If using a dataset with noisy labels, consider a validation of label accuracy or treat it as additional uncertainty. Use metrics robust to imbalance (F1, IoU) and report per-class performance.  

- **Pretraining Overlap and Novelty:**  Be aware if a dataset’s imagery was used to pretrain a model. If the exact or very similar data was seen during GFM pretraining, reported gains may reflect memorization. PANGAEA notes many GFMs have extensive Earth-image pretraining.  
  - *Pitfalls:* Using a test set close to pretraining data can falsely inflate a model’s apparent skill.  
  - *Recommendation:* Prefer datasets collected after the common pretraining cut-off, or from different satellites/geographies. GEO-Bench-2 addressed this by grouping datasets (they assume separate tasks). At least note if a dataset source (e.g. Sentinel-2 tiles) overlaps known pretraining collections.

- **Licensing and Accessibility:**  Choose **permissively licensed** (CC-BY, CC0, etc.) or open datasets so others can reproduce. GEO-Bench-2 prioritized open licenses. Non-commercial or proprietary licenses can block follow-up work.  
  - *Pitfalls:* Benchmarks using copyrighted or non-commercial data hinder community use.  
  - *Recommendation:* Use open data catalogs (Sentinel, Landsat) or datasets explicitly released for research (as listed in GEO-Bench-2 table). If a useful dataset has restrictive terms, document them and consider excluding or replacing it.

**Example:** GEO-Bench-2’s final list of 19 datasets illustrates these criteria: each chosen for being discriminative (not trivial), open-licensed (avoid CC-BY-NC), and diverse in task/modality (see Table 2). PANGAEA’s 11 datasets similarly span floods, land cover, regression, multispectral vs high-res, etc., to “cover diverse domains, tasks, resolutions, modalities, temporalities”.

---

## Experimental Protocols  

- **Data Splitting Strategies:**  Define train/val/test carefully. Common schemes include:  
  - *Random Split* (IID) for baseline.  
  - *Spatial-block split* (divide the area into blocks or by location, use distinct blocks for train/test). CloudSEN12 (Jin et al.) and So2Sat provide block-based splits to prevent overlap. PANGAEA advocates “spatially stratified” splits to avoid auto-correlation.  
  - *Cross-region (OOD) split* (train on some regions, test on held-out region/country). EarthShift formalizes this: each dataset has an in-distribution set and an out-of-distribution set representing one shift (spatial, temporal, sensor, etc).  
  - *Temporal split* (train on earlier dates, test on future dates for the same location). Useful for change detection or forecasting tasks, though less common in static benchmarks. If temporal shifts matter, hold out later dates as OOD.  

  *Pitfalls:* Random splits on spatial data leak location-specific cues. Cross-region splits can alter label distributions (as seen for FiveBillionPixels), so interpret OOD drops carefully.

- **Cross-Region / OOD Testing:**  For each dataset, if possible, perform one or more *location-out* tests. E.g. train on Europe, test on Asia. EarthShift uses paired datasets specifically (e.g. German vs Cambodian field maps) to isolate each shift type. While not always available, you can simulate OOD by excluding entire clusters (country, climate zone) from training.  
  - *Pitfall:* Class distributions may change between regions. Compare OOD performance relative to ID (effective robustness) rather than raw difference to avoid misinterpretation.

- **Label-Fraction (Few-Labels) Experiments:**  Benchmark GFMs under scarce labels by training with a small fraction of data (e.g. 1%, 10%). PANGAEA does a 10%-labels evaluation to reveal which models shine in low-data regimes.  
  - *Pitfalls:* Ensure the small set is still representative (perhaps one or few samples per class). If randomly chosen, stratify by class. Also, run multiple random picks (each as a “seed”) to capture variance.  

- **Hyperparameters and Seeds:**  Fix as many settings as possible to “canonical” values. For example, PANGAEA uses the same decoder architecture and ADAM LR=1e-4 for all models. GEO-Bench-2 similarly prescribes a protocol (learning rate, batch size, etc).  
  - *Pitfalls:* Excessive tuning on each model/dataset can unfairly favor some. PANGAEA found that tuning LR changed performance by only a few percent and rarely altered model ranking. Moreover, random seed variability often matches tuning gains.  
  - *Recommendations:* Use a consistent optimization setup for all tests. A small LR grid (e.g. 1e-5–1e-3) may be explored initially to find a stable value, then fix it. Always run *multiple random seeds* (at least 3–5) per experiment, report mean±std performance. For final reporting, quote mean±std to reflect uncertainty. Using confidence intervals or statistical tests (paired t-test) can further validate differences if needed.

- **Training Protocol:**  Fine-tune only the task-specific head (keeping pretrained encoder fixed) to isolate representation quality, or fully fine-tune depending on evaluation goals. PANGAEA benchmarks both frozen and full fine-tuning. For a standardized protocol:  
  1. **Initialization:** Use public GFM weights (ensuring they support the input bands). Add a randomly initialized task head (e.g. linear classifier or decoder).  
  2. **Warm-up:** Optionally freeze encoder for first few epochs. Some works use few epochs of head-only training.  
  3. **Optimization:** Use Adam (or AdamW) with a moderate LR (commonly 1e-4 for heads). Include weight decay if appropriate.  
  4. **Early stopping:** Use validation loss or metric to stop, or fix epochs (PANGAEA used 80 epochs).  
  5. **Data augmentation:** Simple augmentations (flip, rotate) can help especially when training from scratch (though consistency is key to compare methods). Follow any dataset's recommended augmentations.  
  6. **Repeat:** For each seed and, if performing ablation (like label fraction), for each split/setting.

- **Evaluation Metrics:**  Choose metrics matching the task (e.g. mIoU or F1 for segmentation; accuracy/mAP/F1 for classification; RMSE/MAE for regression). Always report **mean±std** over seeds. For multi-class tasks, also consider per-class metrics if class balance is uneven. GEO-Bench-2 introduced “capability groups” where each group of datasets is summarized, but we can simply show separate results per dataset.  
  - *Pitfalls:* Reporting only best-of-many runs or only ID performance masks true robustness. Use paired (ID vs OOD) comparisons when possible, as in EarthShift, and present both ID and OOD scores.  
  - *Recommendations:* Along with aggregate metrics, provide *effective robustness* if doing OOD (subtract predicted baseline). When comparing models, highlight significant differences (e.g. non-overlapping error bars) instead of just raw means.

---

## Preprocessing Recommendations  

- **Match Model Input Requirements:**  Convert dataset imagery to what the GFM expects. For optical data, if the model was pretrained on RGB, you may need to collapse or drop some bands. PANGAEA “adopts a common band adaptation strategy” so that any model can process all images. For instance, if a model has only 3 input channels but data has 10 bands, select the closest bands or use PCA/averaging.  
  - *Pitfalls:* Mismatched channels can cause errors. Using only RGB bands on a multispectral dataset may lose valuable information. Conversely, feeding a 10-band model 3-channel data can be padded or retrained. Always note these choices.  

- **Radiometric Normalization:**  Apply consistent normalization (mean subtraction, std division) channel-wise. Use the statistics of the training split or the known satellite reflectance scaling. PANGAEA found normalization choice crucial (“some GFMs may have been trained on standardized data”), but ultimately fixed a protocol.  
  - *Pitfalls:* If models expect radiance or reflectance, ensure correct format. Do not mix raw digital numbers with calibrated reflectance inadvertently.  

- **Spatial Resolution/Resampling:**  Decide whether to match the model’s pretraining resolution or preserve original detail. For example, a ViT pretrained on 160×160 images may underperform on 512×512 high-res inputs. PANGAEA’s ablation (Section 5.4) showed that “matching the model’s training resolution” (downsampling inputs) can significantly improve results on Five-Billion-Pixels.  
  - *Pitfalls:* Arbitrarily upsampling can introduce artifacts; downsampling too much loses fine detail.  
  - *Recommendation:* If a model’s input size is fixed, tile or patch large images accordingly. Consider two strategies: **(a)** feed the model the native resolution by tiling and aggregating outputs, or **(b)** resample inputs to the model’s nominal scale. Ideally, test both and report which was used.  

- **Resampling Method:**  Use area resampling (for downsampling) to preserve average pixel values. If needed, use bilinear or nearest when upsampling. Document your choice.  

- **Data Consistency:**  Apply the same preprocessing to train and test. For multitemporal data, ensure all time steps undergo identical processing. If using external data (DEM, slope, etc.), include them consistently for all samples.  

- **Standardization vs Min/Max:**  For multispectral data, a common choice is to normalize each band to [0,1] by known min/max (or reflectance scaling) and then subtract mean/scale by std. Avoid changing normalization between experiments unless deliberately studying its effect (PANGAEA 5.3 did such an ablation).  

**Example:** GEO-Bench-2 provides a “TACO” format with preprocessed, self-contained samples. Many libraries (TorchGeo, EarthNets) embed common transforms. Mimic those to ensure comparability.  

---

## Temporal Data Aggregation  

For **multi-temporal datasets** (time series), deciding how to fuse frames is critical. Two main strategies:  
- **Simple aggregation (linear pooling):** For example, averaging features or soft-voting outputs across time. This is easy but may underutilize temporal patterns.  
- **Learned spatio-temporal encoding:** Feed the sequence into a temporal encoder (LSTM, transformer). PANGAEA experiments compared *linear mapping* vs *Lightweight Temporal Attention Encoder (L-TAE)*, finding L-TAE often **10–20% mIoU gains** on PASTIS-R and BioMassters. This suggests models should exploit time explicitly.  

  - *Pitfall:* Overfitting if time series are very short. On DynamicEarthNet (6 days), L-TAE actually hurt performance (overfit).  
  - *Recommendation:* If sequences are long (many images/year, as in BioMassters or PASTIS), use a temporal model. For short series, linear pooling might suffice. At minimum, experiment: compute baseline by treating each date separately or stacking channels, then try a simple RNN/attention stack.  

Also consider **label temporal interpolation**: if labels are sparse (monthly) but images are daily (DynamicEarthNet), align labels carefully. GEO-Bench-2’s “temporality” grouping suggests always clarify if all time-steps carry labels or just endpoints.  

---

## Evaluation Metrics and Reporting  

- **Mean ± Std:**  Always report average performance *plus/minus* one standard deviation over multiple runs (different random seeds, splits, etc). For example, report *mIoU = 72.5% ± 0.8%*. PANGAEA explicitly uses this to show run-to-run variability.  
  - *Pitfall:* Quoting only the best run or a single number is misleading.  

- **Significance and Robustness:**  If claiming model A > B, ensure differences exceed noise. Non-overlapping error bars or a paired test can help. EarthShift advocates measuring robustness as the *difference* between ID and OOD performance (effective robustness) to isolate shifts.  

- **Per-Axis Aggregation:**  If using multiple datasets, summarize by categories (as GEO-Bench-2 does with “capability groups” – e.g. low-res vs high-res tasks). Even if not formalized, you can present performance in table form by dataset, and highlight broad trends (e.g. SAR tasks vs optical tasks).  

- **Baselines:**  Always include simple supervised baselines (e.g. UNet) and even Vision-Model baselines (ImageNet-pretrained CNN). Many studies (PANGAEA, EarthShift) find that GFMs do not always beat strong task-specific or even random models under all settings.  

---

## Recommended Datasets  

We summarize a **shortlist of 10 datasets** that together cover diverse axes. The table below lists **Name, Location, Task, Modalities, GSD, Size, Access**, plus flags indicating suitability for testing *spatial leakage*, *cross-region shifts*, *temporal robustness*, *modality generalization*, and *label-scarcity*. (Flags are “✅” if the dataset is especially useful for that axis.)

| **Name**        | **Geography**            | **Task**                             | **Modalities**                    | **GSD**       | **Size**                 | **Download / Info**                  | **Coords Avail?** | **Official Split** | **Tests suitability**<br>(Spatial, Cross-region, Temporal, Modality, Label-scarcity) |
|:---------------|:------------------------|:-------------------------------------|:----------------------------------|:------------:|:------------------------|:------------------------------------|:----------------:|:-----------------:|:-------------------------------------------------------------------------------|
| **Sen1Floods11** | Global (11 flood events: S. America, Africa, Asia, NA, Europe) | Flood **segmentation** (binary: flooded vs not) | S1 SAR (VV+VH) + S2 (RGB+NIR) | 10–20 m      | 4,831 images (512×512), ~14 GB | [GitHub](https://github.com/cloudtostreet/Sen1Floods11) | ✅               | ❌ (standard split)  | ✔ (Spatial) ❌ (Cross-reg) ❌ (Temporal) ✔ (Modalities: SAR-optical) ❌ (Labels: dense) |
| **CloudSEN12**   | Global (all continents)   | Cloud/shadow **segmentation**       | S1 + S2 + DEM + aux layers        | 10 m        | ~49,400 patches; ~10K labeled; ~~1 TB~~ | [Zenodo](https://doi.org/10.21227/qngb-ff39) | ✅               | ✅ (pixel- and block-splits) | ✔ (Spatial) ✔ (Cross-reg) ❌ (Temporal) ✔ (Multi-modality) ❌ (dense, some small classes) |
| **So2Sat LCZ42** | Global cities (100+ cities across continents) | Local Climate Zone **classification** (17-class, per-image) | S2 (13 bands) + S1 SAR | 10 m        | 400,673 images (32×32)   | [Data Hub](https://datahub.asu.edu/dataset/so2sat)  | ❌ (no coords released) | ✅ (spatial, cultural) | ✔ (Spatial) ✔ (Cross-reg) ❌ (Temporal) ✔ (Multimodal) ✅ (Each tile small image) |
| **BigEarthNet V2** | Europe | Multi-label Land Use **classification** (19 classes) | S1 + S2 (12 bands)            | 10 m        | 549,000 patches (120×120) | [Download](https://bigearth.net) / [TorchGeo](https://docs.torchgeo.org) | ✅               | ✅ (standard train/val/test) | ✖ (small area) ❌ (Cross-reg) ❌ (Temporal) ✔ (Multimodal) ✖ (dense labels) |
| **Fields of the World (FTW)** | World (multiple countries) | Agricultural **field segmentation** (plot boundaries) | S2 time-series (RGBN)         | 10 m        | 70,795 images (256×256)  | [TorchGeo](https://docs.torchgeo.org) / [GitHub](https://github.com/earthshift) | ✅               | ✅ (country holds-out in EarthShift) | ✔ (Spatial) ✔ (Cross-reg) ❌ (Temporal) ✖ (Optical only) ✖ (many fields, moderate) |
| **PASTIS-R**     | France (multiple regions) | Crop **semantic/panoptic segmentation** | S2 time-series (RGB+NIR) + S1 (asc/desc) | 10 m        | 2,433 patches (128×128); 124k parcels; 54 GB zip | [Zenodo](https://zenodo.org/record/7022687) | ✅               | ✅ (official 5-fold) | ✔ (Spatial) ✖ (Cross-reg) ✔ (Temporal) ✔ (Multimodal) ✖ (Parsimonious: 2433) |
| **Five-Billion-Pixels (FBP)** | China (150 urban/rural areas) + some Asia | Land cover **segmentation** (24 classes) | Gaofen-2 (4m, RGB+NIR)    | 4 m         | 150 images; >5 billion labeled pixels | [Project](https://x-ytong.github.io/project/Five-Billion-Pixels.html) | ✅ (coords given) | ❌ (random subsets available) | ✔ (Spatial: cross-city) ✔ (Cross-reg) ❌ (Temporal) ❌ (Single optical) ✔ (Large, varied) |
| **HLS Burn Scars** | USA (CONUS, wildfire sites) | Burn scar **segmentation** (binary) | HLS (Landsat+S2) 6 bands   | 30 m        | 804 scenes (512×512); 2.7 GB | [HuggingFace](https://huggingface.co/nasa-impact/hls_burn_scars) | ✅               | ✅ (2/3 train,1/3 val) | ✖ (local) ✔ (Cross-reg: different fire sites) ✖ (Temporal) ✖ (Optical only) ✔ (Scarce positives) |
| **KuroSiwo**     | Global flood events      | Flood **segmentation/change** (multi-temporal) | S1 SAR (HH) + DEM/slope     | 10 m        | many events (224×224 patches) | [GitHub](https://github.com/Orion-AI-Lab/KuroSiwo)          | ❌ (no coords)     | ❌ (custom splits)    | ✔ (Spatial) ✔ (Cross-reg: held-out events) ✔ (Temporal) ✔ (SAR-focused) ✖ (Dense masks) |
| **BioMassters**   | Finland (forest inventory) | Biomass **regression** (per-pixel) | S1 (VV/VH) + S2 (10m multispectral) | 10 m        | 13,000 patches (256×256); ~12k target maps; 200+ GB | [HuggingFace](https://huggingface.co/nascetti-a/BioMassters) | ✅               | ✅ (train/val/test provided) | ✖ (local) ✖ (Cross-reg) ✔ (Temporal: annual time series) ✔ (Multimodal) ✔ (Many small patches) |

Each dataset in the shortlist is **publicly available** and has documentation. We highlight their axes: e.g. **Sen1Floods11** tests SAR-optical fusion, **CloudSEN12** tests spatial generalization for clouds, **So2Sat** explicitly offers “seen vs unseen cities” splits, **FTW** has cross-country fields for geography, **BioMassters** brings a unique regression task, etc. Together, they span the requested criteria.

---

## Experimental Checklist  

Below is a recommended checklist to ensure a **rigorous, reproducible evaluation**:  

- **[Dataset Preparation]**  
  - [ ] Collect/download all datasets. Confirm data licenses allow use.  
  - [ ] Verify each sample (bands, resolution) meets model input requirements (e.g. RGB vs multispectral).  
  - [ ] Generate or confirm **train/val/test splits**: ensure **no spatial overlap**. Where possible, reserve entire regions for testing.  
  - [ ] For multi-temporal data, decide how to align labels (e.g. provide label for final time).  

- **[Preprocessing]**  
  - [ ] Compute normalization stats (mean/std) on training splits for each band. Apply same to val/test.  
  - [ ] If needed, **match resolution**: downsample or tile images per model’s input size.  
  - [ ] Confirm all images are in reflectance or consistent scale.  
  - [ ] (Optional) Implement any recommended augmentations (flip, jitter) uniformly.  

- **[Model Setup]**  
  - [ ] Obtain/pretrain weights for each GFM. Ensure compatibility (band ordering, number).  
  - [ ] Define model head for each task (e.g. segmentation decoder, classification layer).  
  - [ ] Use identical head architecture for all GFMs to isolate encoder differences.  

- **[Training Protocol]**  
  - [ ] **Fixed hyperparameters:** e.g. Adam with LR=1e-4, batch size=..., weight decay=... (as per GeoBench/PANGAEA defaults). Only lightly tune LR if absolutely needed (e.g. one dataset trial).  
  - [ ] Train for a **fixed number of epochs** (or early-stop on val). Use same schedule for all.  
  - [ ] Use **several random seeds** (≥3) for weight initialization/data order. Record all.  
  - [ ] (Optional) If testing label-scarcity, subsample a fraction of training labels (e.g. 10%) and repeat training for that scenario.  

- **[Evaluation]**  
  - [ ] Compute metrics (mIoU, F1, accuracy, RMSE, etc) on test splits for each run.  
  - [ ] For OOD: evaluate on held-out region/time separately. Compute **robustness gap** (OOD vs ID).  
  - [ ] Aggregate results: report mean±std across seeds/runs.  
  - [ ] Compare to baselines (UNet, ViT, or a random init). Highlight significant differences.  
  - [ ] Document failure modes: e.g. large gap on cross-region or poor calibration.  

- **[Analysis]**  
  - [ ] Present per-dataset and per-capability summaries (e.g. tables grouping by resolution or temporal).  
  - [ ] Check if any dataset saturates (all models get near-perfect) – if so, consider dropping it.  
  - [ ] Plot trends (e.g. performance vs label fraction) to visualize data scarcity effects.  

Following this checklist, possibly automated in a pipeline (see flowchart below), will ensure a **transparent and fair comparison**.

```mermaid
flowchart LR
    A[Download Datasets] --> B[Preprocess Data]
    B --> C[Define Splits (spatial blocks, OOD holds)]
    C --> D[Initialize Models (load GFM weights)]
    D --> E[Train Heads (fixed LR, seeds)]
    E --> F[Evaluate Metrics (per seed/run)]
    F --> G[Aggregate Results (mean±std, error bars)]
    G --> H[Analyze (plots, tables, significance)]
```

This flowchart illustrates a **reproducible pipeline**. At each step, record all parameters (seed, hyperparams) to facilitate replication. 

**Reporting:** Finally, document all choices (e.g. “We trained for 80 epochs with Adam, LR=1e-4, batch size 8; 5 seeds per experiment; metrics averaged.”). Provide links to code or Docker images if possible.

---

## Sources  
We drew upon recent benchmark papers and dataset documentations. Key references include PANGAEA, GEO-Bench-2, EarthShift, EarthNets, and dataset publications. Each recommendation above is supported by these primary sources. (For brevity, inline citations are given in the text; see those works for further details.)