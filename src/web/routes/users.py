from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import User, Role, Department, UserSidebarPermission, UserCorrespondencePermission
from src.core.security.auth_service import AuthService

users_bp = Blueprint("users", __name__, url_prefix="/users")

SIDEBAR_MODULES = [
    {"key": "dashboard", "name": "الرئيسية", "icon": "bi-house"},
    {"key": "movement", "name": "ادارة الحركة", "icon": "bi-bus-front"},
    {"key": "hr", "name": "الموارد البشرية", "icon": "bi-people"},
    {"key": "marketing", "name": "التسويق", "icon": "bi-megaphone"},
    {"key": "correspondence", "name": "المراسلات", "icon": "bi-envelope"},
    {"key": "warehouses", "name": "المستودعات", "icon": "bi-box-seam"},
    {"key": "reports", "name": "التقارير", "icon": "bi-bar-chart"},
    {"key": "departments", "name": "الاقسام", "icon": "bi-diagram-3"},
    {"key": "users", "name": "المستخدمون", "icon": "bi-person-gear"},
    {"key": "settings", "name": "الاعدادات", "icon": "bi-gear"},
    {"key": "recycle", "name": "سلة المحذوفات", "icon": "bi-trash3"},
]


@users_bp.route("/")
@login_required
def users_list():
    session = get_web_session()
    users = session.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc()).all()
    for u in users:
        if u.department_id:
            u._dept = session.query(Department).filter(Department.id == u.department_id).first()
        else:
            u._dept = None
    return render_template("users/list.html", users=users)


@users_bp.route("/add", methods=["GET", "POST"])
@login_required
def users_add():
    session = get_web_session()
    roles = session.query(Role).filter(Role.is_active == True).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        full_name_ar = request.form.get("full_name_ar", "").strip()
        role_id = request.form.get("role_id", "").strip()

        if not username or not password or not full_name_ar:
            flash("اسم المستخدم وكلمة المرور والاسم مطلوبة", "danger")
            return render_template("users/form.html", roles=roles, departments=departments, user=None, sidebar_modules=SIDEBAR_MODULES)

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
            session.flush()

            for mod in SIDEBAR_MODULES:
                perm = UserSidebarPermission(
                    user_id=user.id,
                    module_name=mod["key"],
                    can_view=request.form.get(f"sidebar_{mod['key']}_view") == "on",
                    can_add=request.form.get(f"sidebar_{mod['key']}_add") == "on",
                    can_edit=request.form.get(f"sidebar_{mod['key']}_edit") == "on",
                    can_delete=request.form.get(f"sidebar_{mod['key']}_delete") == "on",
                )
                session.add(perm)

            for dept in departments:
                if request.form.get(f"corr_{dept.id}_send") or request.form.get(f"corr_{dept.id}_receive"):
                    corr = UserCorrespondencePermission(
                        user_id=user.id,
                        target_department_id=dept.id,
                        can_send=request.form.get(f"corr_{dept.id}_send") == "on",
                        can_receive=request.form.get(f"corr_{dept.id}_receive") == "on",
                    )
                    session.add(corr)

            session.commit()
            flash(f"تم إضافة المستخدم {username} بنجاح", "success")
            return redirect(url_for("users.users_list"))
        except Exception as e:
            flash(f"خطأ في إنشاء المستخدم: {str(e)}", "danger")

    return render_template("users/form.html", roles=roles, departments=departments, user=None, sidebar_modules=SIDEBAR_MODULES)


