from datetime import date, datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import Warehouse, Item, StockTransaction, generate_uuid, VehicleType, Driver
from src.core.models.vehicle_models import (
    Vehicle, VehicleMaintenance, VehicleBreakdown,
    VehicleExpense, VehicleFuel, VehicleSparePart,
    VehicleDocument, VehicleDriverLog,
)

vehicle_bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")


@vehicle_bp.route("/")
@login_required
def vehicle_dashboard():
    with session_scope() as session:
        today = date.today()

        total_vehicles = session.query(Vehicle).count()
        active_vehicles = session.query(Vehicle).filter(Vehicle.status == "active").count()
        maintenance_vehicles = session.query(Vehicle).filter(Vehicle.status == "maintenance").count()
        inactive_vehicles = session.query(Vehicle).filter(Vehicle.status == "inactive").count()

        pending_maintenance = session.query(VehicleMaintenance).filter(
            VehicleMaintenance.status == "pending"
        ).count()

        from datetime import timedelta
        expiring_insurance = session.query(Vehicle).filter(
            Vehicle.insurance_expiry <= today + timedelta(days=30),
            Vehicle.insurance_expiry >= today,
        ).count()
        expiring_registration = session.query(Vehicle).filter(
            Vehicle.registration_expiry <= today + timedelta(days=30),
            Vehicle.registration_expiry >= today,
        ).count()

        month_start = today.replace(day=1)
        total_expenses = session.query(VehicleExpense).filter(
            VehicleExpense.expense_date >= month_start
        ).with_entities(
            __import__("sqlalchemy").func.sum(VehicleExpense.amount)
        ).scalar() or 0

        total_fuel = session.query(VehicleFuel).filter(
            VehicleFuel.fuel_date >= month_start
        ).with_entities(
            __import__("sqlalchemy").func.sum(VehicleFuel.total_cost)
        ).scalar() or 0

        vehicle_types = session.query(VehicleType).filter(VehicleType.is_active == True).all()
        recent_maintenance = session.query(VehicleMaintenance).order_by(
            VehicleMaintenance.created_at.desc()
        ).limit(5).all()

        return render_template("vehicles/dashboard.html",
            total_vehicles=total_vehicles,
            active_vehicles=active_vehicles,
            maintenance_vehicles=maintenance_vehicles,
            inactive_vehicles=inactive_vehicles,
            pending_maintenance=pending_maintenance,
            expiring_insurance=expiring_insurance,
            expiring_registration=expiring_registration,
            total_expenses=total_expenses,
            total_fuel=total_fuel,
            vehicle_types=vehicle_types,
            recent_maintenance=recent_maintenance,
            today=today,
        )


@vehicle_bp.route("/list")
@login_required
def vehicle_list():
    with session_scope() as session:
        search = request.args.get("search", "").strip()
        type_id = request.args.get("type_id", "").strip()
        status = request.args.get("status", "").strip()

        q = session.query(Vehicle)
        if search:
            q = q.filter(
                (Vehicle.plate_number.ilike(f"%{search}%"))
                | (Vehicle.emaar_number.ilike(f"%{search}%"))
                | (Vehicle.brand.ilike(f"%{search}%"))
                | (Vehicle.model.ilike(f"%{search}%"))
            )
        if type_id:
            q = q.filter(Vehicle.vehicle_type_id == type_id)
        if status:
            q = q.filter(Vehicle.status == status)

        vehicles = q.order_by(Vehicle.plate_number).all()
        vehicle_types = session.query(VehicleType).filter(VehicleType.is_active == True).all()
        return render_template("vehicles/list.html",
            vehicles=vehicles, vehicle_types=vehicle_types,
            search=search, type_id=type_id, status=status,
        )


