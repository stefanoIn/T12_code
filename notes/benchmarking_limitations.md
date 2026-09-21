# Executive Summary

Geospatial foundation models (GFMs) promise broad reuse of satellite imagery backbones across Earth-observation tasks. However, recent analyses reveal *inconsistent and narrow* evaluations. Common pitfalls include mismatch between pretraining and evaluation (e.g. image resolution, spectral bands, and preprocessing), spatial and temporal leakage, and unreported experimental details (e.g. hyperparameters, random seeds). Leading benchmarks aim to address these gaps. PANGAEA systematically assembles diverse datasets (multiple resolutions, sensors, geographies) under a unified protocol, highlighting GFMs’ limitations (e.g. often underperforming specialized baselines). EarthShift probes real-world **distribution shifts** (temporal, geographic, sensor, scale), finding GFMs drop ~15–20% OOD and lack robustness gains over standard models. The field-wide audit by Taylor *et al.* (2026) finds widespread reproducibility issues: no shared evaluation harness, divergent protocols, missing weight releases, and lack of variance reporting. 

This report surveys these benchmark efforts (PANGAEA, EarthShift, GEO-Bench-2, etc.) and dataset collections (e.g. BigEarthNet V2, Five-Billion-Pixels, CloudSEN12, Sen1Floods11), catalogs recurring limitations of current evaluations (Table 2), and outlines remedies. Key best practices include aligning preprocessing to model training or dual-reporting results, using spatially-blocked or cross-region splits, performing multiple runs with confidence intervals, and carefully matching model and data resolutions. Open research opportunities include systematic “sensitivity analyses” (varying preprocessing, resolution, sensor inputs, label fraction, splits) and richer diagnostics (per-class confusion, calibration, effect sizes) to understand GFMs’ behavior. We propose a flexible benchmarking pipeline (Fig. 1) and visualization of model performance “sensitivity matrices” to guide future experiments. The accompanying tables map popular datasets (tasks, modalities, etc.) and major papers to the issues they expose. 

# Major Benchmarking Efforts

- **PANGAEA** – A 2025 *arXiv* benchmark that unifies 11 downstream tasks (segmentation, change detection, regression) across diverse resolutions (from 3 m to 100 m), sensors (optical, SAR), and geographies (urban, agriculture, forestry). All GFMs use the same preprocessing (crop/resize, normalization) and band-matching (zero-pad missing bands) for fair comparison. Key findings: GFMs often lag behind specialized baselines, especially on unmatched resolutions; supervised training can outperform GFMs under label scarcity. PANGAEA highlights global biases in prior benchmarks and hyperparameter sensitivity in GFMs.

- **EarthShift** – A 2026 *arXiv* benchmark focusing on *natural distribution shifts*. It defines five shift types (resolution, time, location, sensor, data source) and paired in-/out-of-distribution datasets. Experiments (8 GFMs, 11 tasks) reveal that GFMs suffer ~15–20% performance drops OOD, with no inherent robustness advantage over generic or supervised models. For example, models handle temporal shifts well, but degrade sharply under geographic or sensor shifts. This underscores the need to include realistic OOD tests in benchmarks.

- **GEO-Bench-2** (Simumba *et al.*, 2026) – An arXiv-proposed evaluation suite spanning 19 tasks (classification, segmentation, detection, etc.) and 4 modalities. It emphasizes **capability groups** – grouping tasks by modality and scale – and prescriptive protocols for consistency. Results show no single model dominates all groups: satellite-specific models (TerraMind, Prithvi, Clay) excel on low-resolution/modality-rich tasks, while image-pretrained ViTs do better on high-res RGB tasks. This suggests future GFMs may need multi-resolution adaptability.

- **FoMo-Bench / PhilEO / TorchGeo** – Curated lists of EO tasks (e.g. forest monitoring) with code toolkits, but typically lack *canonical evaluation harnesses*. The Taylor *et al.* audit notes that even when datasets are shared, inconsistent training scripts and metrics (“*weighed vs macro IoU*”) make cross-paper results incomparable.

