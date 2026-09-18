# System Architecture

## 1. Overview

The platform is a modular, multi-tenant web application. One deployment serves many
organizations ("tenants"); each tenant sees only its own data and only the modules it
has enabled. The architecture is deliberately layered so that a module (e.g. Fraud
Detection) can be added, removed, or reused across industries without touching the
platform's authentication, tenancy, or API conventions.

```
                    ┌─────────────────────────────┐
                    │        FRONTEND (Next.js)    │
                    │  Dashboard shell + 5 module   │
                    │  UIs + AI Copilot widget      │
                    └───────────────┬───────────────┘
                                    │ REST (JSON) over HTTPS, JWT bearer auth
                    ┌───────────────▼───────────────┐
                    │        BACKEND (FastAPI)       │
                    │  ┌───────────────────────────┐ │
                    │  │   Platform layer           │ │
                    │  │   auth · orgs · RBAC ·     │ │
                    │  │   module enablement        │ │
                    │  └──────────────┬────────────┘ │
                    │  ┌──────────────▼────────────┐ │
                    │  │   Integration layer         │ │
                    │  │   upload · DB connector ·   │ │
                    │  │   API push · scheduler ·    │ │
                    │  │   webhooks · connectors      │ │
                    │  └──────────────┬────────────┘ │
                    │  ┌──────────────▼────────────┐ │
                    │  │   Module routers            │ │
                    │  │   bi · inventory · fraud ·  │ │
                    │  │   maintenance · workforce   │ │
                    │  └──────────────┬────────────┘ │
                    │  ┌──────────────▼────────────┐ │
                    │  │   Service layer (business   │ │
                    │  │   logic, DB I/O)            │ │
                    │  └──────────────┬────────────┘ │
                    │  ┌──────────────▼────────────┐ │
                    │  │   ML layer (pure functions:  │
                    │  │   feature engineering,      │ │
                    │  │   training, scoring,        │ │
                    │  │   model registry, drift)    │ │
                    │  └───────────────────────────┘ │
                    └───────────────┬───────────────┘
                                    │ SQLAlchemy ORM
                    ┌───────────────▼───────────────┐
                    │   Database (SQLite dev /       │
                    │   PostgreSQL production)       │
                    └─────────────────────────────────┘
```

The ML layer is intentionally decoupled from FastAPI/SQLAlchemy — every training
function takes and returns plain pandas/numpy objects, which is what makes the fast
unit tests in `test_ml_pipelines.py` possible without a database or web server.

## 2. Multi-tenant architecture

Tenancy is enforced with the shared-schema, row-level-isolation pattern: every
tenant-scoped table carries an `organization_id` foreign key (via `TenantMixin`,
`app/models/base.py`), and every query is filtered by it.

The isolation boundary is a single dependency, not a convention scattered across
routes:

```python
def current_org_id(user: User = Depends(get_current_user)) -> int:
    return user.organization_id
```

`org_id` always comes from the authenticated user's JWT — never from a path or query
parameter — so there is no request shape that lets Company A read Company B's data by
guessing an ID. `test_tenant_isolation.py` verifies this directly: two organizations
ingest different data through the real HTTP API, and each can only see its own.
Machine-to-machine calls (REST push, see §4) use the same principle with a different
credential: an API key hashes to exactly one `organization_id`, so there is still only
one function that decides which org a request belongs to.

Module access is a second, orthogonal gate:

```python
def require_module_enabled(module_key: str):
    def _check(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)) -> int:
        enablement = ...  # look up ModuleEnablement(org_id, module_key)
        if not enablement or not enablement.enabled:
            raise HTTPException(403, ...)
        return org_id
    return _check
```

Every module router declares this as a router-level dependency, so a disabled module
returns 403 for every endpoint under it — enabling it via `PUT /api/org/modules/{key}`
is the only way back in. `require_module_enabled_api_key()` is the same check for the
API-key-authenticated push endpoint.

**Scaling path:** the current design (shared schema, `organization_id` filtering) is
the right MVP choice — simple, testable, and sufficient for a capstone-scale deployment.
A production SaaS handling regulated data (e.g. banking customers) would likely move to
schema-per-tenant or database-per-tenant for stronger physical isolation; the service
layer would be unaffected since it never issues raw SQL.

## 3. Data model

Platform layer: `Organization`, `User` (role: super_admin / org_admin / manager /
employee), `ModuleEnablement`.

