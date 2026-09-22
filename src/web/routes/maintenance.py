from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, date

from src.core.database.connection import get_web_session
from src.core.models.maintenance_models import (
    MaintenanceRequest, MaintenanceItem, MaintenanceLog,
    VehiclePart, MaintenancePartReturn, MaintenanceSchedule
)
from src.core.models.vehicle_models import Vehicle
from src.core.models.base_models import Department

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


def _next_request_number(session):
    last = session.query(MaintenanceRequest.request_number).order_by(
        MaintenanceRequest.created_at.desc()
    ).first()
    if last and last[0]:
        import re
        m = re.search(r'(\d{4})$', last[0])
        if m:
            num = int(m.group(1)) + 1
            year = date.today().year
            return f"MSR-{year}-{num:04d}"
    year = date.today().year
    return f"MSR-{year}-0001"


def _next_return_number(session):
    last = session.query(MaintenancePartReturn.return_number).order_by(
        MaintenancePartReturn.created_at.desc()
    ).first()
    if last and last[0]:
        import re
        m = re.search(r'(\d{4})$', last[0])
        if m:
            num = int(m.group(1)) + 1
            year = date.today().year
            return f"RET-{year}-{num:04d}"
    year = date.today().year
    return f"RET-{year}-0001"


# ============================================================
# DASHBOARD
# ============================================================

@maintenance_bp.route("/")
@login_required
def dashboard():
    with get_web_session() as session:
        total_requests = session.query(func.count(MaintenanceRequest.id)).scalar() or 0
        pending = session.query(func.count(MaintenanceRequest.id)).filter(
            MaintenanceRequest.status.in_(["draft", "pending_maintenance", "pending_warehouse"])
        ).scalar() or 0
        in_progress = session.query(func.count(MaintenanceRequest.id)).filter(
            MaintenanceRequest.status == "in_progress"
        ).scalar() or 0
        completed = session.query(func.count(MaintenanceRequest.id)).filter(
            MaintenanceRequest.status.in_(["completed", "closed"])
        ).scalar() or 0

        recent_requests = session.query(MaintenanceRequest).order_by(
            desc(MaintenanceRequest.created_at)
        ).limit(5).all()

        vehicles_count = session.query(func.count(Vehicle.id)).scalar() or 0
        total_cost = session.query(func.sum(MaintenanceRequest.total_cost)).filter(
            MaintenanceRequest.status.in_(["completed", "closed"])
        ).scalar() or 0

        pending_parts = session.query(func.count(MaintenanceItem.id)).filter(
            MaintenanceItem.status == "pending"
        ).scalar() or 0

        pending_returns = session.query(func.count(MaintenancePartReturn.id)).filter(
            MaintenancePartReturn.status == "pending"
        ).scalar() or 0

        return render_template("maintenance/dashboard.html",
            total_requests=total_requests,
            pending=pending,
            in_progress=in_progress,
            completed=completed,
            recent_requests=recent_requests,
            vehicles_count=vehicles_count,
            total_cost=total_cost,
            pending_parts=pending_parts,
            pending_returns=pending_returns,
        )


# ============================================================
# REQUESTS LIST
# ============================================================

@maintenance_bp.route("/requests")
@login_required
def requests_list():
    with get_web_session() as session:
        status_filter = request.args.get("status", "")
        search = request.args.get("search", "")

        q = session.query(MaintenanceRequest)
        if status_filter:
            q = q.filter(MaintenanceRequest.status == status_filter)
        if search:
            q = q.filter(
                MaintenanceRequest.request_number.ilike(f"%{search}%")
            )
        requests = q.order_by(desc(MaintenanceRequest.created_at)).all()
        vehicles = session.query(Vehicle).all()
        return render_template("maintenance/requests_list.html",
            requests=requests, vehicles=vehicles,
            status_filter=status_filter, search=search,
        )


# ============================================================
# ADD REQUEST
# ============================================================

