# Appendix

## A. Secondary Data Sources (in place of questionnaire/interview evidence)

This project uses secondary, public datasets rather than a questionnaire or
interviews (justified in Chapter 3). Full provenance:

| Dataset | Source | Records used | Retrieval script |
|---|---|---|---|
| Online Retail | UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/352/online+retail | 541,909 raw / 530,104 cleaned | `backend/scripts/download_datasets.py::download_online_retail` |
| Simulated card transactions | HuggingFace mirror (Sparkov generator) — `dazzle-nu/CIS435-CreditCardFraudDetection` | 66,006 (stratified sample) | `download_credit_card_fraud` |
| AI4I 2020 Predictive Maintenance | UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset | 4,000 (random sample) | `download_ai4i2020` |
| IBM HR Analytics (Employee Attrition) | HuggingFace mirror — `eduvance/employee_attrition` | 1,370 | `download_employee_attrition` |

## B. Raw Data and Model Outputs

- Raw downloaded files: `data/raw/*.csv` (regenerated on demand by running
  `python backend/scripts/download_datasets.py`; not committed to version control —
  see `.gitignore` — to keep the repository lightweight and reproducible from source).
- Full pipeline run output (equivalent to an SPSS/Excel output file for this
  system-development project): `report/chapter4_results.json`, produced by
  `backend/scripts/seed_demo_org.py`.
- Persisted per-run evaluation records: `ModelEvaluation` table (one row per
  training run, per module) in the application database
  (`backend/platform.db` for local SQLite runs).
- Trained model artefacts: `backend/app/ml/artifacts/*.joblib`.

## C. Automated Test Evidence

18 automated tests (`backend/tests/`) exercise authentication, multi-tenant data
isolation, module gating, every module's ML pipeline, and the AI Copilot. Run with:

```
cd backend && pytest -v
```

Test files: `test_auth.py`, `test_tenant_isolation.py`, `test_ml_pipelines.py`,
`test_workforce_kpi.py`, `test_copilot.py`.

## D. API Reference

The full REST API (36 endpoints across authentication, organization/module
management, and the five analytical modules) is self-documented via OpenAPI/Swagger
at `/docs` when the backend is running (`app/main.py`). A summary table:

| Area | Example endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Organization | `GET /api/org/modules`, `PUT /api/org/modules/{key}`, `POST /api/org/users` |
| BI/Forecasting | `POST /api/bi/ingest/preview`, `POST /api/bi/ingest/commit`, `GET /api/bi/kpis`, `POST /api/bi/forecast/run` |
| Inventory | `POST /api/inventory/reorder/run`, `GET /api/inventory/reorder/latest` |
| Fraud | `POST /api/fraud/train`, `GET /api/fraud/transactions`, `PUT /api/fraud/transactions/{id}/status` |
| Maintenance | `POST /api/maintenance/train`, `GET /api/maintenance/equipment` |
| Workforce | `POST /api/workforce/performance/run`, `PUT /api/workforce/kpi-weights/{dept}/{kpi}`, `POST /api/workforce/attrition/train` |
| AI Copilot | `POST /api/copilot/ask`, `GET /api/copilot/history` |

## E. Source Code

Full source code, architecture documentation, and this report's source Markdown are
maintained in the project repository (see `README.md` for structure). Key reference
documents: `docs/architecture.md` (full system architecture), `docs/deployment.md`
(setup and deployment instructions).
