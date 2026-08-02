from flask import Blueprint, redirect, render_template, request, session, url_for
from urllib.parse import urlparse

main_bp = Blueprint("main", __name__)

@main_bp.get("/language/<lang>")
def language(lang):
    if lang in {"zh", "en"}:
        session["lang"] = lang
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if parsed.netloc and parsed.netloc != request.host:
            referrer = None
    return redirect(referrer or url_for("main.index"))


@main_bp.route("/")
def index():
    return render_template("index.html")