@maintenance_bp.route("/requests/add", methods=["GET", "POST"])
@login_required
def requests_add():
    with get_web_session() as session:
        vehicles = session.query(Vehicle).order_by(Vehicle.plate_number).all()
        next_code = _next_request_number(session)

        if request.method == "POST":
            vehicle_id = request.form.get("vehicle_id", "").strip()
            maintenance_type = request.form.get("maintenance_type", "").strip()
            priority = request.form.get("priority", "normal").strip()
            description = request.form.get("description", "").strip()
            current_km = request.form.get("current_km", "").strip()
            notes = request.form.get("notes", "").strip()

            if not vehicle_id or not maintenance_type:
                flash("السيارة ونوع الصيانة مطلوبان", "danger")
                return render_template("maintenance/request_form.html",
                    vehicles=vehicles, request_obj=None, next_code=next_code)

            req = MaintenanceRequest(
                request_number=next_code,
                vehicle_id=vehicle_id,
                requested_by=current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username,
                request_date=date.today(),
                maintenance_type=maintenance_type,
                priority=priority,
                current_km=float(current_km) if current_km else None,
                description=description,
                status="pending_maintenance",
                notes=notes or None,
                created_by=current_user.id,
            )
            session.add(req)
            session.flush()

            part_names = request.form.getlist("part_name[]")
            part_numbers = request.form.getlist("part_number[]")
            part_quantities = request.form.getlist("part_quantity[]")
            part_units = request.form.getlist("part_unit[]")

            for i in range(len(part_names)):
                if part_names[i].strip():
                    item = MaintenanceItem(
                        request_id=req.id,
                        part_name=part_names[i].strip(),
                        part_number=part_numbers[i].strip() if i < len(part_numbers) and part_numbers[i].strip() else None,
                        quantity=float(part_quantities[i]) if i < len(part_quantities) and part_quantities[i].strip() else 1.0,
                        unit=part_units[i].strip() if i < len(part_units) and part_units[i].strip() else "قطعة",
                    )
                    session.add(item)

            session.commit()
            flash(f"تم إنشاء طلب الصيانة {next_code} بنجاح", "success")
            return redirect(url_for("maintenance.requests_list"))

        return render_template("maintenance/request_form.html",
            vehicles=vehicles, request_obj=None, next_code=next_code)


# ============================================================
# REQUEST DETAIL
# ============================================================

