from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import Driver
from src.core.repositories.base_repository import BaseRepository
from datetime import date

drivers_bp = Blueprint("drivers", __name__, url_prefix="/drivers")


def _parse_date(val):
    if not val or not val.strip():
        return None
    try:
        from datetime import datetime
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@drivers_bp.route("/")
@login_required
def drivers_list():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    session = get_web_session()
    q = session.query(Driver).filter(Driver.is_deleted == False)
    if search:
        q = q.filter(
            (Driver.full_name_ar.ilike(f"%{search}%")) |
            (Driver.driver_number.ilike(f"%{search}%")) |
            (Driver.phone.ilike(f"%{search}%")) |
            (Driver.license_number.ilike(f"%{search}%"))
        )
    if status_filter in ("active", "inactive"):
        q = q.filter(Driver.status == status_filter)
    drivers = q.order_by(Driver.created_at.desc()).all()
    total = session.query(Driver).filter(Driver.is_deleted == False).count()
    active = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").count()
    inactive = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "inactive").count()
    return render_template(
        "drivers/list.html",
        drivers=drivers,
        search=search,
        status_filter=status_filter,
        total_count=total,
        active_count=active,
        inactive_count=inactive,
    )


def _next_driver_number(session):
    from sqlalchemy import func
    import re
    from src.core.models.base_models import Department
    ops_dept = session.query(Department).filter(
        Department.is_deleted == False,
        (Department.code == "OPS") | (Department.name_ar.like("%حركة%")) | (Department.name_ar.like("%عمليات%"))
    ).first()
    dept_code = (ops_dept.code if ops_dept else "OPS")
    max_num = session.query(func.max(Driver.driver_number)).filter(
        Driver.driver_number.like(f"ELT.{dept_code}-%")
    ).scalar()
    if max_num:
        m = re.search(r'(\d+)$', max_num)
        num = int(m.group(1)) + 1 if m else 1
    else:
        num = 1
    driver_number = f"ELT.{dept_code}-{num:03d}"
    while session.query(Driver).filter(Driver.driver_number == driver_number).first():
        num += 1
        driver_number = f"ELT.{dept_code}-{num:03d}"
    return driver_number


@drivers_bp.route("/add", methods=["GET", "POST"])
@login_required
def drivers_add():
    session = get_web_session()
    if request.method == "POST":
        try:
            full_name_ar = request.form.get("full_name_ar", "").strip()
            if not full_name_ar:
                flash("الاسم بالعربي مطلوب", "danger")
                return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

            if not request.form.get("join_date", "").strip():
                flash("تاريخ المباشرة مطلوب", "danger")
                return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

            driver_number = request.form.get("driver_number", "").strip()
            if not driver_number:
                driver_number = _next_driver_number(session)
            else:
                existing = session.query(Driver).filter(Driver.driver_number == driver_number).first()
                if existing:
                    flash(f"الرقم الوظيفي {driver_number} مستخدم مسبقاً", "danger")
                    return render_template("drivers/form.html", driver=None)

            repo = BaseRepository(session, Driver)
            driver = repo.create(
                driver_number=driver_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                id_type=request.form.get("id_type", "").strip() or None,
                id_number=request.form.get("id_number", "").strip() or None,
                mother_name=request.form.get("mother_name", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                phone2=request.form.get("phone2", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                license_number=request.form.get("license_number", "").strip() or None,
                license_type=request.form.get("license_type", "").strip() or None,
                license_issue_date=_parse_date(request.form.get("license_issue_date")),
                license_expiry_date=_parse_date(request.form.get("license_expiry_date")),
                license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
                join_date=_parse_date(request.form.get("join_date")),
                contract_type=request.form.get("contract_type", "").strip() or None,
                activity_type=request.form.get("activity_type", "").strip() or None,
                status=request.form.get("status", "active"),
                notes=request.form.get("notes", "").strip() or None,
                created_by=current_user.id,
            )
            session.commit()
            flash(f"تم إضافة السائق {full_name_ar} بنجاح", "success")
            return redirect(url_for("drivers.drivers_detail", id=driver.id))
        except Exception as e:
            session.rollback()
            import traceback
            traceback.print_exc()
            flash(f"خطأ في حفظ البيانات: {str(e)}", "danger")
            return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

    return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))


