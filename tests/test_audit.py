from tests.conftest import auth_header, create_test_user


class TestAuditLogging:
    def test_patient_create_generates_audit(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        admin = create_test_user(db, role="admin", email="admin@test.com")
        # Create a patient (triggers audit)
        client.post("/api/v1/patients", json={
            "full_name": "Audited Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))

        # Check audit logs
        response = client.get("/api/v1/audit?resource_type=patient&action=create", headers=auth_header(admin))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        log = data["logs"][0]
        assert log["action"] == "create"
        assert log["resource_type"] == "patient"
        assert log["user_email"] == "nurse@test.com"
        assert "Audited Patient" in log["detail"]

    def test_patient_read_generates_audit(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        admin = create_test_user(db, role="admin", email="admin@test.com")
        resp = client.post("/api/v1/patients", json={
            "full_name": "Read Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = resp.json()["id"]

        # Read the patient (triggers audit)
        client.get(f"/api/v1/patients/{pid}", headers=auth_header(nurse))

        response = client.get(f"/api/v1/audit?resource_type=patient&action=read&resource_id={pid}",
                              headers=auth_header(admin))
        assert response.json()["total"] >= 1

    def test_patient_delete_generates_audit(self, client, db):
        admin = create_test_user(db, role="admin")
        resp = client.post("/api/v1/patients", json={
            "full_name": "Delete Me",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(admin))
        pid = resp.json()["id"]
        client.delete(f"/api/v1/patients/{pid}", headers=auth_header(admin))

        response = client.get("/api/v1/audit?action=delete", headers=auth_header(admin))
        data = response.json()
        assert data["total"] >= 1
        delete_log = next(l for l in data["logs"] if l["action"] == "delete")
        assert "Delete Me" in delete_log["detail"]

    def test_vitals_record_generates_audit(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        admin = create_test_user(db, role="admin", email="admin@test.com")
        resp = client.post("/api/v1/patients", json={
            "full_name": "Vitals Audit",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = resp.json()["id"]

        client.post("/api/v1/metrics/vitals", json={
            "patient_id": pid,
            "heart_rate": 75,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "temperature_c": 36.8,
            "respiratory_rate": 16,
            "oxygen_saturation": 98,
        }, headers=auth_header(nurse))

        response = client.get("/api/v1/audit?resource_type=vitals&action=create", headers=auth_header(admin))
        assert response.json()["total"] >= 1


class TestAuditEndpoint:
    def test_admin_can_view_logs(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.get("/api/v1/audit", headers=auth_header(admin))
        assert response.status_code == 200
        assert "logs" in response.json()
        assert "total" in response.json()

    def test_non_admin_cannot_view_logs(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.get("/api/v1/audit", headers=auth_header(nurse))
        assert response.status_code == 403

    def test_patient_cannot_view_logs(self, client, db):
        patient = create_test_user(db, role="patient")
        response = client.get("/api/v1/audit", headers=auth_header(patient))
        assert response.status_code == 403

    def test_unauthenticated_cannot_view_logs(self, client):
        response = client.get("/api/v1/audit")
        assert response.status_code == 401

    def test_filter_by_user_id(self, client, db):
        nurse = create_test_user(db, role="nurse", email="filter-nurse@test.com")
        admin = create_test_user(db, role="admin", email="filter-admin@test.com")
        # Trigger an audit
        client.post("/api/v1/patients", json={
            "full_name": "Filter Test",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))

        response = client.get(f"/api/v1/audit?user_id={nurse.id}", headers=auth_header(admin))
        data = response.json()
        assert data["total"] >= 1
        assert all(log["user_id"] == nurse.id for log in data["logs"])

    def test_audit_pagination(self, client, db):
        admin = create_test_user(db, role="admin")
        headers = auth_header(admin)
        # Create several patients to generate audit entries
        for i in range(5):
            client.post("/api/v1/patients", json={
                "full_name": f"Paginate {i}",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            }, headers=headers)

        response = client.get("/api/v1/audit?limit=2&offset=0", headers=headers)
        data = response.json()
        assert data["total"] >= 5
        assert len(data["logs"]) == 2

    def test_audit_log_has_all_fields(self, client, db):
        admin = create_test_user(db, role="admin")
        client.post("/api/v1/patients", json={
            "full_name": "Fields Test",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(admin))

        response = client.get("/api/v1/audit", headers=auth_header(admin))
        log = response.json()["logs"][0]
        assert "id" in log
        assert "user_id" in log
        assert "user_email" in log
        assert "user_role" in log
        assert "action" in log
        assert "resource_type" in log
        assert "created_at" in log
