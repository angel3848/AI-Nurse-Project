"""Integration tests that run against a real PostgreSQL database.

To run these tests:
  1. Start PostgreSQL: docker run -d --name test-pg -p 5433:5432 \
       -e POSTGRES_DB=ai_nurse_test -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test postgres:15-alpine
  2. Run: TEST_DATABASE_URL=postgresql://test:test@localhost:5433/ai_nurse_test pytest tests/test_integration.py -v

These tests are skipped by default unless TEST_DATABASE_URL is set to a PostgreSQL URL.
"""
import os

import pytest

# Skip entire module if no PostgreSQL URL configured
PG_URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="TEST_DATABASE_URL not set to PostgreSQL — skipping integration tests",
)

if PG_URL.startswith("postgresql"):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient

    from app.database import Base, get_db
    from app.main import app
    from app.models.user import User
    from app.utils.auth import create_access_token, hash_password

    pg_engine = create_engine(PG_URL)
    PGSession = sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)


    @pytest.fixture(scope="module", autouse=True)
    def setup_pg_tables():
        Base.metadata.create_all(bind=pg_engine)
        yield
        Base.metadata.drop_all(bind=pg_engine)


    @pytest.fixture(autouse=True)
    def clean_tables():
        """Truncate all tables between tests."""
        yield
        db = PGSession()
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
        db.commit()
        db.close()


    @pytest.fixture
    def pg_db():
        session = PGSession()
        try:
            yield session
        finally:
            session.close()


    @pytest.fixture
    def pg_client(pg_db):
        def override():
            try:
                yield pg_db
            finally:
                pass
        app.dependency_overrides[get_db] = override
        yield TestClient(app)
        app.dependency_overrides.clear()


    def pg_auth_header(user: User) -> dict:
        token = create_access_token(user.id, user.role)
        return {"Authorization": f"Bearer {token}"}


    class TestPostgresPatients:
        def test_create_and_read_patient(self, pg_client, pg_db):
            nurse = User(email="nurse@pg.com", hashed_password=hash_password("test1234"), full_name="PG Nurse", role="nurse")
            pg_db.add(nurse)
            pg_db.commit()
            pg_db.refresh(nurse)
            headers = pg_auth_header(nurse)

            resp = pg_client.post("/api/v1/patients", json={
                "full_name": "PG Patient",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            }, headers=headers)
            assert resp.status_code == 201
            pid = resp.json()["id"]

            get_resp = pg_client.get(f"/api/v1/patients/{pid}", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["full_name"] == "PG Patient"

        def test_patient_list_pagination(self, pg_client, pg_db):
            nurse = User(email="nurse2@pg.com", hashed_password=hash_password("test1234"), full_name="PG Nurse 2", role="nurse")
            pg_db.add(nurse)
            pg_db.commit()
            pg_db.refresh(nurse)
            headers = pg_auth_header(nurse)

            for i in range(5):
                pg_client.post("/api/v1/patients", json={
                    "full_name": f"Patient {i}",
                    "date_of_birth": "1990-01-01",
                    "gender": "male",
                }, headers=headers)

            resp = pg_client.get("/api/v1/patients?limit=2", headers=headers)
            data = resp.json()
            assert data["total"] == 5
            assert len(data["patients"]) == 2


    class TestPostgresTriage:
        def test_triage_persists_to_pg(self, pg_client, pg_db):
            nurse = User(email="tri@pg.com", hashed_password=hash_password("test1234"), full_name="Tri Nurse", role="nurse")
            pg_db.add(nurse)
            pg_db.commit()
            pg_db.refresh(nurse)
            headers = pg_auth_header(nurse)

            p = pg_client.post("/api/v1/patients", json={
                "full_name": "Triage PG",
                "date_of_birth": "1985-06-15",
                "gender": "female",
            }, headers=headers)
            pid = p.json()["id"]

            resp = pg_client.post("/api/v1/triage", json={
                "patient_id": pid,
                "patient_name": "Triage PG",
                "chief_complaint": "Chest pain",
                "symptoms": ["chest_pain", "shortness_of_breath"],
                "symptom_duration": "1 hour",
                "vitals": {
                    "heart_rate": 110,
                    "blood_pressure_systolic": 150,
                    "blood_pressure_diastolic": 95,
                    "temperature_c": 37.0,
                    "respiratory_rate": 22,
                    "oxygen_saturation": 94,
                },
                "pain_scale": 8,
                "age": 55,
            })
            assert resp.status_code == 200
            assert resp.json()["id"] is not None
            assert resp.json()["priority_level"] <= 2


    class TestPostgresAuth:
        def test_register_login_flow(self, pg_client):
            reg = pg_client.post("/api/v1/auth/register", json={
                "email": "flow@pg.com",
                "password": "secure1234",
                "full_name": "Flow User",
            })
            assert reg.status_code == 201

            login = pg_client.post("/api/v1/auth/login", json={
                "email": "flow@pg.com",
                "password": "secure1234",
            })
            assert login.status_code == 200
            assert "access_token" in login.json()
            assert login.json()["user"]["role"] == "patient"

        def test_json_columns_work_with_pg(self, pg_client, pg_db):
            """Verify native JSON columns serialize/deserialize correctly in PostgreSQL."""
            nurse = User(email="json@pg.com", hashed_password=hash_password("test1234"), full_name="JSON Nurse", role="nurse")
            pg_db.add(nurse)
            pg_db.commit()
            pg_db.refresh(nurse)
            headers = pg_auth_header(nurse)

            # Create patient
            p = pg_client.post("/api/v1/patients", json={
                "full_name": "JSON Patient",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            }, headers=headers)
            pid = p.json()["id"]

            # Create medication with JSON times field
            med = pg_client.post("/api/v1/medications/reminders", json={
                "patient_id": pid,
                "medication_name": "TestMed",
                "dosage": "100mg",
                "frequency": "twice_daily",
                "times": ["08:00:00", "20:00:00"],
                "start_date": "2026-03-24",
                "end_date": "2026-06-24",
            }, headers=headers)
            assert med.status_code == 201
            med_data = med.json()
            assert med_data["times"] == ["08:00:00", "20:00:00"]

            # Read it back
            get = pg_client.get(f"/api/v1/medications/reminders/{med_data['id']}", headers=headers)
            assert get.json()["times"] == ["08:00:00", "20:00:00"]
