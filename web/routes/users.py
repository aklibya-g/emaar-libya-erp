from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import User, Role, Department
from src.core.security.auth_service import AuthService

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@login_required
def users_list():
    with session_scope() as session:
        users = session.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc()).all()
        roles = session.query(Role).filter(Role.is_active == True).all()
    return render_template("users/list.html", users=users, roles=roles)


@users_bp.route("/add", methods=["GET", "POST"])
@login_required
def users_add():
    with session_scope() as session:
        roles = session.query(Role).filter(Role.is_active == True).all()
        departments = session.query(Department).filter(Department.is_deleted == False).all()

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            full_name_ar = request.form.get("full_name_ar", "").strip()
            role_id = request.form.get("role_id", "").strip()

            if not username or not password or not full_name_ar:
                flash("اسم المستخدم وكلمة المرور والاسم مطلوبة", "danger")
                return render_template("users/form.html", roles=roles, departments=departments, user=None)

            auth_service = AuthService(session)
            try:
                user = auth_service.create_user(
                    username=username,
                    password=password,
                    full_name_ar=full_name_ar,
                    role_id=role_id or None,
                    full_name_en=request.form.get("full_name_en", "").strip() or None,
                    email=request.form.get("email", "").strip() or None,
                    phone=request.form.get("phone", "").strip() or None,
                    department_id=request.form.get("department_id", "").strip() or None,
                    created_by=current_user.id,
                )
                flash(f"تم إضافة المستخدم {username} بنجاح", "success")
                return redirect(url_for("users.users_list"))
            except Exception as e:
                flash(f"خطأ في إنشاء المستخدم: {str(e)}", "danger")

    return render_template("users/form.html", roles=roles, departments=departments, user=None)


@users_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def users_edit(id):
    with session_scope() as session:
        user = session.query(User).filter(User.id == id, User.is_deleted == False).first()
        if not user:
            flash("المستخدم غير موجود", "danger")
            return redirect(url_for("users.users_list"))

        roles = session.query(Role).filter(Role.is_active == True).all()
        departments = session.query(Department).filter(Department.is_deleted == False).all()

        if request.method == "POST":
            full_name_ar = request.form.get("full_name_ar", "").strip()
            if not full_name_ar:
                flash("الاسم مطلوب", "danger")
                return render_template("users/form.html", roles=roles, departments=departments, user=user)

            user.full_name_ar = full_name_ar
            user.full_name_en = request.form.get("full_name_en", "").strip() or None
            user.email = request.form.get("email", "").strip() or None
            user.phone = request.form.get("phone", "").strip() or None
            user.role_id = request.form.get("role_id", "").strip() or None
            user.department_id = request.form.get("department_id", "").strip() or None
            user.updated_by = current_user.id

            new_password = request.form.get("new_password", "").strip()
            if new_password:
                from src.core.security.auth_service import hash_password
                user.password_hash = hash_password(new_password)

            flash(f"تم تعديل بيانات المستخدم {user.username} بنجاح", "success")
            return redirect(url_for("users.users_list"))

    return render_template("users/form.html", roles=roles, departments=departments, user=user)


@users_bp.route("/<id>/delete", methods=["POST"])
@login_required
def users_delete(id):
    with session_scope() as session:
        user = session.query(User).filter(User.id == id, User.is_deleted == False).first()
        if user:
            user.is_deleted = True
            from datetime import datetime
            user.deleted_at = datetime.utcnow()
            user.deleted_by = current_user.id
            flash(f"تم حذف المستخدم {user.username} بنجاح", "success")
        else:
            flash("لم يتم العثور على المستخدم", "danger")
    return redirect(url_for("users.users_list"))


@users_bp.route("/<id>/reset-password", methods=["POST"])
@login_required
def users_reset_password(id):
    with session_scope() as session:
        user = session.query(User).filter(User.id == id, User.is_deleted == False).first()
        if not user:
            flash("المستخدم غير موجود", "danger")
            return redirect(url_for("users.users_list"))

        new_password = request.form.get("new_password", "").strip()
        if not new_password:
            flash("كلمة المرور الجديدة مطلوبة", "danger")
            return redirect(url_for("users.users_list"))

        auth_service = AuthService(session)
        if auth_service.change_password(id, new_password):
            flash(f"تم إعادة تعيين كلمة مرور المستخدم {user.username} بنجاح", "success")
        else:
            flash("فشل في إعادة تعيين كلمة المرور", "danger")

    return redirect(url_for("users.users_list"))
