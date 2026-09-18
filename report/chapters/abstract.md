# Abstract

Small and mid-sized organisations are frequently priced out of the predictive and
prescriptive analytics capability that empirical research links to faster,
higher-quality decision-making, largely because enterprise analytics is sold as
fragmented, single-purpose, opaque products. This project designs, builds, and
evaluates an **Enterprise AI Decision Intelligence Platform**: a modular, multi-tenant
system through which an organisation connects its own data, selects only the
analytical modules it needs — Business Intelligence & Forecasting, Inventory &
Procurement Optimization, Fraud & Anomaly Detection, Predictive Maintenance, and
Employee Performance & Workforce Intelligence — and receives explainable
machine-learning output alongside a natural-language AI Copilot, all governed by a
single, tested multi-tenant architecture.

Following a quantitative Design Science Research method, the platform was built
end-to-end (FastAPI/SQLAlchemy backend, Next.js/React frontend, XGBoost-based ML
pipelines) and evaluated against four public, real-world datasets covering retail
transactions, simulated card fraud, industrial sensor telemetry, and HR analytics.
Every classifier was evaluated both on a held-out split and via 5-fold
cross-validation, benchmarked against Logistic Regression and Random Forest baselines
with a paired Wilcoxon significance test. Results were strong for tasks with causally
direct features — fraud detection achieved a cross-validated ROC-AUC of 0.988 ± 0.001
and predictive maintenance 0.964 ± 0.011, both statistically indistinguishable from a
Random Forest baseline but decisively ahead of Logistic Regression — while employee
attrition prediction, whose available features are more indirect proxies for a
psychologically driven outcome, achieved a more modest 0.708 ± 0.038 with no
significant difference between any of the three algorithms tested, a finding
consistent with comparable published work on the same underlying dataset. Automated
tests confirm the platform's central architectural claim: two independently registered
organisations cannot access each other's data, and a disabled module is inaccessible
even to that organisation's own administrator until re-enabled. A researcher-conducted
heuristic usability walkthrough of the live platform additionally found and fixed two
genuine defects — a data-shape rendering crash and a missing mobile-responsive
breakpoint — neither of which the automated test suite was positioned to catch, and
produced a ready-to-administer participant survey instrument for future empirical
evaluation of decision-support value.

The study concludes that a single modular architecture can deliver isolated,
explainable, configurable analytics across multiple distinct business domains from one
codebase, and that resulting prediction quality is bounded by feature richness rather
than by the architecture itself — a distinction the platform's own cross-validated,
statistically compared results make directly visible.

**Keywords:** decision-support systems, multi-tenant SaaS architecture, explainable
AI, predictive analytics
