from app.services.bmi_calculator import calculate_bmi, get_bmi_category, get_healthy_weight_range


class TestCalculateBMI:
    def test_normal_bmi(self):
        assert calculate_bmi(175, 70) == 22.9

    def test_high_bmi(self):
        assert calculate_bmi(170, 100) == 34.6

    def test_low_bmi(self):
        assert calculate_bmi(180, 50) == 15.4

    def test_short_height(self):
        assert calculate_bmi(150, 50) == 22.2

    def test_tall_height(self):
        assert calculate_bmi(200, 90) == 22.5


class TestGetBMICategory:
    def test_severe_underweight(self):
        category, _ = get_bmi_category(14.0)
        assert category == "severe underweight"

    def test_moderate_underweight(self):
        category, _ = get_bmi_category(16.5)
        assert category == "moderate underweight"

    def test_underweight(self):
        category, _ = get_bmi_category(17.5)
        assert category == "underweight"

    def test_normal(self):
        category, _ = get_bmi_category(22.0)
        assert category == "normal"

    def test_overweight(self):
        category, _ = get_bmi_category(27.0)
        assert category == "overweight"

    def test_obese_class_i(self):
        category, _ = get_bmi_category(32.0)
        assert category == "obese class I"

    def test_obese_class_ii(self):
        category, _ = get_bmi_category(37.0)
        assert category == "obese class II"

    def test_obese_class_iii(self):
        category, _ = get_bmi_category(42.0)
        assert category == "obese class III"


class TestGetHealthyWeightRange:
    def test_average_height(self):
        result = get_healthy_weight_range(175)
        assert result.min_kg == 56.7
        assert result.max_kg == 76.3

    def test_short_height(self):
        result = get_healthy_weight_range(150)
        assert result.min_kg == 41.6
        assert result.max_kg == 56.0

    def test_tall_height(self):
        result = get_healthy_weight_range(200)
        assert result.min_kg == 74.0
        assert result.max_kg == 99.6


class TestBMIEndpoint:
    def test_valid_request(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 175, "weight_kg": 70})
        assert response.status_code == 200
        data = response.json()
        assert data["bmi"] == 22.9
        assert data["category"] == "normal"
        assert "healthy_weight_range" in data
        assert "interpretation" in data

    def test_overweight_request(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 170, "weight_kg": 85})
        assert response.status_code == 200
        assert response.json()["category"] == "overweight"

    def test_underweight_request(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 180, "weight_kg": 50})
        assert response.status_code == 200
        assert response.json()["category"] == "severe underweight"

    def test_zero_height_rejected(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 0, "weight_kg": 70})
        assert response.status_code == 422

    def test_negative_weight_rejected(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 175, "weight_kg": -10})
        assert response.status_code == 422

    def test_missing_field_rejected(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 175})
        assert response.status_code == 422

    def test_extreme_height_rejected(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 500, "weight_kg": 70})
        assert response.status_code == 422

    def test_extreme_weight_rejected(self, client):
        response = client.post("/api/v1/metrics/bmi", json={"height_cm": 175, "weight_kg": 800})
        assert response.status_code == 422


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