- **Related Dataset Benchmarks** – Many EO datasets serve as de facto benchmarks. Notable examples (see Dataset Table) include:
  - **BigEarthNet v2** (multilabel land cover on 549K Sentinel-1/2 patches over Europe, 10 m GSD).
  - **Five-Billion-Pixels** (high-res land-cover segmentation, 4 m, covering ~50K km² in China).
  - **DynamicEarthNet** (Planet daily land-cover maps, 3 m, 75 global AOIs).
  - **So2Sat LCZ42** (urban local climate zones, 10 m, 42 cities, optical+SAR).
  - **CloudSEN12** (cloud segmentation, ~50K global patches, optical, SAR, DEM, automated labels).
  - **Sen1Floods11** (flood inundation maps, ~4.8K Sentinel-1 scenes globally).
  - **Fields of the World (FTW)** (global agricultural field boundaries, multi-country).
  - **HLS Burn Scars** (NASA/HuggingFace, USA, post-fire segmentation, 30 m Landsat/Sentinel).
  - **PASTIS-R, MADOS, SpaceNet, etc.** – used in PANGAEA’s analyses (appendix).

These benchmarks vary widely in scope, which highlights the need for consistent evaluation protocols.

# Common Evaluation Limitations

Across GFMs and EO benchmarks we identify recurring pitfalls:

- **Preprocessing–Pretraining Mismatch**: Models often expect inputs in a form different from test data. For example, a GFM pretrained on RGB imagery struggles with multispectral data unless bands are matched or padded. Inconsistent resizing/normalization can inflate differences: PANGAEA found uniform normalization (dataset-wise mean–std) important for fairness. *Remedy:* Apply either a model’s *native* preprocessing or a standardized pipeline, and **report both** or justify choices.

- **Resolution / GSD Differences**: GFMs pretrained on low-res data often underperform on high-res tasks, and vice versa. PANGAEA shows, e.g., Scale-MAE (high-res pretraining) outperforms Sentinel-2 pretrained models on high-res datasets. Conversely, some GFMs struggle with coarse-scale tasks where baselines excel. *Remedy:* Match evaluation data to pretraining resolution when possible, or explicitly test resolution sensitivity (see Open Opportunities).

- **Spectral/Modal Mismatch**: Combining optical and SAR is tricky. Few GFMs (CROMA, DOFA) natively handle both. Using zero-padding or light fusion can introduce artifacts. Mismatches in band availability (e.g., missing NIR band) can degrade performance.  

- **Temporal Aggregation**: Many benchmarks (PANGAEA, EarthShift) include multi-date imagery. But most GFMs take single images. Strategies (e.g., temporal pooling or attention) must be chosen. PANGAEA introduces feature-aggregation modules (linear or transformer) to adapt single-frame GFMs for multi-temporal tasks. Failure to properly aggregate temporal data can unfairly penalize models. *Remedy:* Use or develop appropriate temporal models, or report both single-frame and multi-frame results.

- **Spatial Autocorrelation / Data Leakage**: Random train/test splits in geospatial data often violate independence (nearby pixels are correlated). This inflates reported accuracy. Many legacy studies do not block by location. *Remedy:* Use spatially-blocked or cross-region splits. For example, the FTW dataset randomizes 3×3-km blocks, and GFM audits recommend geographic holdouts. Always clarify split methodology.

- **Class-Distribution Shifts**: Differences between train and test label distributions can mislead results. E.g., PANGAEA notes that omitting minor classes in the test set (compared to training) can drastically reduce performance on those classes. If models are tested on biased or narrower distributions, reported metrics can be overly optimistic.

