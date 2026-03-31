from tests.conftest import auth_header, create_test_user


class TestCreatePatient:
    def test_create_success(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.post(
            "/api/v1/patients",
            json={
                "full_name": "John Doe",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "blood_type": "O+",
                "height_cm": 175.0,
                "weight_kg": 80.0,
            },
            headers=auth_header(nurse),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "John Doe"
        assert data["gender"] == "male"
        assert "id" in data
        assert "created_at" in data

    def test_create_minimal(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.post(
            "/api/v1/patients",
            json={
                "full_name": "Jane Doe",
                "date_of_birth": "1985-01-01",
                "gender": "female",
            },
            headers=auth_header(nurse),
        )
        assert response.status_code == 201
        assert response.json()["blood_type"] is None

    def test_create_invalid_gender(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.post(
            "/api/v1/patients",
            json={
                "full_name": "Test",
                "date_of_birth": "1990-01-01",
                "gender": "invalid",
            },
            headers=auth_header(nurse),
        )
        assert response.status_code == 422

    def test_create_missing_name(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.post(
            "/api/v1/patients",
            json={
                "date_of_birth": "1990-01-01",
                "gender": "male",
            },
            headers=auth_header(nurse),
        )
        assert response.status_code == 422


class TestGetPatient:
    def test_get_existing(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "John Doe",
                "date_of_birth": "1990-05-15",
                "gender": "male",
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["full_name"] == "John Doe"

    def test_get_not_found(self, client, db):
        user = create_test_user(db)
        response = client.get("/api/v1/patients/nonexistent-id", headers=auth_header(user))
        assert response.status_code == 404

    def test_patient_user_can_view_own_record(self, client, db):
        """A patient-role user can view their own linked patient record."""
        nurse = create_test_user(db, role="nurse")
        patient_user = create_test_user(db, role="patient", email="mypatient@test.com")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "Own Patient",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "user_id": patient_user.id,
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.get(f"/api/v1/patients/{patient_id}", headers=auth_header(patient_user))
        assert response.status_code == 200
        assert response.json()["full_name"] == "Own Patient"
        assert response.json()["user_id"] == patient_user.id

    def test_patient_user_cannot_view_other_record(self, client, db):
        """A patient-role user cannot view another patient's record."""
        nurse = create_test_user(db, role="nurse")
        patient_user = create_test_user(db, role="patient", email="mypatient@test.com")
        other_user = create_test_user(db, role="patient", email="other@test.com")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "Other Patient",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "user_id": other_user.id,
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.get(f"/api/v1/patients/{patient_id}", headers=auth_header(patient_user))
        assert response.status_code == 403

    def test_nurse_can_view_any_patient(self, client, db):
        """A nurse can view any patient record regardless of user_id."""
        nurse = create_test_user(db, role="nurse")
        patient_user = create_test_user(db, role="patient", email="linked@test.com")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "Linked Patient",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "user_id": patient_user.id,
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
        assert response.status_code == 200


class TestListPatients:
    def test_list_empty(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.get("/api/v1/patients", headers=auth_header(nurse))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["patients"] == []

    def test_list_with_patients(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        client.post(
            "/api/v1/patients",
            json={
                "full_name": "Patient A",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            },
            headers=headers,
        )
        client.post(
            "/api/v1/patients",
            json={
                "full_name": "Patient B",
                "date_of_birth": "1985-06-15",
                "gender": "female",
            },
            headers=headers,
        )
        response = client.get("/api/v1/patients", headers=headers)
        data = response.json()
        assert data["total"] == 2
        assert len(data["patients"]) == 2

    def test_list_pagination(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        for i in range(5):
            client.post(
                "/api/v1/patients",
                json={
                    "full_name": f"Patient {i}",
                    "date_of_birth": "1990-01-01",
                    "gender": "male",
                },
                headers=headers,
            )
        response = client.get("/api/v1/patients?limit=2&offset=0", headers=headers)
        data = response.json()
        assert data["total"] == 5
        assert len(data["patients"]) == 2


class TestUpdatePatient:
    def test_update_success(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "John Doe",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "weight_kg": 80.0,
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.put(f"/api/v1/patients/{patient_id}", json={"weight_kg": 75.0}, headers=headers)
        assert response.status_code == 200
        assert response.json()["weight_kg"] == 75.0
        assert response.json()["full_name"] == "John Doe"

    def test_update_not_found(self, client, db):
        nurse = create_test_user(db, role="nurse")
        response = client.put("/api/v1/patients/nonexistent-id", json={"weight_kg": 75.0}, headers=auth_header(nurse))
        assert response.status_code == 404

    def test_partial_update(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "John Doe",
                "date_of_birth": "1990-05-15",
                "gender": "male",
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.put(
            f"/api/v1/patients/{patient_id}",
            json={
                "allergies": "penicillin",
                "emergency_contact_name": "Jane Doe",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allergies"] == "penicillin"
        assert data["emergency_contact_name"] == "Jane Doe"


class TestDeletePatient:
    def test_delete_success(self, client, db):
        admin = create_test_user(db, role="admin")
        headers = auth_header(admin)
        create = client.post(
            "/api/v1/patients",
            json={
                "full_name": "John Doe",
                "date_of_birth": "1990-05-15",
                "gender": "male",
            },
            headers=headers,
        )
        patient_id = create.json()["id"]
        response = client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
        assert response.status_code == 204
        get_response = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_not_found(self, client, db):
        admin = create_test_user(db, role="admin")
        response = client.delete("/api/v1/patients/nonexistent-id", headers=auth_header(admin))
        assert response.status_code == 404
