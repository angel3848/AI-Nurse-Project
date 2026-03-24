import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TriageRecord(Base):
    __tablename__ = "triage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    chief_complaint: Mapped[str] = mapped_column(String(1000), nullable=False)
    symptoms: Mapped[str] = mapped_column(String(2000), nullable=False)  # JSON string
    symptom_duration: Mapped[str] = mapped_column(String(200), nullable=False)
    pain_scale: Mapped[int] = mapped_column(Integer, nullable=False)
    heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    bp_systolic: Mapped[int] = mapped_column(Integer, nullable=False)
    bp_diastolic: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    respiratory_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    oxygen_saturation: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_level: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_label: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(500), nullable=False)
    flags: Mapped[str] = mapped_column(String(2000), nullable=False)  # JSON string
    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="triage_records")


class SymptomCheckRecord(Base):
    __tablename__ = "symptom_check_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    symptoms: Mapped[str] = mapped_column(String(2000), nullable=False)  # JSON string
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions_found: Mapped[str] = mapped_column(String(2000), nullable=False)  # JSON string
    recommended_action: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="symptom_checks")
