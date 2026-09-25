# Appendix D: API Reference

The full REST API (73 endpoints across authentication, organization/module
management, the five analytical modules, and the integration/observability layer) is
self-documented via OpenAPI/Swagger at `/docs` when the backend is running
(`app/main.py`). A summary table:

**Table D.1 — REST API summary, by area**

| Area | Example endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Organization | `GET /api/org/modules`, `PUT /api/org/modules/{key}`, `POST /api/org/users` |
| BI/Forecasting | `POST /api/bi/ingest/preview`, `POST /api/bi/ingest/commit`, `GET /api/bi/kpis`, `POST /api/bi/forecast/run` |
| Inventory | `POST /api/inventory/ingest/preview`, `POST /api/inventory/reorder/run`, `GET /api/inventory/reorder/latest` |
| Fraud | `POST /api/fraud/train`, `GET /api/fraud/transactions`, `PUT /api/fraud/transactions/{id}/status` |
| Maintenance | `POST /api/maintenance/train`, `GET /api/maintenance/equipment` |
| Workforce | `POST /api/workforce/performance/run`, `PUT /api/workforce/kpi-weights/{dept}/{kpi}`, `POST /api/workforce/attrition/train` |
| AI Copilot | `POST /api/copilot/ask`, `GET /api/copilot/history` |
| Integrations (#1–#6) | `POST /api/integrations/api-keys`, `POST /api/integrations/db-connections`, `POST /api/integrations/db-connections/{id}/sync`, `POST /api/integrations/scheduled-jobs`, `POST /api/integrations/webhooks`, `POST /api/webhooks/{token}`, `POST /api/integrations/connectors`, `POST /api/integrations/push/{module_key}` |
| Model registry | `GET /api/models/{module_key}`, `POST /api/models/{module_key}/{version}/activate`, `GET /api/models/{module_key}/drift` |
| Observability | `GET /api/integrations/audit-log`, `GET /api/integrations/usage` |
