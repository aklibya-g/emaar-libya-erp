from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required
from src.core.database.connection import get_web_session
from src.core.models.vehicle_models import Vehicle, VehicleDriverLog
from src.core.models.base_models import Driver
from src.web.routes.marketing import WorkOrder, Trip, WorkOrderBus
from sqlalchemy import func, and_, or_
from datetime import date, datetime

movement_bp = Blueprint("movement", __name__, url_prefix="/movement")


@movement_bp.route("/")
@login_required
def movement_dashboard():
    with get_web_session() as session:
        total_vehicles = session.query(func.count(Vehicle.id)).scalar() or 0
        active_vehicles = session.query(func.count(Vehicle.id)).filter(Vehicle.status == "active").scalar() or 0
        maintenance_vehicles = session.query(func.count(Vehicle.id)).filter(Vehicle.status == "maintenance").scalar() or 0
        inactive_vehicles = session.query(func.count(Vehicle.id)).filter(Vehicle.status == "inactive").scalar() or 0

        total_drivers = session.query(func.count(Driver.id)).filter(Driver.is_deleted == False).scalar() or 0
        active_drivers = session.query(func.count(Driver.id)).filter(Driver.status == "active", Driver.is_deleted == False).scalar() or 0
        inactive_drivers = session.query(func.count(Driver.id)).filter(Driver.status == "inactive", Driver.is_deleted == False).scalar() or 0
        today_str = date.today().strftime('%Y-%m-%d')
        new_drivers_today = session.query(func.count(Driver.id)).filter(
            func.date(Driver.created_at) == date.today()
        ).scalar() or 0

        active_orders = session.query(func.count(WorkOrder.id)).filter(WorkOrder.status == "active", WorkOrder.is_deleted == False).scalar() or 0
        today_trips = session.query(func.count(Trip.id)).filter(Trip.trip_date == date.today()).scalar() or 0

        recent_orders = session.query(WorkOrder).filter(WorkOrder.is_deleted == False).order_by(WorkOrder.created_at.desc()).limit(10).all()
        recent_trips = session.query(Trip).order_by(Trip.created_at.desc()).limit(10).all()

        today = date.today()

        from datetime import timedelta
        from src.core.models.hr_models import DriverContract

        expired_licenses_count = 0
        for d in session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").all():
            if d.license_expiry_date and d.license_expiry_date < today:
                expired_licenses_count += 1

        expired_contracts_count = session.query(func.count(DriverContract.id)).filter(
            DriverContract.status == "active",
            DriverContract.end_date.isnot(None),
            DriverContract.end_date < today,
        ).scalar() or 0

        expired_insurance_count = session.query(func.count(Vehicle.id)).filter(
            Vehicle.status == "active",
            Vehicle.insurance_expiry.isnot(None),
            Vehicle.insurance_expiry < today,
        ).scalar() or 0

        return render_template("movement/dashboard.html",
                             page_title="ادارة الحركة",
                             total_vehicles=total_vehicles,
                             active_vehicles=active_vehicles,
                             maintenance_vehicles=maintenance_vehicles,
                             inactive_vehicles=inactive_vehicles,
                             total_drivers=total_drivers,
                             active_drivers=active_drivers,
                             inactive_drivers=inactive_drivers,
                             new_drivers_today=new_drivers_today,
                             active_orders=active_orders,
                             today_trips=today_trips,
                             recent_orders=recent_orders,
                             recent_trips=recent_trips,
                             expired_licenses_count=expired_licenses_count,
                             expired_contracts_count=expired_contracts_count,
                             expired_insurance_count=expired_insurance_count,
                             today=today)


@movement_bp.route("/binding")
@login_required
def driver_vehicle_binding():
    with get_web_session() as session:
        vehicles = session.query(Vehicle).order_by(Vehicle.plate_number).all()
        drivers = session.query(Driver).filter(Driver.is_deleted == False).order_by(Driver.full_name_ar).all()
        logs = session.query(VehicleDriverLog).order_by(VehicleDriverLog.created_at.desc()).limit(50).all()
        return render_template("movement/binding.html",
                             page_title="ربط السائق بالمركبة",
                             vehicles=vehicles,
                             drivers=drivers,
                             logs=logs)


