import hashlib
import secrets
from datetime import timedelta
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse

from .. import db
from ..forms import LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm
from ..models import LoginAudit, PasswordResetToken, User
from ..utils import check_rate_limit, send_email, utcnow

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        allowed, retry = check_rate_limit(current_app, "register", request.remote_addr)
        if not allowed:
            flash(f"注册尝试过于频繁，请 {retry} 秒后再试。", "warning")
            return render_template("register.html", form=form), 429
        exists = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if exists:
            flash("用户名或邮箱已存在。", "danger")
            return render_template("register.html", form=form)

        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            password_hash=generate_password_hash(form.password.data),
        )
        db.session.add(user)
        db.session.commit()
        send_email(current_app, user.email, "注册成功", f"你好 {user.username}，欢迎注册 TruckersMP 举报系统。")
        flash("注册成功，请登录。", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        allowed, retry = check_rate_limit(current_app, "login", request.remote_addr)
        if not allowed:
            flash(f"登录尝试过于频繁，请 {retry} 秒后再试。", "warning")
            return render_template("login.html", form=form), 429
        ident = form.username_or_email.data.strip()
        user = User.query.filter((User.username == ident) | (User.email == ident.lower())).first()
        success = bool(user and check_password_hash(user.password_hash, form.password.data))
        audit = LoginAudit(
            username_input=ident[:120], user_id=user.id if success else None, success=success,
            ip_address=(request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip())[:64],
            user_agent=request.user_agent.string[:500], accept_language=request.headers.get("Accept-Language", "")[:255],
            referrer=request.referrer or "", device_type=_device_type(request.user_agent.string),
        )
        db.session.add(audit)
        db.session.commit()
        if success:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if next_page:
                parsed = urlparse(next_page)
                if parsed.netloc or parsed.scheme or not next_page.startswith("/"):
                    next_page = None
            return redirect(next_page or url_for("main.index"))
        flash("用户名、邮箱或密码不正确。", "danger")
    return render_template("login.html", form=form)


def _device_type(user_agent):
    value = (user_agent or "").lower()
    if "bot" in value or "spider" in value:
        return "bot"
    if "mobile" in value or "android" in value or "iphone" in value:
        return "mobile"
    if value:
        return "desktop"
    return "unknown"


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_request():
    form = RequestResetForm()
    if form.validate_on_submit():
        allowed, retry = check_rate_limit(current_app, "reset", request.remote_addr)
        if not allowed:
            flash(f"请求过于频繁，请 {retry} 秒后再试。", "warning")
            return render_template("reset_request.html", form=form), 429
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            raw = secrets.token_urlsafe(32)
            token = PasswordResetToken(token_hash=hashlib.sha256(raw.encode()).hexdigest(), user=user, expires_at=utcnow() + timedelta(minutes=current_app.config["MAIL_RESET_EXPIRES_MINUTES"]))
            db.session.add(token)
            db.session.commit()
            link = url_for("auth.reset_password", token=raw, _external=True)
            send_email(current_app, user.email, "重置密码", f"请在 {current_app.config['MAIL_RESET_EXPIRES_MINUTES']} 分钟内打开：{link}")
        flash("如果邮箱存在，重置链接已发送。", "info")
        return redirect(url_for("auth.login"))
    return render_template("reset_request.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    record = PasswordResetToken.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest(), used_at=None).first()
    if not record or record.expires_at < utcnow():
        flash("重置链接无效或已过期。", "danger")
        return redirect(url_for("auth.reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        record.user.password_hash = generate_password_hash(form.password.data)
        record.used_at = utcnow()
        db.session.commit()
        flash("密码已重置，请登录。", "success")
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("已退出登录。", "info")
    return redirect(url_for("main.index"))
