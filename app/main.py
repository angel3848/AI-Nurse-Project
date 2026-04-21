import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.middleware.correlation import CorrelationIDMiddleware
from app.database import Base, engine
# Register all models with SQLAlchemy metadata (import-side-effect only)
from app.models import (  # noqa: F401
    audit,
    blacklisted_token,
    encounter,
    medication,
    patient,
    refresh_token,
    triage,
    user,
    vitals,
)
from app.routers import audit as audit_router
from app.routers import auth, encounters, medications, metrics, patients, symptoms
from app.routers import triage as triage_router
from app.routers import ws as ws_router
from app.routers.ws import user_manager
from app.services.event_bus import listen_user_events

BASE_DIR = Path(__file__).resolve().parent.parent
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Alembic owns production schema; auto-create is dev-only convenience.
    if settings.app_env != "production":
        Base.metadata.create_all(bind=engine)

    listener_task: asyncio.Task | None = None
    if settings.enable_realtime_events:
        listener_task = asyncio.create_task(listen_user_events(user_manager.send_to_user))

    try:
        yield
    finally:
        if listener_task is not None:
            listener_task.cancel()
            try:
                await listener_task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered digital nurse for patient triage, symptom checking, health metrics, and medication reminders.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIDMiddleware)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth.router)
app.include_router(metrics.router)
app.include_router(triage_router.router)
app.include_router(symptoms.router)
app.include_router(medications.router)
app.include_router(patients.router)
app.include_router(encounters.router)
app.include_router(audit_router.router)
app.include_router(ws_router.router)


@app.get("/", response_class=HTMLResponse)
def serve_frontend() -> HTMLResponse:
    """Serve the frontend application."""
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/audit", response_class=HTMLResponse)
def serve_audit_viewer() -> HTMLResponse:
    """Serve the audit log viewer UI. Data access still gated by admin role."""
    html_path = BASE_DIR / "templates" / "audit.html"
    return HTMLResponse(content=html_path.read_text())
