from app import create_app


def test_share_url_is_not_returned_for_pending_video():
    app = create_app()
    assert app.test_client().get("/api/v1/videos/999999").status_code in (401, 404)


def test_metrics_requires_token_in_production_config():
    class Config:
        TESTING = True
        SECRET_KEY = "test"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        AUTO_CREATE_DB = True
        UPLOAD_FOLDER = "."
        VIDEO_FOLDER = "."
        METRICS_REQUIRE_AUTH = True
        METRICS_TOKEN = "secret"
    app = create_app(Config)
    client = app.test_client()
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"X-Metrics-Token": "secret"}).status_code == 200
