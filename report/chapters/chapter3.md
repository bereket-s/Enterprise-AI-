# Chapter 3: Research Methodology

## 3.1 Research Method

This project follows a **quantitative, Design Science Research (DSR)** method,
supplemented by a small qualitative usability component (§3.8). DSR is the
established Information Systems methodology whose primary contribution is a working
artefact — here, the platform itself — evaluated through rigorous testing rather than
a survey of respondents' opinions. Every predictive module is assessed against
standard, numeric metrics — Mean Absolute Error (MAE), Root Mean Square Error (RMSE),
and Mean Absolute Percentage Error (MAPE) for forecasting; precision, recall, F1
score, and ROC-AUC (Receiver Operating Characteristic – Area Under the Curve) for
classification — each computed both on a single held-out split and via 5-fold
cross-validation (§3.6), exactly as a quantitative study reports results — the
"instrument" being validated is a system, not a questionnaire. This is justified
directly by the scope decision in §1.6: the research question (§1.4) concerns whether
an *architecture* delivers measurable predictive/prescriptive value, a systems and
data question, not primarily an attitudinal one.

## 3.2 Research Strategy

The strategy combines **artefact development** (building the platform end-to-end)
with **controlled experiments** (training/evaluating each model on a held-out split
and via cross-validation, seeded for reproducibility) and one **integration test** —
an end-to-end pipeline run (`backend/scripts/seed_demo_org.py`) that ingests all four
datasets, trains every model, and records every metric in one reproducible pass,
serving as both a system test and the source of Chapter 4's results.

## 3.3 Research Design

The design is **experimental/evaluative** for the predictive components and
**descriptive** for the platform architecture (`docs/architecture.md`). It is
explicitly *not* correlational or survey-based for its primary evaluation — no
hypotheses about human attitudes are tested there — following from the DSR method
adopted in §3.1; §3.8 adds a small, separately-scoped qualitative strand.

## 3.4 Data Collection Methods and Tools

All data is **secondary, public, open data** — chosen deliberately over
synthetically-generated data (per the project brief's guidance to avoid "a dataset
containing 10,000 records I generated") so that results reflect real operational
patterns rather than an idealised distribution built to flatter the model:

**Table 3.1 — Datasets used, by module and source**

| Module | Dataset | Source |
|---|---|---|
| BI/Forecasting, Inventory | Online Retail | UCI Machine Learning Repository (Chen et al., 2012) |
| Fraud & Anomaly Detection | Simulated card transactions (Sparkov generator) | HuggingFace-mirrored public dataset |
| Predictive Maintenance | AI4I 2020 Predictive Maintenance | UCI Machine Learning Repository (Matzka, 2020) |
| Workforce Intelligence | IBM HR Analytics Employee Attrition | Public HR analytics dataset (HuggingFace mirror) |

No questionnaire or interview instrument drove the primary evaluation, since the
instrument here is the software system itself (see §3.6), documented for
reproducibility as code: `backend/scripts/download_datasets.py` (acquisition), the
`app/services/*_service.py` ingestion functions, and `app/ml/*.py` (feature
engineering, training, evaluation) — every step is deterministic and
version-controlled rather than manual. A separate, genuine participant
questionnaire *was* designed (Appendix G) for the usability component in §3.8.

## 3.5 Population, Sampling, and Sample Size

Each module draws on the full record population of its source dataset, with one
documented exception:

- **BI/Forecasting & Inventory (N = 541,909 raw → 530,104 cleaned):** the complete
  Online Retail population (Dec 2010–Dec 2011, UK online retailer); cancelled orders
  and non-positive quantity/price rows are excluded as returns, not sales.
- **Fraud Detection (N = 66,006, stratified sample):** from ≈1.05 million simulated
  transactions (0.57% fraud rate), a **stratified sample** (all ≈6,000 fraud rows plus
  60,000 random legitimate rows, seed = 42) — non-probability, purposive — keeps the
  fraud rate learnable (9.1%) within a capstone's compute budget while staying
  realistically imbalanced rather than artificially balanced to 50/50.
- **Predictive Maintenance (N = 4,000, random sample of 10,000):** seed = 42; the
  population's 3.4% failure rate is preserved in the sample (3.2%).
- **Workforce Intelligence (N = 1,370):** the full (reduced) IBM HR Analytics mirror,
  no sub-sampling needed at this size.

Sample sizes are justified by statistical adequacy (thousands of records per
classification task) and practical constraint (capstone compute/storage budget,
documented rather than hidden).

## 3.6 Data Analysis

Each module follows the same pipeline: **stratified train/test split** (75/25,
`random_state=42`) → **feature engineering** (module-specific: lag/calendar features
for forecasting; amount/geo/time features for fraud; sensor-deviation features for
maintenance; Key Performance Indicator (KPI) normalisation for workforce) →
**model fitting**
(`XGBRegressor`/`XGBClassifier`, `scale_pos_weight` set from each split's own class
balance) → **evaluation**, using `scikit-learn`'s standard metrics. For every
classification task, this single-split result is **supplemented by 5-fold stratified
cross-validation** (`app/ml/evaluation_utils.py`), reporting a mean ± standard
deviation per metric instead of one figure that can vary by chance from one split to
the next, and by a **three-algorithm comparison** (XGBoost, Logistic Regression,
Random Forest) with a paired Wilcoxon signed-rank test on per-fold ROC-AUC — so the
choice of XGBoost is justified empirically (Chapter 4) rather than assumed. Results
are persisted to a `ModelEvaluation` row per run and exported to
`report/chapter4_results.json`, which Chapter 4 reports directly from.

## 3.7 Ethical Issues

No primary data was collected from human participants, so no informed-consent or
participant-recruitment protocol was required. Three dataset-specific ethical points
are addressed directly: (1) the **Workforce Intelligence** dataset (IBM HR Analytics)
is a long-established, publicly released, and — per its originating documentation —
**synthetic** dataset; no real employees' data is processed, and the platform displays
anonymised identifiers (e.g. "Employee #142") rather than fabricating names, so no
real or invented person is misrepresented as real. (2) The **Fraud** dataset's
transactions are generated by the Sparkov synthetic-data tool, not drawn from real
cardholders; card numbers, names, and addresses in the source file are fictitious.
(3) All four datasets carry open licences permitting research and educational reuse,
and are cited to their original source (§3.4) rather than presented as originally
collected. No deception, risk of harm, or data-protection concern arises from this
project's data use.

## 3.8 Usability Evaluation

Two additional, qualitative methods address decision-support *value* (Chapter 2,
§2.3's right-hand side), which the technical evaluation alone cannot: (1) a
**researcher-conducted heuristic walkthrough** of the live platform against Nielsen's
(1994) usability heuristics and explainability-specific criteria from §2.1–2.2 (full
method and findings in Appendix F); and (2) a **prepared participant survey
instrument** (Appendix G) — task scenarios plus Likert and open-ended questions — for
a small (n=3–5) pilot with real users, ready to administer but not yet run within
this capstone's timeline (justified in Appendix G, §G.8; revisited in Chapter 5).
