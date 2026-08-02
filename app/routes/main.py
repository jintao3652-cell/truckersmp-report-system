from flask import Blueprint, redirect, render_template, request, session, url_for

main_bp = Blueprint("main", __name__)

@main_bp.get("/language/<lang>")
def language(lang):
    if lang in {"zh", "en"}:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/")
def index():
    return render_template("index.html")