@vehicle_bp.route("/add", methods=["GET", "POST"])
@login_required
def vehicle_add():
    with session_scope() as session:
        vehicle_types = session.query(VehicleType).filter(VehicleType.is_active == True).all()
        drivers = session.query(Driver).filter(
            Driver.is_deleted == False,
            Driver.status == "active"
        ).all()

        if request.method == "POST":
            plate_number = request.form.get("plate_number", "").strip()
            vehicle_type_id = request.form.get("vehicle_type_id", "").strip()
            if not plate_number or not vehicle_type_id:
                flash("رقم اللوحة ونوع السيارة مطلوبان", "danger")
                return render_template("vehicles/form.html",
                    vehicle_types=vehicle_types, drivers=drivers, vehicle=None,
                    seats_map={vt.id: vt.seats_count for vt in vehicle_types if vt.seats_count})

            new_driver_id = request.form.get("driver_id", "").strip() or None

            vehicle = Vehicle(
                plate_number=plate_number,
                emaar_number=request.form.get("emaar_number", "").strip() or None,
                vehicle_type_id=vehicle_type_id,
                brand=request.form.get("brand", "").strip() or None,
                model=request.form.get("model", "").strip() or None,
                year=int(request.form.get("year") or 0) or None,
                color=request.form.get("color", "").strip() or None,
                engine_number=request.form.get("engine_number", "").strip() or None,
                chassis_number=request.form.get("chassis_number", "").strip() or None,
                fuel_type=request.form.get("fuel_type", "gasoline"),
                tank_capacity=_parse_float(request.form.get("tank_capacity")),
                seats_count=int(request.form.get("seats_count") or 0) or None,
                current_km=_parse_float(request.form.get("current_km")),
                insurance_expiry=_parse_date(request.form.get("insurance_expiry")),
                registration_expiry=_parse_date(request.form.get("registration_expiry")),
                status=request.form.get("status", "active"),
                driver_id=new_driver_id,
                notes=request.form.get("notes", "").strip() or None,
            )
            session.add(vehicle)
            session.flush()

            if new_driver_id:
                log = VehicleDriverLog(
                    vehicle_id=vehicle.id,
                    driver_id=new_driver_id,
                    start_date=date.today(),
                )
                session.add(log)

            session.commit()
            flash("تم إضافة السيارة بنجاح", "success")
            return redirect(url_for("vehicles.vehicle_list"))

        return render_template("vehicles/form.html",
            vehicle_types=vehicle_types, drivers=drivers, vehicle=None,
            seats_map={vt.id: vt.seats_count for vt in vehicle_types if vt.seats_count})


