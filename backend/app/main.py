from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    bi,
    copilot,
    fraud,
    integrations,
    inventory,
    maintenance,
    model_registry,
    organizations,
    webhooks_public,
    workforce,
)
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.middleware import RequestLoggingMiddleware
from app.core.scheduler import run_tick_now, start_scheduler, stop_scheduler
import app.models  # noqa: F401  (import registers all tables on Base.metadata)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP schema bootstrap. A production deployment should switch to Alembic
    # migrations (backend/alembic/) instead of create_all (see docs/deployment.md).
    Base.metadata.create_all(bind=engine)
    if settings.enable_inprocess_scheduler:
        start_scheduler()
    yield
    if settings.enable_inprocess_scheduler:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/internal/cron-tick")
def cron_tick(request: Request, secret: str | None = None):
    """Runs the same due-jobs sweep as the in-process scheduler's 60-second
    tick (app/core/scheduler.py::_tick), triggered instead by a Vercel Cron
    Job — see docs/deployment.md. Only meaningful when
    ENABLE_INPROCESS_SCHEDULER=false; requires CRON_SECRET to be set so the
    endpoint can't be triggered by anyone who finds the URL. Vercel sends
    CRON_SECRET as an Authorization: Bearer header automatically; the
    `secret` query param is a fallback for manual testing.
    """
    if not settings.cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    authorized = request.headers.get("authorization") == f"Bearer {settings.cron_secret}" or secret == settings.cron_secret
    if not authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")
    run_tick_now()
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(bi.router)
app.include_router(inventory.router)
app.include_router(fraud.router)
app.include_router(maintenance.router)
app.include_router(workforce.router)
app.include_router(copilot.router)
app.include_router(integrations.router)
app.include_router(webhooks_public.router)
app.include_router(model_registry.router)
