from datetime import date

from app.models.allergy import Allergy
from app.models.patient import Patient
from app.services import allergy_service
from tests.conftest import auth_header, create_test_user


def _make_patient(db, user_id=None) -> Patient:
    patient = Patient(
        full_name="Test Patient",
        date_of_birth=date(1990, 1, 1),
        gender="male",
        user_id=user_id,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _seed_allergy(db, patient_id, nurse, **overrides) -> Allergy:
    defaults = dict(
        patient_id=patient_id,
        substance="Penicillin",
        category="medication",
        criticality="high",
        severity="severe",
        reaction="anaphylaxis",
        onset=None,
        notes="",
        recorded_by=nurse,
    )
    defaults.update(overrides)
    return allergy_service.create_allergy(db, **defaults)


class TestAllergyService:
    def test_create_and_list_active(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse)
        _seed_allergy(db, patient.id, nurse, substance="Peanuts", category="food")

        allergies, total = allergy_service.list_allergies(
            db, patient_id=patient.id, include_inactive=False, limit=10, offset=0
        )
        assert total == 2
        assert len(allergies) == 2

    def test_list_excludes_inactive_by_default(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        a = _seed_allergy(db, patient.id, nurse)
        allergy_service.deactivate_allergy(db, a.id)

        allergies, total = allergy_service.list_allergies(
            db, patient_id=patient.id, include_inactive=False, limit=10, offset=0
        )
        assert total == 0

        allergies, total = allergy_service.list_allergies(
            db, patient_id=patient.id, include_inactive=True, limit=10, offset=0
        )
        assert total == 1
        assert allergies[0].status == "inactive"

    def test_contraindication_match_substring(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse, substance="Penicillin")

        # "Amoxicillin-Penicillin 500mg" contains "penicillin"
        matches = allergy_service.check_medication_contraindications(
            db, patient_id=patient.id, medication_name="Amoxicillin-Penicillin 500mg"
        )
        assert len(matches) == 1
        assert matches[0].substance == "Penicillin"

    def test_contraindication_match_case_insensitive(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse, substance="ASPIRIN")

        matches = allergy_service.check_medication_contraindications(
            db, patient_id=patient.id, medication_name="aspirin 81mg"
        )
        assert len(matches) == 1

    def test_contraindication_no_match(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse, substance="Penicillin")

        matches = allergy_service.check_medication_contraindications(
            db, patient_id=patient.id, medication_name="Ibuprofen"
        )
        assert matches == []

    def test_contraindication_ignores_inactive(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        a = _seed_allergy(db, patient.id, nurse, substance="Penicillin")
        allergy_service.deactivate_allergy(db, a.id)

        matches = allergy_service.check_medication_contraindications(
            db, patient_id=patient.id, medication_name="Penicillin 500mg"
        )
        assert matches == []


class TestAllergyEndpoints:
    def test_create_as_nurse(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        resp = client.post(
            "/api/v1/allergies",
            json={
                "patient_id": patient.id,
                "substance": "Latex",
                "category": "biologic",
                "severity": "severe",
            },
            headers=auth_header(nurse),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["substance"] == "Latex"
        assert data["status"] == "active"
        assert data["recorded_by"] == nurse.id

    def test_create_as_patient_forbidden(self, client, db):
        patient_user = create_test_user(db, role="patient")
        patient = _make_patient(db, user_id=patient_user.id)
        resp = client.post(
            "/api/v1/allergies",
            json={"patient_id": patient.id, "substance": "Peanuts"},
            headers=auth_header(patient_user),
        )
        assert resp.status_code == 403

    def test_list_requires_patient_scope(self, client, db):
        patient_a_user = create_test_user(db, role="patient", email="a@test.com")
        patient_b_user = create_test_user(db, role="patient", email="b@test.com")
        nurse = create_test_user(db, role="nurse")
        _make_patient(db, user_id=patient_a_user.id)
        patient_b = _make_patient(db, user_id=patient_b_user.id)
        _seed_allergy(db, patient_b.id, nurse)

        resp = client.get(
            f"/api/v1/allergies?patient_id={patient_b.id}",
            headers=auth_header(patient_a_user),
        )
        assert resp.status_code == 403

    def test_update_and_deactivate(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        a = _seed_allergy(db, patient.id, nurse)

        upd = client.patch(
            f"/api/v1/allergies/{a.id}",
            json={"severity": "mild", "notes": "mild rash only"},
            headers=auth_header(nurse),
        )
        assert upd.status_code == 200
        assert upd.json()["severity"] == "mild"

        delete = client.delete(f"/api/v1/allergies/{a.id}", headers=auth_header(nurse))
        assert delete.status_code == 200
        assert delete.json()["status"] == "inactive"


class TestMedicationContraindicationFlow:
    def test_create_medication_returns_allergy_alert(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse, substance="Penicillin", criticality="high", severity="severe")

        resp = client.post(
            "/api/v1/medications/reminders",
            json={
                "patient_id": patient.id,
                "medication_name": "Penicillin 500mg",
                "dosage": "500mg",
                "frequency": "twice_daily",
                "times": ["08:00:00", "20:00:00"],
                "start_date": "2026-04-21",
                "end_date": "2026-04-28",
            },
            headers=auth_header(nurse),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["allergy_alerts"]) == 1
        assert data["allergy_alerts"][0]["substance"] == "Penicillin"
        assert data["allergy_alerts"][0]["severity"] == "severe"

    def test_create_medication_no_alert_when_no_match(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        _seed_allergy(db, patient.id, nurse, substance="Penicillin")

        resp = client.post(
            "/api/v1/medications/reminders",
            json={
                "patient_id": patient.id,
                "medication_name": "Ibuprofen 200mg",
                "dosage": "200mg",
                "frequency": "three_times_daily",
                "times": ["08:00:00", "14:00:00", "20:00:00"],
                "start_date": "2026-04-21",
                "end_date": "2026-04-28",
            },
            headers=auth_header(nurse),
        )
        assert resp.status_code == 201
        assert resp.json()["allergy_alerts"] == []