@drivers_bp.route("/<id>")
@login_required
def drivers_detail(id):
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))
    return render_template("drivers/detail.html", driver=driver)


@drivers_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def drivers_edit(id):
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))

    if request.method == "POST":
        full_name_ar = request.form.get("full_name_ar", "").strip()
        if not full_name_ar:
            flash("الاسم بالعربي مطلوب", "danger")
            return render_template("drivers/form.html", driver=driver)

        new_driver_number = request.form.get("driver_number", "").strip() or driver.driver_number
        if new_driver_number != driver.driver_number:
            existing = session.query(Driver).filter(Driver.driver_number == new_driver_number, Driver.id != id).first()
            if existing:
                flash(f"الرقم الوظيفي {new_driver_number} مستخدم مسبقاً", "danger")
                return render_template("drivers/form.html", driver=driver)

        repo = BaseRepository(session, Driver)
        repo.update(id,
            driver_number=new_driver_number,
            full_name_ar=full_name_ar,
            full_name_en=request.form.get("full_name_en", "").strip() or None,
            national_id=request.form.get("national_id", "").strip() or None,
            id_type=request.form.get("id_type", "").strip() or None,
            id_number=request.form.get("id_number", "").strip() or None,
            mother_name=request.form.get("mother_name", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            phone2=request.form.get("phone2", "").strip() or None,
            address=request.form.get("address", "").strip() or None,
            license_number=request.form.get("license_number", "").strip() or None,
            license_type=request.form.get("license_type", "").strip() or None,
            license_issue_date=_parse_date(request.form.get("license_issue_date")),
            license_expiry_date=_parse_date(request.form.get("license_expiry_date")),
            license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
            join_date=_parse_date(request.form.get("join_date")),
            contract_type=request.form.get("contract_type", "").strip() or None,
            activity_type=request.form.get("activity_type", "").strip() or None,
            status=request.form.get("status", "active"),
            notes=request.form.get("notes", "").strip() or None,
            updated_by=current_user.id,
        )
        session.commit()
        flash(f"تم تعديل بيانات السائق {full_name_ar} بنجاح", "success")
        return redirect(url_for("drivers.drivers_detail", id=id))

    return render_template("drivers/form.html", driver=driver)


@drivers_bp.route("/<id>/delete", methods=["POST"])
@login_required
def drivers_delete(id):
    session = get_web_session()
    repo = BaseRepository(session, Driver)
    if repo.delete(id, soft=True):
        session.commit()
        flash("تم حذف السائق بنجاح", "success")
    else:
        flash("لم يتم العثور على السائق", "danger")
    return redirect(url_for("drivers.drivers_list"))


@drivers_bp.route("/delete-all", methods=["POST"])
@login_required
def drivers_delete_all():
    if not current_user.is_admin:
        flash("هذه العملية متاحة لمدير النظام فقط", "danger")
        return redirect(url_for("drivers.drivers_list"))
    confirm = request.form.get("typed_confirm", request.form.get("confirm", "")).strip()
    if confirm != "DELETE":
        flash('يرجى كتابة DELETE في مربع التأكيد', "danger")
        return redirect(url_for("drivers.drivers_list"))
    session = get_web_session()
    count = session.query(Driver).filter(Driver.is_deleted == False).count()
    session.query(Driver).filter(Driver.is_deleted == False).update({"is_deleted": True}, synchronize_session=False)
    session.commit()
    flash(f"تم حذف جميع السائقين ({count}) بنجاح", "success")
    return redirect(url_for("drivers.drivers_list"))
