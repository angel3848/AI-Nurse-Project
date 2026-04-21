from datetime import date

import pytest
from fastapi import HTTPException

from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.triage import TriageRecord
from app.services import encounter_service
from tests.conftest import auth_header, create_test_user


NORMAL_VITALS = {
    "heart_rate": 75,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "temperature_c": 36.8,
    "respiratory_rate": 16,
    "oxygen_saturation": 98,
}


def _make_patient(db, user_id: str | None = None) -> Patient:
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


class TestEncounterService:
    def test_open_encounter_defaults(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)

        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=nurse)
        assert enc.status == "in-progress"
        assert enc.encounter_class == "emergency"
        assert enc.opened_by == nurse.id
        assert enc.period_start is not None
        assert enc.period_end is None

    def test_assert_encounter_open_missing(self, db):
        patient = _make_patient(db)
        with pytest.raises(HTTPException) as exc_info:
            encounter_service.assert_encounter_open(db, "nonexistent", patient.id)
        assert exc_info.value.status_code == 404

    def test_assert_encounter_open_wrong_patient(self, db):
        nurse = create_test_user(db, role="nurse")
        patient_a = _make_patient(db)
        patient_b = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient_a.id, opened_by=nurse)

        with pytest.raises(HTTPException) as exc_info:
            encounter_service.assert_encounter_open(db, enc.id, patient_b.id)
        assert exc_info.value.status_code == 400

    def test_assert_encounter_open_completed(self, db):
        doctor = create_test_user(db, role="doctor")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)
        encounter_service.close_encounter(
            db,
            encounter_id=enc.id,
            disposition="discharged_home",
            disposition_notes="",
            closed_by=doctor,
        )
        with pytest.raises(HTTPException) as exc_info:
            encounter_service.assert_encounter_open(db, enc.id, patient.id)
        assert exc_info.value.status_code == 409

    def test_close_auto_completes_open_triage(self, db):
        doctor = create_test_user(db, role="doctor")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)

        # Seed two triage records: one waiting, one already completed
        waiting = TriageRecord(
            patient_id=patient.id,
            encounter_id=enc.id,
            chief_complaint="chest pain",
            symptoms=["chest_pain"],
            symptom_duration="30 min",
            pain_scale=6,
            heart_rate=90,
            bp_systolic=130,
            bp_diastolic=85,
            temperature_c=37.0,
            respiratory_rate=18,
            oxygen_saturation=97,
            priority_level=2,
            priority_label="Emergent",
            recommended_action="immediate",
            flags=[],
            status="waiting",
        )
        already_done = TriageRecord(
            patient_id=patient.id,
            encounter_id=enc.id,
            chief_complaint="prior",
            symptoms=["fatigue"],
            symptom_duration="1h",
            pain_scale=1,
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            temperature_c=36.8,
            respiratory_rate=16,
            oxygen_saturation=98,
            priority_level=5,
            priority_label="Non-urgent",
            recommended_action="routine",
            flags=[],
            status="completed",
        )
        db.add_all([waiting, already_done])
        db.commit()

        encounter_service.close_encounter(
            db,
            encounter_id=enc.id,
            disposition="admitted",
            disposition_notes="ward 3",
            closed_by=doctor,
        )
        db.refresh(waiting)
        db.refresh(already_done)
        assert waiting.status == "completed"
        assert already_done.status == "completed"  # unchanged, still completed

    def test_close_twice_rejects(self, db):
        doctor = create_test_user(db, role="doctor")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)
        encounter_service.close_encounter(
            db,
            encounter_id=enc.id,
            disposition="discharged_home",
            disposition_notes="",
            closed_by=doctor,
        )
        with pytest.raises(HTTPException) as exc_info:
            encounter_service.close_encounter(
                db,
                encounter_id=enc.id,
                disposition="discharged_home",
                disposition_notes="",
                closed_by=doctor,
            )
        assert exc_info.value.status_code == 409

    def test_list_pagination(self, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        for _ in range(5):
            encounter_service.open_encounter(db, patient_id=patient.id, opened_by=nurse)

        encounters, total = encounter_service.list_encounters(
            db,
            patient_id=patient.id,
            status=None,
            start_after=None,
            start_before=None,
            limit=2,
            offset=0,
        )
        assert total == 5
        assert len(encounters) == 2


class TestEncounterEndpoints:
    def test_create_as_nurse(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)

        resp = client.post(
            "/api/v1/encounters",
            json={"patient_id": patient.id, "reason_code": "chest pain"},
            headers=auth_header(nurse),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "in-progress"
        assert data["opened_by"] == nurse.id

    def test_create_as_patient_forbidden(self, client, db):
        patient_user = create_test_user(db, role="patient")
        patient = _make_patient(db, user_id=patient_user.id)
        resp = client.post(
            "/api/v1/encounters",
            json={"patient_id": patient.id},
            headers=auth_header(patient_user),
        )
        assert resp.status_code == 403

    def test_create_missing_patient(self, client, db):
        nurse = create_test_user(db, role="nurse")
        resp = client.post(
            "/api/v1/encounters",
            json={"patient_id": "does-not-exist"},
            headers=auth_header(nurse),
        )
        assert resp.status_code == 404

    def test_close_as_nurse_forbidden(self, client, db):
        nurse = create_test_user(db, role="nurse")
        doctor = create_test_user(db, role="doctor", email="doc@test.com")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)

        resp = client.patch(
            f"/api/v1/encounters/{enc.id}/close",
            json={"disposition": "discharged_home"},
            headers=auth_header(nurse),
        )
        assert resp.status_code == 403

    def test_close_as_doctor(self, client, db):
        doctor = create_test_user(db, role="doctor")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)

        resp = client.patch(
            f"/api/v1/encounters/{enc.id}/close",
            json={"disposition": "discharged_home", "disposition_notes": "follow up"},
            headers=auth_header(doctor),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["disposition"] == "discharged_home"
        assert data["period_end"] is not None

    def test_get_detail_with_nested_records(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=nurse)

        # Add a triage record directly
        record = TriageRecord(
            patient_id=patient.id,
            encounter_id=enc.id,
            chief_complaint="cough",
            symptoms=["cough"],
            symptom_duration="2d",
            pain_scale=1,
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            temperature_c=36.8,
            respiratory_rate=16,
            oxygen_saturation=98,
            priority_level=4,
            priority_label="Less Urgent",
            recommended_action="primary care",
            flags=[],
        )
        db.add(record)
        db.commit()

        resp = client.get(f"/api/v1/encounters/{enc.id}", headers=auth_header(nurse))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["triage_records"]) == 1
        assert data["triage_records"][0]["chief_complaint"] == "cough"

    def test_list_filters_by_patient(self, client, db):
        nurse = create_test_user(db, role="nurse")
        p1 = _make_patient(db)
        p2 = _make_patient(db)
        encounter_service.open_encounter(db, patient_id=p1.id, opened_by=nurse)
        encounter_service.open_encounter(db, patient_id=p1.id, opened_by=nurse)
        encounter_service.open_encounter(db, patient_id=p2.id, opened_by=nurse)

        resp = client.get(
            f"/api/v1/encounters?patient_id={p1.id}",
            headers=auth_header(nurse),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_patient_can_only_see_own(self, client, db):
        patient_user_a = create_test_user(db, role="patient", email="a@test.com")
        patient_user_b = create_test_user(db, role="patient", email="b@test.com")
        nurse = create_test_user(db, role="nurse")
        patient_a = _make_patient(db, user_id=patient_user_a.id)
        patient_b = _make_patient(db, user_id=patient_user_b.id)
        encounter_service.open_encounter(db, patient_id=patient_a.id, opened_by=nurse)
        encounter_service.open_encounter(db, patient_id=patient_b.id, opened_by=nurse)

        # Patient A requests B's encounters → 403
        resp = client.get(
            f"/api/v1/encounters?patient_id={patient_b.id}",
            headers=auth_header(patient_user_a),
        )
        assert resp.status_code == 403

        # Patient A requests own → only their encounter
        resp = client.get(
            "/api/v1/encounters",
            headers=auth_header(patient_user_a),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestTriageAutoOpensEncounter:
    def test_triage_without_encounter_id_auto_opens(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)

        resp = client.post(
            "/api/v1/triage",
            json={
                "patient_id": patient.id,
                "patient_name": patient.full_name,
                "chief_complaint": "Severe chest pain",
                "symptoms": ["chest_pain"],
                "symptom_duration": "30 minutes",
                "vitals": NORMAL_VITALS,
                "pain_scale": 8,
                "age": 55,
            },
            headers=auth_header(nurse),
        )
        assert resp.status_code == 200

        records = db.query(TriageRecord).filter(TriageRecord.patient_id == patient.id).all()
        assert len(records) == 1
        assert records[0].encounter_id is not None

        encounter = db.query(Encounter).filter(Encounter.id == records[0].encounter_id).first()
        assert encounter is not None
        assert encounter.status == "in-progress"
        assert "chest pain" in encounter.reason_code.lower()

    def test_triage_with_explicit_encounter_id(self, client, db):
        nurse = create_test_user(db, role="nurse")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=nurse)

        resp = client.post(
            "/api/v1/triage",
            json={
                "patient_id": patient.id,
                "encounter_id": enc.id,
                "patient_name": patient.full_name,
                "chief_complaint": "Follow-up pain",
                "symptoms": ["headache"],
                "symptom_duration": "2h",
                "vitals": NORMAL_VITALS,
                "pain_scale": 4,
                "age": 40,
            },
            headers=auth_header(nurse),
        )
        assert resp.status_code == 200

        record = db.query(TriageRecord).filter(TriageRecord.patient_id == patient.id).first()
        assert record.encounter_id == enc.id

    def test_triage_with_closed_encounter_rejected(self, client, db):
        doctor = create_test_user(db, role="doctor")
        patient = _make_patient(db)
        enc = encounter_service.open_encounter(db, patient_id=patient.id, opened_by=doctor)
        encounter_service.close_encounter(
            db,
            encounter_id=enc.id,
            disposition="discharged_home",
            disposition_notes="",
            closed_by=doctor,
        )

        resp = client.post(
            "/api/v1/triage",
            json={
                "patient_id": patient.id,
                "encounter_id": enc.id,
                "patient_name": patient.full_name,
                "chief_complaint": "something",
                "symptoms": ["headache"],
                "symptom_duration": "1h",
                "vitals": NORMAL_VITALS,
                "pain_scale": 3,
                "age": 40,
            },
            headers=auth_header(doctor),
        )
        assert resp.status_code == 409