Each module owns its own tables, all `TenantMixin`-scoped:

- **BI/Forecasting:** `Product`, `SalesTransaction`, `ForecastResult`
- **Inventory:** `InventorySnapshot`, `ReorderRecommendation` (reuses BI's `Product`)
- **Fraud:** `FraudTransaction`
- **Maintenance:** `Equipment`
- **Workforce:** `Employee`, `KPIWeightConfig`, `PerformanceScore`, `Goal`
- **Copilot:** `ChatLog` (audit trail of every question/answer)
- **Cross-module:** `ModelEvaluation` — one row per training run, across every module;
  this is the single source the report's Results chapter reads metrics from.

Integration & platform-observability layer (also `TenantMixin`-scoped, see §4 and §6):

- `ApiKey`, `DatabaseConnection`, `ScheduledJob`, `WebhookEndpoint`, `ConnectorInstance`
- `ModelVersion` — one row per trained model artifact, versioned per org/module
- `AuditLog` — one row per sensitive admin action
- `UsageMetric` — one row per org/module/day request counter

## 4. Data ingestion architecture

A company's own data can reach the platform through six independent transports. All
six ultimately produce a plain pandas DataFrame in *some* set of column names and hand
it to the same two building blocks, so adding a transport is a new router, never a new
data model or a new ML pipeline:

- **`suggest_mapping()`** (`app/services/data_mapping.py`) — fuzzy-matches arbitrary
  source column names (`ItemCode`, `Opportunity_Product__c`, `MATNR`, ...) against a
  module's canonical schema (`app/services/canonical_schemas.py`) using a synonym
  table plus a `difflib` similarity fallback.
- **`integration_pipeline.py`** — the single door every transport funnels through:
  `preview_mapping()` / `ingest_with_mapping()` for the human-confirmed path, and
  `auto_ingest()` (mapping applied automatically, no confirmation click) for the four
  transports below that have no admin present to confirm one.

Every module (BI, Inventory, Fraud, Maintenance, Workforce) exposes the same
**preview → commit** pair for transport #1, and the same canonical-field ingestion
function underneath every other transport:

1. **File upload.** `POST /api/{module}/ingest/preview` parses the file and returns
   the proposed mapping plus a sample of rows; `POST /api/{module}/ingest/commit`
   applies the admin-confirmed `{canonical_field: source_column}` mapping
   (`df.rename`) and persists it. This is the only transport with a confirmation step,
   because it is the only one where a human is present in the browser.
2. **Database connector.** `app/services/db_connector.py` opens a short-lived
   SQLAlchemy engine against a company's own database (credentials encrypted at rest,
   see §7), runs either a bare table name or a single validated `SELECT`, and reads
   the result into a DataFrame with `auto_ingest()`. The connection is never held open
   between syncs.
3. **REST API push.** `POST /api/integrations/push/{module_key}` accepts a JSON batch
   of records authenticated by `X-API-Key` (see §7) instead of a user's JWT — for a
   company's own backend to push data on its own schedule rather than the platform
   pulling it.
4. **Scheduled sync.** `app/core/scheduler.py` runs an APScheduler background job that
   ticks once and, on each tick, checks every enabled `ScheduledJob` row for whether
   `last_run_at + interval_minutes` has elapsed; a due `data_sync` job re-runs a saved
   `DatabaseConnection`'s sync, and a due `retrain` job re-runs that module's training.
   Due-ness is derived from a persisted timestamp rather than per-job scheduler state,
   so schedules survive process restarts.
5. **Webhooks.** `POST /api/webhooks/{token}` is an unauthenticated-by-login endpoint
   (a company's system calls it directly) secured instead by an HMAC-SHA256 signature
   over the raw body (`X-Signature` header, verified with `hmac.compare_digest`) using
   a secret shown only once at creation.
6. **Pre-built connectors.** `app/services/connectors.py` — a catalog of
   vendor-specific adapters (Salesforce, QuickBooks, SAP). No OAuth credentials exist
   in this environment, so each adapter runs in **simulated** mode: it generates a
   batch of rows shaped exactly like that vendor's real export (Salesforce's
   `Opportunity`/object field names, QuickBooks' report columns, SAP's field codes),
   then puts it through the *same* `auto_ingest()` every other transport uses. The
   only fake part is where the rows come from — swapping in a real OAuth client call
   later changes nothing downstream. The catalog's `status: "simulated"` is returned
   to the frontend so this is never presented as a live connection.

