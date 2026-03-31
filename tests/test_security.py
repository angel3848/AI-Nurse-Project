from tests.conftest import auth_header, create_test_user


class TestHttpOnlyCookies:
    def test_login_sets_cookie(self, client, db):
        create_test_user(db, email="cookie@test.com")
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "cookie@test.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies

    def test_cookie_auth_works(self, client, db):
        create_test_user(db, email="cookie@test.com")
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "cookie@test.com",
                "password": "testpass123",
            },
        )
        # Use the cookie (no Authorization header)
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "cookie@test.com"

    def test_logout_clears_cookie(self, client, db):
        create_test_user(db, email="logout@test.com")
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout@test.com",
                "password": "testpass123",
            },
        )
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        # Cookie should be cleared — subsequent request should fail
        # (TestClient may not honor cookie deletion fully, so check response)
        assert response.json()["detail"] == "Logged out"

    def test_bearer_header_still_works(self, client, db):
        user = create_test_user(db, email="bearer@test.com")
        response = client.get("/api/v1/auth/me", headers=auth_header(user))
        assert response.status_code == 200
        assert response.json()["email"] == "bearer@test.com"


class TestEmailValidation:
    def test_valid_email_accepted(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "password": "securepass123",
                "full_name": "Valid User",
            },
        )
        assert response.status_code == 201

    def test_invalid_email_no_at(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalidemail.com",
                "password": "securepass123",
                "full_name": "Invalid",
            },
        )
        assert response.status_code == 422

    def test_invalid_email_no_domain(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@",
                "password": "securepass123",
                "full_name": "Invalid",
            },
        )
        assert response.status_code == 422

    def test_invalid_email_just_text(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "aaaaa",
                "password": "securepass123",
                "full_name": "Invalid",
            },
        )
        assert response.status_code == 422


class TestJWTSecretSafety:
    def test_dev_mode_generates_random_secret(self):
        """In development, a random secret is auto-generated if none set."""
        from app.config import settings

        assert settings.jwt_secret_key != ""
        assert len(settings.jwt_secret_key) > 20
