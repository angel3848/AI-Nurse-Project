from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import medications, metrics, symptoms, triage

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered digital nurse for patient triage, symptom checking, health metrics, and medication reminders.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(triage.router)
app.include_router(symptoms.router)
app.include_router(medications.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}
