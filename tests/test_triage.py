from app.schemas.triage import Vitals
from app.services.triage_engine import (
    assess_pain,
    assess_symptoms,
    assess_vitals,
    apply_age_modifier,
)
from tests.conftest import auth_header, create_test_user

NORMAL_VITALS = {
    "heart_rate": 75,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "temperature_c": 36.8,
    "respiratory_rate": 16,
    "oxygen_saturation": 98,
}


def make_request(overrides: dict | None = None) -> dict:
    base = {
        "patient_name": "John Doe",
        "chief_complaint": "Headache",
        "symptoms": ["headache"],
        "symptom_duration": "2 hours",
        "vitals": NORMAL_VITALS,
        "pain_scale": 3,
        "age": 35,
        "notes": "",
    }
    if overrides:
        base.update(overrides)
    return base


class TestAssessVitals:
    def test_normal_vitals(self):
        vitals = Vitals(**NORMAL_VITALS)
        level, flags = assess_vitals(vitals)
        assert level == 5
        assert flags == []

    def test_critical_heart_rate_low(self):
        vitals = Vitals(**{**NORMAL_VITALS, "heart_rate": 35})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_heart_rate" in flags

    def test_critical_heart_rate_high(self):
        vitals = Vitals(**{**NORMAL_VITALS, "heart_rate": 160})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_heart_rate" in flags

    def test_critical_low_bp(self):
        vitals = Vitals(**{**NORMAL_VITALS, "blood_pressure_systolic": 70})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_low_bp" in flags

    def test_critical_low_o2(self):
        vitals = Vitals(**{**NORMAL_VITALS, "oxygen_saturation": 80})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_low_o2" in flags

    def test_critical_respiratory_rate(self):
        vitals = Vitals(**{**NORMAL_VITALS, "respiratory_rate": 6})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_respiratory_rate" in flags

    def test_level2_elevated_heart_rate(self):
        vitals = Vitals(**{**NORMAL_VITALS, "heart_rate": 135})
        level, flags = assess_vitals(vitals)
        assert level == 2
        assert "elevated_heart_rate" in flags

    def test_level2_high_bp(self):
        vitals = Vitals(**{**NORMAL_VITALS, "blood_pressure_systolic": 210})
        level, flags = assess_vitals(vitals)
        assert level == 2
        assert "abnormal_blood_pressure" in flags

    def test_level2_low_o2(self):
        vitals = Vitals(**{**NORMAL_VITALS, "oxygen_saturation": 88})
        level, flags = assess_vitals(vitals)
        assert level == 2
        assert "low_o2_sat" in flags

    def test_level2_hyperthermia(self):
        vitals = Vitals(**{**NORMAL_VITALS, "temperature_c": 41.0})
        level, flags = assess_vitals(vitals)
        assert level == 2
        assert "hyperthermia" in flags

    def test_level3_tachycardia(self):
        vitals = Vitals(**{**NORMAL_VITALS, "heart_rate": 110})
        level, flags = assess_vitals(vitals)
        assert level == 3
        assert "tachycardia" in flags

    def test_level3_fever(self):
        vitals = Vitals(**{**NORMAL_VITALS, "temperature_c": 39.0})
        level, flags = assess_vitals(vitals)
        assert level == 3
        assert "fever" in flags

    def test_multiple_flags(self):
        vitals = Vitals(**{**NORMAL_VITALS, "heart_rate": 160, "oxygen_saturation": 80})
        level, flags = assess_vitals(vitals)
        assert level == 1
        assert "critical_heart_rate" in flags
        assert "critical_low_o2" in flags


class TestAssessSymptoms:
    def test_no_high_risk_symptoms(self):
        level, flags = assess_symptoms(["headache", "fatigue"])
        assert level == 5
        assert flags == []

    def test_level1_symptoms(self):
        level, flags = assess_symptoms(["cardiac_arrest"])
        assert level == 1
        assert "symptom_cardiac_arrest" in flags

    def test_level2_symptoms(self):
        level, flags = assess_symptoms(["chest_pain", "difficulty_breathing"])
        assert level == 2
        assert "symptom_chest_pain" in flags

    def test_level3_symptoms(self):
        level, flags = assess_symptoms(["fracture"])
        assert level == 3
        assert "symptom_fracture" in flags

    def test_case_insensitive(self):
        level, flags = assess_symptoms(["Chest_Pain"])
        assert level == 2


