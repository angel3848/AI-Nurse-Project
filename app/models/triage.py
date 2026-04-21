import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TriageRecord(Base):
    __tablename__ = "triage_records"
    __table_args__ = (
        Index("ix_triage_status_priority_created", "status", "priority_level", "created_at"),
        Index("ix_triage_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    chief_complaint: Mapped[str] = mapped_column(String(1000), nullable=False)
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False)
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
    flags: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="triage_records")
    encounter: Mapped["Encounter | None"] = relationship(back_populates="triage_records")


class SymptomCheckRecord(Base):
    __tablename__ = "symptom_check_records"
    __table_args__ = (Index("ix_symptom_check_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions_found: Mapped[list] = mapped_column(JSON, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="symptom_checks")
    encounter: Mapped["Encounter | None"] = relationship(back_populates="symptom_checks")
