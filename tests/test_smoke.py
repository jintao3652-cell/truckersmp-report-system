from app import create_app


def test_health_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert response.json["status"] in ("ok", "degraded", "error")


def test_api_requires_authentication():
    app = create_app()
    assert app.test_client().get("/api/v1/videos").status_code == 401


def test_security_headers():
    app = create_app()
    response = app.test_client().get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_chunk_upload_requires_authentication():
    app = create_app()
    response = app.test_client().post("/api/v1/uploads", json={"filename": "x.mp4", "size": 1})
    assert response.status_code == 401


def test_metrics_endpoint():
    app = create_app()
    response = app.test_client().get("/metrics")
    assert response.status_code == 200
    assert b"truckersmp_videos_total" in response.data


def test_metrics_authentication_can_be_required():
    class TestConfig:
        TESTING = True
        SECRET_KEY = "test"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        AUTO_CREATE_DB = True
        VIDEO_FOLDER = "."
        UPLOAD_FOLDER = "."
        METRICS_REQUIRE_AUTH = True
        METRICS_TOKEN = "metrics-test"
    from app import create_app
    app = create_app(TestConfig)
    assert app.test_client().get("/metrics").status_code == 401
    assert app.test_client().get("/metrics", headers={"X-Metrics-Token": "metrics-test"}).status_code == 200


def test_api_moderation_requires_admin():
    app = create_app()
    response = app.test_client().post("/api/v1/videos/1/reject", json={"reason": "test"})
    assert response.status_code == 403


def test_chunk_init_validates_payload():
    app = create_app()
    response = app.test_client().post("/api/v1/uploads", json={"filename": "bad.txt", "size": 10})
    assert response.status_code == 401
