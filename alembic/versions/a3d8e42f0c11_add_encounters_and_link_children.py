"""add encounters table and link to triage, vitals, symptom_check records

Revision ID: a3d8e42f0c11
Revises: 7501aeb0465b
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3d8e42f0c11"
down_revision: Union[str, None] = "7501aeb0465b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHILD_TABLES = ("triage_records", "vitals_records", "symptom_check_records")


def upgrade() -> None:
    op.create_table(
        "encounters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in-progress"),
        sa.Column("encounter_class", sa.String(length=20), nullable=False, server_default="emergency"),
        sa.Column("reason_code", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("period_start", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("disposition", sa.String(length=30), nullable=True),
        sa.Column("disposition_notes", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("opened_by", sa.String(length=36), nullable=False),
        sa.Column("closed_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_encounters_patient_id", "encounters", ["patient_id"])
    op.create_index("ix_encounters_patient_status", "encounters", ["patient_id", "status"])
    op.create_index("ix_encounters_period_start", "encounters", ["period_start"])
    op.create_index("ix_encounters_status", "encounters", ["status"])

    for table in CHILD_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("encounter_id", sa.String(length=36), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_encounter",
                "encounters",
                ["encounter_id"],
                ["id"],
            )
            batch_op.create_index(f"ix_{table}_encounter_id", ["encounter_id"])

    _backfill_encounters()


def _backfill_encounters() -> None:
    """Create one legacy encounter per (patient, calendar-day) and link existing rows."""
    conn = op.get_bind()

    # Pick an opened_by user: earliest admin, else earliest user. Skip if none.
    opener = conn.execute(
        sa.text(
            "SELECT id FROM users WHERE role = 'admin' "
            "ORDER BY created_at ASC LIMIT 1"
        )
    ).scalar()
    if opener is None:
        opener = conn.execute(
            sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
        ).scalar()
    if opener is None:
        return  # No users — fresh DB, nothing to backfill

    # Gather distinct (patient_id, day) tuples with the earliest timestamp on that day.
    rows = conn.execute(
        sa.text(
            """
            SELECT patient_id, day, MIN(ts) AS first_ts FROM (
                SELECT patient_id, DATE(created_at) AS day, created_at AS ts
                FROM triage_records
                UNION ALL
                SELECT patient_id, DATE(recorded_at) AS day, recorded_at AS ts
                FROM vitals_records
                UNION ALL
                SELECT patient_id, DATE(created_at) AS day, created_at AS ts
                FROM symptom_check_records
            ) t
            GROUP BY patient_id, day
            """
        )
    ).fetchall()

    import uuid as _uuid

    for patient_id, day, first_ts in rows:
        encounter_id = str(_uuid.uuid4())
        conn.execute(
            sa.text(
                """
                INSERT INTO encounters (
                    id, patient_id, status, encounter_class, reason_code,
                    period_start, period_end, disposition_notes,
                    opened_by, created_at, updated_at
                ) VALUES (
                    :id, :patient_id, 'completed', 'emergency', 'legacy backfill',
                    :period_start, :period_end, '',
                    :opened_by, :created_at, :updated_at
                )
                """
            ),
            {
                "id": encounter_id,
                "patient_id": patient_id,
                "period_start": first_ts,
                "period_end": first_ts,
                "opened_by": opener,
                "created_at": first_ts,
                "updated_at": first_ts,
            },
        )
        # Link all child rows from that patient on that day to this encounter
        for table, ts_col in (
            ("triage_records", "created_at"),
            ("vitals_records", "recorded_at"),
            ("symptom_check_records", "created_at"),
        ):
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET encounter_id = :eid "
                    f"WHERE patient_id = :pid AND DATE({ts_col}) = :day"
                ),
                {"eid": encounter_id, "pid": patient_id, "day": day},
            )


def downgrade() -> None:
    for table in CHILD_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_encounter_id")
            batch_op.drop_constraint(f"fk_{table}_encounter", type_="foreignkey")
            batch_op.drop_column("encounter_id")

    op.drop_index("ix_encounters_status", table_name="encounters")
    op.drop_index("ix_encounters_period_start", table_name="encounters")
    op.drop_index("ix_encounters_patient_status", table_name="encounters")
    op.drop_index("ix_encounters_patient_id", table_name="encounters")
    op.drop_table("encounters")
