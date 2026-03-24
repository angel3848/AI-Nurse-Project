import pytest


def create_patient(client, name="John Doe") -> str:
    """Helper to create a patient and return their ID."""
    response = client.post("/api/v1/patients", json={
        "full_name": name,
        "date_of_birth": "1990-05-15",
        "gender": "male",
    })
    return response.json()["id"]


def make_reminder(patient_id: str, overrides: dict | None = None) -> dict:
    base = {
        "patient_id": patient_id,
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
    def test_create_success(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid))
        assert response.status_code == 201
        data = response.json()
        assert data["medication_name"] == "Metformin"
        assert data["dosage"] == "500mg"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_with_minimal_fields(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {"instructions": ""}))
        assert response.status_code == 201

    def test_create_once_daily(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {
            "frequency": "once_daily",
            "times": ["09:00:00"],
        }))
        assert response.status_code == 201
        assert response.json()["frequency"] == "once_daily"

    def test_invalid_end_before_start(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {
            "start_date": "2026-06-24",
            "end_date": "2026-03-24",
        }))
        assert response.status_code == 400

    def test_invalid_frequency(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {
            "frequency": "every_5_minutes",
        }))
        assert response.status_code == 422

    def test_missing_medication_name(self, client):
        pid = create_patient(client)
        reminder = make_reminder(pid)
        del reminder["medication_name"]
        response = client.post("/api/v1/medications/reminders", json=reminder)
        assert response.status_code == 422

    def test_empty_times_list(self, client):
        pid = create_patient(client)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {"times": []}))
        assert response.status_code == 422


class TestGetReminder:
    def test_get_existing(self, client):
        pid = create_patient(client)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid))
        reminder_id = create.json()["id"]
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["id"] == reminder_id

    def test_get_not_found(self, client):
        response = client.get("/api/v1/medications/reminders/nonexistent-id")
        assert response.status_code == 404


class TestListPatientMedications:
    def test_list_empty(self, client):
        response = client.get("/api/v1/medications/patient/nonexistent-id")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["medications"] == []

    def test_list_with_medications(self, client):
        pid = create_patient(client)
        client.post("/api/v1/medications/reminders", json=make_reminder(pid))
        client.post("/api/v1/medications/reminders", json=make_reminder(pid, {
            "medication_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "once_daily",
            "times": ["08:00:00"],
        }))
        response = client.get(f"/api/v1/medications/patient/{pid}")
        data = response.json()
        assert data["total"] == 2
        names = [m["medication_name"] for m in data["medications"]]
        assert "Metformin" in names
        assert "Lisinopril" in names

    def test_list_filters_by_patient(self, client):
        pid1 = create_patient(client, "Patient A")
        pid2 = create_patient(client, "Patient B")
        client.post("/api/v1/medications/reminders", json=make_reminder(pid1))
        client.post("/api/v1/medications/reminders", json=make_reminder(pid2))
        response = client.get(f"/api/v1/medications/patient/{pid1}")
        assert response.json()["total"] == 1


class TestCancelReminder:
    def test_cancel_success(self, client):
        pid = create_patient(client)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid))
        reminder_id = create.json()["id"]
        response = client.delete(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_not_found(self, client):
        response = client.delete("/api/v1/medications/reminders/nonexistent-id")
        assert response.status_code == 404

    def test_cancelled_reminder_persists(self, client):
        pid = create_patient(client)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid))
        reminder_id = create.json()["id"]
        client.delete(f"/api/v1/medications/reminders/{reminder_id}")
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
