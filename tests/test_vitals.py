from tests.conftest import auth_header, create_test_user
from app.services.vitals_assessor import assess_reading, assess_all_vitals

NORMAL_VITALS = {
    "patient_id": "placeholder",
    "heart_rate": 75,
    "blood_pressure_systolic": 115,
    "blood_pressure_diastolic": 75,
    "temperature_c": 36.8,
    "respiratory_rate": 16,
    "oxygen_saturation": 98,
}


def setup_patient_and_nurse(client, db):
    nurse = create_test_user(db, role="nurse")
    headers = auth_header(nurse)
    resp = client.post(
        "/api/v1/patients",
        json={
            "full_name": "Vitals Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        },
        headers=headers,
    )
    return nurse, headers, resp.json()["id"]


class TestAssessReading:
    def test_normal_heart_rate(self):
        r = assess_reading("heart_rate", 75)
        assert r.status == "normal"

    def test_elevated_heart_rate(self):
        r = assess_reading("heart_rate", 110)
        assert r.status == "elevated"

    def test_critical_high_heart_rate(self):
        r = assess_reading("heart_rate", 160)
        assert r.status == "critical_high"

    def test_normal_temperature(self):
        r = assess_reading("temperature_c", 36.8)
        assert r.status == "normal"

    def test_fever(self):
        r = assess_reading("temperature_c", 38.5)
        assert r.status == "fever"

    def test_high_fever(self):
        r = assess_reading("temperature_c", 39.5)
        assert r.status == "high_fever"

    def test_normal_o2(self):
        r = assess_reading("oxygen_saturation", 97)
        assert r.status == "normal"

    def test_critical_low_o2(self):
        r = assess_reading("oxygen_saturation", 85)
        assert r.status == "critical_low"

    def test_normal_glucose(self):
        r = assess_reading("blood_glucose_mg_dl", 90)
        assert r.status == "normal"

    def test_high_glucose(self):
        r = assess_reading("blood_glucose_mg_dl", 200)
        assert r.status == "high"


class TestAssessAllVitals:
    def test_all_normal(self):
        readings, alerts = assess_all_vitals(75, 115, 75, 36.8, 16, 98)
        assert all(r.status == "normal" for r in readings.values())
        assert alerts == []

    def test_with_alerts(self):
        readings, alerts = assess_all_vitals(160, 115, 75, 39.5, 16, 85)
        assert len(alerts) > 0

    def test_with_glucose(self):
        readings, alerts = assess_all_vitals(75, 115, 75, 36.8, 16, 98, blood_glucose_mg_dl=90)
        assert "blood_glucose_mg_dl" in readings


class TestRecordVitalsEndpoint:
    def test_record_success(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        vitals = {**NORMAL_VITALS, "patient_id": pid}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "readings" in data
        assert data["readings"]["heart_rate"]["status"] == "normal"
        assert data["alerts"] == []
        assert data["recorded_by"] == nurse.id

    def test_record_with_alerts(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        vitals = {**NORMAL_VITALS, "patient_id": pid, "heart_rate": 160, "oxygen_saturation": 85}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data["alerts"]) > 0

    def test_record_with_glucose(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        vitals = {**NORMAL_VITALS, "patient_id": pid, "blood_glucose_mg_dl": 130}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=headers)
        assert response.status_code == 201
        assert "blood_glucose_mg_dl" in response.json()["readings"]

    def test_record_patient_not_found(self, client, db):
        nurse = create_test_user(db, role="nurse")
        vitals = {**NORMAL_VITALS, "patient_id": "nonexistent"}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=auth_header(nurse))
        assert response.status_code == 404

    def test_patient_cannot_record_vitals(self, client, db):
        patient_user = create_test_user(db, role="patient")
        vitals = {**NORMAL_VITALS, "patient_id": "some-id"}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=auth_header(patient_user))
        assert response.status_code == 403

    def test_validation_invalid_heart_rate(self, client, db):
        nurse = create_test_user(db, role="nurse")
        vitals = {**NORMAL_VITALS, "patient_id": "x", "heart_rate": 0}
        response = client.post("/api/v1/metrics/vitals", json=vitals, headers=auth_header(nurse))
        assert response.status_code == 422


class TestVitalsHistory:
    def test_empty_history(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        response = client.get(f"/api/v1/metrics/vitals/{pid}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["records"] == []

    def test_history_with_records(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        client.post("/api/v1/metrics/vitals", json={**NORMAL_VITALS, "patient_id": pid}, headers=headers)
        client.post(
            "/api/v1/metrics/vitals", json={**NORMAL_VITALS, "patient_id": pid, "heart_rate": 90}, headers=headers
        )
        response = client.get(f"/api/v1/metrics/vitals/{pid}", headers=headers)
        data = response.json()
        assert data["total"] == 2
        assert len(data["records"]) == 2

    def test_history_patient_not_found(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/metrics/vitals/nonexistent", headers=auth_header(user))
        assert response.status_code == 404

    def test_history_requires_auth(self, client):
        response = client.get("/api/v1/metrics/vitals/some-id")
        assert response.status_code == 401

    def test_history_pagination(self, client, db):
        nurse, headers, pid = setup_patient_and_nurse(client, db)
        for _ in range(5):
            client.post("/api/v1/metrics/vitals", json={**NORMAL_VITALS, "patient_id": pid}, headers=headers)
        response = client.get(f"/api/v1/metrics/vitals/{pid}?limit=2", headers=headers)
        data = response.json()
        assert data["total"] == 5
        assert len(data["records"]) == 2
