class TestConditionsList:
    def test_list_all_conditions(self, client):
        response = client.get("/api/v1/symptoms/conditions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["conditions"]) == data["total"]

    def test_condition_has_required_fields(self, client):
        response = client.get("/api/v1/symptoms/conditions")
        for condition in response.json()["conditions"]:
            assert "condition" in condition
            assert "category" in condition
            assert "description" in condition
            assert "required_symptoms" in condition
            assert isinstance(condition["required_symptoms"], list)

    def test_filter_by_category_respiratory(self, client):
        response = client.get("/api/v1/symptoms/conditions?category=respiratory")
        data = response.json()
        assert data["total"] > 0
        assert all(c["category"] == "respiratory" for c in data["conditions"])

    def test_filter_by_category_cardiac(self, client):
        response = client.get("/api/v1/symptoms/conditions?category=cardiac")
        data = response.json()
        assert data["total"] > 0
        assert all(c["category"] == "cardiac" for c in data["conditions"])

    def test_filter_by_category_gastrointestinal(self, client):
        response = client.get("/api/v1/symptoms/conditions?category=gastrointestinal")
        data = response.json()
        assert data["total"] > 0

    def test_filter_nonexistent_category(self, client):
        response = client.get("/api/v1/symptoms/conditions?category=nonexistent")
        data = response.json()
        assert data["total"] == 0
        assert data["conditions"] == []

    def test_known_conditions_present(self, client):
        response = client.get("/api/v1/symptoms/conditions")
        names = [c["condition"] for c in response.json()["conditions"]]
        assert "Influenza" in names
        assert "Possible Cardiac Event" in names
        assert "Migraine" in names
        assert "Gastroenteritis" in names

    def test_symptoms_are_sorted(self, client):
        response = client.get("/api/v1/symptoms/conditions")
        for condition in response.json()["conditions"]:
            symptoms = condition["required_symptoms"]
            assert symptoms == sorted(symptoms)

    def test_no_auth_required(self, client):
        """Conditions list is a public endpoint."""
        response = client.get("/api/v1/symptoms/conditions")
        assert response.status_code == 200
