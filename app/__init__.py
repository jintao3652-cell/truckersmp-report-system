import os
from flask import Flask, render_template, request, session
from pathlib import Path
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .i18n import translate, translate_error

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)
    if app.config.get("SENTRY_DSN"):
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=app.config["SENTRY_DSN"], traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")))
        except ImportError:
            app.logger.warning("SENTRY_DSN configured but sentry-sdk is not installed")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    if app.config["ENVIRONMENT"] == "production" and not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set in production")
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = "development-only-change-me"
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["VIDEO_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def translations():
        lang = session.get("lang") or request.accept_languages.best_match(["zh", "en"]) or "zh"
        return {"lang": lang, "t": lambda key: translate(lang, key), "te": lambda message: translate_error(lang, message)}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; script-src 'self'; media-src 'self' blob:; img-src 'self' data:")
        if app.config["ENVIRONMENT"] == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.get("/health")
    def health():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            video_dir = Path(app.config["VIDEO_FOLDER"])
            exists, writable = video_dir.exists(), os.access(video_dir, os.W_OK)
            status = "ok" if exists and writable else "degraded"
            return {"status": status, "database": "ok", "video_folder": exists, "writable": writable}, (200 if status == "ok" else 503)
        except Exception:
            return {"status": "error"}, 503

    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.video import video_bp
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.api_v2 import api_v2_bp
    from .routes.metrics import metrics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(video_bp, url_prefix="/videos")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v2_bp)
    # API clients authenticate with bearer tokens; browser forms remain CSRF protected.
    csrf.exempt(api_bp)
    app.register_blueprint(metrics_bp)

    if app.config["AUTO_CREATE_DB"]:
        with app.app_context():
            from . import models
            db.create_all()

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="页面不存在"), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", code=413, message="文件超过允许大小"), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("error.html", code=500, message="服务器暂时不可用"), 500

    return app
