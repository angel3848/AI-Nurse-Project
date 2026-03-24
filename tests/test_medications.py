import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.medication_scheduler import clear_all_reminders

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear reminders before each test."""
    clear_all_reminders()
    yield
    clear_all_reminders()


def make_reminder(overrides: dict | None = None) -> dict:
    base = {
        "patient_name": "John Doe",
        "medication_name": "Metformin",
        "dosage": "500mg",
        "frequency": "twice_daily",
        "times": ["08:00:00", "20:00:00"],
        "start_date": "2026-03-24",
        "end_date": "2026-06-24",
        "instructions": "Take with food",
    }
    if overrides:
        base.update(overrides)
    return base


class TestCreateReminder:
    def test_create_success(self):
        response = client.post("/api/v1/medications/reminders", json=make_reminder())
        assert response.status_code == 201
        data = response.json()
        assert data["medication_name"] == "Metformin"
        assert data["dosage"] == "500mg"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_with_minimal_fields(self):
        reminder = make_reminder({"instructions": ""})
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 201

    def test_create_once_daily(self):
        reminder = make_reminder({"frequency": "once_daily", "times": ["09:00:00"]})
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 201
        assert response.json()["frequency"] == "once_daily"

    def test_invalid_end_before_start(self):
        reminder = make_reminder({"start_date": "2026-06-24", "end_date": "2026-03-24"})
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 400

    def test_invalid_frequency(self):
        reminder = make_reminder({"frequency": "every_5_minutes"})
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 422

    def test_missing_medication_name(self):
        reminder = make_reminder()
        del reminder["medication_name"]
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 422

    def test_empty_times_list(self):
        reminder = make_reminder({"times": []})
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 422


class TestGetReminder:
    def test_get_existing(self):
        create = client.post("/api/v1/medications/reminders", json=make_reminder())
        reminder_id = create.json()["id"]
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["id"] == reminder_id

    def test_get_not_found(self):
        response = client.get("/api/v1/medications/reminders/nonexistent-id")
        assert response.status_code == 404


class TestListPatientMedications:
    def test_list_empty(self):
        response = client.get("/api/v1/medications/patient/Nobody")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["medications"] == []

    def test_list_with_medications(self):
        client.post("/api/v1/medications/reminders", json=make_reminder())
        client.post("/api/v1/medications/reminders", json=make_reminder({
            "medication_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "once_daily",
            "times": ["08:00:00"],
        }))
        response = client.get("/api/v1/medications/patient/John Doe")
        data = response.json()
        assert data["total"] == 2
        assert data["patient_name"] == "John Doe"
        names = [m["medication_name"] for m in data["medications"]]
        assert "Metformin" in names
        assert "Lisinopril" in names

    def test_list_filters_by_patient(self):
        client.post("/api/v1/medications/reminders", json=make_reminder())
        client.post("/api/v1/medications/reminders", json=make_reminder({"patient_name": "Jane Doe"}))
        response = client.get("/api/v1/medications/patient/John Doe")
        assert response.json()["total"] == 1


class TestCancelReminder:
    def test_cancel_success(self):
        create = client.post("/api/v1/medications/reminders", json=make_reminder())
        reminder_id = create.json()["id"]
        response = client.delete(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_not_found(self):
        response = client.delete("/api/v1/medications/reminders/nonexistent-id")
        assert response.status_code == 404

    def test_cancelled_reminder_persists(self):
        create = client.post("/api/v1/medications/reminders", json=make_reminder())
        reminder_id = create.json()["id"]
        client.delete(f"/api/v1/medications/reminders/{reminder_id}")
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
