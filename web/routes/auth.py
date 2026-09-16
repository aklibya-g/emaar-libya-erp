from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from src.core.database.connection import session_scope
from src.core.security.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("يرجى إدخال اسم المستخدم وكلمة المرور", "danger")
            return render_template("auth/login.html")

        with session_scope() as session:
            auth_service = AuthService(session)
            user = auth_service.authenticate(username, password)
            if user:
                from web.app import FlaskUser
                flask_user = FlaskUser(user)
                login_user(flask_user, remember=bool(request.form.get("remember")))
                flash(f"مرحباً {user.full_name_ar}", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard.dashboard_view"))
            else:
                flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح", "info")
    return redirect(url_for("auth.login"))