## 5. AI/ML architecture

| Module | Task | Model | Key evaluation metrics |
|---|---|---|---|
| BI/Forecasting | Revenue time-series forecasting | XGBoost regressor over lag + calendar features | MAE, RMSE, MAPE vs. naive baseline |
| Inventory | Reorder point / safety stock | Statistical formula (demand rate × lead time + z·σ·√lead time) driven by the same forecasting features | Stockout probability, risk distribution |
| Fraud | Binary classification | XGBoost classifier (fixed schema) or the generic classifier below (bring-your-own data) | Precision, recall, F1, ROC-AUC |
| Maintenance | Binary classification | XGBoost classifier over 5 sensor readings + machine type, or the generic classifier for BYOD sensor sets | Precision, recall, F1, ROC-AUC |
| Workforce (performance) | Configurable composite score | No ML — weighted average of normalised KPIs, weights set per department | N/A (not a prediction task) |
| Workforce (attrition) | Binary classification | XGBoost classifier over employee features | Precision, recall, F1, ROC-AUC |

Every classifier follows the same shape: `engineer_features(df)` → stratified
train/test split → `XGBClassifier` with `scale_pos_weight` tuned to the training
split's imbalance → metrics computed on the held-out test set → the trained model
scores *every* ingested row (not just the test split) so the dashboard has a score for
every transaction/machine/employee. Each training run is persisted as a
`ModelEvaluation` row (the report's Results chapter reads from this).

**Fixed vs. generic dispatch.** Fraud and Maintenance each ship with a public demo
dataset that has its own fixed schema (`amt`/`cc_num`/... for fraud, the 5 AI4I sensor
columns for maintenance). Rather than forcing a company's own data into that exact
shape, `train_and_score()` in each service inspects which canonical fields are
actually present and dispatches to one of two paths: the original fixed-schema
pipeline (unchanged, so the demo org's already-reported results never change) or
`app/ml/generic_classifier.py`, which builds a feature matrix from whatever numeric
and categorical canonical fields the company's own data actually supplied. Workforce
needed no such split — its columns were nullable from the start.

**Model registry.** `app/ml/model_registry.py` persists every trained artifact as a
`ModelVersion` (org, module, version number, metrics, feature columns, and the
training-time per-feature reference statistics used for drift detection), joblib-dumped
to `backend/app/ml/artifacts/{module}/org{id}/v{n}.joblib`. Exactly one version per
org/module is `is_active`; `POST /api/models/{module}/{version}/activate` rolls back to
an older version without retraining. `GET /api/models/{module}/drift` compares a
fresh scoring batch's per-feature means against the active version's training-time
reference stats and flags any feature that has drifted beyond 2 standard deviations —
a cheap first signal that a model may need retraining, without a labelled ground truth.

Reason codes (why a transaction/machine is flagged) are generated from the same
features the model was trained on — e.g. fraud reason codes reference amount vs. that
card's own average, distance from the cardholder's home, and time of day, rather than
opaque model internals. This keeps the "explain the prediction" UI honest: it never
invents a reason the model didn't actually use.

## 6. AI Copilot architecture

```
question (NL) → classify_intent() → handler(db, org_id) → real DB query
                                                          → facts
                                     generate_llm_answer(question, facts) ─┐
                                                          → templated answer ◄┘ (fallback)
                                                          → ChatLog persisted
```

Intent classification is deterministic keyword matching (`app/services/copilot_service.py`)
over six intents (revenue trend, top products, stockout risk, fraud risk, equipment
risk, department attention). Each handler runs a real query against that org's own
computed data (KPIs, `ReorderRecommendation`, `FraudTransaction`, `Equipment`,
`PerformanceScore`) and produces a small dict of facts. If `settings.llm_api_key` is
set, `app/ml/llm_client.py` hands those already-computed facts to an LLM
(`generate_llm_answer`) to phrase a richer answer; the prompt explicitly instructs the
model to use only the supplied facts, and any failure (missing key, API error, timeout)
falls back to the deterministic template. Either way the numbers themselves come from
one place — the org's own database — so the Copilot cannot hallucinate a figure that
isn't actually there.

## 7. Security

- Passwords hashed with bcrypt (via passlib); JWT bearer tokens (HS256) for user auth.
- Machine-to-machine auth uses a separate credential: API keys are shown once at
  creation and stored as a SHA-256 hash (`app/core/deps.py:hash_api_key`), never the
  raw key.
- Secrets at rest — database connector passwords and webhook signing secrets — are
  encrypted with Fernet (`app/core/crypto.py`), key derived from `settings.secret_key`.
- Webhook payloads are authenticated by HMAC-SHA256 signature
  (`hmac.compare_digest`, timing-safe) rather than a login, since the caller is another
  system, not a browser session.
- The database connector only ever runs a bare table name or a single `SELECT`
  (`app/services/db_connector.py`); anything containing `;` or other statement types is
  rejected before it reaches the company's database.
- Every module endpoint is gated by both authentication (`get_current_user` or an API
  key) and module-enablement (`require_module_enabled` / `..._api_key`).
- Role-based access control: `require_roles(...)` restricts admin-only actions
  (creating users, toggling modules, revoking API keys/connections) to
  `org_admin`/`super_admin`.
- Sensitive admin actions (API key issuance/revocation, connection/webhook/connector
  creation and deletion, model activation) are recorded to `AuditLog` with the acting
  user, action, and a JSON detail blob — `GET /api/integrations/audit-log`.
- Tenant isolation is structural (see §2), not query-by-query discipline — there is
  exactly one function that decides "which org am I allowed to touch."

## 8. Frontend architecture

Next.js App Router, a `AuthProvider` React context holds the current user and their
enabled modules (fetched once on load), and the dashboard's sidebar renders only
`MODULE_ROUTES` for modules that are actually enabled — so a company that disabled
Fraud Detection never sees it in navigation, matching the backend's 403 behind it.
Each module page is self-contained (fetch on mount, mutate via the module's REST
endpoints) using a small shared `api.ts` axios client that attaches the JWT. Every
BYOD-capable module page embeds a shared `<CsvUploadCard>` for transport #1, and
`/dashboard/settings/integrations` is a dedicated admin UI for the other five
transports (API keys, DB connections, scheduled jobs, webhooks, connectors) plus the
audit log and per-module usage counters.

## 9. Observability

- **Structured request logging.** `RequestLoggingMiddleware`
  (`app/core/middleware.py`) tags every request with an `X-Request-ID` and logs method,
  path, status, and duration as a single JSON line.
- **Usage metrics.** The same middleware decodes the caller's org from the request
  (JWT or API key) and increments a per-org/per-module/per-day `UsageMetric` counter —
  billing-readiness without a separate analytics pipeline. `GET /api/integrations/usage`
  exposes it.
- **Audit log.** See §7.
- **Drift detection.** See §5.

Background work (the scheduler tick, the middleware's usage counter) opens its own
short-lived DB session rather than depending on a request's session, since neither
runs inside a request's dependency-injection chain.

## 10. Deployment architecture

See [`deployment.md`](deployment.md). Local dev needs no external services (SQLite);
`docker-compose.yml` runs Postgres + backend + frontend as three containers for a
closer-to-production setup; the two apps deploy independently in production (frontend
to Vercel-like static/Node hosting, backend to any container host with a managed
Postgres instance). Schema changes are managed with Alembic (`backend/alembic/`)
rather than relying on `create_all()` once there is real data to preserve across
deploys.

## 11. From capstone prototype to product

What would still change to take this from a capstone MVP to a commercial SaaS product:

1. **Tenancy:** shared-schema → schema-per-tenant (or database-per-tenant) for
   regulated customers. Not needed at capstone scale, and the service layer is
   already written so that migration wouldn't touch business logic.
2. **Pre-built connectors:** the Salesforce/QuickBooks/SAP adapters are real,
   tested ingestion pipelines running on simulated data (see §4) — swapping in
   OAuth would mean replacing each adapter's `_simulated_*_rows()` generator with a
   real API client call, nothing downstream changes.
3. **Additional DB dialects:** the connector's dialect map already lists
   MySQL/MSSQL/Oracle; only their driver packages (`pymysql`, `pyodbc`, `cx_oracle`)
   would need adding once a real target on one of those engines exists to test
   against — PostgreSQL and SQLite are fully wired and tested today.
4. **Copilot:** the LLM-backed phrasing path (§6) is implemented but optional —
   enabling it in production is a matter of provisioning `settings.llm_api_key`.

Ingestion transports, the model registry, drift monitoring, structured logging,
per-tenant usage metrics, and Alembic migrations — all originally listed here as
future work — are implemented; see §4, §5, §9, and §10.