class TestAssessPain:
    def test_severe_pain(self):
        level, flags = assess_pain(9)
        assert level == 2
        assert "severe_pain" in flags

    def test_moderate_pain(self):
        level, flags = assess_pain(6)
        assert level == 3
        assert "moderate_pain" in flags

    def test_mild_pain(self):
        level, flags = assess_pain(3)
        assert level == 4
        assert "mild_pain" in flags

    def test_no_pain(self):
        level, flags = assess_pain(1)
        assert level == 5
        assert flags == []


class TestAgeModifier:
    def test_pediatric_bumps_priority(self):
        level, flags = apply_age_modifier(4, 3)
        assert level == 3
        assert "pediatric_patient" in flags

    def test_geriatric_bumps_priority(self):
        level, flags = apply_age_modifier(4, 75)
        assert level == 3
        assert "geriatric_patient" in flags

    def test_no_bump_below_level2(self):
        level, flags = apply_age_modifier(2, 3)
        assert level == 2

    def test_adult_no_bump(self):
        level, flags = apply_age_modifier(4, 35)
        assert level == 4
        assert flags == []


class TestTriageEndpoint:
    def _headers(self, db):
        user = create_test_user(db, role="nurse")
        return auth_header(user)

    def test_non_urgent_case(self, client, db):
        response = client.post("/api/v1/triage", json=make_request(), headers=self._headers(db))
        assert response.status_code == 200
        data = response.json()
        assert data["priority_label"] == "Semi-Urgent"
        assert data["priority_color"] == "green"
        assert data["patient_name"] == "John Doe"
        assert "vitals_summary" in data

    def test_emergency_chest_pain(self, client, db):
        request = make_request({
            "chief_complaint": "Severe chest pain",
            "symptoms": ["chest_pain", "difficulty_breathing", "sweating"],
            "pain_scale": 9,
            "vitals": {**NORMAL_VITALS, "heart_rate": 135, "oxygen_saturation": 88},
        })
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        assert response.status_code == 200
        data = response.json()
        assert data["priority_level"] <= 2
        assert data["priority_color"] in ("red", "orange")

    def test_critical_cardiac_arrest(self, client, db):
        request = make_request({
            "symptoms": ["cardiac_arrest"],
            "pain_scale": 0,
            "vitals": {**NORMAL_VITALS, "heart_rate": 30, "blood_pressure_systolic": 60},
        })
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        data = response.json()
        assert data["priority_level"] == 1
        assert data["priority_label"] == "Resuscitation"

    def test_pediatric_patient_bump(self, client, db):
        request = make_request({"age": 3, "pain_scale": 5})
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        data = response.json()
        assert data["priority_level"] <= 3
        assert "pediatric_patient" in data["flags"]

    def test_geriatric_patient_bump(self, client, db):
        request = make_request({"age": 80, "pain_scale": 5})
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        data = response.json()
        assert "geriatric_patient" in data["flags"]

    def test_validation_empty_symptoms(self, client, db):
        request = make_request({"symptoms": []})
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_validation_invalid_pain_scale(self, client, db):
        request = make_request({"pain_scale": 15})
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_validation_missing_vitals(self, client, db):
        request = make_request()
        del request["vitals"]
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        assert response.status_code == 422

    def test_vitals_summary_present(self, client, db):
        response = client.post("/api/v1/triage", json=make_request(), headers=self._headers(db))
        data = response.json()
        summary = data["vitals_summary"]
        assert "heart_rate" in summary
        assert "blood_pressure" in summary
        assert "temperature" in summary
        assert "oxygen_saturation" in summary

    def test_flags_are_unique(self, client, db):
        request = make_request({
            "vitals": {**NORMAL_VITALS, "heart_rate": 160, "oxygen_saturation": 80},
        })
        response = client.post("/api/v1/triage", json=request, headers=self._headers(db))
        data = response.json()
        assert len(data["flags"]) == len(set(data["flags"]))

    def test_unauthenticated_rejected(self, client):
        response = client.post("/api/v1/triage", json=make_request())
        assert response.status_code == 401