@maintenance_bp.route("/requests/<request_id>")
@login_required
def requests_detail(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        items = session.query(MaintenanceItem).filter(
            MaintenanceItem.request_id == request_id
        ).all()

        vehicle_parts = session.query(VehiclePart).filter(
            VehiclePart.vehicle_id == req.vehicle_id
        ).all()

        part_returns = session.query(MaintenancePartReturn).filter(
            MaintenancePartReturn.request_id == request_id
        ).all()

        return render_template("maintenance/request_detail.html",
            req=req, items=items, vehicle_parts=vehicle_parts,
            part_returns=part_returns,
        )


# ============================================================
# EDIT REQUEST
# ============================================================

@maintenance_bp.route("/requests/<request_id>/edit", methods=["GET", "POST"])
@login_required
def requests_edit(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        vehicles = session.query(Vehicle).order_by(Vehicle.plate_number).all()

        if request.method == "POST":
            req.vehicle_id = request.form.get("vehicle_id", req.vehicle_id).strip()
            req.maintenance_type = request.form.get("maintenance_type", req.maintenance_type).strip()
            req.priority = request.form.get("priority", req.priority).strip()
            req.description = request.form.get("description", "").strip() or None
            km = request.form.get("current_km", "").strip()
            req.current_km = float(km) if km else req.current_km
            req.notes = request.form.get("notes", "").strip() or None

            session.query(MaintenanceItem).filter(
                MaintenanceItem.request_id == request_id
            ).delete()

            part_names = request.form.getlist("part_name[]")
            part_numbers = request.form.getlist("part_number[]")
            part_quantities = request.form.getlist("part_quantity[]")
            part_units = request.form.getlist("part_unit[]")

            for i in range(len(part_names)):
                if part_names[i].strip():
                    item = MaintenanceItem(
                        request_id=req.id,
                        part_name=part_names[i].strip(),
                        part_number=part_numbers[i].strip() if i < len(part_numbers) and part_numbers[i].strip() else None,
                        quantity=float(part_quantities[i]) if i < len(part_quantities) and part_quantities[i].strip() else 1.0,
                        unit=part_units[i].strip() if i < len(part_units) and part_units[i].strip() else "قطعة",
                    )
                    session.add(item)

            session.commit()
            flash(f"تم تعديل طلب الصيانة {req.request_number}", "success")
            return redirect(url_for("maintenance.requests_detail", request_id=req.id))

        items = session.query(MaintenanceItem).filter(
            MaintenanceItem.request_id == request_id
        ).all()
        return render_template("maintenance/request_form.html",
            vehicles=vehicles, request_obj=req, next_code=req.request_number, items=items)


# ============================================================
# APPROVE REQUEST (Maintenance Manager)
# ============================================================

@maintenance_bp.route("/requests/<request_id>/approve", methods=["POST"])
@login_required
def requests_approve(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        action = request.form.get("action", "")

        if action == "approve_maintenance":
            req.status = "pending_warehouse"
            req.maintenance_approved_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
            req.maintenance_approved_at = datetime.utcnow()
            flash("تم اعتماد الطلب من قسم الصيانة", "success")

        elif action == "start_work":
            req.status = "in_progress"
            flash("تم بدء العمل على الطلب", "success")

        elif action == "complete":
            req.status = "completed"
            req.completed_at = datetime.utcnow()
            req.completed_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
            log = MaintenanceLog(
                vehicle_id=req.vehicle_id,
                request_id=req.id,
                log_date=date.today(),
                km_reading=req.current_km,
                maintenance_type=req.maintenance_type,
                description=req.description,
                cost=req.total_cost,
                performed_by=req.completed_by,
                notes=req.notes,
            )
            session.add(log)
            flash("تم إتمام الصيانة بنجاح", "success")

        elif action == "cancel":
            req.status = "cancelled"
            flash("تم إلغاء الطلب", "warning")

        session.commit()
        return redirect(url_for("maintenance.requests_detail", request_id=req.id))


# ============================================================
# WAREHOUSE: Approve Parts
# ============================================================

@maintenance_bp.route("/requests/<request_id>/warehouse-approve", methods=["POST"])
@login_required
def warehouse_approve(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        item_ids = request.form.getlist("item_id[]")
        item_statuses = request.form.getlist("item_status[]")
        item_notes = request.form.getlist("item_notes[]")

        for i in range(len(item_ids)):
            item = session.query(MaintenanceItem).filter(MaintenanceItem.id == item_ids[i]).first()
            if item:
                item.status = item_statuses[i] if i < len(item_statuses) else "approved"
                item.warehouse_notes = item_notes[i] if i < len(item_notes) and item_notes[i].strip() else None

        req.status = "in_progress"
        req.warehouse_approved_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
        req.warehouse_approved_at = datetime.utcnow()

        session.commit()
        flash("تم اعتماد القطع من المخزن وبدء التنفيذ", "success")
        return redirect(url_for("maintenance.requests_detail", request_id=req.id))


# ============================================================
# PART RETURN (إعادة قطعة للمخزن)
# ============================================================

@maintenance_bp.route("/requests/<request_id>/return-part", methods=["POST"])
@login_required
def return_part(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        ret_number = _next_return_number(session)
        ret = MaintenancePartReturn(
            return_number=ret_number,
            request_id=req.id,
            vehicle_id=req.vehicle_id,
            part_name=request.form.get("part_name", "").strip(),
            part_number=request.form.get("part_number", "").strip() or None,
            condition=request.form.get("condition", "used").strip(),
            quantity=float(request.form.get("quantity", "1") or "1"),
            purchase_value=float(request.form.get("purchase_value", "0") or "0"),
            invoice_number=request.form.get("invoice_number", "").strip() or None,
            invoice_date=None,
            supplier=request.form.get("supplier", "").strip() or None,
            status="pending",
        )
        inv_date = request.form.get("invoice_date", "").strip()
        if inv_date:
            try:
                ret.invoice_date = datetime.strptime(inv_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        session.add(ret)

        vp = VehiclePart(
            vehicle_id=req.vehicle_id,
            part_name=ret.part_name,
            part_number=ret.part_number,
            status="removed",
            removed_date=date.today(),
            removed_km=req.current_km,
            removed_reason=request.form.get("removed_reason", "").strip() or None,
            remove_request_id=req.id,
        )
        session.add(vp)

        session.commit()
        flash(f"تم إنشاء إيصال الإعادة {ret_number}", "success")
        return redirect(url_for("maintenance.requests_detail", request_id=req.id))


# ============================================================
# INSTALL PART (تركيب قطعة على سيارة)
# ============================================================

@maintenance_bp.route("/requests/<request_id>/install-part", methods=["POST"])
@login_required
def install_part(request_id):
    with get_web_session() as session:
        req = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.id == request_id
        ).first()
        if not req:
            flash("طلب الصيانة غير موجود", "danger")
            return redirect(url_for("maintenance.requests_list"))

        vp = VehiclePart(
            vehicle_id=req.vehicle_id,
            part_name=request.form.get("part_name", "").strip(),
            part_number=request.form.get("part_number", "").strip() or None,
            installed_date=date.today(),
            installed_km=req.current_km,
            expected_km_life=float(request.form.get("expected_km_life", "0") or "0") or None,
            condition=request.form.get("condition", "new").strip(),
            install_request_id=req.id,
            status="installed",
        )
        session.add(vp)
        session.commit()
        flash("تم تسجيل تركيب القطعة", "success")
        return redirect(url_for("maintenance.requests_detail", request_id=req.id))


# ============================================================
# VEHICLE HISTORY
# ============================================================

@maintenance_bp.route("/vehicle/<vehicle_id>/history")
@login_required
def vehicle_history(vehicle_id):
    with get_web_session() as session:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            flash("السيارة غير موجودة", "danger")
            return redirect(url_for("maintenance.requests_list"))

        logs = session.query(MaintenanceLog).filter(
            MaintenanceLog.vehicle_id == vehicle_id
        ).order_by(desc(MaintenanceLog.log_date)).all()

        parts = session.query(VehiclePart).filter(
            VehiclePart.vehicle_id == vehicle_id
        ).order_by(desc(VehiclePart.installed_date)).all()

        requests = session.query(MaintenanceRequest).filter(
            MaintenanceRequest.vehicle_id == vehicle_id
        ).order_by(desc(MaintenanceRequest.created_at)).all()

        schedules = session.query(MaintenanceSchedule).filter(
            MaintenanceSchedule.vehicle_id == vehicle_id
        ).all()

        completed_count = session.query(func.count(MaintenanceRequest.id)).filter(
            MaintenanceRequest.vehicle_id == vehicle_id,
            MaintenanceRequest.status.in_(["completed", "closed"])
        ).scalar() or 0

        parts_installed = [p for p in parts if p.status == "installed"]
        parts_returned = [p for p in parts if p.status == "removed"]

        return render_template("maintenance/vehicle_history.html",
            vehicle=vehicle, logs=logs, parts=parts,
            requests=requests, schedules=schedules,
            total_requests=len(requests),
            completed_count=completed_count,
            parts_installed=parts_installed,
            parts_returned=parts_returned,
        )


# ============================================================
# ALL LOGS
# ============================================================

@maintenance_bp.route("/logs")
@login_required
def logs_list():
    with get_web_session() as session:
        logs = session.query(MaintenanceLog).order_by(
            desc(MaintenanceLog.log_date)
        ).all()
        vehicles = session.query(Vehicle).all()
        return render_template("maintenance/logs_list.html", logs=logs, vehicles=vehicles)


# ============================================================
# PART RETURNS LIST
# ============================================================

@maintenance_bp.route("/returns")
@login_required
def returns_list():
    with get_web_session() as session:
        status_filter = request.args.get("status", "")
        q = session.query(MaintenancePartReturn)
        if status_filter:
            q = q.filter(MaintenancePartReturn.status == status_filter)
        returns = q.order_by(desc(MaintenancePartReturn.created_at)).all()
        return render_template("maintenance/returns_list.html", returns=returns, status_filter=status_filter)


# ============================================================
# CONFIRM RETURN (Warehouse)
# ============================================================

@maintenance_bp.route("/returns/<return_id>/confirm", methods=["POST"])
@login_required
def confirm_return(return_id):
    with get_web_session() as session:
        ret = session.query(MaintenancePartReturn).filter(
            MaintenancePartReturn.id == return_id
        ).first()
        if not ret:
            flash("إيصال الإعادة غير موجود", "danger")
            return redirect(url_for("maintenance.returns_list"))

        ret.status = "received"
        ret.received_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
        ret.received_at = datetime.utcnow()
        ret.warehouse_notes = request.form.get("warehouse_notes", "").strip() or None
        session.commit()
        flash(f"تم استلام القطعة {ret.part_name}", "success")
        return redirect(url_for("maintenance.returns_list"))


# ============================================================
# SCHEDULES
# ============================================================

@maintenance_bp.route("/schedules")
@login_required
def schedules_list():
    with get_web_session() as session:
        schedules = session.query(MaintenanceSchedule).all()
        vehicles = session.query(Vehicle).all()
        return render_template("maintenance/schedules_list.html", schedules=schedules, vehicles=vehicles)


@maintenance_bp.route("/schedules/add", methods=["POST"])
@login_required
def schedules_add():
    with get_web_session() as session:
        vehicle_id = request.form.get("vehicle_id", "").strip()
        maintenance_type = request.form.get("maintenance_type", "").strip()
        interval_km = request.form.get("interval_km", "").strip()
        interval_days = request.form.get("interval_days", "").strip()

        if not vehicle_id or not maintenance_type:
            flash("السيارة ونوع الصيانة مطلوبان", "danger")
            return redirect(url_for("maintenance.schedules_list"))

        schedule = MaintenanceSchedule(
            vehicle_id=vehicle_id,
            maintenance_type=maintenance_type,
            interval_km=float(interval_km) if interval_km else None,
            interval_days=int(interval_days) if interval_days else None,
        )
        session.add(schedule)
        session.commit()
        flash("تم إضافة جدول الصيانة الدورية", "success")
        return redirect(url_for("maintenance.schedules_list"))
