"""add allergies table and backfill from Patient.allergies JSON

Revision ID: b6e21f73a890
Revises: a3d8e42f0c11
Create Date: 2026-04-21 00:10:00.000000

"""
import json
import uuid as _uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6e21f73a890"
down_revision: Union[str, None] = "a3d8e42f0c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "allergies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("substance", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="medication"),
        sa.Column("criticality", sa.String(length=30), nullable=False, server_default="unable-to-assess"),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="moderate"),
        sa.Column("reaction", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("onset", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allergies_patient_id", "allergies", ["patient_id"])
    op.create_index("ix_allergies_patient_status", "allergies", ["patient_id", "status"])
    op.create_index("ix_allergies_status", "allergies", ["status"])
    op.create_index("ix_allergies_substance", "allergies", ["substance"])

    _backfill_from_patient_json()


def _backfill_from_patient_json() -> None:
    """Create one Allergy row per string in each patient's legacy JSON list."""
    conn = op.get_bind()

    # Pick a recording user: earliest admin, else earliest user. Skip if none.
    recorder = conn.execute(
        sa.text("SELECT id FROM users WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1")
    ).scalar()
    if recorder is None:
        recorder = conn.execute(
            sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
        ).scalar()
    if recorder is None:
        return

    rows = conn.execute(
        sa.text("SELECT id, allergies FROM patients WHERE allergies IS NOT NULL")
    ).fetchall()

    for patient_id, allergies_raw in rows:
        if allergies_raw is None:
            continue
        # Postgres JSON returns native list; SQLite stores as text
        if isinstance(allergies_raw, str):
            try:
                items = json.loads(allergies_raw)
            except (ValueError, TypeError):
                continue
        else:
            items = allergies_raw
        if not isinstance(items, list):
            continue

        for entry in items:
            substance = str(entry).strip() if entry is not None else ""
            if not substance:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO allergies (
                        id, patient_id, substance, category, criticality, severity,
                        reaction, status, notes, recorded_by
                    ) VALUES (
                        :id, :pid, :sub, 'medication', 'unable-to-assess', 'moderate',
                        '', 'active', 'backfilled from legacy JSON list', :rec
                    )
                    """
                ),
                {
                    "id": str(_uuid.uuid4()),
                    "pid": patient_id,
                    "sub": substance[:200],
                    "rec": recorder,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_allergies_substance", table_name="allergies")
    op.drop_index("ix_allergies_status", table_name="allergies")
    op.drop_index("ix_allergies_patient_status", table_name="allergies")
    op.drop_index("ix_allergies_patient_id", table_name="allergies")
    op.drop_table("allergies")
