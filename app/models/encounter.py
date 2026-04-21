import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Encounter(Base):
    __tablename__ = "encounters"
    __table_args__ = (
        Index("ix_encounters_patient_status", "patient_id", "status"),
        Index("ix_encounters_period_start", "period_start"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in-progress", index=True)
    encounter_class: Mapped[str] = mapped_column(String(20), nullable=False, default="emergency")
    reason_code: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    period_start: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    disposition_notes: Mapped[str] = mapped_column(String(2000), default="")
    opened_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="encounters")
    triage_records: Mapped[list["TriageRecord"]] = relationship(back_populates="encounter")
    vitals_records: Mapped[list["VitalsRecord"]] = relationship(back_populates="encounter")
    symptom_checks: Mapped[list["SymptomCheckRecord"]] = relationship(back_populates="encounter")
