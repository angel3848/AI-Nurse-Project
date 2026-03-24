class TestCreatePatient:
    def test_create_success(self, client):
        response = client.post("/api/v1/patients", json={
            "full_name": "John Doe",
            "date_of_birth": "1990-05-15",
            "gender": "male",
            "blood_type": "O+",
            "height_cm": 175.0,
            "weight_kg": 80.0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "John Doe"
        assert data["gender"] == "male"
        assert "id" in data
        assert "created_at" in data

    def test_create_minimal(self, client):
        response = client.post("/api/v1/patients", json={
            "full_name": "Jane Doe",
            "date_of_birth": "1985-01-01",
            "gender": "female",
        })
        assert response.status_code == 201
        assert response.json()["blood_type"] is None

    def test_create_invalid_gender(self, client):
        response = client.post("/api/v1/patients", json={
            "full_name": "Test",
            "date_of_birth": "1990-01-01",
            "gender": "invalid",
        })
        assert response.status_code == 422

    def test_create_missing_name(self, client):
        response = client.post("/api/v1/patients", json={
            "date_of_birth": "1990-01-01",
            "gender": "male",
        })
        assert response.status_code == 422


class TestGetPatient:
    def test_get_existing(self, client):
        create = client.post("/api/v1/patients", json={
            "full_name": "John Doe",
            "date_of_birth": "1990-05-15",
            "gender": "male",
        })
        patient_id = create.json()["id"]
        response = client.get(f"/api/v1/patients/{patient_id}")
        assert response.status_code == 200
        assert response.json()["full_name"] == "John Doe"

    def test_get_not_found(self, client):
        response = client.get("/api/v1/patients/nonexistent-id")
        assert response.status_code == 404


class TestListPatients:
    def test_list_empty(self, client):
        response = client.get("/api/v1/patients")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["patients"] == []

    def test_list_with_patients(self, client):
        client.post("/api/v1/patients", json={
            "full_name": "Patient A",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        })
        client.post("/api/v1/patients", json={
            "full_name": "Patient B",
            "date_of_birth": "1985-06-15",
            "gender": "female",
        })
        response = client.get("/api/v1/patients")
        data = response.json()
        assert data["total"] == 2
        assert len(data["patients"]) == 2

    def test_list_pagination(self, client):
        for i in range(5):
            client.post("/api/v1/patients", json={
                "full_name": f"Patient {i}",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            })
        response = client.get("/api/v1/patients?limit=2&offset=0")
        data = response.json()
        assert data["total"] == 5
        assert len(data["patients"]) == 2


class TestUpdatePatient:
    def test_update_success(self, client):
        create = client.post("/api/v1/patients", json={
            "full_name": "John Doe",
            "date_of_birth": "1990-05-15",
            "gender": "male",
            "weight_kg": 80.0,
        })
        patient_id = create.json()["id"]
        response = client.put(f"/api/v1/patients/{patient_id}", json={"weight_kg": 75.0})
        assert response.status_code == 200
        assert response.json()["weight_kg"] == 75.0
        assert response.json()["full_name"] == "John Doe"

    def test_update_not_found(self, client):
        response = client.put("/api/v1/patients/nonexistent-id", json={"weight_kg": 75.0})
        assert response.status_code == 404

    def test_partial_update(self, client):
        create = client.post("/api/v1/patients", json={
            "full_name": "John Doe",
            "date_of_birth": "1990-05-15",
            "gender": "male",
        })
        patient_id = create.json()["id"]
        response = client.put(f"/api/v1/patients/{patient_id}", json={
            "allergies": "penicillin",
            "emergency_contact_name": "Jane Doe",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allergies"] == "penicillin"
        assert data["emergency_contact_name"] == "Jane Doe"


class TestDeletePatient:
    def test_delete_success(self, client):
        create = client.post("/api/v1/patients", json={
            "full_name": "John Doe",
            "date_of_birth": "1990-05-15",
            "gender": "male",
        })
        patient_id = create.json()["id"]
        response = client.delete(f"/api/v1/patients/{patient_id}")
        assert response.status_code == 204
        get_response = client.get(f"/api/v1/patients/{patient_id}")
        assert get_response.status_code == 404

    def test_delete_not_found(self, client):
        response = client.delete("/api/v1/patients/nonexistent-id")
        assert response.status_code == 404
