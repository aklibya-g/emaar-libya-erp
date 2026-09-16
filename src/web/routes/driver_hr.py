from datetime import date, datetime, time

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import Driver, DriverDocument, Department
from src.core.models.hr_models import (
    DriverLicense, DriverTrip, AttendanceRecord, LeaveRequest, Contract,
)

driver_hr_bp = Blueprint("driver_hr", __name__, url_prefix="/driver-hr")


@driver_hr_bp.route("/")
@login_required
def driver_hr_dashboard():
    with session_scope() as session:
        today = date.today()

        total_drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").count()

        # Licenses: expired vs expiring within 30 days (all drivers, not just active)
        expired_licenses = 0
        expiring_soon = 0
        drivers = session.query(Driver).filter(Driver.is_deleted == False).all()
        for d in drivers:
            if d.license_expiry_date:
                if d.license_expiry_date < today:
                    expired_licenses += 1
                elif d.license_expiry_date <= today + __import__("datetime").timedelta(days=30):
                    expiring_soon += 1

        # Today's trips
        today_trips = session.query(DriverTrip).filter(DriverTrip.trip_date == today).count()

        # Pending leaves (if linked to employees)
        pending_leaves = session.query(LeaveRequest).filter(LeaveRequest.status == "pending").count()

        # Active contracts
        active_contracts = session.query(Contract).filter(Contract.status == "active").count()

        # Recent driver documents
        recent_docs = session.query(DriverDocument).order_by(DriverDocument.created_at.desc()).limit(5).all()

        return render_template("driver_hr/dashboard.html",
            total_drivers=total_drivers,
            expired_licenses=expired_licenses,
            expiring_soon=expiring_soon,
            today_trips=today_trips,
            pending_leaves=pending_leaves,
            active_contracts=active_contracts,
            recent_docs=recent_docs,
            today=today,
        )


@driver_hr_bp.route("/list")
@login_required
def driver_list():
    with session_scope() as session:
        search = request.args.get("search", "").strip()
        q = session.query(Driver).filter(Driver.is_deleted == False)
        if search:
            q = q.filter(
                (Driver.full_name_ar.ilike(f"%{search}%"))
                | (Driver.driver_number.ilike(f"%{search}%"))
                | (Driver.phone.ilike(f"%{search}%"))
                | (Driver.national_id.ilike(f"%{search}%"))
            )
        drivers = q.order_by(Driver.full_name_ar).all()
        return render_template("driver_hr/list.html", drivers=drivers, search=search)


@driver_hr_bp.route("/<id>")
@login_required
def driver_file(id):
    with session_scope() as session:
        driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
        if not driver:
            flash("السائق غير موجود", "danger")
            return redirect(url_for("driver_hr.driver_list"))

        documents = session.query(DriverDocument).filter(
            DriverDocument.driver_id == id
        ).order_by(DriverDocument.created_at.desc()).all()

        licenses = session.query(DriverLicense).filter(
            DriverLicense.employee_id == driver.employee_id
        ).order_by(DriverLicense.created_at.desc()).all() if driver.employee_id else []

        trips = session.query(DriverTrip).filter(
            DriverTrip.driver_id == driver.employee_id
        ).order_by(DriverTrip.trip_date.desc()).limit(20).all() if driver.employee_id else []

        active_tab = request.args.get("tab", "personal")

        return render_template("driver_hr/file.html",
            driver=driver,
            documents=documents,
            licenses=licenses,
            trips=trips,
            active_tab=active_tab,
            today=date.today(),
        )


@driver_hr_bp.route("/<id>/documents/add", methods=["POST"])
@login_required
def driver_document_add(id):
    with session_scope() as session:
        driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
        if not driver:
            flash("السائق غير موجود", "danger")
            return redirect(url_for("driver_hr.driver_list"))

        title = request.form.get("title", "").strip()
        doc_type = request.form.get("doc_type", "").strip()
        if not title or not doc_type:
            flash("النوع والعنوان مطلوبان", "danger")
            return redirect(url_for("driver_hr.driver_file", id=id))

        doc = DriverDocument(
            driver_id=id,
            doc_type=doc_type,
            title=title,
            description=request.form.get("description", "").strip() or None,
        )
        session.add(doc)
        session.commit()
        flash("تم إضافة المستند بنجاح", "success")
        return redirect(url_for("driver_hr.driver_file", id=id, tab="documents"))


@driver_hr_bp.route("/licenses")
@login_required
def licenses_list():
    with session_scope() as session:
        from datetime import timedelta
        today = date.today()
        delta30 = timedelta(days=30)
        drivers = session.query(Driver).filter(
            Driver.is_deleted == False,
            Driver.license_expiry_date.isnot(None)
        ).order_by(Driver.license_expiry_date).all()
        return render_template("driver_hr/licenses.html", drivers=drivers, today=today, delta30=delta30)


@driver_hr_bp.route("/trips")
@login_required
def trips_list():
    with session_scope() as session:
        trips = session.query(DriverTrip).join(
            Driver, DriverTrip.driver_id == Driver.employee_id
        ).order_by(DriverTrip.trip_date.desc()).limit(50).all()
        return render_template("driver_hr/trips.html", trips=trips)
