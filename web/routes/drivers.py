from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import Driver
from src.core.repositories.base_repository import BaseRepository

drivers_bp = Blueprint("drivers", __name__, url_prefix="/drivers")


@drivers_bp.route("/")
@login_required
def drivers_list():
    search = request.args.get("search", "").strip()
    with session_scope() as session:
        q = session.query(Driver).filter(Driver.is_deleted == False)
        if search:
            q = q.filter(
                (Driver.full_name_ar.ilike(f"%{search}%")) |
                (Driver.driver_number.ilike(f"%{search}%")) |
                (Driver.phone.ilike(f"%{search}%")) |
                (Driver.license_number.ilike(f"%{search}%"))
            )
        drivers = q.order_by(Driver.created_at.desc()).all()
    return render_template("drivers/list.html", drivers=drivers, search=search)


@drivers_bp.route("/add", methods=["GET", "POST"])
@login_required
def drivers_add():
    with session_scope() as session:
        if request.method == "POST":
            driver_number = request.form.get("driver_number", "").strip()
            full_name_ar = request.form.get("full_name_ar", "").strip()
            if not driver_number or not full_name_ar:
                flash("رقم السائق والاسم بالعربي مطلوبان", "danger")
                return render_template("drivers/form.html", driver=None)

            repo = BaseRepository(session, Driver)
            driver = repo.create(
                driver_number=driver_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                license_number=request.form.get("license_number", "").strip() or None,
                license_type=request.form.get("license_type", "").strip() or None,
                license_issue_date=request.form.get("license_issue_date", "").strip() or None,
                license_expiry_date=request.form.get("license_expiry_date", "").strip() or None,
                license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
                employee_id=request.form.get("employee_id", "").strip() or None,
                join_date=request.form.get("join_date", "").strip() or None,
                status=request.form.get("status", "active"),
                notes=request.form.get("notes", "").strip() or None,
                created_by=current_user.id,
            )
            flash(f"تم إضافة السائق {full_name_ar} بنجاح", "success")
            return redirect(url_for("drivers.drivers_detail", id=driver.id))

    return render_template("drivers/form.html", driver=None)


@drivers_bp.route("/<id>")
@login_required
def drivers_detail(id):
    with session_scope() as session:
        driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
        if not driver:
            flash("السائق غير موجود", "danger")
            return redirect(url_for("drivers.drivers_list"))
    return render_template("drivers/detail.html", driver=driver)


@drivers_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def drivers_edit(id):
    with session_scope() as session:
        driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
        if not driver:
            flash("السائق غير موجود", "danger")
            return redirect(url_for("drivers.drivers_list"))

        if request.method == "POST":
            full_name_ar = request.form.get("full_name_ar", "").strip()
            if not full_name_ar:
                flash("الاسم بالعربي مطلوب", "danger")
                return render_template("drivers/form.html", driver=driver)

            repo = BaseRepository(session, Driver)
            repo.update(id,
                driver_number=request.form.get("driver_number", "").strip() or driver.driver_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                license_number=request.form.get("license_number", "").strip() or None,
                license_type=request.form.get("license_type", "").strip() or None,
                license_issue_date=request.form.get("license_issue_date", "").strip() or None,
                license_expiry_date=request.form.get("license_expiry_date", "").strip() or None,
                license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
                employee_id=request.form.get("employee_id", "").strip() or None,
                join_date=request.form.get("join_date", "").strip() or None,
                status=request.form.get("status", "active"),
                notes=request.form.get("notes", "").strip() or None,
                updated_by=current_user.id,
            )
            flash(f"تم تعديل بيانات السائق {full_name_ar} بنجاح", "success")
            return redirect(url_for("drivers.drivers_detail", id=id))

    return render_template("drivers/form.html", driver=driver)


@drivers_bp.route("/<id>/delete", methods=["POST"])
@login_required
def drivers_delete(id):
    with session_scope() as session:
        repo = BaseRepository(session, Driver)
        if repo.delete(id, soft=True):
            flash("تم حذف السائق بنجاح", "success")
        else:
            flash("لم يتم العثور على السائق", "danger")
    return redirect(url_for("drivers.drivers_list"))