@movement_bp.route("/binding/assign", methods=["POST"])
@login_required
def assign_driver():
    with get_web_session() as session:
        vehicle_id = request.form.get("vehicle_id")
        driver_id = request.form.get("driver_id")

        if not vehicle_id or not driver_id:
            flash("يجب اختيار السيارة والسائق", "danger")
            return redirect(url_for("movement.driver_vehicle_binding"))

        vehicle = session.query(Vehicle).get(vehicle_id)
        driver = session.query(Driver).get(driver_id)

        if not vehicle or not driver:
            flash("السيارة أو السائق غير موجود", "danger")
            return redirect(url_for("movement.driver_vehicle_binding"))

        old_log = session.query(VehicleDriverLog).filter(
            VehicleDriverLog.vehicle_id == vehicle_id,
            VehicleDriverLog.end_date == None
        ).first()
        if old_log:
            old_log.end_date = date.today()

        log = VehicleDriverLog(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            start_date=date.today(),
        )
        session.add(log)
        vehicle.driver_id = driver_id
        session.commit()
        flash(f"تم ربط السائق {driver.full_name_ar} بالسيارة {vehicle.plate_number} بنجاح", "success")
        return redirect(url_for("movement.driver_vehicle_binding"))


@movement_bp.route("/binding/unassign", methods=["POST"])
@login_required
def unassign_driver():
    with get_web_session() as session:
        vehicle_id = request.form.get("vehicle_id")

        if not vehicle_id:
            flash("يجب اختيار السيارة", "danger")
            return redirect(url_for("movement.driver_vehicle_binding"))

        vehicle = session.query(Vehicle).get(vehicle_id)
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("movement.driver_vehicle_binding"))

        old_log = session.query(VehicleDriverLog).filter(
            VehicleDriverLog.vehicle_id == vehicle_id,
            VehicleDriverLog.end_date == None
        ).first()
        if old_log:
            old_log.end_date = date.today()

        vehicle.driver_id = None
        session.commit()
        flash(f"تم تفريغ السيارة {vehicle.plate_number} بنجاح", "success")
        return redirect(url_for("movement.driver_vehicle_binding"))


@movement_bp.route("/api/available-vehicles")
@login_required
def available_vehicles():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    with get_web_session() as session:
        q = session.query(Vehicle).filter(
            Vehicle.status == "active"
        )

        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()

                busy_vehicle_ids = session.query(WorkOrderBus.vehicle_id).join(
                    WorkOrder
                ).filter(
                    WorkOrder.status.in_(["active", "draft"]),
                    WorkOrderBus.vehicle_id != None,
                    or_(
                        and_(WorkOrder.departure_date <= ed, WorkOrder.return_date >= sd),
                        WorkOrder.departure_date == None
                    )
                ).subquery()

                q = q.filter(Vehicle.id.notin_(busy_vehicle_ids))
            except ValueError:
                pass

        vehicles = q.order_by(Vehicle.plate_number).all()
        result = []
        today = date.today()
        for v in vehicles:
            driver_status = ""
            if v.driver:
                active_trip = session.query(WorkOrder).join(WorkOrderBus).filter(
                    WorkOrderBus.driver_id == v.driver_id,
                    WorkOrder.status.in_(["active"]),
                    WorkOrder.departure_date != None,
                    WorkOrder.return_date != None,
                    WorkOrder.departure_date <= today,
                    WorkOrder.return_date >= today
                ).first()
                if active_trip:
                    driver_status = f"في رحلة حتى {active_trip.return_date.strftime('%Y-%m-%d')}"
                else:
                    upcoming_trip = session.query(WorkOrder).join(WorkOrderBus).filter(
                        WorkOrderBus.driver_id == v.driver_id,
                        WorkOrder.status.in_(["active", "draft"]),
                        WorkOrder.departure_date != None,
                        WorkOrder.departure_date > today
                    ).order_by(WorkOrder.departure_date).first()
                    if upcoming_trip:
                        driver_status = f"رحلة قادمة من {upcoming_trip.departure_date.strftime('%Y-%m-%d')}"

            result.append({
                "id": v.id,
                "plate": v.plate_number,
                "emaar": v.emaar_number or "",
                "brand": v.brand or "",
                "model": v.model or "",
                "driver": v.driver.full_name_ar if v.driver else "",
                "driver_phone": v.driver.phone if v.driver else "",
                "driver_id": v.driver_id or "",
                "driver_status": driver_status,
                "vehicle_type_id": v.vehicle_type_id or "",
                "seats_count": v.seats_count or 0,
            })
        return jsonify(result)


