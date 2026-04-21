import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Allergy(Base):
    __tablename__ = "allergies"
    __table_args__ = (
        Index("ix_allergies_patient_status", "patient_id", "status"),
        Index("ix_allergies_substance", "substance"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    substance: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="medication")
    criticality: Mapped[str] = mapped_column(String(30), nullable=False, default="unable-to-assess")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate")
    reaction: Mapped[str] = mapped_column(String(500), default="")
    onset: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    recorded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="allergy_records")