@users_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def users_edit(id):
    session = get_web_session()
    user = session.query(User).filter(User.id == id, User.is_deleted == False).first()
    if not user:
        flash("المستخدم غير موجود", "danger")
        return redirect(url_for("users.users_list"))

    roles = session.query(Role).filter(Role.is_active == True).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()

    sidebar_perms = {}
    for sp in session.query(UserSidebarPermission).filter(UserSidebarPermission.user_id == id).all():
        sidebar_perms[sp.module_name] = sp

    corr_perms = {}
    for cp in session.query(UserCorrespondencePermission).filter(UserCorrespondencePermission.user_id == id).all():
        corr_perms[cp.target_department_id] = cp

    if request.method == "POST":
        full_name_ar = request.form.get("full_name_ar", "").strip()
        if not full_name_ar:
            flash("الاسم مطلوب", "danger")
            return render_template("users/form.html", roles=roles, departments=departments, user=user, sidebar_modules=SIDEBAR_MODULES, sidebar_perms=sidebar_perms, corr_perms=corr_perms)

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

        for mod in SIDEBAR_MODULES:
            existing = session.query(UserSidebarPermission).filter(
                UserSidebarPermission.user_id == id,
                UserSidebarPermission.module_name == mod["key"]
            ).first()
            if existing:
                existing.can_view = request.form.get(f"sidebar_{mod['key']}_view") == "on"
                existing.can_add = request.form.get(f"sidebar_{mod['key']}_add") == "on"
                existing.can_edit = request.form.get(f"sidebar_{mod['key']}_edit") == "on"
                existing.can_delete = request.form.get(f"sidebar_{mod['key']}_delete") == "on"
            else:
                perm = UserSidebarPermission(
                    user_id=id,
                    module_name=mod["key"],
                    can_view=request.form.get(f"sidebar_{mod['key']}_view") == "on",
                    can_add=request.form.get(f"sidebar_{mod['key']}_add") == "on",
                    can_edit=request.form.get(f"sidebar_{mod['key']}_edit") == "on",
                    can_delete=request.form.get(f"sidebar_{mod['key']}_delete") == "on",
                )
                session.add(perm)

        for dept in departments:
            existing_corr = session.query(UserCorrespondencePermission).filter(
                UserCorrespondencePermission.user_id == id,
                UserCorrespondencePermission.target_department_id == dept.id
            ).first()
            has_perm = request.form.get(f"corr_{dept.id}_send") == "on" or request.form.get(f"corr_{dept.id}_receive") == "on"
            if has_perm:
                if existing_corr:
                    existing_corr.can_send = request.form.get(f"corr_{dept.id}_send") == "on"
                    existing_corr.can_receive = request.form.get(f"corr_{dept.id}_receive") == "on"
                else:
                    corr = UserCorrespondencePermission(
                        user_id=id,
                        target_department_id=dept.id,
                        can_send=request.form.get(f"corr_{dept.id}_send") == "on",
                        can_receive=request.form.get(f"corr_{dept.id}_receive") == "on",
                    )
                    session.add(corr)
            elif existing_corr:
                session.delete(existing_corr)

        session.commit()
        flash(f"تم تعديل بيانات المستخدم {user.username} بنجاح", "success")
        return redirect(url_for("users.users_list"))

    return render_template("users/form.html", roles=roles, departments=departments, user=user, sidebar_modules=SIDEBAR_MODULES, sidebar_perms=sidebar_perms, corr_perms=corr_perms)


@users_bp.route("/<id>/delete", methods=["POST"])
@login_required
def users_delete(id):
    session = get_web_session()
    user = session.query(User).filter(User.id == id, User.is_deleted == False).first()
    if user:
        from src.web.routes.recycle_bin import add_to_recycle_bin
        add_to_recycle_bin(session, "user", user.id, item_number=user.username, item_title=user.full_name_ar)
        user.is_deleted = True
        from datetime import datetime
        user.deleted_at = datetime.utcnow()
        user.deleted_by = current_user.id
        session.commit()
        flash(f"تم حذف المستخدم {user.username} بنجاح", "success")
    else:
        flash("لم يتم العثور على المستخدم", "danger")
    return redirect(url_for("users.users_list"))


@users_bp.route("/<id>/reset-password", methods=["POST"])
@login_required
def users_reset_password(id):
    session = get_web_session()
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
        session.commit()
        flash(f"تم إعادة تعيين كلمة مرور المستخدم {user.username} بنجاح", "success")
    else:
        flash("فشل في إعادة تعيين كلمة المرور", "danger")

    return redirect(url_for("users.users_list"))


@users_bp.route("/api/quick-add-role", methods=["POST"])
@login_required
def roles_quick_add():
    from flask import jsonify
    session = get_web_session()
    data = request.get_json()
    name_ar = (data.get("name_ar") or "").strip()
    if not name_ar:
        return jsonify({"success": False, "message": "اسم الدور مطلوب"}), 400

    existing = session.query(Role).filter(Role.name_ar == name_ar).first()
    if existing:
        return jsonify({"success": False, "message": "اسم الدور موجود مسبقاً"})

    name_en = name_ar
    role = Role(
        name=name_en,
        name_ar=name_ar,
    )
    session.add(role)
    session.commit()

    return jsonify({"success": True, "id": role.id, "name_ar": role.name_ar})