- **Sensor/Domain Shifts**: Many tasks use data from different sensors or sources (e.g. Sentinel vs Maxar, or Landsat vs Sentinel composites). Models may not generalize across sensors. EarthShift found GFMs brittle to sensor changes (e.g. training on one satellite vs testing on another).  

- **Hyperparameter / Tuning Sensitivity**: GFMs can be extremely sensitive to learning rate, batch size, and epochs. Taylor *et al.* note that few papers perform proper tuning, leading to unfair comparisons. PANGAEA fixes a decoder LR schedule (80 epochs, Adam, LR1e-4) for all models, but acknowledges this may not be optimal for every model. *Remedy:* Perform dedicated hyperparameter search for each model/task (or at least ablate common settings), and document the protocol.

- **Stochasticity / Seed Variance**: Random seeds and training nondeterminism can shift metrics by several points. Taylor *et al.* explicitly recommend **reporting variance** or confidence intervals. Yet most works run only 1-3 seeds. *Remedy:* Train multiple runs per setting and report mean±SD or statistical tests. Use bootstrapped confidence intervals for key metrics.

- **Inconsistent Splits and Overlap**: Beyond autocorrelation, some benchmarks share similar geographies between train and test (overlap by design). For example, global datasets sometimes sample the same tiles. Without precise split documentation, comparisons break. *Remedy:* Clearly publish split indices or geographic coordinates.

- **Label Quality / Annotation Differences**: Many EO benchmarks use labels of varying quality (e.g. auto-generated, crowd-sourced, or derived from coarse maps). Even class definitions can differ between datasets. As the audit notes, “class definitions, geographic coverage, label quality” vary widely. Some datasets (e.g. CloudSEN12) use consensus of cloud-detection algorithms as labels, not hand annotations. Users must consider label noise.

- **Metrics and Averaging**: Papers sometimes use different metrics (accuracy vs IoU vs F1) or different averaging (micro vs macro IoU). For example, two papers reported Scale-MAE accuracies on the same benchmark differing by 56 points (33% vs 89%) due to protocol differences. *Remedy:* Use standardized metrics and averaging definitions; report multiple metrics (overall accuracy and per-class IoU, for example) and clarify how they are computed.

- **Compute/Resource Bias**: High-resolution GFMs demand large compute. Models trained only on high-end GPUs or supercomputers may not be easily reproduced by smaller labs. Some benchmarks (like Young *et al.*) highlight lack of documentation on resource requirements. *Remedy:* Authors should report model sizes and training resources.

- **Reproducibility and Transparency**: Many GFM papers do not release code or weights (39% released none). Without open weights or detailed training logs, results cannot be verified. *Remedy:* Release code, model checkpoints, data processing scripts, and fix random seeds. Even legacy models should have archived versions. Depositing weights and code in permanent repositories (Zenodo, Hugging Face, etc.) is recommended.

- **Usability/Documentation**: Young *et al.* (2026) note that ~1/3 of GFMs offer no user support beyond raw code. This hinders adoption by domain experts. *Remedy:* Provide clear documentation, tutorials, and maintain a user community. Evaluate models not just by accuracy but also by ease-of-use (see dimension “Scientific Permanence & Reproducibility” in).

These issues often interact (e.g. spatial leakage + high variance can give deceptively high results), so systematic validation is crucial.

```mermaid
flowchart TD
    A[Define tasks and datasets] --> B[Split data with spatial independence]
    B --> C[Preprocess data (standardized and/or model-specific)]
    C --> D[Train models (multiple seeds, tune hyperparams)]
    D --> E[Evaluate (in-distribution & OOD tests, consistent metrics)]
    E --> F[Aggregate results (confidence intervals, per-class analysis)]
    F --> G[Document full pipeline (compute, code, configs)]
```
*Figure 1: Recommended GFM evaluation pipeline (mermaid flowchart). Steps include dataset selection, spatially-independent splits, dual-mode preprocessing, multi-seed training, robust evaluation, and transparent reporting.*

# Paper–Limitations Mapping

