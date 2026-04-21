import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    allergies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(back_populates="patient", foreign_keys=[user_id])
    medications: Mapped[list["MedicationReminderModel"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    triage_records: Mapped[list["TriageRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    symptom_checks: Mapped[list["SymptomCheckRecord"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    vitals_records: Mapped[list["VitalsRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    allergy_records: Mapped[list["Allergy"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
