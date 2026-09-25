# Deployment Guide

## Local development (no Docker)

```bash
# Backend
cd backend
python -m venv ../.venv
../.venv/Scripts/activate        # Windows; use `source ../.venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python scripts/download_datasets.py    # one-time: fetches the public datasets into data/raw
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Backend defaults to SQLite (`backend/platform.db`) — zero extra infrastructure needed.
Copy `backend/.env.example` to `backend/.env` to override any setting.

## Docker Compose (Postgres-backed)

```bash
docker compose up --build
```

This starts three services: `db` (Postgres 16), `backend` (FastAPI on :8000), and
`frontend` (Next.js on :3000). The backend picks up `DATABASE_URL` from the compose
file automatically and switches from SQLite to Postgres with no code changes — the
ORM layer (SQLAlchemy) and schema are database-agnostic.

## Production deployment

The two services deploy independently:

- **Frontend** → Vercel (or any static/Node host). Set `NEXT_PUBLIC_API_BASE_URL` to
  the deployed backend's URL.
- **Backend** → any container host (Render, Railway, Oracle Cloud, Fly.io, AWS ECS),
  **or Vercel itself** (see below). Either way, provide `DATABASE_URL` pointing at a
  managed Postgres instance and a strong `SECRET_KEY`.

Before a real production deployment, run Alembic migrations instead of relying on
the MVP `Base.metadata.create_all()` bootstrap still used for local dev convenience
(`app/main.py` runs both — `create_all()` is a no-op once Alembic has already
created the tables), and switch bcrypt/JWT secrets to values pulled from a secrets
manager rather than `.env`.

### Deploying both services to Vercel, with Supabase as the database

Vercel's Python runtime now runs a full FastAPI app as a Vercel Function (Fluid
compute), so both halves of the platform can live on the same host:

1. **Database — Supabase.** Create a Supabase project, then copy its Postgres
   connection string (Project Settings → Database → Connection string, "URI"
   format — use the *pooled* `pgbouncer` connection string, port 6543, since each
   serverless invocation opens a new connection). Run migrations against it once
   from a machine that can reach it: `DATABASE_URL=<supabase-uri> alembic upgrade head`.
2. **Backend project.** Import the repo into a new Vercel project with **Root
   Directory** set to `backend`. Vercel auto-detects `app/main.py`'s `app` object —
   no build config needed beyond `backend/vercel.json` (already in the repo, sets
   `maxDuration` and the cron schedule below). Set these environment variables on
   the project: `DATABASE_URL` (the Supabase URI from step 1), `SECRET_KEY`,
   `ENABLE_INPROCESS_SCHEDULER=false`, and `CRON_SECRET` (any random 16+ character
   string — Vercel automatically sends it back as an `Authorization: Bearer`
   header on every cron invocation, which `GET /api/internal/cron-tick` checks).
3. **Scheduled jobs on Vercel.** The in-process 60-second scheduler
   (`app/core/scheduler.py`) can't run on a serverless platform — there's no
   persistent process for it to tick in. `backend/vercel.json` instead defines a
   Vercel Cron Job that calls `GET /api/internal/cron-tick` once a day
   (`0 3 * * *` UTC), which runs the identical due-jobs sweep
   (`scheduler.run_tick_now()`). This is a real behavioural difference from local
   dev's 60-second tick: on Vercel's free Hobby plan, cron jobs are restricted to
   once per day with imprecise timing (Vercel's own limit, not this app's) — a
   scheduled sync/retrain job set to run "every 2 hours" will instead run once
   daily. The Pro plan allows per-minute cron scheduling if that granularity is
   ever needed.
4. **Frontend project.** Import the same repo again as a second Vercel project,
   Root Directory `frontend` (zero-config Next.js). Set
   `NEXT_PUBLIC_API_BASE_URL` to the backend project's deployed URL from step 2.

## Database migrations (Alembic)

```bash
cd backend
alembic upgrade head          # apply all migrations to whatever DATABASE_URL points at
alembic revision --autogenerate -m "describe the change"   # after editing app/models/*
alembic downgrade -1          # roll back one migration
```

`alembic/env.py` reads `DATABASE_URL` from the same settings the app itself uses
(`app/core/config.py`), so pointing `DATABASE_URL` at Postgres before running
`alembic upgrade head` creates the schema there with no code changes.

## Re-seeding demo data

`backend/scripts/seed_demo_org.py` creates a demo organization, ingests every public
dataset, trains every model, and writes the resulting metrics to
`report/chapter4_results.json`. Safe to re-run — it's idempotent on the organization
row (matches by name) though re-running will re-ingest and duplicate transactional
rows, so use a fresh database for a clean report run:

```bash
rm backend/platform.db
python backend/scripts/seed_demo_org.py
```