| **Paper/Benchmark**      | **Limitations Highlighted**                                                    |
|--------------------------|-------------------------------------------------------------------------------|
| **PANGAEA (2025)**  | Geographic bias (mostly Europe/NA previously); need for multi-resolution, multi-sensor benchmarks. Shows *preprocessing impact* (normalization, band matching) and *resolution mismatch* effects. Notes hyperparam and seed sensitivity when comparing GFMs to baselines. |
| **EarthShift (2026)**  | Absence of OOD tests in earlier benchmarks. Finds large *performance drops under distribution shift* (time, location, sensor, etc.), and that GFMs offer no inherent robustness edge over simpler models. Implies necessity of targeted OOD evaluations. |
| **GEO-Bench-2 (2026)** | Emphasizes inconsistent evaluation across modalities; proposes unified protocols. Demonstrates no single GFM excels on all tasks, underscoring the *task specialization* of current models. (Insufficient standardization in previous works.) |
| **No-One-Knows (2026)** | Documents widespread *inconsistent protocols*: divergent metrics, missing weight/code releases (39% no weights), unique data configurations, lack of variance reporting, spatial overlap. Advocates shared benchmarks, reporting uncertainty, and disentangling model vs data effects. |
| **How Usable Are GFMs? (2026)** | Focus on *usability*: finds ~1/3 of GFMs lack documentation/support. Highlights dimensions like access, transparency, reproducibility (long-term archival) as often neglected. |
| **Fields of the World (2024)** | Introduces *blocked random splits* to avoid spatial autocorrelation. Its design choice exemplifies the need for careful spatial partitioning in benchmarks. |
| **Standard Dataset Papers (e.g. BigEarthNet, Five-Billion)** | Often note their own biases: e.g., Five-Billion-Pixels is China-only (so not globally representative); Sen1Floods11 focuses on flood events in select regions. These imply potential geographic and class-coverage biases in benchmarking GFMs. |
| **Other Evaluations (GeoBench, SustainBench, etc.)** | GeoBench (Lacoste et al.) introduced SDG monitoring tasks but shares similar issues of diverse metrics. Misc. field papers note label noise and imbalance. |

This mapping (Table 2) emphasizes that no single work covers all issues; the field must address them collectively.

# Best Practices and Remedies

Based on the above, we recommend the following to improve GFM benchmarking:

- **Model-Native vs Standardized Preprocessing:** When possible, **align preprocessing with pretraining**: e.g., use the original normalization and band selection for each GFM. Where unknown, use a fair standard pipeline for all models (as PANGAEA does). *Dual-reporting* (show both native and standardized results) can be informative. Clearly document any resampling or cropping.

- **Band and Modality Matching:** Explicitly map model input channels to dataset bands. If a model lacks needed bands, consider augmenting or padding, but note this can bias results.

- **Balanced Hyperparameter Tuning:** Perform (and document) hyperparameter search for each model/task instead of one-size-fits-all settings. At minimum, follow established schedules (e.g. EarthShift’s two-stage LR sweep). Report the tuning process.

- **Multiple Seeds and Confidence Intervals:** Train models with multiple random seeds and report mean±std of metrics (or bootstrap confidence intervals). Taylor *et al.* specifically recommend *“variance reporting”* in all comparisons. Even a box-and-whisker of performance helps gauge uncertainty.

- **Spatially-Aware Splitting:** Use **blocked** or **cross-region** splits to avoid spatial leakage. For example, Fields-of-World splits data into 3×3 km blocks randomly, and other works hold out entire geographic regions. Clearly report split methodology and justify if spatial blocks were not used.

- **Temporal Holdouts:** Similarly, if evaluating future applicability, hold out later time periods entirely. EarthShift’s temporal shifts (e.g., two different years) are good practice.

- **Domain-Specific Baselines:** Always include not only GFMs but also *task-specific supervised baselines* (UNets, ResNets) and simple seasonal models to contextualize performance. Many benchmarks (PANGAEA, EarthShift) find supervised baselines are competitive.

