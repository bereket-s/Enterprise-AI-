# Enterprise AI Decision Intelligence Platform

A modular, multi-tenant AI decision-support platform: organizations connect their data,
choose which modules they need, and get predictive/prescriptive analytics plus an AI
Copilot that answers natural-language questions over their own metrics.

Built as an MSc capstone — see [`report/`](report/) for the full dissertation and
[`docs/architecture.md`](docs/architecture.md) for the system design.

## Modules

| Module | What it does | Status |
|---|---|---|
| Business Intelligence & Forecasting | Sales KPIs, trend analysis, ML demand forecasting | Production |
| Inventory & Procurement Optimization | Reorder points, safety stock, purchase recommendations | Production |
| Fraud & Anomaly Detection | Transaction risk scoring with an investigation workflow | Production |
| Predictive Maintenance | Equipment failure-risk prediction from sensor data | Prototype |
| Employee Performance & Workforce Intelligence | Configurable KPI scoring, goals, attrition risk | Production |

Every module can be independently enabled/disabled per organization. Companies never
see or reach a disabled module's data or API.

## Integrations

A company can connect its own data through six independent paths — CSV upload,
a read-only database connector, REST API push (API key auth), scheduled sync, inbound
webhooks, and a catalog of pre-built connectors (Salesforce/QuickBooks/SAP, simulated
in this environment but running real data through the real ingestion pipeline). See
[`docs/architecture.md`](docs/architecture.md#4-data-ingestion-architecture) for how
they work, and `/dashboard/settings/integrations` in the app to manage them.

## Tech stack

- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS, Recharts
- **Backend:** FastAPI, SQLAlchemy, Pydantic, JWT auth
- **ML:** scikit-learn, XGBoost, pandas
- **Database:** SQLite (local dev) / PostgreSQL (production, via Docker Compose)
- **Datasets:** UCI Online Retail, UCI AI4I 2020 Predictive Maintenance, a simulated
  card-transactions fraud dataset, and the IBM HR Attrition dataset — see
  [`backend/scripts/download_datasets.py`](backend/scripts/download_datasets.py)

## Quick start

See [`docs/deployment.md`](docs/deployment.md) for full setup instructions (local dev
and Docker Compose). Short version:

```bash
cd backend && pip install -r requirements.txt && python scripts/download_datasets.py
python scripts/seed_demo_org.py   # optional: populate a demo org with real results
uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

Then visit `http://localhost:3000`, register an organization, and explore.

## Project structure

```
backend/    FastAPI app, ML pipelines, tests, dataset scripts
frontend/   Next.js dashboard
docs/       Architecture and deployment documentation
report/     MSc capstone report chapters
data/raw/   Downloaded public datasets (not committed — see download script)
```

## Testing

```bash
cd backend && pytest
```

42 tests cover authentication, multi-tenant data isolation, module gating, each
module's ML pipeline, the AI Copilot, and all six integration paths (file upload,
database connector, REST push, scheduled sync, webhooks, connectors) plus the model
registry and audit log.
