from tests.conftest import auth_header, create_test_user


def _mk_patient(client, headers, name="Trend Patient"):
    resp = client.post(
        "/api/v1/patients",
        json={"full_name": name, "date_of_birth": "1990-01-01", "gender": "male"},
        headers=headers,
    )
    return resp.json()["id"]


def _mk_vital(client, headers, pid, hr=75):
    return client.post(
        "/api/v1/metrics/vitals",
        json={
            "patient_id": pid,
            "heart_rate": hr,
            "blood_pressure_systolic": 115,
            "blood_pressure_diastolic": 75,
            "temperature_c": 36.8,
            "respiratory_rate": 16,
            "oxygen_saturation": 98,
        },
        headers=headers,
    )


class TestVitalsTrend:
    def test_trend_returns_series(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = _mk_patient(client, headers)
        for hr in (70, 75, 80):
            _mk_vital(client, headers, pid, hr=hr)

        resp = client.get(f"/api/v1/metrics/vitals/{pid}/trend?vital=heart_rate", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["vital"] == "heart_rate"
        assert data["unit"] == "bpm"
        assert data["count"] == 3
        assert [p["value"] for p in data["points"]] == [70, 75, 80]

    def test_trend_unknown_vital(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = _mk_patient(client, headers)
        resp = client.get(f"/api/v1/metrics/vitals/{pid}/trend?vital=mood", headers=headers)
        assert resp.status_code == 422

    def test_trend_patient_not_found(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        resp = client.get("/api/v1/metrics/vitals/nonexistent/trend?vital=heart_rate", headers=headers)
        assert resp.status_code == 404

    def test_trend_requires_auth(self, client):
        resp = client.get("/api/v1/metrics/vitals/any/trend?vital=heart_rate")
        assert resp.status_code == 401

    def test_trend_patient_cannot_view_other(self, client, db):
        nurse = create_test_user(db, role="nurse")
        pid = _mk_patient(client, auth_header(nurse))

        other_patient = create_test_user(db, role="patient", email="p@test.com")
        resp = client.get(
            f"/api/v1/metrics/vitals/{pid}/trend?vital=heart_rate",
            headers=auth_header(other_patient),
        )
        assert resp.status_code == 403

    def test_trend_empty_when_no_records(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = _mk_patient(client, headers)
        resp = client.get(f"/api/v1/metrics/vitals/{pid}/trend?vital=heart_rate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["points"] == []

    def test_trend_each_vital(self, client, db):
        nurse = create_test_user(db, role="nurse")
        headers = auth_header(nurse)
        pid = _mk_patient(client, headers)
        _mk_vital(client, headers, pid)
        for vital in (
            "heart_rate",
            "bp_systolic",
            "bp_diastolic",
            "temperature_c",
            "respiratory_rate",
            "oxygen_saturation",
        ):
            resp = client.get(f"/api/v1/metrics/vitals/{pid}/trend?vital={vital}", headers=headers)
            assert resp.status_code == 200, f"Failed for {vital}"
            assert resp.json()["count"] == 1