- **Metadata and Context Reporting:** Provide detailed dataset metadata (geographical extents, resolution, sensor types, date ranges) and model training details (compute, GPUs, training time). At least specify the pretraining data/domain. Archive code and seeds. Address *“scientific permanence”* by using stable identifiers (DOIs, Git tags). 

- **Effective Resolution Reporting:** When using multiple sensor types or re-sampled imagery (e.g. computing 10 m bands from 20 m), report the “effective GSD” of inputs. This transparency is often missing.

- **Data-Quality Checks:** Evaluate label noise and completeness. For instance, if ground truth is automatically derived (as in CloudSEN12), note this and if possible cross-validate with manual labels. 

- **Task-Specific Metrics:** Beyond overall accuracy, use metrics suited to the task (e.g. *mIoU* or *F1* for segmentation, *ndvi reduction* for crop tasks). Be consistent in class weighting (macro vs micro averages) across papers.

- **Compute Equity:** If benchmarking many models, report the hardware and time. This lets others gauge feasibility. Small labs might test only smaller GFMs; this difference should be transparent.

- **Open and Shared Harnesses:** Whenever possible, submit models to community evaluation harnesses. (The Taylor audit compares this to LLM leaderboards; currently EO lacks a single “official” platform.) In lieu of that, publish your evaluation scripts and splits so others can rerun. PANGAEA provides open code, which is a good model.

By following these practices, future GFM evaluations will be more reliable, comparable, and informative.

# Open Research Opportunities

The GFM evaluation landscape is still emerging. We suggest the following directions and protocols for thesis work:

- **Sensitivity Matrices:** Systematically vary multiple factors to chart model sensitivity. For example, one could fix a GFM and vary *preprocessing type (native vs standardized) × image resolution (native, upsampled, downsampled) × input modalities (RGB vs NIR vs combined) × label fraction (100%, 50%, 10%) × split type (random vs spatial block)*. Evaluate the impact on a target metric (e.g. mIoU). A heatmap or bar chart (“sensitivity matrix”) could illustrate which axes cause the largest performance swings.

- **Complementary Dataset Suite:** Use a *diverse shortlist of datasets* that cover different axes. For instance, 
  - **Fine-scale segmentation**: Five-Billion-Pixels (4m, rural China, 24 classes) vs SpaceNet (0.3m building masks) vs MTLCC (30m climate zones) to test scale. 
  - **Modality shift**: BigEarthNet (S2 multi-label) vs SEN12MS (SAR+optical).
  - **Temporal dynamics**: DynamicEarthNet (daily landcover) vs crop-type time series.
  - **Geography**: Sen1Floods11 (flooding global) vs Crop mapping in Africa vs urban tasks in Europe.
  - **Label scarcity**: Use few-shot splits or simulate label noise (e.g. remove classes) on each task.

- **Statistical Tests and Visuals:** Go beyond aggregate scores. Plot *per-class confusion matrices* to see which classes break down under shift. Compute calibration plots (confidence vs accuracy). Use effect-size (Cohen’s d) to quantify differences between models or settings. Employ bootstrap sampling to compute 95% confidence intervals on all metrics. When comparing two settings, use a paired test (e.g. bootstrap difference) to see if the gap is significant.

- **Mermaid Timeline / Workflow:** Visualize your evaluation pipeline as we do in Fig.1. A mermaid chart can also show timing/dependencies of steps (e.g. data preparation→training→evaluation→analysis) to help plan experiments.

- **Benchmarking Timeline:** If multiple rounds of evaluation are done (e.g. initial run, follow-up with new model), a Gantt or sequence diagram could track the schedule and model additions.

- **Ethical and Societal Axes:** As GFMs are used for policy and humanitarian work, consider evaluating fairness or bias (e.g. performance across different socio-economic regions). This is largely unexplored in EO FM literature.

