from tests.conftest import auth_header, create_test_user


def create_patient(client, headers, name="John Doe") -> str:
    """Helper to create a patient and return their ID."""
    response = client.post(
        "/api/v1/patients",
        json={
            "full_name": name,
            "date_of_birth": "1990-05-15",
            "gender": "male",
        },
        headers=headers,
    )
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
    def test_create_success(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid), headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["medication_name"] == "Metformin"
        assert data["dosage"] == "500mg"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_once_daily(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.post(
            "/api/v1/medications/reminders",
            json=make_reminder(
                pid,
                {
                    "frequency": "once_daily",
                    "times": ["09:00:00"],
                },
            ),
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["frequency"] == "once_daily"

    def test_invalid_end_before_start(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.post(
            "/api/v1/medications/reminders",
            json=make_reminder(
                pid,
                {
                    "start_date": "2026-06-24",
                    "end_date": "2026-03-24",
                },
            ),
            headers=headers,
        )
        assert response.status_code == 400

    def test_invalid_frequency(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.post(
            "/api/v1/medications/reminders",
            json=make_reminder(
                pid,
                {
                    "frequency": "every_5_minutes",
                },
            ),
            headers=headers,
        )
        assert response.status_code == 422

    def test_missing_medication_name(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        reminder = make_reminder(pid)
        del reminder["medication_name"]
        response = client.post("/api/v1/medications/reminders", json=reminder, headers=headers)
        assert response.status_code == 422

    def test_empty_times_list(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.post("/api/v1/medications/reminders", json=make_reminder(pid, {"times": []}), headers=headers)
        assert response.status_code == 422


class TestGetReminder:
    def test_get_existing(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid), headers=headers)
        reminder_id = create.json()["id"]
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == reminder_id

    def test_get_not_found(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/medications/reminders/nonexistent-id", headers=auth_header(user))
        assert response.status_code == 404


class TestListPatientMedications:
    def test_list_nonexistent_patient(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/medications/patient/nonexistent-id", headers=auth_header(user))
        assert response.status_code == 404

    def test_list_empty(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        response = client.get(f"/api/v1/medications/patient/{pid}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["medications"] == []

    def test_list_with_medications(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        client.post("/api/v1/medications/reminders", json=make_reminder(pid), headers=headers)
        client.post(
            "/api/v1/medications/reminders",
            json=make_reminder(
                pid,
                {
                    "medication_name": "Lisinopril",
                    "dosage": "10mg",
                    "frequency": "once_daily",
                    "times": ["08:00:00"],
                },
            ),
            headers=headers,
        )
        response = client.get(f"/api/v1/medications/patient/{pid}", headers=headers)
        data = response.json()
        assert data["total"] == 2
        names = [m["medication_name"] for m in data["medications"]]
        assert "Metformin" in names
        assert "Lisinopril" in names

    def test_list_filters_by_patient(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid1 = create_patient(client, headers, "Patient A")
        pid2 = create_patient(client, headers, "Patient B")
        client.post("/api/v1/medications/reminders", json=make_reminder(pid1), headers=headers)
        client.post("/api/v1/medications/reminders", json=make_reminder(pid2), headers=headers)
        response = client.get(f"/api/v1/medications/patient/{pid1}", headers=headers)
        assert response.json()["total"] == 1


class TestCancelReminder:
    def test_cancel_success(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid), headers=headers)
        reminder_id = create.json()["id"]
        response = client.delete(f"/api/v1/medications/reminders/{reminder_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_not_found(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.delete("/api/v1/medications/reminders/nonexistent-id", headers=auth_header(nurse))
        assert response.status_code == 404

    def test_cancelled_reminder_persists(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = create_patient(client, headers)
        create = client.post("/api/v1/medications/reminders", json=make_reminder(pid), headers=headers)
        reminder_id = create.json()["id"]
        client.delete(f"/api/v1/medications/reminders/{reminder_id}", headers=headers)
        response = client.get(f"/api/v1/medications/reminders/{reminder_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
