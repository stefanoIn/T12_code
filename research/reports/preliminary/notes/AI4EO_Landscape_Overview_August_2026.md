# Artificial Intelligence for Earth Observation

## Current research landscape, scientific development, open problems, and MSc thesis directions

**Prepared for:** Stefano Infusini  
**Purpose:** Technical orientation for discussion of feasible MSc thesis directions  
**Literature cut-off:** 9 August 2026

**Evidence note:** The overview prioritizes original papers, official benchmark reports, and ESA/NASA sources. Because the field is moving quickly, it includes both peer-reviewed work and clearly identifiable recent preprints; claims of state of the art from individual model papers are treated as provisional unless supported by independent benchmarks.

---

## Executive synthesis

Artificial Intelligence for Earth Observation (AI4EO) is not a single task or model family. It is the research area concerned with converting measurements of the Earth—optical, multispectral, hyperspectral, thermal, radar, LiDAR, elevation, meteorological, in-situ, and textual data—into reliable information about the state and evolution of the planet.

The field has developed through five broad transitions:

1. **From physically designed features and statistical classifiers to learned representations.** Early operational pipelines depended on spectral indices, texture descriptors, dimensionality reduction, maximum-likelihood classifiers, Support Vector Machines, Random Forests, and expert-designed rules.
2. **From pixel-wise models to spatial and spectral–spatial deep learning.** CNNs, fully convolutional networks, and encoder–decoder models made it possible to learn spatial context, perform dense mapping, and process very-high-resolution imagery.
3. **From single images to multimodal and temporal learning.** Research began to exploit optical–SAR complementarity, satellite image time series, phenology, change, irregular observations, and auxiliary geospatial variables.
4. **From task-specific supervised models to self-supervised pretraining and EO foundation models.** Large unlabelled archives are now used to pretrain encoders that can be adapted to multiple tasks with fewer labels.
5. **From benchmark accuracy to capability, reliability, and deployment.** The most important current questions concern geographic and sensor transfer, missing modalities, trustworthy uncertainty, physical validity, reproducible evaluation, computational efficiency, natural-language interaction, and tool-using agents.

The main conclusion of the 2024–2026 literature is deliberately more cautious than the current foundation-model enthusiasm:

> **There is no single state-of-the-art AI4EO model.** Performance depends on the sensor, spectral bands, spatial and temporal resolution, task, label budget, adaptation protocol, and target geography.