@movement_bp.route("/api/available-drivers")
@login_required
def available_drivers():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    with get_web_session() as session:
        q = session.query(Driver).filter(
            Driver.status == "active",
            Driver.is_deleted == False
        )

        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()

                busy_driver_ids = session.query(WorkOrderBus.driver_id).join(
                    WorkOrder
                ).filter(
                    WorkOrder.status.in_(["active", "draft"]),
                    WorkOrderBus.driver_id != None,
                    or_(
                        and_(WorkOrder.departure_date <= ed, WorkOrder.return_date >= sd),
                        WorkOrder.departure_date == None
                    )
                ).subquery()

                q = q.filter(Driver.id.notin_(busy_driver_ids))
            except ValueError:
                pass

        drivers = q.order_by(Driver.full_name_ar).all()
        result = [{"id": d.id, "name": d.full_name_ar, "phone": d.phone or "", "license": d.license_number or ""} for d in drivers]
        return jsonify(result)


@movement_bp.route("/api/alerts")
@login_required
def movement_alerts():
    with get_web_session() as session:
        today = date.today()
        from datetime import timedelta
        three_days = today + timedelta(days=3)

        active_orders = session.query(WorkOrder).filter(
            WorkOrder.status == "active",
            WorkOrder.departure_date != None,
            WorkOrder.return_date != None
        ).all()

        ending_today = []
        ending_soon = []
        starting_today = []
        starting_soon = []

        for order in active_orders:
            client_name = order.client.name_ar if order.client else ""
            if order.return_date == today:
                ending_today.append({"order_number": order.order_number, "client": client_name, "return_date": order.return_date.strftime('%Y-%m-%d')})
            elif today < order.return_date <= three_days:
                ending_soon.append({"order_number": order.order_number, "client": client_name, "return_date": order.return_date.strftime('%Y-%m-%d')})

            if order.departure_date == today:
                starting_today.append({"order_number": order.order_number, "client": client_name, "departure_date": order.departure_date.strftime('%Y-%m-%d')})
            elif today < order.departure_date <= three_days:
                starting_soon.append({"order_number": order.order_number, "client": client_name, "departure_date": order.departure_date.strftime('%Y-%m-%d')})

        return jsonify({
            "ending_today": ending_today,
            "ending_soon": ending_soon,
            "starting_today": starting_today,
            "starting_soon": starting_soon
        })


@movement_bp.route("/api/driver-trip-info/<driver_id>")
@login_required
def driver_trip_info(driver_id):
    with get_web_session() as session:
        today = date.today()
        driver = session.query(Driver).get(driver_id)
        if not driver:
            return jsonify({"error": "السائق غير موجود"})

        active_trips = session.query(WorkOrder).join(WorkOrderBus).filter(
            WorkOrderBus.driver_id == driver_id,
            WorkOrder.status == "active",
            WorkOrder.departure_date != None,
            WorkOrder.return_date != None,
            WorkOrder.departure_date <= today,
            WorkOrder.return_date >= today
        ).all()

        upcoming_trips = session.query(WorkOrder).join(WorkOrderBus).filter(
            WorkOrderBus.driver_id == driver_id,
            WorkOrder.status.in_(["active", "draft"]),
            WorkOrder.departure_date != None,
            WorkOrder.departure_date > today
        ).order_by(WorkOrder.departure_date).all()

        result = {
            "driver_name": driver.full_name_ar,
            "active_trips": [],
            "upcoming_trips": []
        }

        for t in active_trips:
            remaining = (t.return_date - today).days
            result["active_trips"].append({
                "order_number": t.order_number,
                "client": t.client.name_ar if t.client else "",
                "departure_date": t.departure_date.strftime('%Y-%m-%d'),
                "return_date": t.return_date.strftime('%Y-%m-%d'),
                "remaining_days": remaining
            })

        for t in upcoming_trips:
            days_until = (t.departure_date - today).days
            result["upcoming_trips"].append({
                "order_number": t.order_number,
                "client": t.client.name_ar if t.client else "",
                "departure_date": t.departure_date.strftime('%Y-%m-%d'),
                "return_date": t.return_date.strftime('%Y-%m-%d'),
                "days_until_start": days_until
            })

        return jsonify(result)


