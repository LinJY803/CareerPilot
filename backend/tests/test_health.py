def test_health_reports_database_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_failure(client, monkeypatch):
    def boom(_db):
        raise RuntimeError("down")

    monkeypatch.setattr("app.api.v1.routes.ping_database", boom)
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["detail"] == "数据库不可用"
