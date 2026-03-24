from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import audit, medication, patient, triage, user, vitals  # noqa: F401 — register models
from app.routers import audit as audit_router
from app.routers import auth, medications, metrics, patients, symptoms
from app.routers import triage as triage_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered digital nurse for patient triage, symptom checking, health metrics, and medication reminders.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(metrics.router)
app.include_router(triage_router.router)
app.include_router(symptoms.router)
app.include_router(medications.router)
app.include_router(patients.router)
app.include_router(audit_router.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}
