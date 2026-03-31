from app.services.symptom_checker import (
    check_symptoms,
    determine_urgency,
    match_conditions,
    score_to_probability,
)
from app.schemas.symptom import SymptomCheckRequest
from tests.conftest import auth_header, create_test_user


def make_request(overrides: dict | None = None) -> dict:
    base = {
        "symptoms": ["headache", "fatigue"],
        "duration_days": 3,
        "severity": "mild",
        "age": 35,
        "additional_info": "",
    }
    if overrides:
        base.update(overrides)
    return base


class TestMatchConditions:
    def test_flu_symptoms(self):
        matches = match_conditions(["fever", "cough", "fatigue", "body_aches"])
        names = [m[0] for m in matches]
        assert "Influenza" in names

    def test_cardiac_symptoms(self):
        matches = match_conditions(["chest_pain", "shortness_of_breath", "sweating"])
        names = [m[0] for m in matches]
        assert "Possible Cardiac Event" in names

    def test_no_matches(self):
        matches = match_conditions(["hiccups"])
        assert matches == []

    def test_partial_match(self):
        matches = match_conditions(["fever", "cough"])
        assert len(matches) > 0

    def test_gastro_symptoms(self):
        matches = match_conditions(["nausea", "vomiting", "diarrhea"])
        names = [m[0] for m in matches]
        assert "Gastroenteritis" in names

    def test_migraine_symptoms(self):
        matches = match_conditions(["headache", "nausea", "light_sensitivity"])
        names = [m[0] for m in matches]
        assert "Migraine" in names

    def test_meningitis_symptoms(self):
        matches = match_conditions(["headache", "fever", "stiff_neck"])
        names = [m[0] for m in matches]
        assert "Meningitis" in names

    def test_results_sorted_by_score(self):
        matches = match_conditions(["fever", "cough", "fatigue", "body_aches", "runny_nose", "sore_throat"])
        scores = [m[1] for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_case_insensitive(self):
        matches = match_conditions(["Fever", "Cough", "Fatigue"])
        assert len(matches) > 0

    def test_max_five_results_via_service(self):
        request = SymptomCheckRequest(
            symptoms=["fever", "cough", "fatigue", "body_aches", "nausea", "headache", "rash", "chills"],
            duration_days=2,
            severity="moderate",
            age=35,
        )
        result = check_symptoms(request)
        assert len(result.possible_conditions) <= 5


class TestScoreToProbability:
    def test_high(self):
        assert score_to_probability(0.8) == "high"

    def test_moderate(self):
        assert score_to_probability(0.6) == "moderate"

    def test_low(self):
        assert score_to_probability(0.3) == "low"

    def test_boundary_high(self):
        assert score_to_probability(0.75) == "high"

    def test_boundary_moderate(self):
        assert score_to_probability(0.5) == "moderate"


class TestDetermineUrgency:
    def test_emergency_condition(self):
        conditions = [("Possible Cardiac Event", 1.0, "desc", "cardiac")]
        assert determine_urgency(conditions, "severe", 1, 50) == "emergency"

    def test_meningitis_emergency(self):
        conditions = [("Meningitis", 1.0, "desc", "neurological")]
        assert determine_urgency(conditions, "severe", 1, 30) == "emergency"

    def test_no_conditions_mild(self):
        assert determine_urgency([], "mild", 5, 35) == "low"

    def test_no_conditions_severe(self):
        assert determine_urgency([], "severe", 5, 35) == "moderate"

    def test_acute_onset_bumps_urgency(self):
        conditions = [("Common Cold", 0.8, "desc", "respiratory")]
        urgency = determine_urgency(conditions, "mild", 1, 35)
        assert urgency == "high"

    def test_elderly_bumps_urgency(self):
        conditions = [("Arthritis Flare", 0.8, "desc", "musculoskeletal")]
        urgency = determine_urgency(conditions, "mild", 7, 75)
        assert urgency == "moderate"

    def test_pediatric_bumps_urgency(self):
        conditions = [("Arthritis Flare", 0.8, "desc", "musculoskeletal")]
        urgency = determine_urgency(conditions, "mild", 7, 3)
        assert urgency == "moderate"

    def test_severe_bumps_low_to_moderate(self):
        conditions = [("Arthritis Flare", 0.8, "desc", "musculoskeletal")]
        urgency = determine_urgency(conditions, "severe", 7, 35)
        assert urgency == "moderate"


class TestSymptomEndpoint:
    def _headers(self, db):
        user = create_test_user(db, role="patient")
        return auth_header(user)

    def test_valid_request(self, client, db):
        request = make_request({"symptoms": ["fever", "cough", "fatigue", "body_aches"]})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        assert response.status_code == 200
        data = response.json()
        assert "possible_conditions" in data
        assert "recommended_action" in data
        assert "urgency" in data
        assert "disclaimer" in data

    def test_cardiac_emergency(self, client, db):
        request = make_request({
            "symptoms": ["chest_pain", "shortness_of_breath", "sweating"],
            "severity": "severe",
            "duration_days": 1,
        })
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        data = response.json()
        assert data["urgency"] == "emergency"
        conditions = [c["condition"] for c in data["possible_conditions"]]
        assert "Possible Cardiac Event" in conditions

    def test_mild_symptoms(self, client, db):
        request = make_request({"symptoms": ["cough", "runny_nose", "sore_throat"]})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        data = response.json()
        conditions = [c["condition"] for c in data["possible_conditions"]]
        assert "Common Cold" in conditions

    def test_no_matching_conditions(self, client, db):
        request = make_request({"symptoms": ["hiccups"]})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        data = response.json()
        assert data["possible_conditions"] == []
        assert data["urgency"] == "low"

    def test_disclaimer_always_present(self, client, db):
        request = make_request()
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        data = response.json()
        assert "not a medical diagnosis" in data["disclaimer"]

    def test_conditions_have_required_fields(self, client, db):
        request = make_request({"symptoms": ["fever", "cough", "fatigue"]})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        data = response.json()
        for condition in data["possible_conditions"]:
            assert "condition" in condition
            assert "probability" in condition
            assert "description" in condition
            assert "category" in condition

    def test_validation_empty_symptoms(self, client, db):
        request = make_request({"symptoms": []})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_validation_invalid_severity(self, client, db):
        request = make_request({"severity": "extreme"})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_validation_zero_duration(self, client, db):
        request = make_request({"duration_days": 0})
        response = client.post("/api/v1/symptoms/check", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_unauthenticated_rejected(self, client):
        request = make_request()
        response = client.post("/api/v1/symptoms/check", json=request)
        assert response.status_code == 401
