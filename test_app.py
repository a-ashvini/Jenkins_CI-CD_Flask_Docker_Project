import app as app_module

def test_home_returns_message_and_version(monkeypatch):
    monkeypatch.setattr(app_module, "APP_VERSION", "test-version")
    response = app_module.app.test_client().get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["version"] == "test-version"
    assert "Flask CI/CD" in data["message"]

def test_health_endpoint_is_healthy():
    response = app_module.app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}
