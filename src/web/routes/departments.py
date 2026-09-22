from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from src.core.database.connection import get_web_session
from src.core.models.base_models import Department, Company
from src.core.repositories.base_repository import BaseRepository

departments_bp = Blueprint("departments", __name__, url_prefix="/departments")


def _next_dept_code(session):
    from sqlalchemy import func
    last = session.query(Department.code).filter(
        Department.is_deleted == False
    ).order_by(Department.created_at.desc()).first()
    if last and last[0]:
        code = last[0]
        import re
        m = re.match(r'^[A-Za-z]*(\d+)$', code)
        if m:
            num = int(m.group(1)) + 1
            return f"C{num:02d}"
    count = session.query(func.count(Department.id)).filter(Department.is_deleted == False).scalar() or 0
    return f"C{count + 1:02d}"


@departments_bp.route("/")
@login_required
def departments_list():
    session = get_web_session()
    departments = session.query(Department).filter(
        Department.is_deleted == False
    ).order_by(Department.sort_order, Department.created_at.desc()).all()
    companies = session.query(Company).filter(Company.is_deleted == False).all()
    return render_template("departments/list.html", departments=departments, companies=companies)


@departments_bp.route("/<id>")
@login_required
def departments_detail(id):
    session = get_web_session()
    department = session.query(Department).filter(Department.id == id, Department.is_deleted == False).first()
    if not department:
        flash("القسم غير موجود", "danger")
        return redirect(url_for("departments.departments_list"))
    return render_template("departments/detail.html", department=department)


@departments_bp.route("/add", methods=["GET", "POST"])
@login_required
def departments_add():
    session = get_web_session()
    companies = session.query(Company).filter(Company.is_deleted == False).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()
    next_code = _next_dept_code(session)

    if request.method == "POST":
        name_ar = request.form.get("name_ar", "").strip()
        code = request.form.get("code", "").strip()
        company_id = request.form.get("company_id", "").strip()
        if not name_ar or not code or not company_id:
            flash("اسم القسم والكود والشركة مطلوبان", "danger")
            return render_template("departments/form.html", companies=companies, departments=departments, department=None)

        repo = BaseRepository(session, Department)
        try:
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
            session.commit()
            flash(f"تم إضافة القسم {name_ar} بنجاح", "success")
            return redirect(url_for("departments.departments_list"))
        except IntegrityError:
            session.rollback()
            flash(f"كود القسم '{code}' موجود مسبقاً، يرجى استخدام كود آخر", "danger")
            return render_template("departments/form.html", companies=companies, departments=departments, department=None, next_code=next_code)
        except Exception as e:
            session.rollback()
            flash(f"حدث خطأ أثناء إضافة القسم: {str(e)}", "danger")
            return render_template("departments/form.html", companies=companies, departments=departments, department=None, next_code=next_code)

    return render_template("departments/form.html", companies=companies, departments=departments, department=None, next_code=next_code)


@departments_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def departments_edit(id):
    session = get_web_session()
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
        try:
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
            session.commit()
            flash(f"تم تعديل القسم {name_ar} بنجاح", "success")
            return redirect(url_for("departments.departments_list"))
        except IntegrityError:
            session.rollback()
            flash(f"كود القسم '{code}' موجود مسبقاً، يرجى استخدام كود آخر", "danger")
            return render_template("departments/form.html", companies=companies, departments=departments_list, department=department)
        except Exception as e:
            session.rollback()
            flash(f"حدث خطأ أثناء تعديل القسم: {str(e)}", "danger")
            return render_template("departments/form.html", companies=companies, departments=departments_list, department=department)

    return render_template("departments/form.html", companies=companies, departments=departments_list, department=department)


@departments_bp.route("/<id>/delete", methods=["POST"])
@login_required
def departments_delete(id):
    session = get_web_session()
    repo = BaseRepository(session, Department)
    if repo.delete(id, soft=True):
        session.commit()
        flash("تم حذف القسم بنجاح", "success")
    else:
        flash("لم يتم العثور على القسم", "danger")
    return redirect(url_for("departments.departments_list"))


@departments_bp.route("/api/quick-add", methods=["POST"])
@login_required
def departments_quick_add():
    session = get_web_session()
    data = request.get_json()
    name_ar = (data.get("name_ar") or "").strip()
    if not name_ar:
        return jsonify({"success": False, "message": "اسم القسم مطلوب"}), 400

    code = _next_dept_code(session)
    company = session.query(Company).filter(Company.is_deleted == False).first()

    dept = Department(
        name_ar=name_ar,
        code=code,
        company_id=company.id if company else None,
        created_by=current_user.id,
    )
    session.add(dept)
    session.commit()

    return jsonify({"success": True, "id": dept.id, "name_ar": dept.name_ar})


@departments_bp.route("/api/quick-add-company", methods=["POST"])
@login_required
def departments_quick_add_company():
    session = get_web_session()
    data = request.get_json()
    name_ar = (data.get("name_ar") or "").strip()
    if not name_ar:
        return jsonify({"success": False, "message": "اسم الشركة مطلوب"}), 400

    company = Company(
        name_ar=name_ar,
        created_by=current_user.id,
    )
    session.add(company)
    session.commit()

    return jsonify({"success": True, "id": company.id, "name_ar": company.name_ar})
