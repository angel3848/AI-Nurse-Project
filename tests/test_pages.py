class TestStaticPages:
    def test_index_served(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_audit_viewer_served(self, client):
        resp = client.get("/audit")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Audit Log" in resp.text
