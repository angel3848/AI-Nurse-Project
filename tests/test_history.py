from tests.conftest import auth_header, create_test_user

NORMAL_VITALS = {
    "heart_rate": 75,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "temperature_c": 36.8,
    "respiratory_rate": 16,
    "oxygen_saturation": 98,
}


def setup_patient(client, db):
    """Create a nurse and patient, return (headers, patient_id)."""
    nurse = create_test_user(db, role="nurse")
    headers = auth_header(nurse)
    resp = client.post("/api/v1/patients", json={
        "full_name": "History Patient",
        "date_of_birth": "1990-01-01",
        "gender": "male",
    }, headers=headers)
    return headers, resp.json()["id"]


class TestTriagePersistence:
    def test_triage_without_patient_id(self, client, db):
        response = client.post("/api/v1/triage", json={
            "patient_name": "Anonymous",
            "chief_complaint": "Headache",
            "symptoms": ["headache"],
            "symptom_duration": "2 hours",
            "vitals": NORMAL_VITALS,
            "pain_scale": 3,
            "age": 35,
        })
        assert response.status_code == 200
        assert response.json()["id"] is None

    def test_triage_with_patient_id_persists(self, client, db):
        headers, pid = setup_patient(client, db)
        response = client.post("/api/v1/triage", json={
            "patient_id": pid,
            "patient_name": "History Patient",
            "chief_complaint": "Chest pain",
            "symptoms": ["chest_pain"],
            "symptom_duration": "30 minutes",
            "vitals": NORMAL_VITALS,
            "pain_scale": 7,
            "age": 35,
        })
        assert response.status_code == 200
        assert response.json()["id"] is not None


class TestSymptomPersistence:
    def test_symptom_without_patient_id(self, client, db):
        response = client.post("/api/v1/symptoms/check", json={
            "symptoms": ["headache", "fatigue"],
            "duration_days": 3,
            "severity": "mild",
            "age": 35,
        })
        assert response.status_code == 200
        assert response.json()["id"] is None

    def test_symptom_with_patient_id_persists(self, client, db):
        headers, pid = setup_patient(client, db)
        response = client.post("/api/v1/symptoms/check", json={
            "patient_id": pid,
            "symptoms": ["fever", "cough", "fatigue"],
            "duration_days": 2,
            "severity": "moderate",
            "age": 35,
        })
        assert response.status_code == 200
        assert response.json()["id"] is not None


class TestPatientHistory:
    def test_empty_history(self, client, db):
        headers, pid = setup_patient(client, db)
        response = client.get(f"/api/v1/patients/{pid}/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["records"] == []
        assert data["patient_name"] == "History Patient"

    def test_history_with_triage(self, client, db):
        headers, pid = setup_patient(client, db)
        client.post("/api/v1/triage", json={
            "patient_id": pid,
            "patient_name": "History Patient",
            "chief_complaint": "Severe headache",
            "symptoms": ["headache"],
            "symptom_duration": "4 hours",
            "vitals": NORMAL_VITALS,
            "pain_scale": 6,
            "age": 35,
        })
        response = client.get(f"/api/v1/patients/{pid}/history", headers=headers)
        data = response.json()
        assert data["total"] == 1
        record = data["records"][0]
        assert record["record_type"] == "triage"
        assert "Severe headache" in record["summary"]
        assert record["details"]["pain_scale"] == 6

    def test_history_with_symptom_check(self, client, db):
        headers, pid = setup_patient(client, db)
        client.post("/api/v1/symptoms/check", json={
            "patient_id": pid,
            "symptoms": ["fever", "cough", "fatigue", "body_aches"],
            "duration_days": 2,
            "severity": "moderate",
            "age": 35,
        })
        response = client.get(f"/api/v1/patients/{pid}/history", headers=headers)
        data = response.json()
        assert data["total"] == 1
        record = data["records"][0]
        assert record["record_type"] == "symptom_check"
        assert "urgency" in record["details"]

    def test_history_mixed_records(self, client, db):
        headers, pid = setup_patient(client, db)
        # Add triage
        client.post("/api/v1/triage", json={
            "patient_id": pid,
            "patient_name": "History Patient",
            "chief_complaint": "Back pain",
            "symptoms": ["back_pain"],
            "symptom_duration": "1 day",
            "vitals": NORMAL_VITALS,
            "pain_scale": 4,
            "age": 35,
        })
        # Add symptom check
        client.post("/api/v1/symptoms/check", json={
            "patient_id": pid,
            "symptoms": ["nausea", "vomiting", "diarrhea"],
            "duration_days": 1,
            "severity": "moderate",
            "age": 35,
        })
        response = client.get(f"/api/v1/patients/{pid}/history", headers=headers)
        data = response.json()
        assert data["total"] == 2
        types = {r["record_type"] for r in data["records"]}
        assert types == {"triage", "symptom_check"}

    def test_history_filter_by_type(self, client, db):
        headers, pid = setup_patient(client, db)
        # Add both types
        client.post("/api/v1/triage", json={
            "patient_id": pid,
            "patient_name": "History Patient",
            "chief_complaint": "Cough",
            "symptoms": ["cough"],
            "symptom_duration": "3 days",
            "vitals": NORMAL_VITALS,
            "pain_scale": 2,
            "age": 35,
        })
        client.post("/api/v1/symptoms/check", json={
            "patient_id": pid,
            "symptoms": ["headache", "nausea", "light_sensitivity"],
            "duration_days": 1,
            "severity": "severe",
            "age": 35,
        })
        # Filter triage only
        response = client.get(f"/api/v1/patients/{pid}/history?record_type=triage", headers=headers)
        data = response.json()
        assert data["total"] == 1
        assert data["records"][0]["record_type"] == "triage"

        # Filter symptom_check only
        response = client.get(f"/api/v1/patients/{pid}/history?record_type=symptom_check", headers=headers)
        data = response.json()
        assert data["total"] == 1
        assert data["records"][0]["record_type"] == "symptom_check"

    def test_history_pagination(self, client, db):
        headers, pid = setup_patient(client, db)
        for i in range(5):
            client.post("/api/v1/triage", json={
                "patient_id": pid,
                "patient_name": "History Patient",
                "chief_complaint": f"Complaint {i}",
                "symptoms": ["headache"],
                "symptom_duration": "1 hour",
                "vitals": NORMAL_VITALS,
                "pain_scale": 2,
                "age": 35,
            })
        response = client.get(f"/api/v1/patients/{pid}/history?limit=2&offset=0", headers=headers)
        data = response.json()
        assert data["total"] == 5
        assert len(data["records"]) == 2

    def test_history_not_found(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/patients/nonexistent/history", headers=auth_header(user))
        assert response.status_code == 404

    def test_history_requires_auth(self, client):
        response = client.get("/api/v1/patients/some-id/history")
        assert response.status_code == 401

    def test_triage_details_contain_vitals(self, client, db):
        headers, pid = setup_patient(client, db)
        client.post("/api/v1/triage", json={
            "patient_id": pid,
            "patient_name": "History Patient",
            "chief_complaint": "Fever",
            "symptoms": ["fever"],
            "symptom_duration": "1 day",
            "vitals": {**NORMAL_VITALS, "temperature_c": 39.5},
            "pain_scale": 4,
            "age": 35,
        })
        response = client.get(f"/api/v1/patients/{pid}/history", headers=headers)
        details = response.json()["records"][0]["details"]
        assert "vitals" in details
        assert details["vitals"]["temperature_c"] == 39.5
        assert details["vitals"]["heart_rate"] == 75
