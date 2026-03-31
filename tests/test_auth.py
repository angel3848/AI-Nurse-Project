from tests.conftest import auth_header, create_test_user


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "securepass123",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "patient"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, db):
        create_test_user(db, email="dup@test.com")
        response = client.post("/api/v1/auth/register", json={
            "email": "dup@test.com",
            "password": "securepass123",
            "full_name": "Dup User",
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "short",
            "full_name": "Short Pass",
        })
        assert response.status_code == 422

    def test_register_missing_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "password": "securepass123",
            "full_name": "No Email",
        })
        assert response.status_code == 422

    def test_register_always_patient_role(self, client):
        """Users cannot self-assign elevated roles through registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "hacker@test.com",
            "password": "securepass123",
            "full_name": "Hacker",
        })
        assert response.status_code == 201
        assert response.json()["role"] == "patient"


class TestLogin:
    def test_login_success(self, client, db):
        create_test_user(db, email="login@test.com")
        response = client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login@test.com"

    def test_login_wrong_password(self, client, db):
        create_test_user(db, email="wrong@test.com")
        response = client.post("/api/v1/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "ghost@test.com",
            "password": "testpass123",
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db):
        user = create_test_user(db, email="inactive@test.com")
        user.is_active = False
        db.commit()
        response = client.post("/api/v1/auth/login", json={
            "email": "inactive@test.com",
            "password": "testpass123",
        })
        assert response.status_code == 403


class TestGetMe:
    def test_get_me_authenticated(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/auth/me", headers=auth_header(user))
        assert response.status_code == 200
        assert response.json()["email"] == user.email

    def test_get_me_no_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401


class TestRoleBasedAccess:
    def test_patient_cannot_create_patient(self, client, db):
        user = create_test_user(db, role="patient")
        response = client.post("/api/v1/patients", json={
            "full_name": "Test",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(user))
        assert response.status_code == 403

    def test_nurse_can_create_patient(self, client, db):
        user = create_test_user(db, role="nurse")
        response = client.post("/api/v1/patients", json={
            "full_name": "Test Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(user))
        assert response.status_code == 201

    def test_doctor_can_create_patient(self, client, db):
        user = create_test_user(db, role="doctor")
        response = client.post("/api/v1/patients", json={
            "full_name": "Test Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(user))
        assert response.status_code == 201

    def test_patient_cannot_delete_patient(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        create_resp = client.post("/api/v1/patients", json={
            "full_name": "To Delete",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = create_resp.json()["id"]

        patient_user = create_test_user(db, role="patient", email="patient@test.com")
        response = client.delete(f"/api/v1/patients/{pid}", headers=auth_header(patient_user))
        assert response.status_code == 403

    def test_admin_can_delete_patient(self, client, db):
        admin = create_test_user(db, role="admin")
        create_resp = client.post("/api/v1/patients", json={
            "full_name": "To Delete",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(admin))
        pid = create_resp.json()["id"]
        response = client.delete(f"/api/v1/patients/{pid}", headers=auth_header(admin))
        assert response.status_code == 204

    def test_patient_can_view_own_record(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        patient_user = create_test_user(db, role="patient", email="viewer@test.com")
        create_resp = client.post("/api/v1/patients", json={
            "full_name": "Viewable",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = create_resp.json()["id"]

        # Link the patient record to the user
        from app.models.patient import Patient
        patient_record = db.query(Patient).filter(Patient.id == pid).first()
        patient_record.user_id = patient_user.id
        db.commit()

        response = client.get(f"/api/v1/patients/{pid}", headers=auth_header(patient_user))
        assert response.status_code == 200

    def test_patient_cannot_view_other_patient(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        create_resp = client.post("/api/v1/patients", json={
            "full_name": "Other Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = create_resp.json()["id"]

        patient_user = create_test_user(db, role="patient", email="viewer@test.com")
        response = client.get(f"/api/v1/patients/{pid}", headers=auth_header(patient_user))
        assert response.status_code == 403

    def test_patient_cannot_list_all_patients(self, client, db):
        user = create_test_user(db, role="patient")
        response = client.get("/api/v1/patients", headers=auth_header(user))
        assert response.status_code == 403

    def test_nurse_can_create_medication_reminder(self, client, db):
        nurse = create_test_user(db, role="nurse")
        # Create patient first
        p_resp = client.post("/api/v1/patients", json={
            "full_name": "Med Patient",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, headers=auth_header(nurse))
        pid = p_resp.json()["id"]

        response = client.post("/api/v1/medications/reminders", json={
            "patient_id": pid,
            "medication_name": "Aspirin",
            "dosage": "100mg",
            "frequency": "once_daily",
            "times": ["08:00:00"],
            "start_date": "2026-03-24",
            "end_date": "2026-06-24",
        }, headers=auth_header(nurse))
        assert response.status_code == 201

    def test_patient_cannot_create_medication_reminder(self, client, db):
        user = create_test_user(db, role="patient")
        response = client.post("/api/v1/medications/reminders", json={
            "patient_id": "some-id",
            "medication_name": "Aspirin",
            "dosage": "100mg",
            "frequency": "once_daily",
            "times": ["08:00:00"],
            "start_date": "2026-03-24",
            "end_date": "2026-06-24",
        }, headers=auth_header(user))
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_protected(self, client):
        response = client.get("/api/v1/patients")
        assert response.status_code == 401


class TestListUsers:
    def test_admin_can_list_users(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        create_test_user(db, role="nurse", email="nurse@test.com")
        create_test_user(db, role="patient", email="patient@test.com")
        response = client.get("/api/v1/auth/users", headers=auth_header(admin))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_filter_by_role(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        create_test_user(db, role="nurse", email="nurse1@test.com")
        create_test_user(db, role="nurse", email="nurse2@test.com")
        create_test_user(db, role="patient", email="patient@test.com")
        response = client.get("/api/v1/auth/users?role=nurse", headers=auth_header(admin))
        data = response.json()
        assert data["total"] == 2
        assert all(u["role"] == "nurse" for u in data["users"])

    def test_non_admin_cannot_list_users(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.get("/api/v1/auth/users", headers=auth_header(nurse))
        assert response.status_code == 403

    def test_pagination(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        for i in range(5):
            create_test_user(db, role="patient", email=f"p{i}@test.com")
        response = client.get("/api/v1/auth/users?limit=2&offset=0", headers=auth_header(admin))
        data = response.json()
        assert data["total"] == 6  # admin + 5 patients
        assert len(data["users"]) == 2


class TestUpdateRole:
    def test_promote_to_nurse(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        patient = create_test_user(db, role="patient", email="promote@test.com")
        response = client.put(f"/api/v1/auth/users/{patient.id}/role",
                              json={"role": "nurse"}, headers=auth_header(admin))
        assert response.status_code == 200
        assert response.json()["role"] == "nurse"

    def test_promote_to_doctor(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        response = client.put(f"/api/v1/auth/users/{nurse.id}/role",
                              json={"role": "doctor"}, headers=auth_header(admin))
        assert response.status_code == 200
        assert response.json()["role"] == "doctor"

    def test_demote_to_patient(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        doctor = create_test_user(db, role="doctor", email="doc@test.com")
        response = client.put(f"/api/v1/auth/users/{doctor.id}/role",
                              json={"role": "patient"}, headers=auth_header(admin))
        assert response.status_code == 200
        assert response.json()["role"] == "patient"

    def test_cannot_change_own_role(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.put(f"/api/v1/auth/users/{admin.id}/role",
                              json={"role": "patient"}, headers=auth_header(admin))
        assert response.status_code == 400
        assert "own role" in response.json()["detail"]

    def test_invalid_role_rejected(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        user = create_test_user(db, role="patient", email="user@test.com")
        response = client.put(f"/api/v1/auth/users/{user.id}/role",
                              json={"role": "superadmin"}, headers=auth_header(admin))
        assert response.status_code == 422

    def test_user_not_found(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.put("/api/v1/auth/users/nonexistent/role",
                              json={"role": "nurse"}, headers=auth_header(admin))
        assert response.status_code == 404

    def test_non_admin_cannot_change_roles(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        patient = create_test_user(db, role="patient", email="patient@test.com")
        response = client.put(f"/api/v1/auth/users/{patient.id}/role",
                              json={"role": "doctor"}, headers=auth_header(nurse))
        assert response.status_code == 403

    def test_role_change_generates_audit(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        patient = create_test_user(db, role="patient", email="audit@test.com")
        client.put(f"/api/v1/auth/users/{patient.id}/role",
                   json={"role": "nurse"}, headers=auth_header(admin))
        response = client.get("/api/v1/audit?action=update&resource_type=user",
                              headers=auth_header(admin))
        data = response.json()
        assert data["total"] >= 1
        assert "patient -> nurse" in data["logs"][0]["detail"]


class TestDeactivateActivate:
    def test_deactivate_user(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        user = create_test_user(db, role="nurse", email="deact@test.com")
        response = client.put(f"/api/v1/auth/users/{user.id}/deactivate",
                              headers=auth_header(admin))
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_deactivated_user_cannot_login(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        user = create_test_user(db, role="nurse", email="blocked@test.com")
        client.put(f"/api/v1/auth/users/{user.id}/deactivate", headers=auth_header(admin))
        response = client.post("/api/v1/auth/login", json={
            "email": "blocked@test.com",
            "password": "testpass123",
        })
        assert response.status_code == 403

    def test_activate_user(self, client, db):
        admin = create_test_user(db, role="admin", email="admin@test.com")
        user = create_test_user(db, role="nurse", email="react@test.com")
        client.put(f"/api/v1/auth/users/{user.id}/deactivate", headers=auth_header(admin))
        response = client.put(f"/api/v1/auth/users/{user.id}/activate",
                              headers=auth_header(admin))
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_cannot_deactivate_self(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.put(f"/api/v1/auth/users/{admin.id}/deactivate",
                              headers=auth_header(admin))
        assert response.status_code == 400

    def test_deactivate_not_found(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.put("/api/v1/auth/users/nonexistent/deactivate",
                              headers=auth_header(admin))
        assert response.status_code == 404

    def test_non_admin_cannot_deactivate(self, client, db):
        nurse = create_test_user(db, role="nurse", email="nurse@test.com")
        patient = create_test_user(db, role="patient", email="patient@test.com")
        response = client.put(f"/api/v1/auth/users/{patient.id}/deactivate",
                              headers=auth_header(nurse))
        assert response.status_code == 403
