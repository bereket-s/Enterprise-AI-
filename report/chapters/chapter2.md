# Chapter 2: Literature Review

## 2.1 Theories and Concepts (Conceptual Review)

**Analytics maturity and Decision Support Systems (DSS).** The dominant framework for
describing analytics capability is a four-stage maturity model: *descriptive*
analytics (what happened), *diagnostic* (why it happened), *predictive* (what is
likely to happen), and *prescriptive* (what action to take). Classical DSS theory
positions technology as an extension of human judgement rather than a replacement for
it — the system surfaces relevant, timely information so a manager decides faster and
better, not so the system decides alone. This platform is explicitly positioned at the
predictive-to-prescriptive boundary: every module produces a score (predictive) and an
accompanying recommended action or explanation (prescriptive-adjacent), and a human
role retains the final decision (e.g., "Investigate / Approve / Block" for a
fraud alert).

**Dynamic Capabilities Theory.** Several of the empirical studies reviewed below
(Božič & Dimovski, 2019; Torres et al., 2018) frame business intelligence not as a
static IT asset but as a *dynamic capability* — an organisation's ability to sense
opportunities in data, transform that sensing into insight, and drive changed
behaviour. This conceptual lens motivates a specific architectural decision in this
project: the platform is not "a forecasting tool," it is a *sensing layer* (data
ingestion and mapping), a *transforming layer* (the ML/feature-engineering pipeline
shared across modules), and a *driving layer* (the dashboards, alerts, and Copilot
that turn a model's output into a concrete next action).

**Explainable AI (XAI).** As predictive models move from experimentation into
operational decision-making, the literature converges on a consistent finding:
explanation quality is not a cosmetic feature but a direct driver of user trust,
adoption, and appropriate reliance (Almtrf, 2025; Sharma et al., 2024; Staley, 2025).
Two broad XAI approaches exist: *post-hoc* explanation of an opaque model (e.g. SHAP —
SHapley Additive exPlanations — values layered on top of a trained model) and
*inherently interpretable* explanation,
where the reason a case is flagged is derived directly from domain-meaningful features
rather than reverse-engineered from the model afterwards. This project adopts the
second approach throughout — fraud, maintenance, and performance-score explanations
are all generated from the same engineered features the model was trained on (e.g.
"amount is 4.1× this account's average," "tool wear is 2.3 std above normal"), which
is cheaper to compute and easier for a non-technical manager to audit than a
SHAP-value plot, at the cost of being less fine-grained than a true per-feature
attribution method.

**Class imbalance in supervised learning.** Fraud, equipment failure, and employee
attrition all share a structural property: the outcome of interest is rare (in this
project's datasets, roughly 9%, 3%, and 16% positive respectively). A classifier
trained naively on such data tends to simply predict the majority class. The
established mitigation used throughout this project — cost-sensitive learning via a
`scale_pos_weight` term in gradient boosting — re-weights the minority class during
training rather than resampling the dataset, preserving the original data
distribution for evaluation (a practice consistent with Alfaiz & Fati, 2022; Btoush
et al., 2023).

**Multi-tenancy.** In software architecture, *multi-tenancy* describes a single
application instance serving multiple customer organisations ("tenants") while
keeping each tenant's data logically isolated. Pinto et al. (2016) distinguish
tenancy models by isolation strength: shared schema with row-level
filtering (cheapest, weakest physical isolation), schema-per-tenant, and
database-per-tenant (most expensive, strongest isolation). This project adopts the
first model deliberately, as the appropriate trade-off for a Minimum Viable Product
(MVP)/capstone-scale system, and documents the migration path to stronger isolation
as the platform scales
(see Chapter 5 and `docs/architecture.md`).

## 2.2 Current Research (Empirical Review)

**Business intelligence and decision quality.** Torres et al. (2018) surveyed firms
and found that BI/analytics capability improves firm performance
*indirectly*, mediated by improved decision-making processes — simply having the
technology is not sufficient; the mediating variable is whether decisions actually
change. Božič and Dimovski (2019) extended this with a dynamic-capabilities lens,
showing BI/analytics use is associated with "innovation ambidexterity" (the ability to
both exploit existing and explore new opportunities), again mediated by organisational
process changes rather than a direct technology effect. Mamakou (2026) further
disaggregates this relationship by firm size, finding the analytics-to-performance
link is moderated by organisational capability to convert insight into decisions —
directly relevant to this project's emphasis on the Copilot and explanation layer as
the "last mile" that turns a forecast into a decision, not just a chart.

**Fraud detection.** Alfaiz and Fati (2022) benchmarked multiple ML classifiers on the
European credit-card fraud dataset — anonymised via Principal Component Analysis
(PCA) — finding ensemble methods
(including gradient boosting) consistently outperformed single classifiers,
particularly once class-imbalance-aware resampling was applied. Btoush et al. (2023),
in a systematic review of the credit-card-fraud literature, report that boosting
algorithms (XGBoost, LightGBM, AdaBoost) dominate recent high-performing studies, and
identify *interpretability* and *evaluation on realistic (non-oversampled) test sets*
as recurring weaknesses across the reviewed literature — both directly addressed in
this project's fraud module, which evaluates only on a held-out, non-resampled test
split and generates feature-grounded reason codes rather than a bare probability.

**Predictive maintenance.** Matzka (2020) — whose AI4I 2020 dataset this project uses
directly — introduced a synthetic-but-realistic sensor dataset specifically to enable
reproducible predictive-maintenance research where real industrial failure data is
proprietary and hard to obtain, and paired it with an explainability-first modelling
approach. Sharma et al. (2024), reviewing XAI in predictive
maintenance broadly, report that interpretable failure explanations (not just a risk
percentage) are consistently identified by maintenance engineers as the deciding
factor in whether they trust and act on a model's alert — directly motivating this
project's `contributing_factors` output (e.g. "torque is 1.8 std above the normal
operating range") rather than a bare score.

**Employee attrition / HR analytics.** Raza et al. (2022) benchmarked five ML models on the IBM HR Analytics dataset — the same public
dataset used in this project's Workforce module — and found ensemble/boosting methods
outperformed logistic regression, but with materially weaker absolute performance
(ROC-AUC in the 0.6–0.8 range) than the fraud or maintenance literature, which the
authors attribute to attrition being driven substantially by unobserved factors (job
market conditions, personal circumstances) not present in typical HR datasets. This
project's own attrition model, evaluated on the same dataset, produced a comparable
result (ROC-AUC 0.63; see Chapter 4) — a finding discussed critically rather than
treated as a shortfall, since it replicates a documented, structural limitation of the
underlying data rather than a modelling error.

**Inventory / demand forecasting.** Goulart et al. (2026) implemented an ML-based
demand-forecasting pipeline for a real distributor,
reporting that a properly validated ML forecast materially outperformed the
distributor's prior manual/statistical process, and — notably for this project's
design — that operational value came less from marginal forecast-accuracy gains and
more from converting the forecast into a concrete reorder recommendation the
non-technical purchasing team could act on directly. This finding is the direct
justification for this project's Inventory module output being a recommended order
quantity and risk label, not merely a forecast number.

**Explainability and trust.** Across three independent studies in different sectors —
financial services (Staley, 2025), general managerial decision support (Almtrf,
2025), and predictive maintenance specifically (Sharma et al., 2024) — the same
pattern recurs: explanation quality, not raw model accuracy, is the strongest
predictor of whether a human decision-maker actually adopts and acts on an AI
system's output. This is the single most load-bearing finding from the literature
for this project's design, and is why every module (fraud, maintenance, workforce
performance) was built with a human-readable "why" from the outset, rather than as a
later addition.

**Multi-tenant architecture.** Pinto et al.'s (2016) systematic mapping study of the
multi-tenant SaaS literature finds that most published work addresses tenancy as a
*database-partitioning* problem, with comparatively little attention to how tenancy
composes with a *modular feature-toggle* architecture (i.e. not just "whose data is
this row" but "which capabilities is this tenant even allowed to reach"). This
project's `require_module_enabled` dependency (Chapter 3; `docs/architecture.md`) —
enforcing both tenant isolation and per-module access in a single, testable
choke-point — addresses that specific gap directly, in a way none of the reviewed
architecture papers combine explicitly with an analytics-module context.

## 2.3 Research Framework

Synthesising the conceptual review (§2.1) and the empirical findings (§2.2) into a
single framework:

**Figure 2.1 — Research framework**, linking data integration, module-specific ML,
the explainability layer, cross-cutting configurability, and decision-support value.

```
        DATA INTEGRATION            MODULE-SPECIFIC ML          EXPLAINABILITY LAYER
        (upload, column-map)  ───▶  (forecast / classify /  ───▶ (feature-grounded
                                     score, per module)           reason codes)
              │                            │                            │
              ▼                            ▼                            ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │        CONFIGURABILITY  (per-tenant module toggles;                │
        │        per-department KPI weights — not one universal formula)    │
        └──────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                              DECISION-SUPPORT VALUE
                    (faster, more confident, more trusted action —
                     Božič & Dimovski 2019; Staley 2025; Torres et al. 2018)
```

The framework's central claim, drawn directly from the literature above, is that
**decision-support value is not produced by the model alone** — it requires the
model's output to be integrated, explained, and configurable to the context it is
used in. Chapters 3 and 4 operationalise and test the *left-hand side* of this
framework (data integration → ML → explainability, evaluated quantitatively per
module); the *right-hand side* (organisational decision-quality impact) is discussed
qualitatively in Chapter 5 as a direction for future, survey-based evaluation beyond
this capstone's scope (see Chapter 1, §1.6).