@vehicle_bp.route("/<id>")
@login_required
def vehicle_detail(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        active_tab = request.args.get("tab", "info")
        maintenance = session.query(VehicleMaintenance).filter(
            VehicleMaintenance.vehicle_id == id
        ).order_by(VehicleMaintenance.maintenance_date.desc()).all()

        breakdowns = session.query(VehicleBreakdown).filter(
            VehicleBreakdown.vehicle_id == id
        ).order_by(VehicleBreakdown.breakdown_date.desc()).all()

        expenses = session.query(VehicleExpense).filter(
            VehicleExpense.vehicle_id == id
        ).order_by(VehicleExpense.expense_date.desc()).limit(20).all()

        fuel_records = session.query(VehicleFuel).filter(
            VehicleFuel.vehicle_id == id
        ).order_by(VehicleFuel.fuel_date.desc()).limit(20).all()

        spare_parts = session.query(VehicleSparePart).filter(
            VehicleSparePart.vehicle_id == id
        ).order_by(VehicleSparePart.usage_date.desc()).limit(20).all()

        documents = session.query(VehicleDocument).filter(
            VehicleDocument.vehicle_id == id
        ).order_by(VehicleDocument.created_at.desc()).all()

        driver_logs = session.query(VehicleDriverLog).filter(
            VehicleDriverLog.vehicle_id == id
        ).order_by(VehicleDriverLog.start_date.desc()).all()

        from sqlalchemy import func
        total_expenses = session.query(func.sum(VehicleExpense.amount)).filter(
            VehicleExpense.vehicle_id == id
        ).scalar() or 0
        total_fuel = session.query(func.sum(VehicleFuel.total_cost)).filter(
            VehicleFuel.vehicle_id == id
        ).scalar() or 0
        total_parts = session.query(func.sum(VehicleSparePart.total_price)).filter(
            VehicleSparePart.vehicle_id == id
        ).scalar() or 0

        items = session.query(Item).filter(Item.is_active == True).all()
        warehouses = session.query(Warehouse).filter(Warehouse.status == "active").all()
        drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").all()

        driver_photo = None
        if vehicle.driver:
            driver_photo = vehicle.driver.photo_path
            if not driver_photo and vehicle.driver.employee:
                driver_photo = vehicle.driver.employee.photo_path

        return render_template("vehicles/detail.html",
            vehicle=vehicle, active_tab=active_tab,
            maintenance=maintenance, breakdowns=breakdowns,
            expenses=expenses, fuel_records=fuel_records,
            spare_parts=spare_parts, items=items, warehouses=warehouses,
            total_expenses=total_expenses, total_fuel=total_fuel,
            total_parts=total_parts, today=date.today(),
            documents=documents, driver_logs=driver_logs,
            drivers=drivers, driver_photo=driver_photo,
        )


@vehicle_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def vehicle_edit(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        vehicle_types = session.query(VehicleType).filter(VehicleType.is_active == True).all()
        drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").all()

        if request.method == "POST":
            old_driver_id = vehicle.driver_id
            new_driver_id = request.form.get("driver_id", "").strip() or None

            vehicle.plate_number = request.form.get("plate_number", "").strip()
            vehicle.emaar_number = request.form.get("emaar_number", "").strip() or None
            vehicle.vehicle_type_id = request.form.get("vehicle_type_id", "").strip()
            vehicle.brand = request.form.get("brand", "").strip() or None
            vehicle.model = request.form.get("model", "").strip() or None
            vehicle.year = int(request.form.get("year") or 0) or None
            vehicle.color = request.form.get("color", "").strip() or None
            vehicle.engine_number = request.form.get("engine_number", "").strip() or None
            vehicle.chassis_number = request.form.get("chassis_number", "").strip() or None
            vehicle.fuel_type = request.form.get("fuel_type", "gasoline")
            vehicle.tank_capacity = _parse_float(request.form.get("tank_capacity"))
            vehicle.seats_count = int(request.form.get("seats_count") or 0) or None
            vehicle.current_km = _parse_float(request.form.get("current_km"))
            vehicle.insurance_expiry = _parse_date(request.form.get("insurance_expiry"))
            vehicle.registration_expiry = _parse_date(request.form.get("registration_expiry"))
            vehicle.status = request.form.get("status", "active")
            vehicle.driver_id = new_driver_id
            vehicle.notes = request.form.get("notes", "").strip() or None

            if old_driver_id != new_driver_id:
                if old_driver_id:
                    last_log = session.query(VehicleDriverLog).filter(
                        VehicleDriverLog.vehicle_id == id,
                        VehicleDriverLog.driver_id == old_driver_id,
                        VehicleDriverLog.end_date == None,
                    ).order_by(VehicleDriverLog.start_date.desc()).first()
                    if last_log:
                        last_log.end_date = date.today()

                if new_driver_id:
                    log = VehicleDriverLog(
                        vehicle_id=id,
                        driver_id=new_driver_id,
                        start_date=date.today(),
                    )
                    session.add(log)

            session.commit()
            flash("تم تعديل السيارة بنجاح", "success")
            return redirect(url_for("vehicles.vehicle_detail", id=id))

        return render_template("vehicles/form.html",
            vehicle_types=vehicle_types, drivers=drivers, vehicle=vehicle,
            seats_map={vt.id: vt.seats_count for vt in vehicle_types if vt.seats_count})


@vehicle_bp.route("/<id>/maintenance/add", methods=["POST"])
@login_required
def maintenance_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        maintenance = VehicleMaintenance(
            vehicle_id=id,
            maintenance_type=request.form.get("maintenance_type", "").strip(),
            description=request.form.get("description", "").strip(),
            maintenance_date=_parse_date(request.form.get("maintenance_date")) or date.today(),
            next_maintenance_date=_parse_date(request.form.get("next_maintenance_date")),
            next_maintenance_km=_parse_float(request.form.get("next_maintenance_km")),
            cost=_parse_float(request.form.get("cost")) or 0,
            performed_by=request.form.get("performed_by", "").strip() or None,
            status=request.form.get("status", "completed"),
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(maintenance)
        session.commit()
        flash("تم إضافة سجل الصيانة بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="maintenance"))


@vehicle_bp.route("/<id>/maintenance/<mid>/update-status", methods=["POST"])
@login_required
def maintenance_update_status(id, mid):
    with session_scope() as session:
        maintenance = session.query(VehicleMaintenance).filter(VehicleMaintenance.id == mid).first()
        if maintenance:
            maintenance.status = request.form.get("status", "completed")
            if request.form.get("notes"):
                maintenance.notes = request.form.get("notes", "").strip()
            session.commit()
            flash("تم تحديث حالة الصيانة", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="maintenance"))


@vehicle_bp.route("/<id>/breakdown/add", methods=["POST"])
@login_required
def breakdown_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        breakdown = VehicleBreakdown(
            vehicle_id=id,
            breakdown_date=_parse_date(request.form.get("breakdown_date")) or date.today(),
            description=request.form.get("description", "").strip(),
            severity=request.form.get("severity", "minor"),
            cost=_parse_float(request.form.get("cost")) or 0,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(breakdown)
        session.commit()
        flash("تم تسجيل العطل بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="breakdowns"))


@vehicle_bp.route("/<id>/breakdown/<bid>/resolve", methods=["POST"])
@login_required
def breakdown_resolve(id, bid):
    with session_scope() as session:
        breakdown = session.query(VehicleBreakdown).filter(VehicleBreakdown.id == bid).first()
        if breakdown:
            breakdown.resolved = True
            breakdown.resolution_date = date.today()
            breakdown.resolution_notes = request.form.get("resolution_notes", "").strip() or None
            session.commit()
            flash("تم حل العطل بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="breakdowns"))


@vehicle_bp.route("/<id>/expense/add", methods=["POST"])
@login_required
def expense_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        expense = VehicleExpense(
            vehicle_id=id,
            expense_type=request.form.get("expense_type", "").strip(),
            amount=_parse_float(request.form.get("amount")) or 0,
            expense_date=_parse_date(request.form.get("expense_date")) or date.today(),
            description=request.form.get("description", "").strip() or None,
            receipt_number=request.form.get("receipt_number", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(expense)
        session.commit()
        flash("تم إضافة المصروف بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="expenses"))


@vehicle_bp.route("/<id>/fuel/add", methods=["POST"])
@login_required
def fuel_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        liters = _parse_float(request.form.get("liters")) or 0
        cost_per_liter = _parse_float(request.form.get("cost_per_liter")) or 0

        fuel = VehicleFuel(
            vehicle_id=id,
            fuel_date=_parse_date(request.form.get("fuel_date")) or date.today(),
            liters=liters,
            cost_per_liter=cost_per_liter,
            total_cost=liters * cost_per_liter,
            odometer_km=_parse_float(request.form.get("odometer_km")),
            fuel_station=request.form.get("fuel_station", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(fuel)
        session.commit()
        flash("تم إضافة سجل الوقود بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="fuel"))


@vehicle_bp.route("/<id>/spare-part/add", methods=["POST"])
@login_required
def spare_part_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        item_id = request.form.get("item_id", "").strip()
        quantity = _parse_float(request.form.get("quantity")) or 0
        unit_price = _parse_float(request.form.get("unit_price")) or 0

        if not item_id or quantity <= 0:
            flash("يجب اختيار الصنف والكمية", "danger")
            return redirect(url_for("vehicles.vehicle_detail", id=id, tab="parts"))

        item = session.query(Item).filter(Item.id == item_id).first()
        if not item:
            flash("الصنف غير موجود", "danger")
            return redirect(url_for("vehicles.vehicle_detail", id=id, tab="parts"))

        if item.current_quantity < quantity:
            flash(f"الكمية المتوفرة {item.current_quantity} أقل من المطلوبة {quantity}", "danger")
            return redirect(url_for("vehicles.vehicle_detail", id=id, tab="parts"))

        item.current_quantity -= quantity

        tx = StockTransaction(
            transaction_number=f"VH-{date.today().strftime('%Y%m%d')}-{generate_uuid()[:8]}",
            transaction_type="out",
            date=date.today(),
            warehouse_id=item.warehouse_id,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=quantity * unit_price,
            destination=f"سيارة {vehicle.plate_number}",
            notes=f"استهلاك قطعة غيار للسيارة {vehicle.plate_number}",
        )
        session.add(tx)

        spare_part = VehicleSparePart(
            vehicle_id=id,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=quantity * unit_price,
            usage_date=date.today(),
            maintenance_id=request.form.get("maintenance_id", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(spare_part)
        session.commit()
        flash(f"تم صرف {quantity} {item.name_ar} من المخزن بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="parts"))


@vehicle_bp.route("/<id>/document/add", methods=["POST"])
@login_required
def document_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        title = request.form.get("title", "").strip()
        doc_type = request.form.get("doc_type", "").strip()
        if not title or not doc_type:
            flash("النوع والعنوان مطلوبان", "danger")
            return redirect(url_for("vehicles.vehicle_detail", id=id, tab="documents"))

        document = VehicleDocument(
            vehicle_id=id,
            doc_type=doc_type,
            title=title,
            issue_date=_parse_date(request.form.get("issue_date")),
            expiry_date=_parse_date(request.form.get("expiry_date")),
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(document)
        session.commit()
        flash("تم إضافة المستند بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="documents"))


@vehicle_bp.route("/<id>/document/<did>/delete", methods=["POST"])
@login_required
def document_delete(id, did):
    with session_scope() as session:
        doc = session.query(VehicleDocument).filter(VehicleDocument.id == did).first()
        if doc:
            session.delete(doc)
            session.commit()
            flash("تم حذف المستند", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="documents"))


@vehicle_bp.route("/<id>/driver-log/add", methods=["POST"])
@login_required
def driver_log_add(id):
    with session_scope() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("vehicles.vehicle_list"))

        driver_id = request.form.get("driver_id", "").strip()
        start_date = _parse_date(request.form.get("start_date"))

        if not driver_id or not start_date:
            flash("يجب اختيار السائق وتاريخ البدء", "danger")
            return redirect(url_for("vehicles.vehicle_detail", id=id, tab="drivers"))

        log = VehicleDriverLog(
            vehicle_id=id,
            driver_id=driver_id,
            start_date=start_date,
            end_date=_parse_date(request.form.get("end_date")),
            notes=request.form.get("notes", "").strip() or None,
        )
        session.add(log)

        if not log.end_date:
            vehicle.driver_id = driver_id

        session.commit()
        flash("تم إضافة السجل بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="drivers"))


@vehicle_bp.route("/<id>/driver-log/<lid>/end", methods=["POST"])
@login_required
def driver_log_end(id, lid):
    with session_scope() as session:
        log = session.query(VehicleDriverLog).filter(VehicleDriverLog.id == lid).first()
        if log:
            log.end_date = date.today()
            vehicle = session.query(Vehicle).filter(Vehicle.id == id).first()
            if vehicle and vehicle.driver_id == log.driver_id:
                vehicle.driver_id = None
            session.commit()
            flash("تم إنهاء فترة السائق بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_detail", id=id, tab="drivers"))


@vehicle_bp.route("/types")
@login_required
def vehicle_types_list():
    with session_scope() as session:
        types = session.query(VehicleType).order_by(VehicleType.name_ar).all()
        return render_template("vehicles/types.html", vehicle_types=types)


@vehicle_bp.route("/types/add", methods=["POST"])
@login_required
def vehicle_type_add():
    with session_scope() as session:
        name_ar = request.form.get("name_ar", "").strip()
        code = request.form.get("code", "").strip()
        if not name_ar or not code:
            flash("الاسم والكود مطلوبان", "danger")
            return redirect(url_for("vehicles.vehicle_types_list"))

        existing = session.query(VehicleType).filter(VehicleType.code == code).first()
        if existing:
            flash("هذا الكود موجود مسبقاً", "danger")
            return redirect(url_for("vehicles.vehicle_types_list"))

        seats_str = request.form.get("seats_count", "").strip()
        vtype = VehicleType(
            name_ar=name_ar,
            name_en=request.form.get("name_en", "").strip() or None,
            code=code,
            description=request.form.get("description", "").strip() or None,
            seats_count=int(seats_str) if seats_str else None,
            is_active=True,
        )
        session.add(vtype)
        session.commit()
        flash("تم إضافة النوع بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_types_list"))


@vehicle_bp.route("/types/<id>/update", methods=["POST"])
@login_required
def vehicle_type_update(id):
    with session_scope() as session:
        vtype = session.query(VehicleType).get(id)
        if not vtype:
            flash("النوع غير موجود", "danger")
            return redirect(url_for("vehicles.vehicle_types_list"))
        name_ar = request.form.get("name_ar", "").strip()
        code = request.form.get("code", "").strip()
        if not name_ar or not code:
            flash("الاسم والكود مطلوبان", "danger")
            return redirect(url_for("vehicles.vehicle_types_list"))
        dup = session.query(VehicleType).filter(VehicleType.code == code, VehicleType.id != id).first()
        if dup:
            flash("هذا الكود موجود مسبقاً", "danger")
            return redirect(url_for("vehicles.vehicle_types_list"))
        vtype.name_ar = name_ar
        vtype.name_en = request.form.get("name_en", "").strip() or None
        vtype.code = code
        vtype.description = request.form.get("description", "").strip() or None
        seats_str = request.form.get("seats_count", "").strip()
        vtype.seats_count = int(seats_str) if seats_str else None
        session.commit()
        flash("تم تحديث النوع بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_types_list"))


@vehicle_bp.route("/types/<id>/delete", methods=["POST"])
@login_required
def vehicle_type_delete(id):
    with session_scope() as session:
        vtype = session.query(VehicleType).get(id)
        if vtype:
            from src.web.routes.recycle_bin import add_to_recycle_bin
            add_to_recycle_bin(session, "vehicle_type", vtype.id, item_number=vtype.code, item_title=vtype.name_ar)
            session.delete(vtype)
            session.commit()
            flash("تم حذف النوع بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_types_list"))


@vehicle_bp.route("/types/<id>/toggle", methods=["POST"])
@login_required
def vehicle_type_toggle(id):
    with session_scope() as session:
        vtype = session.query(VehicleType).get(id)
        if vtype:
            vtype.is_active = not vtype.is_active
            session.commit()
            status = "تفعيل" if vtype.is_active else "تعطيل"
            flash(f"تم {status} النوع بنجاح", "success")
        return redirect(url_for("vehicles.vehicle_types_list"))


@vehicle_bp.route("/api/types/<id>")
@login_required
def api_vehicle_type(id):
    with session_scope() as session:
        vtype = session.query(VehicleType).get(id)
        if vtype:
            return jsonify({
                "success": True,
                "id": vtype.id,
                "name_ar": vtype.name_ar,
                "name_en": vtype.name_en or "",
                "code": vtype.code,
                "description": vtype.description or "",
                "seats_count": vtype.seats_count or 0,
                "is_active": vtype.is_active,
            })
        return jsonify({"success": False})


def _parse_date(value):
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def _parse_float(value):
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None
