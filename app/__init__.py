import os
from flask import Flask, render_template
from pathlib import Path
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)
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

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; script-src 'self'; media-src 'self' blob:")
        if app.config["ENVIRONMENT"] == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.get("/health")
    def health():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            video_dir = Path(app.config["VIDEO_FOLDER"])
            return {"status": "ok", "database": "ok", "video_folder": video_dir.exists(), "writable": os.access(video_dir, os.W_OK)}
        except Exception:
            return {"status": "error"}, 503

    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.video import video_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(video_bp, url_prefix="/videos")
    app.register_blueprint(admin_bp, url_prefix="/admin")

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