Overall, more *holistic and systematic* benchmarking—mirroring best practices from ML robustness studies—will yield deeper insights than isolated accuracy numbers. Reporting effect sizes and uncertainty will help the community build genuine consensus on GFM progress.

# Dataset Metadata Table

| **Dataset**         | **Task**                  | **Region/Coverage**           | **Modalities**           | **GSD**         | **Size & Format**                    | **Access / Key Links**                         | **Notes / Caveats**                            |
|---------------------|---------------------------|-------------------------------|--------------------------|-----------------|--------------------------------------|------------------------------------------------|-----------------------------------------------|
| **Sen1Floods11**   | Flood segmentation        | Global flood events (20k+ km²) | SAR (Sentinel-1 VV/VH)    | ~10 m           | 4,831 tiles (512×512)   | [GFZ dataset](https://github.com/cloudwalkio/Sen1Floods11) | Binary (flood/no-flood) and multi-class (3-class) masks. Tropical bias. |
| **CloudSEN12**     | Cloud & shadow segmentation| Global (excl. polar)         | S2 (10–60 m) optical, S1 SAR, DEM, water, LULC | ~10–60 m        | ~49,400 patches (~5 km)^2 | [Zenodo/GitHub](https://github.com/ibm-research/CloudSEN12) | Labels from 8 cloud-detect algorithms (no manual labels). Very large (∼1 TB). |
| **So2Sat LCZ42**   | Urban climate zone classification (17 classes) | 42 world cities +10 smaller areas | S2 optical + S1 SAR            | 10 m           | ~500,000 patches (each patch ~320×320) | [Zenodo/Dataset](https://doi.org/10.5281/zenodo.2541270) | Multi-modal; only cities (urban areas). Curated train/val/test splits. |
| **BigEarthNet v2** | Multi-label landcover   | Europe (10 countries)         | S2 (optical multi-band) + S1 SAR | 10 m           | 549,488 Sentinel-1/Sentinel-2 patch pairs| [Zenodo](https://doi.org/10.5281/zenodo.3962791) | 19 CORINE LULC classes. Labels cover 19 classes, often multiple per tile. |
| **Five-Billion-Pixels** | Land-cover segmentation (24 classes) | 5 Chinese cities (50k km²) | High-res optical (Gaofen-2 RGBNIR) | 4 m           | 150 images (~5 billion labeled pixels) | [Project site / Google Drive] | Only China (context-specific classes). Very detailed annotations. |
| **DynamicEarthNet** | Daily segmentation (7 classes), change detection | 75 global AOIs (12.5 km each) | Planet Fusion (RGB+NIR) time-series | ~3 m           | 54,825 daily images (2018–2019) + 12 monthly labels | [Hugging Face](https://huggingface.co/datasets/planet/dynamic_earth_net) | Two tasks: pixelwise seg. and change. Large (~8.5 GB data). |
| **Fields of the World** | Agricultural field boundary (instance seg) | 24 countries (Europe, Asia, Africa) | High-res optical (various satellites) | ~0.5–1 m    | 1.6M field polygons | [GitHub/Project](https://fieldsofthe.world) | Country-level splits. Ensured block splitting to reduce spatial autocorrelation. |
| **HLS Burn Scars**  | Burned area segmentation | USA (contiguous) 2018–2021    | Harmonized Landsat+S2 (6 bands) | 30 m           | 804 scenes (512×512)   | [Hugging Face](https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars) | Only North America. Binary masks (burned vs not). |
| **So2Sat LCZ42**   | LCZ classification       | 42 cities worldwide          | Optical + SAR           | 10 m           | 500k patches          | DOI 10.5281/zenodo.2541270 | Uniform global classes (urban morphology). Balanced splits.  |
| **Sen1Floods11**   | Flood segmentation       | (repeated)                       | SAR (Sentinel-1)        | 10 m           | 4,831 scenes         | (same as above)       | See above.                                   |

*Table 1: Selected EO datasets for foundation-model evaluation, with tasks, coverage, modalities, resolution (ground sampling distance, GSD), data volume, access links, and caveats (e.g. class coverage, label source). (“-” indicates unspecified detail.)* 

# Methodological Best Practices

Drawing on the critiques above, we summarize key **best practices** for rigorous GFM benchmarking:

- **Maintain Model “Native” Conditions (if known):** Ideally use each model’s intended input format (mean–std normalization, band ordering, image size). If uncertain, document the adapted preprocessing. PANGAEA’s unified approach (same cropping/resizing & normalization for all GFMs) is transparent, but care should be taken if this diverges from a model’s pretraining. Reporting results under *both* native and standardized pipelines can clarify these effects.

- **Dual-Report Performance:** Whenever preprocessing or resolution adjustments are nontrivial, report metrics for (a) the *model-aligned* setup and (b) a common baseline pipeline. This shows the impact of such choices.

- **Spatially and Temporally Independent Splitting:** Avoid random splits that mix nearby pixels. Use held-out regions or blocked samples. For example, partition entire countries or watersheds for test. The Fields-of-World split and *cropland mapping* schemes (some hold out specific states/countries) are good templates. Ensure any time-series evaluation uses non-overlapping time periods for train vs test.

- **Multiple Runs & Uncertainty:** Report mean and confidence intervals from repeated training with different seeds. Even if deep networks are stable, small tasks (few classes, small data) can show high variance. Taylor *et al.* recommend this explicitly. Visualizations like error bars or box plots are encouraged.

- **Hyperparameter Protocol:** Define a clear hyperparameter search strategy (grid or random) and keep it consistent across models. Document the search ranges and final settings. For fairness, using a fixed schedule (e.g. Adam, 80 epochs, cosine decay) for all models can be acceptable if all models converge (PANGAEA did this), but note when this may under-tune some models. Report any deviations (e.g. memory constraints).

- **Metrics Standardization:** Use the same evaluation metrics and aggregation rules for all models. For segmentation, specify whether IoU is averaged per class or weighted by area. Ideally report multiple metrics (accuracy, F1, IoU). If using exotic metrics (e.g. boundary F1 for instance tasks), explain them clearly. Cite how your implementation matches prior work.

- **Benchmark Coverage:** Select datasets that cover diverse scenarios (see Table 1). A mix of global multi-class land cover, focused disaster/event mapping, urban vs rural, and different seasons/sensors will test generality. For example, pairing EO tasks (land use, disaster, agriculture) with non-EO tasks (NOAA weather imagery, if considering all “geospatial”) can further stress test.

- **Baseline Diversity:** Include both task-specific networks (UNet, ResNet, segmentation heads) and generic computer-vision models (ImageNet-ViT, CLIP) as baselines. In many studies (PANGAEA, EarthShift) these simple baselines are competitive or more robust under shift.

- **Compute Logging:** Record GPU/TPU type, memory, and runtime for each experiment. This transparency helps assess model feasibility. Indicate any pre-training details (data, epochs, batches) or point to existing papers for each GFM.

- **Data and Code Release:** Publish training and evaluation code (including data preprocessing steps) in version-controlled repositories. At minimum, share split indices or geocoordinates. Deposit final model weights and seeds in an archive (e.g. Zenodo DOI) to guarantee future reproducibility. Release an *evaluation harness* if possible (like a script that downloads checkpoints and computes metrics on the benchmark tasks).

- **Task Difficulty Reporting:** In addition to raw scores, consider reporting how “hard” each task is (e.g. baseline accuracy of simple models, or label entropy). This contextualizes whether GFMs are approaching a plateau or the task is trivial.

Adhering to these practices will reduce confounding factors and make GFM benchmarks more trustworthy.

# Future Work: Sensitivity Analyses and Protocols

To advance the field systematically, we recommend new experimental protocols:

1. **Design Sensitivity Matrices:** For each GFM, vary one factor at a time and measure performance change. For example, fix a dataset and GFM, and sweep through: (i) input resolution (full vs ½ vs ¼), (ii) image bit-depth or bands used, (iii) amount of label noise (e.g. drop 10%, 30%, 50% of labels), (iv) training set size. Aggregate results in charts (e.g. heatmaps or line plots) to identify where performance is most sensitive. 

2. **Multi-Axis Benchmarks:** Combine multiple shifts in evaluation. E.g. train on one region/sensor and test on both a new region *and* a later time. This simulates real “wild deployment”. 

3. **Statistical Testing:** Use *effect sizes* (Cohen’s d, Cliff’s Delta) to compare models across tasks, not just p-values. Plot performance distributions. Provide calibration curves for probabilistic outputs. Use bootstrapping to compute 95% CIs on mean IoU differences between models.

4. **Complementary Datasets:** Propose “mini-benchmarks” spanning orthogonal axes. For instance, 
   - **Resolution axis:** a dataset pair at 1 m vs 30 m (e.g. SpaceNet vs HLS).
   - **Modality axis:** same area labeled by optical vs SAR (SEN12MS).
   - **Temporal axis:** seasonal vs annual images (e.g. Continental US scenes in summer vs winter).
   - **Class granularity:** coarse landcover (forest vs non-forest) vs fine classes.
   The survey table (Table 1) can guide such selection.

5. **Visualization Tools:** Create interactive dashboards (or use Jupyter) to explore performance per task/region. For example, plot GFMs’ IoU per class under geographic shift.

6. **Mermaid-style Timeline/Flowchart:** Document your evaluation *workflow* as code. This aids transparency. (We provide Fig.1 as an example pipeline.) One could further create a “timeline” for a full benchmark campaign, marking when each model is added, which data versions were used, etc.

By treating benchmarking as a full **data science process** (with EDA, experimental design, analysis, and documentation), we can better understand and improve GFMs.

# References

- Marsocci *et al.* (2025). *PANGAEA: A Global and Inclusive Benchmark for Geospatial Foundation Models*. arXiv:2412.04204.  
- Doerksen *et al.* (2026). *EarthShift: Measuring Robustness to Real-World Distribution Shifts in Earth Observation*. arXiv:2605.29330.  
- Simumba *et al.* (2026). *GEO-Bench-2: From Performance to Capability, Rethinking Evaluation in Geospatial AI*. arXiv:2511.15658.  
- Corley *et al.* (2026). *No One Knows the State of the Art in Geospatial Foundation Models*. arXiv:2605.12678.  
- Young *et al.* (2026). *How Usable Are Geospatial Foundation Models? A Systematic Evaluation of 89 Models*. *Remote Sensing of Environment* (in press).  
- Tong *et al.* (2023). *Five-Billion-Pixels: Land-Cover Benchmarking for Meta-Datasegmentation*. *ISPRS J. Photogram. Remote Sens.*, 194:133–150.  
- Sumbul *et al.* (2019). *BigEarthNet: A Large-Scale Benchmark Archive For Remote Sensing Image Understanding*. IGARSS (2019).  
- Bonafilia *et al.* (2020). *Sen1Floods11: A Sentinel-1 Dataset for Flood Mapping*. CVPRW (2020).  
- Shibli *et al.* (2024). *CloudSEN12: A Multi-Source Sentinel-1/2 Dataset for Cloud Detection*. *Scientific Data* 11, 547 (2024).  
- Rematas *et al.* (2023). *DynamicEarthNet: A Dataset for Daily Semantic Segmentation of Satellite Image Time Series*. ICCV (2023).  
- Schneider *et al.* (2024). *Fields of The World (FTW): Global Agricultural Field-Boundary Segmentation Dataset*. arXiv:2409.16252.  