@movement_bp.route("/driver-trips")
@login_required
def driver_trips_overview():
    with get_web_session() as session:
        today = date.today()
        drivers = session.query(Driver).filter(Driver.is_deleted == False).order_by(Driver.full_name_ar).all()

        drivers_data = []
        for driver in drivers:
            active_trips = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status == "active",
                WorkOrder.departure_date != None,
                WorkOrder.return_date != None,
                WorkOrder.departure_date <= today,
                WorkOrder.return_date >= today
            ).all()

            upcoming_trips = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status.in_(["active", "draft"]),
                WorkOrder.departure_date != None,
                WorkOrder.departure_date > today
            ).order_by(WorkOrder.departure_date).all()

            completed_trips = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status == "active",
                WorkOrder.return_date != None,
                WorkOrder.return_date < today
            ).order_by(WorkOrder.return_date.desc()).limit(5).all()

            drivers_data.append({
                "driver": driver,
                "active_trips": active_trips,
                "upcoming_trips": upcoming_trips,
                "completed_trips": completed_trips
            })

        return render_template("movement/driver_trips.html", drivers_data=drivers_data, today=today)


# ============================================================
# ايقاف و تفعيل السائقين
# ============================================================

from src.core.models.vehicle_models import DriverSuspension

@movement_bp.route("/suspensions")
@login_required
def suspensions_list():
    with get_web_session() as session:
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()

        q = session.query(DriverSuspension).join(Driver, DriverSuspension.driver_id == Driver.id)
        if search:
            q = q.filter(
                (Driver.full_name_ar.ilike(f"%{search}%"))
                | (Driver.driver_number.ilike(f"%{search}%"))
            )
        if status_filter:
            q = q.filter(DriverSuspension.status == status_filter)
        suspensions = q.order_by(DriverSuspension.created_at.desc()).all()

        drivers = session.query(Driver).filter(Driver.is_deleted == False).order_by(Driver.full_name_ar).all()
        today_str = date.today().strftime('%Y-%m-%d')
        return render_template("movement/suspensions.html",
                             page_title="ايقاف و تفعيل السائقين",
                             suspensions=suspensions,
                             drivers=drivers,
                             search=search,
                             status_filter=status_filter,
                             today_str=today_str)


@movement_bp.route("/suspensions/toggle", methods=["POST"])
@login_required
def toggle_driver_status():
    with get_web_session() as session:
        driver_id = request.form.get("driver_id")
        reason = request.form.get("reason", "").strip()
        notes = request.form.get("notes", "").strip()
        suspension_date_str = request.form.get("suspension_date", "").strip()

        if not driver_id:
            flash("يجب اختيار السائق", "danger")
            return redirect(url_for("movement.suspensions_list"))

        driver = session.query(Driver).get(driver_id)
        if not driver:
            flash("السائق غير موجود", "danger")
            return redirect(url_for("movement.suspensions_list"))

        if suspension_date_str:
            suspension_date = date.fromisoformat(suspension_date_str)
        else:
            suspension_date = date.today()

        new_status = "inactive" if driver.status == "active" else "active"
        status_label = "ايقاف" if new_status == "inactive" else "تفعيل"

        suspension = DriverSuspension(
            driver_id=driver_id,
            status=new_status,
            suspension_date=suspension_date,
            reason=reason or None,
            notes=notes or None,
        )
        session.add(suspension)

        driver.status = new_status

        from src.core.models.hr_models import DriverContract
        active_contracts = session.query(DriverContract).filter(
            DriverContract.driver_id == driver_id,
            DriverContract.status == "active"
        ).all()
        for contract in active_contracts:
            contract.status = new_status

        if new_status == "inactive":
            log = session.query(VehicleDriverLog).filter(
                VehicleDriverLog.driver_id == driver_id,
                VehicleDriverLog.end_date == None
            ).first()
            if log:
                log.end_date = suspension_date
            vehicle = session.query(Vehicle).filter(Vehicle.driver_id == driver_id).first()
            if vehicle:
                vehicle.driver_id = None

        session.commit()
        flash(f"تم {status_label} السائق {driver.full_name_ar} بنجاح", "success")
        return redirect(url_for("movement.suspensions_list"))
