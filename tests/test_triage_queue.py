from tests.conftest import auth_header, create_test_user

NORMAL_VITALS = {
    "heart_rate": 75,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "temperature_c": 36.8,
    "respiratory_rate": 16,
    "oxygen_saturation": 98,
}


def setup_with_triage(client, db, chief_complaint="Headache", pain_scale=3):
    """Create nurse, patient, and a triage record. Return (headers, patient_id, triage_id)."""
    nurse = create_test_user(db, role="nurse", email=f"nurse-{chief_complaint}@test.com")
    headers = auth_header(nurse)
    p_resp = client.post("/api/v1/patients", json={
        "full_name": f"Patient {chief_complaint}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
    }, headers=headers)
    pid = p_resp.json()["id"]

    t_resp = client.post("/api/v1/triage", json={
        "patient_id": pid,
        "patient_name": f"Patient {chief_complaint}",
        "chief_complaint": chief_complaint,
        "symptoms": ["headache"],
        "symptom_duration": "2 hours",
        "vitals": NORMAL_VITALS,
        "pain_scale": pain_scale,
        "age": 35,
    })
    tid = t_resp.json()["id"]
    return nurse, headers, pid, tid


class TestTriageQueue:
    def test_empty_queue(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.get("/api/v1/triage/queue", headers=auth_header(nurse))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["queue"] == []

    def test_queue_with_patients(self, client, db):
        nurse, headers, _, _ = setup_with_triage(client, db, "Back pain", 4)
        # Need a second nurse with different email for the second triage
        nurse2 = create_test_user(db, role="nurse", email="nurse2@test.com")
        headers2 = auth_header(nurse2)
        p2 = client.post("/api/v1/patients", json={
            "full_name": "Patient 2",
            "date_of_birth": "1985-01-01",
            "gender": "female",
        }, headers=headers2)
        client.post("/api/v1/triage", json={
            "patient_id": p2.json()["id"],
            "patient_name": "Patient 2",
            "chief_complaint": "Chest pain",
            "symptoms": ["chest_pain"],
            "symptom_duration": "30 min",
            "vitals": NORMAL_VITALS,
            "pain_scale": 8,
            "age": 55,
        })

        response = client.get("/api/v1/triage/queue", headers=headers)
        data = response.json()
        assert data["total"] == 2
        # Higher priority (lower number) should be first
        assert data["queue"][0]["priority_level"] <= data["queue"][1]["priority_level"]

    def test_queue_sorted_by_priority(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)

        # Create 3 patients with different severities
        for i, (complaint, pain) in enumerate([("Mild headache", 2), ("Severe chest pain", 9), ("Moderate pain", 5)]):
            p = client.post("/api/v1/patients", json={
                "full_name": f"Patient {i}",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            }, headers=headers)
            client.post("/api/v1/triage", json={
                "patient_id": p.json()["id"],
                "patient_name": f"Patient {i}",
                "chief_complaint": complaint,
                "symptoms": ["chest_pain"] if pain > 7 else ["headache"],
                "symptom_duration": "1 hour",
                "vitals": NORMAL_VITALS,
                "pain_scale": pain,
                "age": 35,
            })

        response = client.get("/api/v1/triage/queue", headers=headers)
        levels = [item["priority_level"] for item in response.json()["queue"]]
        assert levels == sorted(levels)

    def test_queue_has_wait_time(self, client, db):
        nurse, headers, _, _ = setup_with_triage(client, db)
        response = client.get("/api/v1/triage/queue", headers=headers)
        item = response.json()["queue"][0]
        assert "wait_time_minutes" in item
        assert item["wait_time_minutes"] >= 0

    def test_queue_has_required_fields(self, client, db):
        nurse, headers, _, _ = setup_with_triage(client, db)
        response = client.get("/api/v1/triage/queue", headers=headers)
        item = response.json()["queue"][0]
        assert "id" in item
        assert "patient_id" in item
        assert "patient_name" in item
        assert "priority_level" in item
        assert "priority_label" in item
        assert "priority_color" in item
        assert "chief_complaint" in item
        assert "created_at" in item

    def test_queue_filter_by_status(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        # Move to in_progress
        client.put(f"/api/v1/triage/{tid}/status?status=in_progress", headers=headers)

        # Waiting queue should be empty
        response = client.get("/api/v1/triage/queue?status=waiting", headers=headers)
        assert response.json()["total"] == 0

        # In progress queue should have 1
        response = client.get("/api/v1/triage/queue?status=in_progress", headers=headers)
        assert response.json()["total"] == 1

    def test_patient_cannot_view_queue(self, client, db):
        patient = create_test_user(db, role="patient")
        response = client.get("/api/v1/triage/queue", headers=auth_header(patient))
        assert response.status_code == 403

    def test_unauthenticated_cannot_view_queue(self, client):
        response = client.get("/api/v1/triage/queue")
        assert response.status_code == 401


class TestUpdateTriageStatus:
    def test_update_to_in_progress(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        response = client.put(f"/api/v1/triage/{tid}/status?status=in_progress", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_to_completed(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        response = client.put(f"/api/v1/triage/{tid}/status?status=completed", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_completed_not_in_waiting_queue(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        client.put(f"/api/v1/triage/{tid}/status?status=completed", headers=headers)
        response = client.get("/api/v1/triage/queue?status=waiting", headers=headers)
        assert response.json()["total"] == 0

    def test_not_found(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.put("/api/v1/triage/nonexistent/status?status=completed", headers=auth_header(nurse))
        assert response.status_code == 404

    def test_invalid_status(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        response = client.put(f"/api/v1/triage/{tid}/status?status=invalid", headers=headers)
        assert response.status_code == 422

    def test_patient_cannot_update_status(self, client, db):
        nurse, headers, _, tid = setup_with_triage(client, db)
        patient = create_test_user(db, role="patient", email="pat@test.com")
        response = client.put(f"/api/v1/triage/{tid}/status?status=completed", headers=auth_header(patient))
        assert response.status_code == 403
