import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VitalsRecord(Base):
    __tablename__ = "vitals_records"
    __table_args__ = (Index("ix_vitals_recorded_at", "recorded_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    recorded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    bp_systolic: Mapped[int] = mapped_column(Integer, nullable=False)
    bp_diastolic: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    respiratory_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    oxygen_saturation: Mapped[int] = mapped_column(Integer, nullable=False)
    blood_glucose_mg_dl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    assessments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="vitals_records")
