from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import Department, Company
from src.core.repositories.base_repository import BaseRepository

departments_bp = Blueprint("departments", __name__, url_prefix="/departments")


@departments_bp.route("/")
@login_required
def departments_list():
    with session_scope() as session:
        departments = session.query(Department).filter(
            Department.is_deleted == False
        ).order_by(Department.sort_order, Department.created_at.desc()).all()
    return render_template("departments/list.html", departments=departments)


@departments_bp.route("/add", methods=["GET", "POST"])
@login_required
def departments_add():
    with session_scope() as session:
        companies = session.query(Company).filter(Company.is_deleted == False).all()
        departments = session.query(Department).filter(Department.is_deleted == False).all()

        if request.method == "POST":
            name_ar = request.form.get("name_ar", "").strip()
            code = request.form.get("code", "").strip()
            company_id = request.form.get("company_id", "").strip()
            if not name_ar or not code or not company_id:
                flash("اسم القسم والكود والشركة مطلوبان", "danger")
                return render_template("departments/form.html", companies=companies, departments=departments, department=None)

            repo = BaseRepository(session, Department)
            dept = repo.create(
                name_ar=name_ar,
                name_en=request.form.get("name_en", "").strip() or None,
                code=code,
                company_id=company_id,
                parent_department_id=request.form.get("parent_department_id", "").strip() or None,
                manager_id=request.form.get("manager_id", "").strip() or None,
                location=request.form.get("location", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                description=request.form.get("description", "").strip() or None,
                sort_order=int(request.form.get("sort_order") or 0),
                created_by=current_user.id,
            )
            flash(f"تم إضافة القسم {name_ar} بنجاح", "success")
            return redirect(url_for("departments.departments_list"))

    return render_template("departments/form.html", companies=companies, departments=departments, department=None)


@departments_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def departments_edit(id):
    with session_scope() as session:
        department = session.query(Department).filter(Department.id == id, Department.is_deleted == False).first()
        if not department:
            flash("القسم غير موجود", "danger")
            return redirect(url_for("departments.departments_list"))

        companies = session.query(Company).filter(Company.is_deleted == False).all()
        departments_list = session.query(Department).filter(
            Department.is_deleted == False, Department.id != id
        ).all()

        if request.method == "POST":
            name_ar = request.form.get("name_ar", "").strip()
            code = request.form.get("code", "").strip()
            if not name_ar or not code:
                flash("اسم القسم والكود مطلوبان", "danger")
                return render_template("departments/form.html", companies=companies, departments=departments_list, department=department)

            repo = BaseRepository(session, Department)
            repo.update(id,
                name_ar=name_ar,
                name_en=request.form.get("name_en", "").strip() or None,
                code=code,
                company_id=request.form.get("company_id", "").strip() or department.company_id,
                parent_department_id=request.form.get("parent_department_id", "").strip() or None,
                manager_id=request.form.get("manager_id", "").strip() or None,
                location=request.form.get("location", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                description=request.form.get("description", "").strip() or None,
                sort_order=int(request.form.get("sort_order") or 0),
                updated_by=current_user.id,
            )
            flash(f"تم تعديل القسم {name_ar} بنجاح", "success")
            return redirect(url_for("departments.departments_list"))

    return render_template("departments/form.html", companies=companies, departments=departments_list, department=department)


@departments_bp.route("/<id>/delete", methods=["POST"])
@login_required
def departments_delete(id):
    with session_scope() as session:
        repo = BaseRepository(session, Department)
        if repo.delete(id, soft=True):
            flash("تم حذف القسم بنجاح", "success")
        else:
            flash("لم يتم العثور على القسم", "danger")
    return redirect(url_for("departments.departments_list"))