This conclusion is supported by several independent evaluations. [PANGAEA](https://arxiv.org/abs/2412.04204) found that geospatial foundation models do not consistently outperform supervised U-Net and ViT baselines. [GEO-Bench-2](https://arxiv.org/html/2511.15658v1) found that EO-specific pretraining is particularly valuable when multispectral or temporal information matters, while large natural-image models remain highly competitive on high-resolution RGB tasks. A 2026 audit of 152 foundation-model papers found major inconsistencies in evaluation and concluded that the published record does not presently support a universal ranking of models ([Corley et al., 2026](https://arxiv.org/html/2605.12678v1)).

For an MSc thesis, this is good news. A meaningful contribution does **not** require pretraining another giant model. A stronger and more feasible thesis can use open pretrained models to investigate a precise EO problem such as:

- transfer to unseen cities, regions, seasons, or sensors;
- robustness when one sensor is cloudy, delayed, or unavailable;
- uncertainty calibration under distribution shift;
- physically consistent reconstruction or downscaling;
- fair, leakage-resistant evaluation of EO foundation models;
- reliability of language agents that select and process EO products.

Given Stefano's background in AI/CV, signal and image processing, NLP, HPC, and earlier Landsat–Sentinel-2 land-surface-temperature work, the strongest provisional direction is:

> **Uncertainty-aware and physically consistent LST downscaling using EO foundation-model representations, evaluated across cities, seasons, and sensors.**

This is not a final topic selection. It is the most promising intersection identified so far between prior experience, current research gaps, open data, tractable compute, and a defensible experimental protocol.

---

## 1. How to organize the AI4EO field

Many reviews mix together data types, computer-vision tasks, scientific applications, and methodological research trends. They are different axes.

| Axis | Representative categories | What it answers |
|---|---|---|
| **Observation modality** | RGB/optical, multispectral, hyperspectral, thermal, SAR, LiDAR/DEM, meteorology, in-situ data, text | What is measured, by which physical process? |
| **AI task** | Classification, semantic/instance/panoptic segmentation, object detection, regression/retrieval, change detection, forecasting, reconstruction, super-resolution, retrieval, VQA | What mathematical output must the system produce? |
| **Scientific/application domain** | Agriculture, forestry, biodiversity, disasters, climate, urban systems, ocean, cryosphere, atmosphere, water, geology | What Earth-system or societal question is being addressed? |
| **Research branch** | Foundation models, multimodal fusion, spatio-temporal learning, generalization, trustworthy/physics-aware AI, vision-language and agents | What reusable scientific or methodological problem is being studied? |

A thesis topic should normally select one element from each axis. For example:

> **Sentinel-1 + Sentinel-2** (modalities) + **flood segmentation** (task) + **disaster response** (application) + **missing-modality robustness and uncertainty under event shift** (research problem).

This formulation is much sharper than a topic such as “use Transformers for satellite images,” because it specifies the scientific question and the conditions under which the contribution can be evaluated.

### 1.1 Task taxonomy

The main AI tasks in EO are:

- **Scene or patch classification:** assign one or multiple labels to an image patch.
- **Pixel-wise classification / semantic segmentation:** assign a class to every pixel; land-cover mapping is usually formulated this way when a spatial map is required.
- **Object detection:** localize countable entities with boxes or oriented boxes, such as ships, aircraft, vehicles, buildings, or wind turbines.
- **Instance or panoptic segmentation:** separate individual objects or parcels while also assigning semantic classes.
- **Regression and geophysical retrieval:** estimate continuous quantities such as LST, biomass, soil moisture, crop yield, chlorophyll, or atmospheric variables.
- **Change detection:** identify where, what, and sometimes when a meaningful surface change occurred.
- **Time-series modelling and forecasting:** infer phenology, monitor event evolution, fill gaps, or predict future states.
- **Reconstruction and enhancement:** cloud removal, denoising, gap filling, super-resolution, data fusion, and cross-modal generation.
- **Retrieval, captioning, visual question answering, and grounding:** connect imagery with language and external knowledge.

Land-cover classification and object detection are therefore different problem formulations. In land-cover mapping, the output is generally a dense categorical field. In object detection, the output is a set of localized object instances. Neither task is itself a complete “research branch”: both can be studied using multimodal learning, foundation models, domain adaptation, uncertainty estimation, or other branches.

---

## 2. Scientific development of AI for EO

### 2.1 Developmental timeline

| Period | Dominant scientific idea | What changed in EO | Principal limitation left behind |
|---|---|---|---|
| **Before ~2005** | Physical models, statistical pattern recognition, expert-designed features | Spectral indices, transforms, per-pixel classifiers, rule-based retrieval, and signal-processing pipelines encoded domain knowledge directly | Limited ability to learn complex spatial patterns; extensive feature engineering |
| **~2005–2014** | Classical machine learning | SVMs, Random Forests, boosting, object-based image analysis, kernel methods, and sparse representations improved nonlinear classification with comparatively small labelled datasets | Representations remained largely hand-designed; spatial context was often shallow |
| **~2014–2018** | Deep representation learning | Autoencoders, DBNs, 1-D/2-D/3-D CNNs, transfer learning, FCNs, and encoder–decoder models learned spectral, spatial, and joint spectral–spatial features | Label hunger, patch-level evaluation, limited geographic transfer, and dependence on ImageNet/RGB assumptions |
| **~2018–2021** | Dataset and task scaling | BigEarthNet, SEN12MS, SpaceNet, xView, So2Sat, PASTIS, and other benchmarks supported dense mapping, multimodal fusion, and time-series learning | Datasets remained geographically and semantically fragmented; random splits often overstated transfer |
| **~2020–2023** | Self-supervision and Transformers | Contrastive learning, masked modelling, temporal attention, and sensor-aware pretraining exploited massive unlabelled archives | Models often remained tied to fixed sensors, band configurations, resolutions, or tasks |
| **~2023–2025** | EO foundation models | Prithvi, CROMA, DOFA, SkySense, AnySat, and related models pursued reusable, multimodal, multi-temporal representations | Comparisons were inconsistent; universal superiority was not established |
| **~2025–2026** | Capability, generation, reasoning, and operations | TerraMind, OlmoEarth, RAMEN, vision-language systems, agents, global embeddings, lightweight variants, and on-orbit demonstrations expanded the target from feature extraction to flexible Earth intelligence | Reliability, physical faithfulness, cross-domain transfer, evaluation, provenance, and deployment remain open |

The classical-to-deep-learning transition is documented in the 2017 review by [Zhu et al.](https://arxiv.org/abs/1710.03959). That paper is useful historically because it captures the moment at which remote sensing was moving from hand-crafted features to learned spectral–spatial representations, while already warning against treating deep learning as a domain-free black box.

### 2.2 The dataset transition

Deep learning became scientifically useful in EO only when the community began constructing larger, georeferenced datasets and benchmarks.

- [BigEarthNet](https://arxiv.org/abs/1902.06148) introduced 590,326 multi-label Sentinel-2 patches in its original release, demonstrating the importance of domain-specific large-scale pretraining rather than relying only on ImageNet.
- [SEN12MS](https://arxiv.org/abs/1906.07789) provided 180,662 globally distributed Sentinel-1/Sentinel-2/MODIS triplets, helping establish radar–optical learning and multimodal land-cover research.
- [PASTIS](https://arxiv.org/abs/2107.07933) made satellite image time series and agricultural parcel segmentation a central benchmark problem.
- [SSL4EO-S12](https://arxiv.org/abs/2211.07044) explicitly constructed a global, multi-seasonal Sentinel-1/2 corpus for self-supervised learning.
- [Major TOM](https://arxiv.org/html/2402.12095v2) moved toward expandable, AI-ready global EO data and, later, openly distributed global embedding products.

This history matters because model progress cannot be separated from data design. Label ontologies, spatial coverage, temporal sampling, cloud filtering, co-registration, and train/test geography all determine what a model can learn and what a benchmark score means.

### 2.3 The self-supervised and Transformer transition

EO is unusually well suited to self-supervised learning: unlabelled measurements are abundant, while high-quality labels require expensive expert interpretation and may exist only for particular places or dates.

[Seasonal Contrast (SeCo)](https://openaccess.thecvf.com/content/ICCV2021/papers/Manas_Seasonal_Contrast_Unsupervised_Pre-Training_From_Uncurated_Remote_Sensing_Data_ICCV_2021_paper.pdf) used repeated observations of the same locations to learn seasonally robust representations. [SatMAE](https://proceedings.neurips.cc/paper_files/paper/2022/hash/01c561df365429f33fcd7a7faa44c985-Abstract-Conference.html) adapted masked autoencoding to temporal and multispectral satellite imagery through temporal and spectral positional information. These works changed the scientific question from “How do we label enough pixels?” to “Which invariant and predictive structures can be learned directly from the observation archive?”

### 2.4 The foundation-model transition

The term *EO foundation model* is now used for a pretrained model intended to be adapted across several EO tasks, regions, sensors, or label regimes. Representative developments include:

| Model | Year | Main scientific idea | Important limitation or question |
|---|---:|---|---|
| [SeCo](https://openaccess.thecvf.com/content/ICCV2021/papers/Manas_Seasonal_Contrast_Unsupervised_Pre-Training_From_Uncurated_Remote_Sensing_Data_ICCV_2021_paper.pdf) | 2021 | Temporal/seasonal contrastive pretraining | Primarily optical; not a universal sensor model |
| [SatMAE](https://proceedings.neurips.cc/paper_files/paper/2022/hash/01c561df365429f33fcd7a7faa44c985-Abstract-Conference.html) | 2022 | Masked modelling for temporal and multispectral imagery | Fixed input assumptions and adaptation choices still matter |
| [Presto](https://arxiv.org/abs/2304.14065) | 2023 | Lightweight pretraining for multimodal pixel time series | Does not model fine spatial structure in the same way as image encoders |
| [CROMA](https://arxiv.org/abs/2311.00566) | 2023 | Contrastive radar–optical masked autoencoding | Focused on Sentinel-1/2 radar–optical representations |
| [Prithvi-EO-2.0](https://arxiv.org/abs/2412.02732) | 2024 | Global HLS multi-temporal masked pretraining with temporal/location embeddings | 300M/600M variants remain expensive relative to small task-specific models |
| [DOFA](https://arxiv.org/abs/2403.15356) | 2024 | Wavelength-conditioned dynamic model for heterogeneous sensors | Wavelength metadata does not solve all non-spectral modality and resolution shifts |
| [SkySense](https://arxiv.org/abs/2312.10115) | 2024 | Billion-scale multimodal, temporal, and geo-context pretraining | Size, reproducibility, and adaptation complexity |
| [AnySat](https://arxiv.org/abs/2412.14123) | 2025 | One JEPA-based model across heterogeneous resolutions, scales, modalities, and datasets | A single shared model must still negotiate negative transfer and task-specific needs |
| [TerraMind](https://arxiv.org/html/2504.11171v5) | 2025 | Any-to-any generative multimodal modelling and “thinking in modalities” | Generated modalities must be tested for physical faithfulness and downstream bias |
| [OlmoEarth](https://arxiv.org/abs/2511.13655) | 2026 | Stable latent modelling for multimodal, spatio-temporal EO | Claims across heterogeneous benchmarks still depend on evaluation protocol |
| [RAMEN](https://arxiv.org/abs/2512.05025) | 2026 | Sensor-agnostic, resolution-adjustable representation and explicit detail/compute trade-off | New-model results require broader independent reproduction |

The trajectory is clear: single-sensor encoders are becoming multisensor, temporal, resolution-aware, and sometimes generative. The unresolved question is not whether such models are promising. It is **when their learned representation transfers more reliably or efficiently than a well-tuned smaller baseline**.

### 2.5 The evaluation transition

The scientific maturation of the field is visible in its benchmarks:

- [GEO-Bench](https://proceedings.neurips.cc/paper_files/paper/2023/hash/a0644215d9cff6646fa334dfa5d29c5a-Abstract-Datasets_and_Benchmarks.html) standardized six classification and six segmentation tasks.
- [PhilEO Bench](https://arxiv.org/abs/2401.04464) evaluated label efficiency using a global Sentinel-2 testbed and common decoder.
- [PANGAEA](https://arxiv.org/abs/2412.04204) expanded evaluation across tasks, resolutions, modalities, temporalities, and geographies.
- [GEO-Bench-2](https://arxiv.org/html/2511.15658v1) shifted from a single aggregate leaderboard toward capability-oriented evaluation.
- [No One Knows the State of the Art in Geospatial Foundation Models](https://arxiv.org/html/2605.12678v1) audited the literature itself and exposed a reproducibility and comparability crisis.

This is a transition from model-centric research—“our encoder gains 1.2 points”—to scientific evaluation—“which capability improved, under what distribution shift, with which labels, preprocessing, decoder, and compute?”

---

## 3. Current core research branches

The following six branches provide a stable taxonomy for the main scientific directions. Efficient deployment and data/benchmark infrastructure are treated afterward as cross-cutting enabling layers.

### 3.1 Large-scale pretraining and EO foundation models

**Central objective:** Learn reusable representations from large unlabelled EO archives so that downstream models require fewer labels and less task-specific training.

Current interests include:

- contrastive, masked, predictive, generative, and latent-space objectives;
- sensor-specific versus sensor-agnostic encoders;
- spatial, spectral, temporal, and geographic positional information;
- frozen encoders, linear probing, full fine-tuning, adapters, LoRA, and prompt tuning;
- scaling laws for model size, data volume, resolution, and modality diversity;
- pretrained embeddings as a reusable data product;
- model selection: predicting which encoder and adaptation strategy suit a target task.

**Open scientific problem:** Pretraining at scale does not guarantee useful invariances. A model may learn location, season, sensor artefacts, or land-cover prevalence rather than transferable Earth-process structure.

**State of evidence:**

- PANGAEA found that current GFMs do not consistently beat supervised models.
- GEO-Bench-2 found stronger benefits on multispectral tasks than on RGB-only tasks.
- The 2026 audit found that inconsistent protocols make universal rankings scientifically unsupported.
- A 2026 cross-region agriculture study found that Prithvi, SpectralGPT, and SatMAE all degraded sharply on unseen US states and tended to miss rare crops ([Shang et al., 2026](https://arxiv.org/abs/2606.29664)).

**High-value research questions:**

1. What part of downstream performance comes from pretraining data, architecture, model scale, or adaptation?
2. Which EO-specific capabilities—spectral, temporal, radar, geographic—are actually present in the representation?
3. When do frozen features suffice, and when is full fine-tuning necessary?
4. Can small models preserve the useful capabilities of large models?
5. Can model selection be performed without fine-tuning every candidate?

### 3.2 Multimodal and multisensor learning

**Central objective:** Combine complementary measurements of the same Earth system.

Typical combinations include:

- optical + SAR;
- multispectral + hyperspectral;
- optical/SAR + DEM or LiDAR;
- satellite imagery + weather/reanalysis;
- EO imagery + in-situ measurements;
- imagery + maps, coordinates, land-cover products, or text.

The research problem is more difficult than concatenating channels. Different sensors measure different physical quantities, have different noise models, resolutions, acquisition geometries, revisit schedules, and missingness mechanisms.

Current interests include:

- early, intermediate, late, and token-level fusion;
- shared versus modality-specific encoders;
- cross-modal contrastive learning and masked reconstruction;
- asynchronous fusion of non-simultaneous observations;
- missing-modality training and inference;
- cross-modal generation and imputation;
- fusion without destructive resampling to a single nominal resolution.

Representative models include [CROMA](https://arxiv.org/abs/2311.00566), [AnySat](https://arxiv.org/abs/2412.14123), [TerraMind](https://arxiv.org/html/2504.11171v5), [OlmoEarth](https://arxiv.org/abs/2511.13655), and [RAMEN](https://arxiv.org/abs/2512.05025).

**Open scientific problem:** A multimodal model trained on perfectly aligned data may fail in deployment precisely when multimodality is most valuable—for example, when optical imagery is cloudy, acquisitions are asynchronous, or one sensor is unavailable.

### 3.3 Spatio-temporal modelling and change analysis

**Central objective:** Model the Earth as a dynamic system rather than a collection of independent image chips.

Research topics include:

- bi-temporal and semantic change detection;
- multi-temporal land-cover and crop mapping;
- phenology and seasonal dynamics;
- event onset, evolution, and recovery;
- irregular sampling and cloud-related gaps;
- long-context satellite image time series;
- surface, weather, climate, and hazard forecasting;
- continuous spatio-temporal representations.

[PASTIS](https://arxiv.org/abs/2107.07933) showed the value of temporal attention for agricultural parcel mapping. [EarthNet2021](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf) formalized Earth-surface forecasting from Sentinel-2 imagery and weather data. [Presto](https://arxiv.org/abs/2304.14065) showed that a small architecture specifically designed for multimodal time series can compete with much larger models.

**Open scientific problems:**

- distinguishing semantic change from phenology, illumination, atmosphere, or sensor differences;
- learning from irregular and incomplete time series;
- handling abrupt rare events that are underrepresented in pretraining;
- forecasting calibrated distributions rather than visually plausible single futures;
- transferring temporal patterns across climate zones and agricultural calendars.

### 3.4 Generalization, domain adaptation, and limited supervision

**Central objective:** Make models work where labels were not collected.

EO distribution shifts include:

- **geographic shift:** another city, biome, country, or continent;
- **temporal shift:** another season, year, climate regime, or post-disaster stage;
- **sensor shift:** different spectral response functions, polarizations, noise, or product levels;
- **resolution shift:** different ground-sampling distance or point density;
- **acquisition shift:** view angle, illumination, orbit, atmosphere, or preprocessing;
- **semantic shift:** different label ontology or class prevalence.

Current methods include transfer learning, unsupervised and source-free domain adaptation, domain generalization, self-training, pseudo-labels, few-shot learning, active learning, weak supervision, continual learning, test-time adaptation, and parameter-efficient fine-tuning.

This branch is arguably the most important for real-world AI4EO. A random chip split can place neighbouring, highly correlated samples into train and test sets and thereby measure interpolation rather than deployment transfer. Spatial and temporal separation must be part of the scientific question.

Recent evidence is sobering:

- [GeoCrossBench](https://arxiv.org/abs/2511.02831) reports large losses when models face satellites with non-overlapping bands or even additional unseen bands.
- [Shang et al.](https://arxiv.org/abs/2606.29664) found sharp regional degradation for foundation models in crop mapping.
- [WILDS](https://proceedings.mlr.press/v139/koh21a/koh21a.pdf), which includes the FMoW satellite benchmark, helped establish evaluation under naturally occurring distribution shift.

**Open scientific problem:** Better average in-domain accuracy can coexist with worse performance on rare classes or unseen regions. Robustness must be measured by geography, class, event, season, and uncertainty—not only by one global score.

### 3.5 Trustworthy, uncertainty-aware, explainable, and physics-aware AI

**Central objective:** Produce outputs that scientists and operational users can audit, calibrate, and reconcile with the measurement process and Earth-system knowledge.

This branch contains several connected but distinct topics:

- aleatoric and epistemic uncertainty;
- probability calibration and selective prediction;
- out-of-distribution and anomaly detection;
- interpretable features and explanation stability;
- robustness to clouds, noise, corruption, and adversarial artefacts;
- physical constraints, conservation relationships, and differentiable forward models;
- hybrid numerical–ML models;
- causal inference and process discovery;
- provenance, traceability, fairness, privacy, and responsible use.

EO uncertainty enters at every stage: sensor noise, atmospheric correction, geolocation, resampling, imperfect reference labels, model parameters, and distribution shift. A 2024 study notes that no broadly adopted, reliable, easy-to-use uncertainty framework yet exists for ML in EO ([Singh et al., 2024](https://www.nature.com/articles/s41598-024-65954-w)). A 2025 benchmark specifically evaluates whether pixel-wise uncertainty identifies segmentation errors and corrupted regions ([Rey et al., 2025](https://arxiv.org/abs/2510.19586)).

Physics-aware AI is especially relevant for geophysical retrieval and downscaling. The objective is not merely to add a penalty called “physics loss,” but to identify a valid physical or measurement constraint. Examples include:

- aggregate consistency between a high-resolution reconstruction and the original coarse observation;
- non-negativity, boundedness, or conservation constraints;
- sensor forward models and spectral response functions;
- radiative-transfer constraints;
- dynamics imposed by differential equations or numerical simulators.

**Open scientific problem:** Post-hoc visual explanations can look convincing without being faithful, and a low test RMSE does not guarantee physical validity or calibrated uncertainty under a new region or event.

### 3.6 Vision-language and agentic geospatial AI

**Central objective:** Connect EO measurements, spatial concepts, scientific language, and executable tools.

The branch has three levels:

1. **Image–text representation learning:** retrieval, zero-shot classification, and open-vocabulary recognition. [RemoteCLIP](https://arxiv.org/abs/2306.11029) is a representative system.
2. **Conversational vision-language models:** captioning, VQA, grounding, counting, and multi-image reasoning. Representative systems include [GeoChat](https://openaccess.thecvf.com/content/CVPR2024/html/Kuckreja_GeoChat_Grounded_Large_Vision-Language_Model_for_Remote_Sensing_CVPR_2024_paper.html) and [EarthDial](https://arxiv.org/abs/2412.15190).
3. **Tool-using EO agents:** select datasets and sensors, generate code, call catalogues or Earth Engine, execute analysis, inspect failures, and return evidence.

This branch is scientifically interesting because EO analysis depends heavily on metadata and procedural knowledge: correct collections, units, scale factors, bands, cloud masks, projections, date ranges, and spatial reducers.

It is also immature. The 2026 [UnivEARTH](https://aclanthology.org/2026.findings-acl.124.pdf) benchmark contains 408 evidence-grounded EO questions. In zero-shot Google Earth Engine code generation, the best evaluated agent answered only 40% correctly and failed to execute code in more than 44% of cases. Reflection reduced syntax failures and raised accuracy toward 60%, but correct execution still did not guarantee correct scientific logic.

**Open scientific problems:**

- hallucinated collections, bands, units, dates, and scale factors;
- failure to distinguish sensor products with similar names;
- weak spatial and temporal reasoning;
- answers that are plausible but unsupported by pixels or executable evidence;
- poor uncertainty and provenance;
- lack of formal verification for generated geospatial workflows.

---

## 4. Cross-cutting enabling layers

### 4.1 Efficient, scalable, operational, and onboard AI

EO systems operate at scales ranging from one local patch to the entire planet and from ground-based clusters to satellite processors. Research therefore includes:

- parameter-efficient fine-tuning;
- knowledge distillation, pruning, quantization, and low-rank adaptation;
- efficient data loading, tiling, and distributed inference;
- learned compression and intelligent data selection;
- low-latency disaster products;
- edge and onboard inference;
- energy, memory, bandwidth, and radiation constraints.

ESA's [Φsat-2](https://www.esa.int/Applications/Observing_the_Earth/Phsat-2), launched on 16 August 2024, carries six AI applications including cloud filtering, vessel detection/classification, image-to-map conversion, compression, anomaly detection, and wildfire detection. A 2025 paper reported the first on-orbit demonstration of a compressed geospatial foundation model and emphasized that compression and domain adaptation were both necessary for flight-ready inference ([Du et al.](https://arxiv.org/abs/2512.01181)).

This is a strategically important ESA-facing branch, but an MSc thesis needs either access to representative hardware or a carefully justified hardware simulator. FLOPs alone are not an operational evaluation.

### 4.2 Datasets, benchmarks, embeddings, and representation infrastructure

This layer includes:

- AI-ready data cubes and harmonized products;
- global pretraining corpora;
- label quality and ontology alignment;
- spatially and temporally explicit splits;
- benchmark harnesses and reproduced baselines;
- model cards, data cards, licences, and provenance;
- global embedding layers and similarity search;
- STAC catalogues, cloud-native formats, and reproducible pipelines.

The 2026 audit by [Corley et al.](https://arxiv.org/html/2605.12678v1) quantified the problem: among 152 audited papers, it found 46 cross-paper disagreements of at least 10 points for nominally the same model, benchmark, and protocol; 94 of 126 papers with extractable pretraining configurations used a configuration no other paper used; and 39% released no weights.

Benchmark and data work is therefore not secondary administration. It is a substantive scientific branch when it establishes a capability that was previously impossible to measure.

---

## 5. The principal unresolved AI4EO problems

| Problem | Why it is specifically difficult in EO | Researchable question |
|---|---|---|
| **Geographic generalization** | Nearby pixels are correlated; land-cover appearance and class prevalence vary by region | Can adaptation improve leave-one-region-out performance without harming rare classes? |
| **Temporal and climate shift** | Phenology, land management, atmosphere, and extremes change across seasons and years | Which temporal representations remain stable across years and climate zones? |
| **Cross-sensor transfer** | Sensors have different spectral response functions, polarizations, resolutions, and noise | Can wavelength/metadata-aware adapters transfer between instruments with partially overlapping bands? |
| **Label scarcity and noise** | Expert labels are expensive, temporally stale, spatially imprecise, and ontology-dependent | Which SSL, active-learning, or weak-supervision method gives the best gain per labelled area? |
| **Rare events and long tails** | Extreme fires, floods, damage levels, and minority crops are scientifically important but statistically rare | Can event-aware sampling and calibrated uncertainty prevent majority-class collapse? |
| **Multimodal alignment** | Acquisitions are asynchronous, co-registration is imperfect, and missingness is not random | Does fusion remain useful under realistic cloud, delay, and sensor-outage patterns? |
| **Resolution and scale** | Resampling changes grid size but not native information content; objects appear at radically different scales | Can models represent native resolutions without false detail or excessive compute? |
| **Benchmark leakage** | Random chip splits can share scenes, neighbourhoods, dates, or derived labels across partitions | How much reported performance disappears under spatially and temporally blocked evaluation? |
| **Foundation-model comparability** | Input bands, decoders, preprocessing, adaptation, and metrics vary across papers | Which capabilities survive a shared data and adaptation protocol? |
| **Uncertainty and OOD behaviour** | Operational decisions need to know where a map is unreliable | Which uncertainty method remains calibrated under geographic and sensor shift? |
| **Physical faithfulness** | A visually plausible output may violate the sensor observation or Earth-system constraints | Can explicit forward/aggregation consistency prevent hallucinated fine-scale structure? |
| **Generative reliability** | Cross-modal generation has many plausible outputs, but only one Earth was observed | How should conditional distributions, ambiguity, and downstream bias be evaluated? |
| **Agent reliability** | EO tools require exact product IDs, bands, scale factors, projections, and temporal logic | Can typed tools, retrieval, and automatic scientific checks make generated workflows auditable? |
| **Operational efficiency** | Planet-scale inference and onboard processing have strict storage, energy, and latency limits | What is the accuracy–calibration–latency frontier after compression? |
| **Data and representation inequality** | Training data and benchmarks overrepresent some continents, climates, and commercial data users | How does performance vary by geography, and which sampling strategy closes the gap? |

### 5.1 Why spatially correct evaluation is central

Suppose adjacent patches from one Sentinel-2 tile are randomly divided into training and test sets. They share acquisition conditions, local land-cover structure, atmospheric state, preprocessing, and often label sources. A high test score may therefore reflect local interpolation.

A deployment-oriented protocol should separate data according to the intended claim:

- **new place:** spatial blocks, countries, cities, watersheds, or events;
- **new time:** later year or unseen season;
- **new sensor:** held-out platform or band configuration;
- **few labels:** explicit n-shot or labelled-area budget;
- **rare event:** leave-one-event-out or leave-one-hazard-out;
- **operational uncertainty:** calibration and risk–coverage under the same shift.

The split is part of the hypothesis, not a bookkeeping decision.

### 5.2 Why “best foundation model” is currently the wrong question

The more useful questions are:

- best for **which sensor and band set**;
- best under **which label budget**;
- best with **frozen, parameter-efficient, or full fine-tuning**;
- best for **in-domain accuracy or cross-region transfer**;
- best at **which spatial resolution and map scale**;
- best with **which uncertainty and compute requirements**.

Model claims should be capability-specific. TerraMind, OlmoEarth, and RAMEN report very strong results, but their own papers use different data, adaptation choices, and benchmark subsets. Their progress is real; a universal total ordering is not yet supported.

---

## 6. Current scientific and agency interests

### 6.1 ESA-facing interests

Recent ESA Φ-lab work and calls indicate sustained interest in:

- multimodal EO foundation models and benchmarking;
- trustworthy, explainable, and physics-aware AI;
- compact foundation models and onboard intelligence;
- disaster response and extreme-event generalization;
- global embeddings and AI-ready data infrastructure;
- natural-language and code-based access to EO;
- digital twins and integration with Earth-system models.

TerraMind is a major current ESA/IBM programme, while PANGAEA and PhilEO illustrate the emphasis on independent evaluation. Φsat-2 makes compression, raw-to-product processing, application updating, and onboard inference operational research rather than speculative topics. ESA's 2025 Living Planet Symposium explicitly highlighted explainable, trustworthy, and physics-aware AI ([ESA Φ-lab](https://philab.esa.int/unmissable-%CF%86-lab-moments-at-lps-2025/)).

### 6.2 NASA-facing interests

NASA's open-science foundation-model programme includes:

- Prithvi-EO for HLS imagery;
- Prithvi Weather–Climate for MERRA-2 atmospheric data;
- open models, code, and downstream scientific applications;
- disaster response, crop and land-use mapping, ecosystem monitoring, and LST;
- model deployment and collaboration with domain scientists.

[Prithvi-EO-2.0](https://arxiv.org/abs/2412.02732) was trained on 4.2 million global HLS time-series samples and released in 300M and 600M variants. NASA describes the model as part of a wider open family of scientific foundation models ([NASA, 2024](https://science.nasa.gov/science-research/ai-geospatial-model-earth/)).

### 6.3 Application domains with sustained research demand

- **Disasters:** floods, wildfire, earthquake damage, landslides, rapid mapping, and recovery.
- **Agriculture and food security:** crop type, field boundaries, phenology, yield, irrigation, and transfer to data-scarce regions.
- **Forestry and biodiversity:** biomass, canopy height, deforestation, habitat, species distributions, and ecosystem change.
- **Climate and urban systems:** LST, urban heat, emissions, downscaling, extremes, and adaptation.
- **Water, ocean, and cryosphere:** surface water, soil moisture, coastal change, sea ice, water quality, and marine anomalies.
- **Atmosphere and weather:** retrieval, nowcasting, data assimilation, parameterization, and hybrid numerical–AI models.

Applications alone do not define novelty. “Flood mapping with a Transformer” is likely too broad and incremental. “Calibrated leave-one-event-out flood mapping with missing optical observations” defines a research contribution.

---

## 7. Designing a defensible MSc thesis

### 7.1 Thesis formula

A strong AI4EO MSc thesis can usually be expressed as:

> **For [EO phenomenon/task], under [realistic shift or data constraint], determine whether [methodological contribution] improves [scientifically appropriate metrics] relative to [strong classical, supervised, and pretrained baselines].**

Every candidate should have:

1. **A precise failure mode**, not merely a new architecture.
2. **Open or institutionally guaranteed data.**
3. **A leakage-resistant split defined before modelling.**
4. **At least three baseline families:** classical/physical, task-specific deep model, and pretrained model.
5. **Metrics matched to the claim:** accuracy alone is rarely sufficient.
6. **A compute plan that uses pretrained weights rather than new foundation-model pretraining.**
7. **A negative-result path:** the thesis remains valuable if the foundation model does not win.

### 7.2 Feasibility gates

Reject or redesign a candidate if any of the following is unresolved:

- The reference labels cannot support the claimed spatial resolution.
- Train and test data cannot be separated by the intended geography/time/event.
- The proposed novelty is only replacing a CNN with a Transformer.
- Required imagery is commercial or access is uncertain.
- The experiment requires pretraining at institutional-cluster scale.
- The only evaluation is one saturated dataset with random patches.
- The contribution cannot be isolated through ablations.
- “Physical consistency” is asserted without an explicit measurement or process constraint.

---

## 8. Candidate thesis directions tailored to Stefano's background

### 8.1 Comparative decision matrix

| Candidate | Core contribution | Open data | Compute | Evaluation clarity | Novelty potential | Principal risk | Provisional fit |
|---|---|---:|---:|---:|---:|---|---:|
| **A. Uncertainty-aware, physically consistent LST downscaling with EO-FM features** | Cross-region thermal sharpening with aggregation consistency and calibrated uncertainty | High | Medium | High if validation is designed carefully | High | No true 10 m thermal ground truth | **Very high** |
| **B. Geographic transfer and parameter-efficient adaptation of EO foundation models** | Controlled comparison under spatial/temporal shifts; adapters or domain-distance-aware selection | High | Medium | Very high | Medium–high | Can become “just a benchmark” without a method contribution | **Very high** |
| **C. Missing-modality robust Sentinel-1/2 fusion** | Fusion that degrades gracefully under clouds, delay, and sensor absence | High | Medium | High | High | Simulated missingness may be unrealistic | **High** |
| **D. Uncertainty-aware disaster change detection under event shift** | Leave-one-event-out change maps with calibrated pixel uncertainty | High | Medium | High | High | Labels across events are heterogeneous/noisy | **High** |
| **E. Sensor-aware, verifiable EO agent** | Retrieval + typed constraints + execution checks for auditable EO workflows | Medium–high | Low–medium | High with UnivEARTH-style benchmark | Very high | Rapidly moving field; API/tool dependence | **High but riskier** |
| **F. Compact/onboard adaptation of an EO foundation model** | Quantization/distillation and accuracy–latency–calibration frontier | High | Medium | Medium–high with hardware | High | Weak without representative hardware | **Conditional** |
| **G. Cross-sensor hyperspectral representation transfer** | Spectral-response-aware adaptation across hyperspectral/multispectral sensors | Medium | Medium | Medium | High | Labels and realistic cross-sensor pairs are scarce | **Conditional** |

### 8.2 Candidate A — LST downscaling with uncertainty and physical consistency

**Working title**  
*Uncertainty-Aware and Physically Consistent Land-Surface-Temperature Downscaling Using Earth-Observation Foundation-Model Representations*

**Why it fits**

- It builds on prior Landsat 8/9 and Sentinel-2 LST work rather than discarding that investment.
- It adds current AI4EO questions: pretrained representations, geographic transfer, physical consistency, and uncertainty.
- It connects image/signal processing, regression, multimodal fusion, and environmental application.
- It can produce a useful negative result if pretrained features do not outperform carefully tuned RF/CNN baselines.

**Possible research question**

> Do frozen or parameter-efficient EO foundation-model features improve cross-city and cross-season LST downscaling, and can coarse-scale consistency plus uncertainty calibration prevent unsupported fine-scale thermal detail?

**Key methodological contribution**

Predict high-resolution residual structure using Sentinel-2, land-cover, DEM, and possibly weather/context features, while enforcing that the downscaled prediction aggregates back to the observed coarse thermal measurement:

$$
\mathcal{L} = \mathcal{L}_{\text{reconstruction}} + \lambda_{c}\,\left\|D(\hat{T}_{HR})-T_{LR}\right\|_1 + \lambda_{u}\,\mathcal{L}_{\text{uncertainty}},
$$

where \(D\) is the sensor-aware degradation or aggregation operator, \(T_{LR}\) is observed coarse LST, and \(\hat{T}_{HR}\) is the predicted high-resolution field.

**Essential caution**

Downscaling cannot manufacture measured 10 m thermal information. Because true 10 m LST ground truth is normally unavailable, a credible thesis must combine several validation levels:

1. reduced-resolution simulation where the target is observable;
2. coarse-scale reconstruction/energy consistency;
3. cross-city and cross-season transfer;
4. independent comparison with temporally matched thermal products or stations where available;
5. spatial uncertainty and risk–coverage analysis;
6. tests of whether added fine detail tracks independent urban morphology rather than merely sharpening optical edges.

**Baselines**

- linear regression and Random Forest;
- a task-specific CNN/U-Net or geographically weighted model;
- frozen features from one or two open EO encoders such as Prithvi, DOFA, or a TerraMind compact variant;
- ablations without consistency and without uncertainty.

**Novelty boundary**

IBM already provides a [foundation-model-based LST system](https://github.com/ibm-granite/granite-geospatial-land-surface-temperature), and Landsat–Sentinel thermal fusion remains active research. The thesis novelty should therefore be **cross-domain reliability and physical validation**, not simply “apply Prithvi to LST.”

### 8.3 Candidate B — Geographic transfer and efficient adaptation

**Working title**  
*Capability-Oriented Evaluation and Parameter-Efficient Adaptation of Earth-Observation Foundation Models under Geographic Shift*

**Research question**

> Under spatially disjoint evaluation, which adaptation strategies preserve rare-class performance and calibration, and can a measurable domain-distance signal predict which model or adapter will transfer best?

**Contribution options**

- compare frozen, linear-probe, adapter/LoRA, and full fine-tuning under equal compute;
- quantify target-domain distance using embeddings, metadata, or optimal transport;
- select the model/adapter before target labels are fully available;
- report class-wise transfer, calibration, and compute rather than only average accuracy.

**Data and tools**

- one PANGAEA or GEO-Bench-2 task with genuine geographic units;
- BigEarthNet v2 country/region splits;
- Sen1Floods11 leave-one-event-out;
- an agricultural benchmark with region-separated labels.

**Baselines**

- Random Forest or gradient boosting on spectral/temporal features;
- ResNet/U-Net or a small ViT trained from scratch;
- two or three open GFMs selected for complementary capabilities, not a long leaderboard.

**What makes it a thesis rather than a benchmark report**

Add a method or scientific hypothesis—for example, domain-distance-guided adapter selection, rare-class-aware adaptation, or calibration-aware early stopping.

### 8.4 Candidate C — Robust optical–SAR fusion with missing observations

**Working title**  
*Robust Multimodal Earth Observation under Cloud, Delay, and Sensor Absence*

**Research question**

> Can modality-dropout, asynchronous temporal encoding, or uncertainty-aware fusion retain useful performance when optical and SAR observations are not perfectly paired?

**Suitable data**

- [SEN12MS-CR-TS](https://arxiv.org/abs/2201.09613) for cloudy optical, clear optical, and SAR time series;
- BigEarthNet-MM for paired Sentinel-1/2 classification;
- PASTIS-R for agricultural radar–optical time series.

**Evaluation regimes**

- all modalities present;
- optical missing at random;
- optical missing conditional on real cloud masks;
- asynchronous observation delays;
- sensor outage at test time;
- transfer to an unseen geography or season.

**Metrics**

Task performance versus missingness rate, calibration, worst-group/event performance, inference cost, and degradation relative to the full-modality upper bound.

**Main danger**

Artificially deleting channels uniformly is not a realistic missing-data model. Missingness should follow cloud, revisit, or acquisition patterns.

### 8.5 Candidate D — Uncertainty-aware change or disaster mapping

**Working title**  
*Calibrated Semantic Change Detection under Unseen Disaster Events*

**Research question**

> Which uncertainty method best identifies incorrect change predictions when the test event, geography, or sensor conditions differ from training?

**Experimental design**

- choose one hazard and one clear output, such as flood extent or burned-area segmentation;
- train on several events and hold out complete events;
- compare deterministic confidence, deep ensembles, evidential/probabilistic heads, and conformal risk control;
- evaluate IoU/F1 alongside Brier score, expected calibration error, negative log-likelihood, risk–coverage, and error-detection AUROC;
- analyse boundaries, rare severity levels, and corrupted/missing inputs separately.

**Why it is useful**

Emergency mapping needs a map of *where the model may be wrong*, not only a globally averaged accuracy score.

### 8.6 Candidate E — Verifiable EO agents

**Working title**  
*Sensor-Aware Verification for Tool-Using Earth-Observation Agents*

**Research question**

> Can retrieval of authoritative metadata, typed tool schemas, and automatic physical/unit checks reduce execution and scientific-logic failures in EO code-generating agents?

**Possible contribution**

- retrieve product-specific documentation before code generation;
- constrain collection IDs, band names, temporal availability, units, and scale factors;
- run static checks and small sentinel queries before full execution;
- verify numerical ranges and provenance;
- compare zero-shot, retrieval-only, reflection-only, and constrained-agent conditions on UnivEARTH.

**Why it fits**

It uses Stefano's NLP and multi-agent background while remaining grounded in actual EO data and sensor knowledge.

**Why it is riskier**

The field changes quickly; cloud APIs and base models may change during the thesis; reproducibility needs cached questions, pinned tools, and recorded outputs.

### 8.7 Candidate F — Efficient and onboard EO foundation models

**Research question**

> What accuracy–calibration–latency trade-off is achieved by distillation or quantization of an EO encoder under realistic onboard inputs and distribution shift?

This becomes strong only if representative hardware, an emulator, or collaboration is available. Otherwise it risks becoming a generic compression comparison with estimated FLOPs. ESA Φsat-2 makes it strategically relevant, but operational constraints must be real.

### 8.8 Candidate G — Cross-sensor hyperspectral transfer

**Research question**

> Can wavelength-conditioned representations transfer material or crop classifiers across sensors with different band centres and spectral response functions?

This is scientifically attractive and links to recent hyperspectral study. A credible version should avoid the standard random-pixel Indian Pines experiment. It needs spatially disjoint regions, preferably more than one sensor, explicit spectral-response modelling, and limited-label evaluation. Data availability and ground truth should be confirmed before selecting it.

---

## 9. Provisional recommendation

The directions can be grouped by thesis character:

| Desired thesis character | Best candidate |
|---|---|
| Strong continuity with earlier work and a clear environmental variable | **A — LST downscaling** |
| Most methodologically general ML/CV thesis | **B — geographic transfer/adaptation** |
| Strong multisensor EO identity | **C — missing-modality S1/S2 fusion** |
| Strong operational/trustworthy-AI identity | **D — uncertainty-aware disaster mapping** |
| Strong NLP/agentic and emerging-topic identity | **E — verifiable EO agents** |
| Strong ESA upstream/edge identity, if hardware is available | **F — onboard adaptation** |
| Strong imaging-spectroscopy identity, if suitable paired data exist | **G — hyperspectral transfer** |

The recommended discussion order with the professors is:

1. **Candidate A**, because it combines existing domain experience with several open AI4EO problems and can be scoped from conservative to ambitious.
2. **Candidate B**, because it has the cleanest methodology and the lowest dependence on a particular Earth-science application.
3. **Candidate C or D**, depending on whether the group prefers multisensor representation learning or trustworthy disaster mapping.
4. **Candidate E**, as a higher-risk, high-novelty alternative that uses the NLP background.

The immediate decision should not be “which architecture?” It should be:

- Which scientific variable or operational task matters to the supervisors?
- Which geographic/temporal transfer claim can be evaluated?
- Which labels and compute are guaranteed?
- Does the group prefer a method contribution, an application contribution, or a benchmark/reliability contribution?

---

## 10. Recommended reading sequence

### Stage 1 — Understand the field's development

1. [Zhu et al. — Deep Learning in Remote Sensing: A Comprehensive Review and List of Resources (2017)](https://arxiv.org/abs/1710.03959)  
   Read for the transition from classical remote sensing to learned spectral–spatial representations.

2. [Tuia et al. — Artificial Intelligence to Advance Earth Observation: A Perspective (2023/2024)](https://arxiv.org/html/2305.08413v2)  
   Read for the wider progression from mapping to explanation, physics, communication, trust, and ethics.

3. [Schmitt et al. — Data-centric Machine Learning for Geospatial Remote Sensing Data (2024)](https://arxiv.org/html/2312.05327v3)  
   Read for label quality, geographic diversity, data curation, and evaluation.

### Stage 2 — Understand representation learning

4. [Mañas et al. — Seasonal Contrast / SeCo (ICCV 2021)](https://openaccess.thecvf.com/content/ICCV2021/papers/Manas_Seasonal_Contrast_Unsupervised_Pre-Training_From_Uncurated_Remote_Sensing_Data_ICCV_2021_paper.pdf)  
   Why temporal consistency is an EO-specific self-supervision signal.

5. [Cong et al. — SatMAE (NeurIPS 2022)](https://proceedings.neurips.cc/paper_files/paper/2022/hash/01c561df365429f33fcd7a7faa44c985-Abstract-Conference.html)  
   How masked modelling is adapted to spectral and temporal structure.

6. [Fuller et al. — CROMA (2023)](https://arxiv.org/abs/2311.00566)  
   Radar–optical contrastive and masked pretraining.

7. [Xiong et al. — DOFA (2024/2025)](https://arxiv.org/abs/2403.15356)  
   Cross-sensor modelling with wavelength-conditioned parameters.

8. [Astruc et al. — AnySat (CVPR 2025)](https://arxiv.org/abs/2412.14123)  
   Heterogeneous resolutions, scales, modalities, and datasets in one model.

9. [Jakubik et al. — TerraMind (2025/2026)](https://arxiv.org/html/2504.11171v5)  
   Generative multimodality and the current ESA/IBM direction.

### Stage 3 — Understand what is still unsolved

10. [Lacoste et al. — GEO-Bench (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/a0644215d9cff6646fa334dfa5d29c5a-Abstract-Datasets_and_Benchmarks.html)  
    Standardized multi-task evaluation.

11. [Marsocci et al. — PANGAEA (2024/2025)](https://arxiv.org/abs/2412.04204)  
    Why GFMs do not universally beat supervised baselines.

12. [GEO-Bench-2 (2025)](https://arxiv.org/html/2511.15658v1)  
    Capability-oriented evaluation and the distinction between RGB and EO-specific advantages.

13. [Corley et al. — No One Knows the State of the Art in Geospatial Foundation Models (2026)](https://arxiv.org/html/2605.12678v1)  
    Essential reading before accepting any leaderboard or “best model” claim.

14. [Shang et al. — Benchmarking GFMs for Agriculture Applications (2026)](https://arxiv.org/abs/2606.29664)  
    A concrete example of geographic transfer failure.

15. [Kao et al. — Towards LLM Agents for Earth Observation (ACL 2026)](https://aclanthology.org/2026.findings-acl.124.pdf)  
    Evidence that agentic EO is promising but far from reliable.

For each paper, use the established review template:

- problem;
- why it matters;
- dataset and geographic coverage;
- model and input modalities;
- claimed contribution;
- evaluation split and metrics;
- results;
- weaknesses and missing baselines;
- relevance to a possible thesis.

---

## 11. Questions to take to the thesis meeting

1. Should the thesis make its main contribution in **AI methodology**, **EO application**, or **evaluation/reliability**?
2. Is the group interested in continuing the LST/urban-heat work, or should the scientific application change?
3. What GPU, storage, and cloud/HPC resources are guaranteed for the full thesis period?
4. Does the group have access to expert labels, in-situ measurements, or a domain collaborator?
5. Would a negative result about foundation-model transfer be considered a valid contribution if the evaluation is rigorous?
6. Is collaboration with an ESA/EO group realistic, or should the thesis be fully reproducible from open data and weights?
7. Which deployment claim matters: another city, another season, another sensor, another event, or low-label adaptation?

---

## 12. Final assessment

AI4EO has moved beyond the simple transplantation of computer-vision architectures to satellite images. Its scientific frontier is defined by the structure of EO itself: many sensing physics, multiple native resolutions, repeated but irregular observations, global spatial heterogeneity, scarce and noisy labels, rare extremes, and the requirement that outputs remain scientifically and operationally credible.

Foundation models are an important part of this frontier, but they are not the whole field and not automatically the best solution. The most valuable current research asks what capabilities pretraining creates, where those capabilities fail, how they can be adapted efficiently, and how their uncertainty and physical consistency can be demonstrated outside the benchmark on which they were tuned.

For an MSc thesis, the opportunity is therefore to choose one precise intersection of:

1. an Earth-observation problem;
2. an observable and reproducible dataset;
3. a real deployment shift or constraint;
4. a methodological contribution;
5. a rigorous evaluation protocol.

That structure makes the work useful even if the newest model does not win—which is exactly what a scientifically strong thesis should allow.
