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
- **Backend** → any container host (Render, Railway, Oracle Cloud, Fly.io, AWS ECS).
  Provide `DATABASE_URL` pointing at a managed Postgres instance and a strong
  `SECRET_KEY`.

Before a real production deployment, run Alembic migrations instead of relying on
the MVP `Base.metadata.create_all()` bootstrap still used for local dev convenience
(`app/main.py` runs both — `create_all()` is a no-op once Alembic has already
created the tables), and switch bcrypt/JWT secrets to values pulled from a secrets
manager rather than `.env`.

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
