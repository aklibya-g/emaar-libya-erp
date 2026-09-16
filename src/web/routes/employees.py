from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from src.core.database.connection import get_web_session
from src.core.models.base_models import Employee, Department, Position
from src.core.repositories.base_repository import BaseRepository

employees_bp = Blueprint("employees", __name__, url_prefix="/employees")


@employees_bp.route("/")
@login_required
def employees_list():
    search = request.args.get("search", "").strip()
    department_id = request.args.get("department_id", "").strip()
    status = request.args.get("status", "").strip()

    session = get_web_session()
    repo = BaseRepository(session, Employee)
    q = session.query(Employee).filter(Employee.is_deleted == False)

    if search:
        q = q.filter(
            (Employee.full_name_ar.ilike(f"%{search}%")) |
            (Employee.employee_number.ilike(f"%{search}%")) |
            (Employee.phone.ilike(f"%{search}%")) |
            (Employee.national_id.ilike(f"%{search}%"))
        )
    if department_id:
        q = q.filter(Employee.department_id == department_id)
    if status:
        q = q.filter(Employee.status == status)
    else:
        q = q.filter(Employee.status == "active")

    employees = q.order_by(Employee.created_at.desc()).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()

    return render_template("employees/list.html",
        employees=employees, departments=departments,
        search=search, department_id=department_id, status=status)


@employees_bp.route("/add", methods=["GET", "POST"])
@login_required
def employees_add():
    session = get_web_session()
    departments = session.query(Department).filter(Department.is_deleted == False).all()
    positions = session.query(Position).filter(Position.is_active == True).all()

    if request.method == "POST":
        employee_number = request.form.get("employee_number", "").strip()
        full_name_ar = request.form.get("full_name_ar", "").strip()
        if not employee_number or not full_name_ar:
            flash("رقم الموظف والاسم بالعربي مطلوبان", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=None)

        hire_date_str = request.form.get("hire_date", "").strip()
        hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d").date() if hire_date_str else None

        dob_str = request.form.get("date_of_birth", "").strip()
        date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None

        repo = BaseRepository(session, Employee)
        try:
            employee = repo.create(
                employee_number=employee_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                mother_name=request.form.get("mother_name", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                gender=request.form.get("gender", "").strip() or None,
                nationality=request.form.get("nationality", "").strip() or None,
                marital_status=request.form.get("marital_status", "").strip() or None,
                department_id=request.form.get("department_id", "").strip() or None,
                position_id=request.form.get("position_id", "").strip() or None,
                date_of_birth=date_of_birth,
                place_of_birth=request.form.get("place_of_birth", "").strip() or None,
                hire_date=hire_date,
                contract_type=request.form.get("contract_type", "").strip() or None,
                salary=float(request.form.get("salary") or 0),
                status=request.form.get("status", "active"),
                notes=request.form.get("notes", "").strip() or None,
                created_by=current_user.id,
            )
            session.commit()
            flash(f"تم إضافة الموظف {full_name_ar} بنجاح", "success")
            return redirect(url_for("employees.employees_detail", id=employee.id))
        except IntegrityError:
            session.rollback()
            flash(f"رقم الموظف '{employee_number}' موجود مسبقاً", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=None)
        except Exception as e:
            session.rollback()
            flash(f"حدث خطأ: {str(e)}", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=None)

    return render_template("employees/form.html", departments=departments, positions=positions, employee=None)


@employees_bp.route("/<id>")
@login_required
def employees_detail(id):
    session = get_web_session()
    employee = session.query(Employee).filter(Employee.id == id, Employee.is_deleted == False).first()
    if not employee:
        flash("الموظف غير موجود", "danger")
        return redirect(url_for("employees.employees_list"))
    return render_template("employees/detail.html", employee=employee)


@employees_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def employees_edit(id):
    session = get_web_session()
    employee = session.query(Employee).filter(Employee.id == id, Employee.is_deleted == False).first()
    if not employee:
        flash("المو��ف غير موجود", "danger")
        return redirect(url_for("employees.employees_list"))

    departments = session.query(Department).filter(Department.is_deleted == False).all()
    positions = session.query(Position).filter(Position.is_active == True).all()

    if request.method == "POST":
        full_name_ar = request.form.get("full_name_ar", "").strip()
        if not full_name_ar:
            flash("الاسم بالعربي مطلوب", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=employee)

        hire_date_str = request.form.get("hire_date", "").strip()
        hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d").date() if hire_date_str else None

        dob_str = request.form.get("date_of_birth", "").strip()
        date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None

        repo = BaseRepository(session, Employee)
        try:
            repo.update(id,
                employee_number=request.form.get("employee_number", "").strip() or employee.employee_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                mother_name=request.form.get("mother_name", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                gender=request.form.get("gender", "").strip() or None,
                nationality=request.form.get("nationality", "").strip() or None,
                marital_status=request.form.get("marital_status", "").strip() or None,
                department_id=request.form.get("department_id", "").strip() or None,
                position_id=request.form.get("position_id", "").strip() or None,
                date_of_birth=date_of_birth,
                place_of_birth=request.form.get("place_of_birth", "").strip() or None,
                hire_date=hire_date,
                contract_type=request.form.get("contract_type", "").strip() or None,
                salary=float(request.form.get("salary") or 0),
                status=request.form.get("status", "active"),
                notes=request.form.get("notes", "").strip() or None,
                updated_by=current_user.id,
            )
            session.commit()
            flash(f"تم تعديل بيانات الموظف {full_name_ar} بنجاح", "success")
            return redirect(url_for("employees.employees_detail", id=id))
        except IntegrityError:
            session.rollback()
            flash(f"رقم الموظف موجود مسبقاً", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=employee)
        except Exception as e:
            session.rollback()
            flash(f"حدث خطأ: {str(e)}", "danger")
            return render_template("employees/form.html", departments=departments, positions=positions, employee=employee)

    return render_template("employees/form.html", departments=departments, positions=positions, employee=employee)


@employees_bp.route("/<id>/delete", methods=["POST"])
@login_required
def employees_delete(id):
    session = get_web_session()
    repo = BaseRepository(session, Employee)
    if repo.delete(id, soft=True):
        flash("تم حذف الموظف بنجاح", "success")
    else:
        flash("لم يتم العثور على الموظف", "danger")
    session.commit()
    return redirect(url_for("employees.employees_list"))


@employees_bp.route("/api/quick-add-position", methods=["POST"])
@login_required
def quick_add_position():
    session = get_web_session()
    data = request.get_json()
    name_ar = (data.get("name_ar") or "").strip()
    if not name_ar:
        return jsonify({"success": False, "message": "المسمى الوظيفي مطلوب"}), 400

    pos = Position(name_ar=name_ar, name_en=data.get("name_en", "").strip() or None)
    session.add(pos)
    session.commit()
    return jsonify({"success": True, "id": pos.id, "name_ar": pos.name_ar})
