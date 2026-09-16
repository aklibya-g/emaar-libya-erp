from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime, date
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import joinedload
from src.core.database.connection import get_web_session
from src.core.models.marketing_models import (
    MarketingClient, MarketingContract, WorkOrder, WorkOrderBus, WorkOrderAnnex,
    Trip, SchoolDriverEntitlement, MonthlyTripSheet
)
from src.core.models.base_models import Driver
from src.core.models.vehicle_models import Vehicle


marketing_bp = Blueprint("marketing", __name__, url_prefix="/marketing")


# ============================================================
# BUSINESS LOGIC HELPERS
# ============================================================

def generate_next_order_number(session):
    """توليد رقم أمر التشغيل التالي مع منع التكرار"""
    from sqlalchemy import func
    max_num = session.query(func.max(WorkOrder.order_number)).scalar()
    if max_num and max_num.isdigit():
        num = int(max_num) + 1
    else:
        num = 1201
    order_number = str(num)
    while session.query(WorkOrder).filter(WorkOrder.order_number == order_number).first():
        num += 1
        order_number = str(num)
    return order_number


def check_driver_availability(session, driver_name, start_date, end_date, exclude_order_id=None):
    """
    التحقق من حالة السائق (Active/Free) لحظة اختيار اسمه
    يتحقق من عدم وجود تعارض مع اوامر التشغيل النشطة
    """
    if not driver_name or not start_date or not end_date:
        return True, ""
    query = session.query(WorkOrder).join(WorkOrderBus).filter(
        WorkOrderBus.driver_name == driver_name,
        WorkOrder.status.in_(["active", "draft"]),
        or_(
            and_(WorkOrder.departure_date <= end_date, WorkOrder.return_date >= start_date),
            and_(WorkOrder.departure_date.is_(None), WorkOrder.return_date.is_(None))
        )
    )
    if exclude_order_id:
        query = query.filter(WorkOrder.id != exclude_order_id)
    conflicting_order = query.first()
    if conflicting_order:
        return False, f"السائق {driver_name} موجود حالياً في أمر التشغيل رقم {conflicting_order.order_number}"
    return True, ""


def check_bus_availability(session, bus_number, start_date, end_date, exclude_order_id=None):
    """التحقق من عدم تعارض الحافلة مع اوامر التشغيل النشطة"""
    if not bus_number or not start_date or not end_date:
        return True, ""
    query = session.query(WorkOrder).join(WorkOrderBus).filter(
        WorkOrderBus.bus_number == bus_number,
        WorkOrder.status.in_(["active", "draft"]),
        or_(
            and_(WorkOrder.departure_date <= end_date, WorkOrder.return_date >= start_date),
            and_(WorkOrder.departure_date.is_(None), WorkOrder.return_date.is_(None))
        )
    )
    if exclude_order_id:
        query = query.filter(WorkOrder.id != exclude_order_id)
    conflicting_order = query.first()
    if conflicting_order:
        return False, f"الحافلة {bus_number} موجودة حالياً في أمر التشغيل رقم {conflicting_order.order_number}"
    return True, ""


# ============================================================
# DASHBOARD
# ============================================================

@marketing_bp.route("/")
@login_required
def dashboard():
    with get_web_session() as session:
        today = date.today()
        current_month = today.month
        current_year = today.year

        total_orders = session.query(WorkOrder).filter(WorkOrder.is_deleted == False).count()
        active_orders = session.query(WorkOrder).filter(WorkOrder.status == "active", WorkOrder.is_deleted == False).count()
        draft_orders = session.query(WorkOrder).filter(WorkOrder.status == "draft", WorkOrder.is_deleted == False).count()
        total_contracts = session.query(MarketingContract).count()
        total_clients = session.query(MarketingClient).count()

        month_trips = session.query(Trip).filter(
            extract('month', Trip.trip_date) == current_month,
            extract('year', Trip.trip_date) == current_year
        ).count()
        month_value = session.query(func.sum(Trip.value)).filter(
            extract('month', Trip.trip_date) == current_month,
            extract('year', Trip.trip_date) == current_year
        ).scalar() or 0

        month_entitlements = session.query(func.sum(SchoolDriverEntitlement.net_entitlement)).filter(
            SchoolDriverEntitlement.month == current_month,
            SchoolDriverEntitlement.year == current_year
        ).scalar() or 0

        alerts = []

        pending_orders_query = session.query(WorkOrder).filter(
            WorkOrder.status == "draft",
            WorkOrder.is_deleted == False
        ).order_by(WorkOrder.created_at.desc()).limit(10).all()

        now = datetime.utcnow()
        pending_orders = []
        for order in pending_orders_query:
            days_since = (now - order.created_at).days if order.created_at else 0
            delayed_dept = None
            if not order.marketing_approved:
                delayed_dept = "التسويق"
            elif not order.movement_approved:
                delayed_dept = "الحركة"
            elif not order.finance_approved:
                delayed_dept = "المالي"
            elif not order.executive_approved:
                delayed_dept = "المدير التنفيذي"
            pending_orders.append({
                "order": order,
                "days_since": days_since,
                "delayed_dept": delayed_dept,
                "client_name": order.client.name_ar if order.client else "-",
            })
            approvals_needed = []
            if not order.marketing_approved:
                approvals_needed.append("التسويق")
            if not order.finance_approved:
                approvals_needed.append("المالي")
            if not order.movement_approved:
                approvals_needed.append("الحركة")
            if not order.executive_approved:
                approvals_needed.append("المدير التنفيذي")
            if approvals_needed:
                alerts.append({
                    "type": "warning",
                    "message": f"أمر التشغيل رقم {order.order_number} — بانتظار: {', '.join(approvals_needed)}",
                    "order_id": order.id,
                    "order_number": order.order_number,
                })

        upcoming_returns = session.query(WorkOrder).filter(
            WorkOrder.status == "active",
            WorkOrder.is_deleted == False,
            WorkOrder.return_date.isnot(None),
            WorkOrder.return_date <= today
        ).all()
        for order in upcoming_returns:
            alerts.append({
                "type": "danger",
                "message": f"أمر التشغيل رقم {order.order_number} — تاريخ عودة الحافلة {order.return_date.strftime('%Y-%m-%d')}",
                "order_id": order.id,
                "order_number": order.order_number,
            })

        recent_orders = session.query(WorkOrder).options(joinedload(WorkOrder.client)).filter(WorkOrder.is_deleted == False).order_by(WorkOrder.created_at.desc()).limit(10).all()
        recent_trips = session.query(Trip).order_by(Trip.trip_date.desc()).limit(10).all()

        school_driver_trips = session.query(func.sum(SchoolDriverEntitlement.trip_count)).filter(
            SchoolDriverEntitlement.month == current_month,
            SchoolDriverEntitlement.year == current_year
        ).scalar() or 0
        school_driver_value = session.query(func.sum(SchoolDriverEntitlement.net_entitlement)).filter(
            SchoolDriverEntitlement.month == current_month,
            SchoolDriverEntitlement.year == current_year
        ).scalar() or 0

        return render_template(
            "marketing/dashboard.html",
            page_title="لوحة تحكم التسويق التجاري",
            total_orders=total_orders,
            active_orders=active_orders,
            draft_orders=draft_orders,
            total_contracts=total_contracts,
            total_clients=total_clients,
            month_trips=month_trips,
            month_value=month_value,
            month_entitlements=month_entitlements,
            recent_orders=recent_orders,
            recent_trips=recent_trips,
            alerts=alerts,
            school_driver_trips=school_driver_trips,
            school_driver_value=school_driver_value,
            pending_orders=pending_orders,
        )


# ============================================================
# CLIENTS
# ============================================================

@marketing_bp.route("/clients")
@login_required
def clients_list():
    with get_web_session() as session:
        clients = session.query(MarketingClient).order_by(MarketingClient.client_number.desc()).all()
        return render_template(
            "marketing/clients_list.html",
            page_title="إدارة العملاء",
            clients=clients,
        )


@marketing_bp.route("/clients/add", methods=["GET", "POST"])
@login_required
def client_add():
    if request.method == "POST":
        with get_web_session() as session:
            from sqlalchemy import func
            max_num = session.query(func.max(MarketingClient.client_number)).scalar()
            if max_num and max_num.startswith("C"):
                try:
                    num = int(max_num[1:]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            client_number = f"C{num:04d}"
            client = MarketingClient(
                client_number=client_number,
                name_ar=request.form.get("name_ar", ""),
                name_en=request.form.get("name_en"),
                phone=request.form.get("phone"),
                address=request.form.get("address"),
                scope=request.form.get("scope"),
                contact_person=request.form.get("contact_person"),
                notes=request.form.get("notes"),
            )
            session.add(client)
            session.commit()
            flash("تم إضافة العميل بنجاح", "success")
            return redirect(url_for("marketing.clients_list"))
    return render_template("marketing/client_form.html", page_title="إضافة عميل", client=None)


@marketing_bp.route("/clients/<client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id):
    with get_web_session() as session:
        client = session.query(MarketingClient).get(client_id)
        if not client:
            flash("العميل غير موجود", "danger")
            return redirect(url_for("marketing.clients_list"))
        if request.method == "POST":
            client.name_ar = request.form.get("name_ar", client.name_ar)
            client.name_en = request.form.get("name_en")
            client.phone = request.form.get("phone")
            client.address = request.form.get("address")
            client.scope = request.form.get("scope")
            client.contact_person = request.form.get("contact_person")
            client.notes = request.form.get("notes")
            session.commit()
            flash("تم تعديل العميل بنجاح", "success")
            return redirect(url_for("marketing.clients_list"))
        return render_template("marketing/client_form.html", page_title="تعديل العميل", client=client)


# ============================================================
# CONTRACTS
# ============================================================

@marketing_bp.route("/contracts")
@login_required
def contracts_list():
    with get_web_session() as session:
        contracts = session.query(MarketingContract).order_by(MarketingContract.created_at.desc()).all()
        return render_template(
            "marketing/contracts_list.html",
            page_title="إدارة العقود",
            contracts=contracts,
        )


@marketing_bp.route("/contracts/add", methods=["GET", "POST"])
@login_required
def contract_add():
    if request.method == "POST":
        with get_web_session() as session:
            from sqlalchemy import func
            max_num = session.query(func.max(MarketingContract.contract_number)).scalar()
            if max_num and max_num.startswith("CON"):
                try:
                    num = int(max_num[3:]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            contract_number = f"CON{num:04d}"
            contract = MarketingContract(
                contract_number=contract_number,
                title=request.form.get("title", ""),
                client_id=request.form.get("client_id"),
                start_date=datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date(),
                end_date=datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date(),
                total_value=float(request.form.get("total_value", 0)),
                bus_count=int(request.form["bus_count"]) if request.form.get("bus_count") else None,
                responsible_name=request.form.get("responsible_name") or None,
                description=request.form.get("description"),
                notes=request.form.get("notes"),
                amendment_bus_count=int(request.form["amendment_bus_count"]) if request.form.get("amendment_bus_count") else None,
                amendment_value=float(request.form["amendment_value"]) if request.form.get("amendment_value") else None,
                amendment_description=request.form.get("amendment_description") or None,
            )
            session.add(contract)
            session.commit()
            flash("تم إضافة العقد بنجاح", "success")
            return redirect(url_for("marketing.contracts_list"))
    with get_web_session() as session:
        clients = session.query(MarketingClient).filter(MarketingClient.is_active == True).all()
        return render_template(
            "marketing/contract_form.html",
            page_title="إضافة عقد",
            contract=None,
            clients=clients,
        )


@marketing_bp.route("/contracts/<contract_id>/edit", methods=["GET", "POST"])
@login_required
def contract_edit(contract_id):
    with get_web_session() as session:
        contract = session.query(MarketingContract).get(contract_id)
        if not contract:
            flash("العقد غير موجود", "danger")
            return redirect(url_for("marketing.contracts_list"))
        if request.method == "POST":
            contract.title = request.form.get("title", contract.title)
            contract.client_id = request.form.get("client_id", contract.client_id)
            contract.start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
            contract.end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()
            contract.total_value = float(request.form.get("total_value", contract.total_value))
            contract.bus_count = int(request.form["bus_count"]) if request.form.get("bus_count") else None
            contract.responsible_name = request.form.get("responsible_name") or None
            contract.description = request.form.get("description")
            contract.notes = request.form.get("notes")
            contract.amendment_bus_count = int(request.form["amendment_bus_count"]) if request.form.get("amendment_bus_count") else None
            contract.amendment_value = float(request.form["amendment_value"]) if request.form.get("amendment_value") else None
            contract.amendment_description = request.form.get("amendment_description") or None
            contract.status = request.form.get("status", contract.status)
            session.commit()
            flash("تم تعديل العقد بنجاح", "success")
            return redirect(url_for("marketing.contracts_list"))
        clients = session.query(MarketingClient).filter(MarketingClient.is_active == True).all()
        return render_template(
            "marketing/contract_form.html",
            page_title="تعديل العقد",
            contract=contract,
            clients=clients,
        )


@marketing_bp.route("/contracts/<contract_id>")
@login_required
def contract_detail(contract_id):
    with get_web_session() as session:
        contract = session.query(MarketingContract).get(contract_id)
        if not contract:
            flash("العقد غير موجود", "danger")
            return redirect(url_for("marketing.contracts_list"))
        work_orders = session.query(WorkOrder).filter(
            WorkOrder.contract_id == contract.id
        ).order_by(WorkOrder.created_at.desc()).all()
        return render_template(
            "marketing/contract_detail.html",
            page_title=f"عرض العقد {contract.contract_number}",
            contract=contract,
            work_orders=work_orders,
        )


@marketing_bp.route("/contracts/<contract_id>/print")
@login_required
def contract_print(contract_id):
    with get_web_session() as session:
        contract = session.query(MarketingContract).get(contract_id)
        if not contract:
            flash("العقد غير موجود", "danger")
            return redirect(url_for("marketing.contracts_list"))
        return render_template(
            "marketing/contract_print.html",
            contract=contract,
            today=date.today().strftime('%Y-%m-%d'),
        )


# ============================================================
# WORK ORDERS
# ============================================================

@marketing_bp.route("/work-orders")
@login_required
def work_orders_list():
    with get_web_session() as session:
        status = request.args.get("status", None)
        query = session.query(WorkOrder).options(joinedload(WorkOrder.client)).filter(WorkOrder.is_deleted == False)
        if status:
            if status == "approved":
                query = query.filter(WorkOrder.status.in_(["approved", "active"]))
            else:
                query = query.filter(WorkOrder.status == status)
        orders = query.order_by(WorkOrder.created_at.desc()).all()
        total = session.query(WorkOrder).filter(WorkOrder.is_deleted == False).count()
        draft_count = session.query(WorkOrder).filter(WorkOrder.is_deleted == False, WorkOrder.status == "draft").count()
        marketing_approved_count = session.query(WorkOrder).filter(WorkOrder.is_deleted == False, WorkOrder.status == "marketing_approved").count()
        movement_approved_count = session.query(WorkOrder).filter(WorkOrder.is_deleted == False, WorkOrder.status == "movement_approved").count()
        finance_approved_count = session.query(WorkOrder).filter(WorkOrder.is_deleted == False, WorkOrder.status == "finance_approved").count()
        approved_count = session.query(WorkOrder).filter(WorkOrder.is_deleted == False, WorkOrder.status.in_(["approved", "active"])).count()
        return render_template(
            "marketing/work_orders_list.html",
            page_title="اوامر التشغيل",
            orders=orders,
            current_status=status,
            total_orders=total,
            draft_count=draft_count,
            marketing_approved_count=marketing_approved_count,
            movement_approved_count=movement_approved_count,
            finance_approved_count=finance_approved_count,
            approved_count=approved_count,
        )


@marketing_bp.route("/api/check-duplicate", methods=["POST"])
@login_required
def check_duplicate_order():
    data = request.get_json()
    client_id = data.get("client_id")
    departure_date = data.get("departure_date")
    return_date = data.get("return_date")
    destination = data.get("destination")
    bus_count = data.get("bus_count")
    duration = data.get("duration")
    exclude_id = data.get("exclude_id")
    if not client_id or not departure_date:
        return jsonify({"duplicates": []})
    with get_web_session() as session:
        q = session.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.client_id == client_id
        )
        if exclude_id:
            q = q.filter(WorkOrder.id != exclude_id)
        orders = q.all()
        duplicates = []
        for o in orders:
            score = 0
            if o.departure_date and departure_date:
                try:
                    dep_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
                    from datetime import timedelta
                    date_diff = abs((o.departure_date - dep_date).days)
                    if date_diff == 0:
                        score += 3
                    elif date_diff <= 3:
                        score += 2
                    elif date_diff <= 7:
                        score += 1
                except ValueError:
                    pass
            if o.destination and destination:
                if o.destination.strip() == destination.strip():
                    score += 2
                elif destination.strip() in o.destination.strip() or o.destination.strip() in destination.strip():
                    score += 1
            if o.buses and bus_count:
                if len(o.buses) == int(bus_count):
                    score += 2
            if o.duration_days and duration:
                if o.duration_days == int(duration):
                    score += 2
            if o.return_date and return_date:
                try:
                    ret_date = datetime.strptime(return_date, "%Y-%m-%d").date()
                    if o.return_date == ret_date:
                        score += 2
                except ValueError:
                    pass
            if score >= 4:
                duplicates.append({
                    "id": o.id,
                    "order_number": o.order_number,
                    "departure_date": o.departure_date.strftime('%Y-%m-%d') if o.departure_date else "-",
                    "return_date": o.return_date.strftime('%Y-%m-%d') if o.return_date else "-",
                    "destination": o.destination or "-",
                    "total_value": o.total_value,
                    "status": o.status,
                    "buses": len(o.buses) if o.buses else 0,
                    "duration": o.duration_days or 0,
                })
        return jsonify({"duplicates": duplicates})


@marketing_bp.route("/api/trip-locations", methods=["GET"])
@login_required
def trip_locations():
    with get_web_session() as session:
        from_values = session.query(WorkOrder.trip_from).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_from.isnot(None),
            WorkOrder.trip_from != ""
        ).distinct().all()
        to_values = session.query(WorkOrder.trip_to).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_to.isnot(None),
            WorkOrder.trip_to != ""
        ).distinct().all()
        return jsonify({
            "from": sorted([v[0] for v in from_values]),
            "to": sorted([v[0] for v in to_values])
        })


@marketing_bp.route("/work-orders/add", methods=["GET", "POST"])
@login_required
def work_order_add():
    if request.method == "POST":
        with get_web_session() as session:
            order_number = generate_next_order_number(session)
            start_date = request.form.get("departure_date")
            end_date = request.form.get("return_date")
            if start_date and end_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                bus_count = int(request.form.get("bus_count", 0))
                for i in range(bus_count):
                    driver_name = request.form.get(f"driver_name_{i}")
                    bus_number = request.form.get(f"bus_number_{i}")
                    driver_ok, driver_msg = check_driver_availability(session, driver_name, start_date, end_date)
                    if not driver_ok:
                        flash(driver_msg, "danger")
                        return redirect(url_for("marketing.work_order_add"))
                    bus_ok, bus_msg = check_bus_availability(session, bus_number, start_date, end_date)
                    if not bus_ok:
                        flash(bus_msg, "danger")
                        return redirect(url_for("marketing.work_order_add"))
            order = WorkOrder(
                order_number=order_number,
                contract_id=request.form.get("contract_id") or None,
                client_id=request.form.get("client_id"),
                destination=request.form.get("destination") or request.form.get("trip_to") or "",
                contact_phone=request.form.get("contact_phone"),
                trip_route=request.form.get("trip_route"),
                trip_from=request.form.get("trip_from"),
                trip_to=request.form.get("trip_to"),
                duration_days=int(request.form.get("duration_days", 1)),
                bus_count_requested=int(request.form.get("bus_count_requested", 1)),
                bus_rental_value=float(request.form.get("bus_rental_value") or 0),
                bus_maintenance_value=float(request.form.get("bus_maintenance_value") or 0),
                driver_transport_value=float(request.form.get("driver_transport_value") or 0),
                trip_price=float(request.form.get("trip_price") or 0),
                total_value=float(request.form.get("total_value") or 0),
                estimated_distance=float(request.form["estimated_distance"]) if request.form.get("estimated_distance") else None,
                adjustment_percent=float(request.form["adjustment_percent"]) if request.form.get("adjustment_percent") else None,
                adjustment_value=float(request.form["adjustment_value"]) if request.form.get("adjustment_value") else None,
                adjustment_type=request.form.get("adjustment_type") or None,
                departure_date=start_date if isinstance(start_date, date) else None,
                return_date=end_date if isinstance(end_date, date) else None,
                notes=request.form.get("notes"),
                is_draft=True,
                status="draft",
                created_by_user_id=current_user.id if current_user.is_authenticated else None,
                edited_by_user_id=current_user.id if current_user.is_authenticated else None,
                edited_by_name=current_user.full_name_ar if current_user.is_authenticated else None,
                order_type=request.form.get("order_type") or "new",
                related_order_id=request.form.get("related_order_id") or None,
                amendment_reason=request.form.get("amendment_reason") or None,
                trip_type=request.form.get("trip_type") or "internal",
            )
            session.add(order)
            session.flush()
            bus_count = int(request.form.get("bus_count", 0))
            for i in range(bus_count):
                vehicle_id = request.form.get(f"vehicle_id_{i}") or None
                driver_id = request.form.get(f"driver_id_{i}") or None
                bus_number = request.form.get(f"bus_number_{i}")
                driver_name = request.form.get(f"driver_name_{i}")
                if vehicle_id:
                    v = session.query(Vehicle).get(vehicle_id)
                    if v:
                        bus_number = v.plate_number
                        if not driver_id and v.driver_id:
                            driver_id = v.driver_id
                if driver_id:
                    d = session.query(Driver).get(driver_id)
                    if d:
                        driver_name = d.full_name_ar
                bus = WorkOrderBus(
                    work_order_id=order.id,
                    vehicle_id=vehicle_id,
                    driver_id=driver_id,
                    bus_number=bus_number,
                    driver_name=driver_name,
                    bus_price=float(request.form.get(f"bus_price_{i}", 0)),
                    driver_share_pct=float(request.form.get(f"driver_share_pct_{i}", 10) or 10),
                    driver_share_value=float(request.form.get(f"driver_share_value_{i}", 0) or 0),
                    notes=request.form.get(f"bus_notes_{i}"),
                )
                session.add(bus)
            try:
                session.commit()
                if order.is_draft:
                    flash(f"تم حفظ أمر التشغيل رقم {order_number} كمسودة", "warning")
                else:
                    flash(f"تم إضافة أمر التشغيل رقم {order_number} بنجاح", "success")
                return redirect(url_for("marketing.work_order_detail", order_id=order.id))
            except Exception as e:
                session.rollback()
                import traceback
                traceback.print_exc()
                flash(f"خطأ في حفظ البيانات: {str(e)}", "danger")
    with get_web_session() as session:
        clients = session.query(MarketingClient).filter(
            MarketingClient.is_active == True
        ).order_by(MarketingClient.created_at.desc()).all()
        contracts = session.query(MarketingContract).all()
        next_order_number = generate_next_order_number(session)
        trip_from_values = session.query(WorkOrder.trip_from).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_from.isnot(None),
            WorkOrder.trip_from != ""
        ).distinct().all()
        trip_from_locations = sorted([v[0] for v in trip_from_values])
        trip_to_values = session.query(WorkOrder.trip_to).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_to.isnot(None),
            WorkOrder.trip_to != ""
        ).distinct().all()
        trip_to_locations = sorted([v[0] for v in trip_to_values])
        related_orders = session.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.order_type == "new",
            WorkOrder.status.in_(["draft", "marketing_approved", "movement_approved", "finance_approved", "approved", "active"]),
        ).order_by(WorkOrder.created_at.desc()).all()
        return render_template(
            "marketing/work_order_form.html",
            page_title="إضافة أمر تشغيل",
            order=None,
            clients=clients,
            contracts=contracts,
            next_order_number=next_order_number,
            trip_from_locations=trip_from_locations,
            trip_to_locations=trip_to_locations,
            related_orders=related_orders,
        )


@marketing_bp.route("/work-orders/<order_id>")
@login_required
def work_order_detail(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("امر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        all_orders = session.query(WorkOrder).filter(
            WorkOrder.is_deleted == False
        ).all()
        return render_template(
            "marketing/work_order_detail.html",
            page_title=f"أمر تشغيل رقم {order.order_number}",
            order=order,
            all_orders=all_orders,
            now_datetime=datetime.utcnow(),
        )


@marketing_bp.route("/approval-tracking")
@login_required
def approval_tracking():
    with get_web_session() as session:
        now = datetime.utcnow()
        status_filter = request.args.get("status", "pending")
        q = session.query(WorkOrder).options(joinedload(WorkOrder.client)).filter(WorkOrder.is_deleted == False)
        if status_filter == "pending":
            q = q.filter(WorkOrder.status.in_(["draft", "marketing_approved", "movement_approved", "finance_approved"]))
        elif status_filter == "approved":
            q = q.filter(WorkOrder.status == "approved")
        elif status_filter == "cancelled":
            q = q.filter(WorkOrder.status == "cancelled")
        orders = q.order_by(WorkOrder.created_at.desc()).all()
        orders_data = []
        for order in orders:
            days_since = (now - order.created_at).days if order.created_at else 0
            delayed_dept = None
            if not order.marketing_approved:
                delayed_dept = "التسويق"
            elif not order.movement_approved:
                delayed_dept = "الحركة"
            elif not order.finance_approved:
                delayed_dept = "المالي"
            elif not order.executive_approved:
                delayed_dept = "المدير التنفيذي"
            mkt_delay = days_since if not order.marketing_approved else 0
            mov_delay = days_since if not order.movement_approved and order.marketing_approved else 0
            fin_delay = days_since if not order.finance_approved and order.movement_approved else 0
            exe_delay = days_since if not order.executive_approved and order.finance_approved else 0
            orders_data.append({
                "order": order,
                "days_since": days_since,
                "delayed_dept": delayed_dept,
                "mkt_delay": mkt_delay,
                "mov_delay": mov_delay,
                "fin_delay": fin_delay,
                "exe_delay": exe_delay,
                "client_name": order.client.name_ar if order.client else "-",
            })
        return render_template(
            "marketing/approval_tracking.html",
            orders_data=orders_data,
            status_filter=status_filter,
            now=now,
        )


@marketing_bp.route("/work-orders/<order_id>/edit", methods=["GET", "POST"])
@login_required
def work_order_edit(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("أمر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if order.marketing_approved or order.movement_approved or order.finance_approved or order.executive_approved:
            flash("لا يمكن تعديل أمر التشغيل بعد الاعتماد", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        if request.method == "POST":
            was_active = order.status == "active"
            order.contract_id = request.form.get("contract_id") or None
            order.client_id = request.form.get("client_id")
            order.contact_phone = request.form.get("contact_phone")
            order.trip_route = request.form.get("trip_route")
            order.trip_from = request.form.get("trip_from")
            order.trip_to = request.form.get("trip_to")
            order.destination = request.form.get("destination") or request.form.get("trip_to") or ""
            order.duration_days = int(request.form.get("duration_days", 1))
            order.bus_count_requested = int(request.form.get("bus_count_requested", 1))
            order.bus_maintenance_value = float(request.form.get("bus_maintenance_value") or 0)
            order.driver_transport_value = float(request.form.get("driver_transport_value") or 0)
            order.trip_price = float(request.form.get("trip_price") or 0)
            order.total_value = float(request.form.get("total_value") or 0)
            order.estimated_distance = float(request.form["estimated_distance"]) if request.form.get("estimated_distance") else None
            order.adjustment_percent = float(request.form["adjustment_percent"]) if request.form.get("adjustment_percent") else None
            order.adjustment_value = float(request.form["adjustment_value"]) if request.form.get("adjustment_value") else None
            order.adjustment_type = request.form.get("adjustment_type") or None
            order.notes = request.form.get("notes")
            order.edited_by_user_id = current_user.id if current_user.is_authenticated else None
            order.edited_by_name = current_user.full_name_ar if current_user.is_authenticated else None
            dep = request.form.get("departure_date")
            ret = request.form.get("return_date")
            if dep:
                order.departure_date = datetime.strptime(dep, "%Y-%m-%d").date()
            if ret:
                order.return_date = datetime.strptime(ret, "%Y-%m-%d").date()
            order.is_draft = True
            order.status = "draft"
            order.trip_type = request.form.get("trip_type") or "internal"
            # حذف الحافلات القديمة وإعادة اضافتها
            for old_bus in order.buses:
                session.delete(old_bus)
            session.flush()
            bus_count = int(request.form.get("bus_count", 0))
            for i in range(bus_count):
                vehicle_id = request.form.get(f"vehicle_id_{i}") or None
                driver_id = request.form.get(f"driver_id_{i}") or None
                bus_number = request.form.get(f"bus_number_{i}")
                driver_name = request.form.get(f"driver_name_{i}")
                if vehicle_id:
                    v = session.query(Vehicle).get(vehicle_id)
                    if v:
                        bus_number = v.plate_number
                        if not driver_id and v.driver_id:
                            driver_id = v.driver_id
                if driver_id:
                    d = session.query(Driver).get(driver_id)
                    if d:
                        driver_name = d.full_name_ar
                bus = WorkOrderBus(
                    work_order_id=order.id,
                    vehicle_id=vehicle_id,
                    driver_id=driver_id,
                    bus_number=bus_number,
                    driver_name=driver_name,
                    bus_price=float(request.form.get(f"bus_price_{i}", 0)),
                    driver_share_pct=float(request.form.get(f"driver_share_pct_{i}", 10) or 10),
                    driver_share_value=float(request.form.get(f"driver_share_value_{i}", 0) or 0),
                    notes=request.form.get(f"bus_notes_{i}"),
                )
                session.add(bus)
            if was_active:
                order.marketing_approved = False
                order.finance_approved = False
                order.movement_approved = False
                order.executive_approved = False
                flash("تمت إعادة الاعتمادات بسبب التعديل على أمر التشغيل", "warning")
            session.commit()
            flash(f"تم حفظ التعديلات على أمر التشغيل رقم {order.order_number}", "success")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        clients = session.query(MarketingClient).filter(
            MarketingClient.is_active == True
        ).order_by(MarketingClient.created_at.desc()).all()
        contracts = session.query(MarketingContract).all()
        trip_from_values = session.query(WorkOrder.trip_from).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_from.isnot(None),
            WorkOrder.trip_from != ""
        ).distinct().all()
        trip_from_locations = sorted([v[0] for v in trip_from_values])
        trip_to_values = session.query(WorkOrder.trip_to).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.trip_to.isnot(None),
            WorkOrder.trip_to != ""
        ).distinct().all()
        trip_to_locations = sorted([v[0] for v in trip_to_values])
        related_orders = session.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.order_type == "new",
            WorkOrder.status.in_(["draft", "marketing_approved", "movement_approved", "finance_approved", "approved", "active"]),
        ).order_by(WorkOrder.created_at.desc()).all()
        return render_template(
            "marketing/work_order_form.html",
            page_title=f"تعديل أمر التشغيل رقم {order.order_number}",
            order=order,
            clients=clients,
            contracts=contracts,
            trip_from_locations=trip_from_locations,
            trip_to_locations=trip_to_locations,
            related_orders=related_orders,
        )


@marketing_bp.route("/work-orders/<order_id>/delete", methods=["POST"])
@login_required
def work_order_delete(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("امر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if order.marketing_approved or order.movement_approved or order.finance_approved or order.executive_approved:
            flash("لا يمكن حذف أمر التشغيل بعد الاعتماد", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        order_number = order.order_number
        order.is_deleted = True
        from src.web.routes.recycle_bin import add_to_recycle_bin
        add_to_recycle_bin(
            session, "work_order", order.id,
            item_number=order_number,
            item_title=f"امر تشغيل - {order.client.name_ar if order.client else '-'}",
        )
        session.commit()
        flash(f"تم حذف أمر التشغيل رقم {order_number} (يمكن استعادته من سلة المحذوفات)", "warning")
        return redirect(url_for("marketing.work_orders_list"))


@marketing_bp.route("/work-orders/<order_id>/apply-discount", methods=["POST"])
@login_required
def work_order_apply_discount(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("امر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if not current_user.is_admin and current_user.role_name != "executive":
            flash("صلاحية مرفوضة - المدير التنفيذي فقط", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        if order.status == "cancelled":
            flash("لا يمكن التخفيض على أمر ملغي", "warning")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        discount_type = request.form.get("discount_type", "value")
        discount_value = float(request.form.get("discount_value") or 0)
        if discount_type == "percent":
            discount_percent = float(request.form.get("discount_percent") or 0)
            discount_value = order.total_value * (discount_percent / 100)
        discount_reason = request.form.get("discount_reason") or ""
        if discount_value <= 0:
            flash("قيمة التخفيض يجب ان تكون اكثر من صفر", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        if discount_value > order.total_value:
            flash("قيمة التخفيض لا يمكن ان تتجاوز القيمة الأصلية", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        order.executive_discount_value = discount_value
        order.executive_discount_reason = discount_reason
        order.executive_discount_by = current_user.full_name_ar if current_user.is_authenticated else current_user.username
        order.executive_discount_at = datetime.utcnow()
        order.final_value = order.total_value - discount_value
        session.commit()
        flash(f"تم تطبيق تخفيض {discount_value:,.0f} د.ل على أمر التشغيل رقم {order.order_number}", "success")
        return redirect(url_for("marketing.work_order_detail", order_id=order.id))


@marketing_bp.route("/work-orders/<order_id>/reverse-discount", methods=["POST"])
@login_required
def work_order_reverse_discount(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("امر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if not current_user.is_admin:
            flash("صلاحية مرفوضة - المدير التنفيذي فقط", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        if not order.executive_discount_value or order.executive_discount_value <= 0:
            flash("لا يوجد تخفيض لازالته", "warning")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        old_value = order.executive_discount_value
        order.executive_discount_value = 0
        order.executive_discount_reason = None
        order.executive_discount_by = None
        order.executive_discount_at = None
        order.final_value = 0
        session.commit()
        flash(f"تم التراجع عن التخفيض {old_value:,.0f} د.ل على أمر التشغيل رقم {order.order_number}", "success")
        return redirect(url_for("marketing.work_order_detail", order_id=order.id))


@marketing_bp.route("/work-orders/<order_id>/cancel", methods=["POST"])
@login_required
def work_order_cancel(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("امر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if order.status == "cancelled":
            flash("امر التشغيل ملغي بالفعل", "warning")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        has_approval = order.marketing_approved or order.movement_approved or order.finance_approved or order.executive_approved
        if has_approval and not current_user.is_admin:
            flash("لا يمكن الالغاء - صلاحية المدير التنفيذي فقط بعد الاعتماد", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order.id))
        order.status = "cancelled"
        order.is_draft = False
        # الغاء مستحقات السائقين المرتبطة
        ents = session.query(SchoolDriverEntitlement).filter(
            SchoolDriverEntitlement.work_order_id == order.id
        ).all()
        for ent in ents:
            ent.status = "cancelled"
        session.commit()
        flash(f"تم الالغاء أمر التشغيل رقم {order.order_number}", "warning")
        return redirect(url_for("marketing.work_orders_list"))


@marketing_bp.route("/work-orders/delete-all", methods=["POST"])
@login_required
def work_order_delete_all():
    with get_web_session() as session:
        from src.core.security.auth_service import AuthService
        auth_service = AuthService(session)
        password = request.form.get("password", "")
        username = current_user.username if current_user.is_authenticated else "admin"
        user = auth_service.authenticate(username, password)
        if not user:
            flash("كلمة المرور غير صحيحة", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        orders = session.query(WorkOrder).filter(WorkOrder.is_deleted == False).all()
        count = 0
        from src.web.routes.recycle_bin import add_to_recycle_bin
        for order in orders:
            order.is_deleted = True
            add_to_recycle_bin(
                session, "work_order", order.id,
                item_number=order.order_number,
                item_title=f"امر تشغيل - {order.client.name_ar if order.client else '-'}",
            )
            count += 1
        session.commit()
        flash(f"تم حذف {count} أمر تشغيل (يمكن استعادتها من سلة المحذوفات)", "warning")
        return redirect(url_for("marketing.work_orders_list"))


@marketing_bp.route("/work-orders/<order_id>/approve", methods=["POST"])
@login_required
def work_order_approve(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("أمر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        department = request.form.get("department")
        now = datetime.utcnow()
        user_name = current_user.full_name_ar if current_user.is_authenticated else "غير معروف"
        from src.core.models.base_models import ApprovalStep
        steps = session.query(ApprovalStep).filter(
            ApprovalStep.is_active == True
        ).order_by(ApprovalStep.step_order).all()
        field_map = {
            "التسويق": "marketing_approved",
            "الحركة": "movement_approved",
            "المالية": "finance_approved",
            "المدير التنفيذي": "executive_approved",
        }
        dept_key_map = {
            "التسويق": "marketing",
            "الحركة": "movement",
            "المالية": "finance",
            "المدير التنفيذي": "executive",
        }
        current_step = None
        for step in steps:
            if dept_key_map.get(step.name) == department:
                current_step = step
                break
        if not current_step:
            flash("خطوة الاعتماد غير صالحة", "danger")
            return redirect(url_for("marketing.work_order_detail", order_id=order_id))
        for prev_step in steps:
            if prev_step.step_order >= current_step.step_order:
                break
            prev_field = field_map.get(prev_step.name)
            if prev_field and not getattr(order, prev_field, False):
                flash(f"يجب اعتماد {prev_step.name} أولاً", "danger")
                return redirect(url_for("marketing.work_order_detail", order_id=order_id))
        target_field = field_map.get(current_step.name)
        if target_field:
            setattr(order, target_field, True)
            setattr(order, f"{target_field}_at", now)
            setattr(order, f"{target_field}_by", user_name)
            if current_step.name == "المدير التنفيذي":
                order.status = "approved"
            else:
                order.status = f"{department}_approved"
            order.is_draft = False

            if department == "movement" and order.movement_approved:
                from src.core.models.marketing_models import FinancialClaim
                existing_claim = session.query(FinancialClaim).filter(
                    FinancialClaim.work_order_id == order.id
                ).first()
                if not existing_claim:
                    def _next_claim_number(s):
                        last = s.query(FinancialClaim).order_by(FinancialClaim.id.desc()).first()
                        if last and last.claim_number:
                            try:
                                num = int(last.claim_number.split("-")[-1]) + 1
                            except:
                                num = 1
                        else:
                            num = 1
                        return f"FC-{date.today().year}-{num:04d}"
                    route_parts = []
                    if order.trip_from:
                        route_parts.append(order.trip_from)
                    if order.trip_to:
                        route_parts.append(order.trip_to)
                    route_desc = " ← ".join(route_parts) if route_parts else order.destination or "-"
                    final_val = order.final_value or order.total_value or 0
                    claim = FinancialClaim(
                        claim_number=_next_claim_number(session),
                        work_order_id=order.id,
                        client_id=order.client_id,
                        contract_id=order.contract_id,
                        claim_date=date.today(),
                        order_number=order.order_number,
                        destination=order.destination,
                        trip_from=order.trip_from,
                        trip_to=order.trip_to,
                        route_description=route_desc,
                        duration_days=order.duration_days or 1,
                        departure_date=order.departure_date,
                        return_date=order.return_date,
                        bus_count=order.bus_count_requested or 0,
                        total_value=order.total_value or 0,
                        adjustment_value=order.adjustment_value or 0,
                        executive_discount_value=order.executive_discount_value or 0,
                        final_value=final_val,
                        remaining_amount=final_val,
                        status="pending",
                        created_by="النظام",
                    )
                    session.add(claim)
                    session.flush()
                    from src.core.models.base_models import Notification, User
                    admin_users = session.query(User).filter(User.is_active == True).all()
                    for au in admin_users:
                        session.add(Notification(
                            user_id=au.id,
                            title="مطالبة مالية جديدة بانتظار التحصيل",
                            message=f"تم توليد مطالبة مالية رقم {claim.claim_number} للجهة {order.client.name_ar if order.client else ''} بمبلغ {final_val:,.0f} د.ل - امر تشغيل رقم {order.order_number}",
                            notification_type="finance_claim_pending",
                            reference_id=claim.id,
                            reference_type="financial_claim",
                        ))
        all_approved = True
        for step in steps:
            f = field_map.get(step.name)
            if f and not getattr(order, f, False):
                all_approved = False
                break
        if all_approved:
            order.status = "approved"
            order.is_draft = False
            # انشاء مستحقات السائقين تلقائياً
            if order.trip_type == "external":
                for wb in order.buses:
                    if wb.driver_name and wb.driver_share_value and wb.driver_share_value > 0:
                        existing_ent = session.query(SchoolDriverEntitlement).filter(
                            SchoolDriverEntitlement.work_order_id == order.id,
                            SchoolDriverEntitlement.bus_number == wb.bus_number,
                        ).first()
                        if not existing_ent:
                            route = ""
                            if order.trip_from or order.trip_to:
                                route = f"{order.trip_from or ''} ← {order.trip_to or ''}"
                            elif order.destination:
                                route = order.destination
                            elif order.trip_route:
                                route = order.trip_route
                            ent = SchoolDriverEntitlement(
                                month=order.departure_date.month if order.departure_date else datetime.now().month,
                                year=order.departure_date.year if order.departure_date else datetime.now().year,
                                driver_name=wb.driver_name or "",
                                driver_id=wb.driver_id,
                                school_name=order.client.name_ar if order.client else "",
                                bus_number=wb.bus_number,
                                trip_count=order.duration_days or 1,
                                driver_type="school",
                                work_order_id=order.id,
                                work_order_number=order.order_number,
                                route=route,
                                trip_value=(wb.bus_price or 0) * (order.duration_days or 1),
                                driver_share=wb.driver_share_value,
                                overnight_stay=order.bus_maintenance_value or 0,
                                total_share=wb.driver_share_value + (order.bus_maintenance_value or 0),
                                net_entitlement=wb.driver_share_value + (order.bus_maintenance_value or 0),
                                entitlement_value=(wb.bus_price or 0) * (order.duration_days or 1),
                                entitlement_date=order.departure_date or datetime.now().date(),
                                status="pending",
                            )
                            session.add(ent)
        session.commit()
        flash(f"تم اعتماد {current_step.name} بنجاح", "success")
        return redirect(url_for("marketing.work_order_detail", order_id=order_id))


# ============================================================
# ANNEXES
# ============================================================

@marketing_bp.route("/work-orders/<order_id>/annex/add", methods=["GET", "POST"])
@login_required
def annex_add(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("أمر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        if request.method == "POST":
            annex_count = session.query(WorkOrderAnnex).filter(
                WorkOrderAnnex.work_order_id == order_id
            ).count()
            annex_number = f"{order.order_number}/{annex_count + 1}"
            annex = WorkOrderAnnex(
                work_order_id=order_id,
                annex_number=annex_number,
                title=request.form.get("title", ""),
                extended_days=int(request.form.get("extended_days", 0)),
                new_bus_count=int(request.form.get("new_bus_count", 0)),
                reduction_days=int(request.form.get("reduction_days", 0)),
                reduction_value=float(request.form.get("reduction_value", 0)),
                replacement_bus_number=request.form.get("replacement_bus_number"),
                replacement_driver_name=request.form.get("replacement_driver_name"),
                total_value=float(request.form.get("total_value", 0)),
                notes=request.form.get("notes"),
            )
            session.add(annex)
            session.commit()
            flash(f"تم إضافة الملحق رقم {annex_number} بنجاح", "success")
            return redirect(url_for("marketing.work_order_detail", order_id=order_id))
        return render_template(
            "marketing/annex_form.html",
            page_title=f"إضافة ملحق لأمر التشغيل {order.order_number}",
            order=order,
        )


# ============================================================
# TRIPS
# ============================================================

@marketing_bp.route("/trips")
@login_required
def trips_list():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)
        client_id = request.args.get("client_id", "").strip()

        q = session.query(Trip).filter(
            extract('month', Trip.trip_date) == month,
            extract('year', Trip.trip_date) == year
        )
        if client_id:
            q = q.filter(Trip.client_id == client_id)
        trips = q.order_by(Trip.trip_date.desc()).all()
        total_value = sum(t.value for t in trips)

        trips_data = []
        for t in trips:
            emaar = t.bus_number or ''
            if t.work_order_id:
                wob = session.query(WorkOrderBus).filter(WorkOrderBus.work_order_id == t.work_order_id).first()
                if wob and wob.vehicle_id:
                    v = session.query(Vehicle).filter(Vehicle.id == wob.vehicle_id).first()
                    if v and v.emaar_number:
                        emaar = v.emaar_number
            trips_data.append({"trip": t, "emaar": emaar})

        clients = session.query(MarketingClient).order_by(MarketingClient.name_ar).all()

        return render_template(
            "marketing/trips_list.html",
            page_title="كشف الرحلات",
            trips=trips_data,
            total_value=total_value,
            current_month=month,
            current_year=year,
            clients=clients,
            selected_client=client_id,
        )


@marketing_bp.route("/trips/approve", methods=["POST"])
@login_required
def trips_approve():
    with get_web_session() as session:
        data = request.get_json()
        month = data.get("month", datetime.now().month)
        year = data.get("year", datetime.now().year)
        role = data.get("role")

        from src.core.models.hr_models import AttendanceApproval

        approval = session.query(AttendanceApproval).filter(
            AttendanceApproval.year == year,
            AttendanceApproval.month == month,
            AttendanceApproval.person_type == f"trips_{role}",
        ).first()

        if not approval:
            approval = AttendanceApproval(
                year=year, month=month, person_type=f"trips_{role}"
            )
            session.add(approval)

        now = datetime.utcnow()
        if role == "marketing":
            if approval.executive_approved:
                approval.executive_approved = False
                approval.executive_approved_by = None
                approval.executive_approved_at = None
            else:
                approval.executive_approved = True
                approval.executive_approved_by = str(current_user.id)
                approval.executive_approved_at = now
        elif role == "executive":
            if approval.hr_approved:
                approval.hr_approved = False
                approval.hr_approved_by = None
                approval.hr_approved_at = None
            else:
                approval.hr_approved = True
                approval.hr_approved_by = str(current_user.id)
                approval.hr_approved_at = now

        session.commit()
        return jsonify({"success": True, "marketing": approval.executive_approved, "executive": approval.hr_approved})


@marketing_bp.route("/trips/approval-status")
@login_required
def trips_approval_status():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)

        from src.core.models.hr_models import AttendanceApproval

        approval = session.query(AttendanceApproval).filter(
            AttendanceApproval.year == year,
            AttendanceApproval.month == month,
        ).filter(
            AttendanceApproval.person_type.like("trips_%")
        ).all()

        result = {"marketing": False, "executive": False}
        for a in approval:
            if a.person_type == "trips_marketing" and a.executive_approved:
                result["marketing"] = True
            elif a.person_type == "trips_executive" and a.hr_approved:
                result["executive"] = True

        return jsonify(result)


# ============================================================
# SCHOOL DRIVER ENTITLEMENTS
# ============================================================

@marketing_bp.route("/school-drivers")
@login_required
def school_drivers_list():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)
        search_driver = request.args.get("driver_name", "").strip()
        search_entity = request.args.get("entity_name", "").strip()
        search_type = request.args.get("driver_type", "").strip()

        all_entities = session.query(SchoolDriverEntitlement.school_name).filter(
            SchoolDriverEntitlement.month == month,
            SchoolDriverEntitlement.year == year
        ).distinct().order_by(SchoolDriverEntitlement.school_name).all()
        all_entities = [e[0] for e in all_entities if e[0]]

        all_drivers = session.query(SchoolDriverEntitlement.driver_name).filter(
            SchoolDriverEntitlement.month == month,
            SchoolDriverEntitlement.year == year
        ).distinct().order_by(SchoolDriverEntitlement.driver_name).all()
        all_drivers = [d[0] for d in all_drivers if d[0]]

        q = session.query(SchoolDriverEntitlement).filter(
            SchoolDriverEntitlement.month == month,
            SchoolDriverEntitlement.year == year
        )
        if search_driver:
            q = q.filter(SchoolDriverEntitlement.driver_name == search_driver)
        if search_entity:
            q = q.filter(SchoolDriverEntitlement.school_name == search_entity)
        if search_type:
            q = q.filter(SchoolDriverEntitlement.driver_type == search_type)
        entitlements = q.order_by(SchoolDriverEntitlement.driver_name).all()

        for ent in entitlements:
            if ent.work_order_id:
                wo = session.query(WorkOrder).filter(WorkOrder.id == ent.work_order_id).first()
                if wo:
                    ent.work_order_number = wo.order_number
                    ent.route = f"{wo.trip_from or ''} ← {wo.trip_to or ''}" if wo.trip_from or wo.trip_to else wo.destination or ""
                    wo_buses = session.query(WorkOrderBus).filter(WorkOrderBus.work_order_id == wo.id).all()
                    total_trip_value = 0
                    total_driver_share = 0
                    for wb in wo_buses:
                        bus_trip_val = (wb.bus_price or 0) * (wo.duration_days or 1)
                        total_trip_value += bus_trip_val
                        total_driver_share += wb.driver_share_value or 0
                    ent.trip_value = total_trip_value
                    ent.driver_share = total_driver_share
                    ent.total_share = ent.driver_share + ent.overnight_stay

        total_trips = sum(e.trip_count for e in entitlements)
        total_value = sum(e.total_share for e in entitlements)

        from collections import OrderedDict
        grouped = OrderedDict()
        for ent in entitlements:
            name = ent.driver_name or 'غير محدد'
            if name not in grouped:
                grouped[name] = {
                    'driver_name': name,
                    'trips': [],
                    'total_trip_value': 0,
                    'total_driver_share': 0,
                    'total_overnight': 0,
                    'total_share': 0,
                }
            grouped[name]['trips'].append(ent)
            grouped[name]['total_trip_value'] += ent.trip_value or 0
            grouped[name]['total_driver_share'] += ent.driver_share or 0
            grouped[name]['total_overnight'] += ent.overnight_stay or 0
            grouped[name]['total_share'] += ent.total_share or 0

        return render_template(
            "marketing/school_drivers.html",
            page_title="مستحقات السائقين",
            entitlements=entitlements,
            grouped=grouped,
            total_trips=total_trips,
            total_value=total_value,
            current_month=month,
            current_year=year,
            search_driver=search_driver,
            search_entity=search_entity,
            search_type=search_type,
            all_drivers=all_drivers,
            all_entities=all_entities,
        )


# ============================================================
# SCHOOL DRIVERS PRINT PREVIEW
# ============================================================

@marketing_bp.route("/school-drivers/print")
@login_required
def school_drivers_print():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)
        entitlements = session.query(SchoolDriverEntitlement).filter(
            SchoolDriverEntitlement.month == month,
            SchoolDriverEntitlement.year == year
        ).order_by(SchoolDriverEntitlement.driver_name).all()

        for ent in entitlements:
            if ent.work_order_id:
                wo = session.query(WorkOrder).filter(WorkOrder.id == ent.work_order_id).first()
                if wo:
                    ent.work_order_number = wo.order_number
                    ent.route = f"{wo.trip_from or ''} ← {wo.trip_to or ''}" if wo.trip_from or wo.trip_to else wo.destination or ""
                    wo_buses = session.query(WorkOrderBus).filter(WorkOrderBus.work_order_id == wo.id).all()
                    total_trip_value = 0
                    total_driver_share = 0
                    for wb in wo_buses:
                        bus_trip_val = (wb.bus_price or 0) * (wo.duration_days or 1)
                        total_trip_value += bus_trip_val
                        total_driver_share += wb.driver_share_value or 0
                    ent.trip_value = total_trip_value
                    ent.driver_share = total_driver_share
                    ent.total_share = ent.driver_share + ent.overnight_stay

        total_trips = sum(e.trip_count for e in entitlements)
        total_value = sum(e.total_share for e in entitlements)
        months_ar = ["يناير", "فبراير", "مارس", "ابريل", "مايو", "يونيو",
                     "يوليو", "اغسطس", "سبتمبر", "اكتوبر", "نوفمبر", "ديسمبر"]

        from collections import OrderedDict
        grouped = OrderedDict()
        for ent in entitlements:
            name = ent.driver_name or 'غير محدد'
            if name not in grouped:
                grouped[name] = {
                    'driver_name': name,
                    'trips': [],
                    'total_trip_value': 0,
                    'total_driver_share': 0,
                    'total_overnight': 0,
                    'total_share': 0,
                }
            grouped[name]['trips'].append(ent)
            grouped[name]['total_trip_value'] += ent.trip_value or 0
            grouped[name]['total_driver_share'] += ent.driver_share or 0
            grouped[name]['total_overnight'] += ent.overnight_stay or 0
            grouped[name]['total_share'] += ent.total_share or 0

        from src.core.models.hr_models import AttendanceApproval
        marketing_approval = session.query(AttendanceApproval).filter(
            AttendanceApproval.year == year,
            AttendanceApproval.month == month,
            AttendanceApproval.person_type == "school_drivers_marketing",
        ).first()
        executive_approval = session.query(AttendanceApproval).filter(
            AttendanceApproval.year == year,
            AttendanceApproval.month == month,
            AttendanceApproval.person_type == "school_drivers_executive",
        ).first()

        marketing_approved = marketing_approval.hr_approved if marketing_approval else False
        executive_approved = executive_approval.executive_approved if executive_approval else False
        marketing_by = marketing_approval.hr_approved_by if marketing_approval and marketing_approval.hr_approved else None
        executive_by = executive_approval.executive_approved_by if executive_approval and executive_approval.executive_approved else None

        return render_template(
            "marketing/school_drivers_print.html",
            entitlements=entitlements,
            grouped=grouped,
            total_trips=total_trips,
            total_value=total_value,
            current_month=month,
            current_year=year,
            months_ar=months_ar,
            today=date.today().strftime('%Y-%m-%d'),
            marketing_approved=marketing_approved,
            executive_approved=executive_approved,
            marketing_by=marketing_by,
            executive_by=executive_by,
        )


# ============================================================
# SCHOOL DRIVERS PDF REPORT
# ============================================================

@marketing_bp.route("/school-drivers/pdf")
@login_required
def school_drivers_pdf():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)
        entitlements = session.query(SchoolDriverEntitlement).filter(
            SchoolDriverEntitlement.month == month,
            SchoolDriverEntitlement.year == year
        ).order_by(SchoolDriverEntitlement.driver_name).all()
        total_trips = sum(e.trip_count for e in entitlements)
        total_value = sum(e.net_entitlement for e in entitlements)

        months_ar = ["يناير", "فبراير", "مارس", "ابريل", "مايو", "يونيو",
                     "يوليو", "اغسطس", "سبتمبر", "اكتوبر", "نوفمبر", "ديسمبر"]

        import arabic_reshaper
        from bidi.algorithm import get_display

        def ar(text):
            t = text or ""
            if len(t) <= 2:
                return t
            reshaped = arabic_reshaper.reshape(t)
            return get_display(reshaped)

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        pdfmetrics.registerFont(TTFont("Ar", r"C:\Windows\Fonts\trado.ttf"))
        pdfmetrics.registerFont(TTFont("ArBd", r"C:\Windows\Fonts\tahomabd.ttf"))

        buf = io.BytesIO()
        page_w, page_h = landscape(A4)
        c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))

        navy = colors.HexColor("#0f172a")
        navy_l = colors.HexColor("#1e293b")
        blue = colors.HexColor("#2563eb")
        green = colors.HexColor("#16a34a")
        red = colors.HexColor("#dc2626")
        amber = colors.HexColor("#d97706")
        slate = colors.HexColor("#64748b")
        bg_alt = colors.HexColor("#f1f5f9")
        line_c = colors.HexColor("#e2e8f0")
        white = colors.white

        margin = 12 * mm
        row_h = 7 * mm
        hdr_h = 8 * mm

        y = page_h - 10 * mm

        # Top bar
        c.setFillColor(navy)
        c.rect(0, y - 2*mm, page_w, 18*mm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 18)
        c.drawCentredString(page_w/2, y + 5*mm, ar("شركة اعمار ليبيا لنقل الركاب"))
        c.setFont("Ar", 9)
        c.drawCentredString(page_w/2, y - 1*mm, ar("شركة اعمار ليبيا القابضة"))
        c.setFillColor(blue)
        c.rect(0, y - 2*mm, page_w, 1*mm, fill=1, stroke=0)
        y -= 22 * mm

        # Title
        title = f"كشف المستحقات الشهرية للسائقين — {months_ar[month-1]} {year}"
        c.setFillColor(navy)
        c.roundRect(margin, y - 4*mm, page_w - margin*2, 10*mm, 3, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 12)
        c.drawCentredString(page_w/2, y - 0.5*mm, ar(title))
        y -= 14 * mm

        # Table headers
        col_defs = [
            ("التسلسل", 12*mm),
            ("اسم الجهة", 40*mm),
            ("الباص", 18*mm),
            ("اسم السائق", 35*mm),
            ("عدد الرحلات", 18*mm),
            ("نوع السائق", 18*mm),
            ("الاستحقاق", 22*mm),
            ("نسبة الشركة 10%", 22*mm),
            ("صافي المستحق", 22*mm),
            ("تاريخ الاستحقاق", 22*mm),
            ("الحالة", 18*mm),
        ]

        x = margin
        c.setFillColor(navy)
        c.roundRect(x, y - hdr_h, page_w - margin*2, hdr_h, 2, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 7)
        for label, w in col_defs:
            c.drawCentredString(x + w/2, y - hdr_h + 2.5*mm, ar(label))
            x += w
        y -= hdr_h

        # Data rows
        for idx, ent in enumerate(entitlements):
            if y < 50 * mm:
                c.showPage()
                y = page_h - 15 * mm

            bg = bg_alt if idx % 2 == 0 else white
            c.setFillColor(bg)
            c.rect(margin, y - row_h, page_w - margin*2, row_h, fill=1, stroke=0)

            c.setStrokeColor(line_c)
            c.setLineWidth(0.3)
            c.line(margin, y - row_h, page_w - margin, y - row_h)

            x = margin
            c.setFillColor(colors.HexColor("#1e293b"))
            c.setFont("Ar", 6.5)

            type_labels = {"school": "مدارس", "trip": "رحلات", "reserve": "احتياطي"}
            status_labels = {"paid": "مدفوع", "pending": "بانتظار الدفع"}

            row_data = [
                str(idx + 1),
                ent.school_name or "-",
                ent.bus_number or "-",
                ent.driver_name,
                str(ent.trip_count),
                type_labels.get(ent.driver_type, ent.driver_type),
                f"{ent.entitlement_value:,.0f} د.ل",
                f"{ent.company_share:,.0f} د.ل",
                f"{ent.net_entitlement:,.0f} د.ل",
                ent.entitlement_date.strftime('%Y-%m-%d') if ent.entitlement_date else "-",
                status_labels.get(ent.status, ent.status),
            ]

            for i, (_, w) in enumerate(col_defs):
                val = ar(row_data[i]) if i not in [0, 4] else row_data[i]
                c.drawCentredString(x + w/2, y - row_h + 2*mm, val)
                x += w

            y -= row_h

        # Footer line
        y -= 3 * mm
        c.setStrokeColor(blue)
        c.setLineWidth(1.5)
        c.line(margin, y, page_w - margin, y)
        y -= 8 * mm

        # Summary
        c.setFillColor(navy)
        c.setFont("ArBd", 9)
        c.drawString(margin, y, ar(f"اجمالي المستحقات: {total_value:,.0f} د.ل"))
        c.drawString(margin + 100*mm, y, ar(f"اجمالي الرحلات: {total_trips} رحلة"))
        c.drawString(page_w/2, y, ar(f"عدد السائقين: {len(entitlements)}"))
        y -= 15 * mm

        # Approval stamps
        stamp_w = 70 * mm
        stamp_h = 35 * mm
        stamp_gap = 15 * mm

        right_x = page_w - margin - stamp_w
        left_x = right_x - stamp_w - stamp_gap

        # Marketing stamp (right)
        c.setStrokeColor(blue)
        c.setLineWidth(1.2)
        c.roundRect(right_x, y - stamp_h, stamp_w, stamp_h, 4, stroke=1, fill=0)
        c.setFillColor(blue)
        c.setFont("ArBd", 8)
        c.drawCentredString(right_x + stamp_w/2, y - 6*mm, ar("ادارة التسويق التجاري"))
        c.setFont("Ar", 7)
        c.setFillColor(slate)
        c.drawCentredString(right_x + stamp_w/2, y - 14*mm, ar("الاسم: ........................"))
        c.drawCentredString(right_x + stamp_w/2, y - 21*mm, ar("التوقيع: ........................"))
        c.drawCentredString(right_x + stamp_w/2, y - 28*mm, ar("التاريخ: ........................"))

        # Executive stamp (left)
        c.setStrokeColor(green)
        c.setLineWidth(1.2)
        c.roundRect(left_x, y - stamp_h, stamp_w, stamp_h, 4, stroke=1, fill=0)
        c.setFillColor(green)
        c.setFont("ArBd", 8)
        c.drawCentredString(left_x + stamp_w/2, y - 6*mm, ar("المدير التنفيذي"))
        c.setFont("Ar", 7)
        c.setFillColor(slate)
        c.drawCentredString(left_x + stamp_w/2, y - 14*mm, ar("الاسم: ........................"))
        c.drawCentredString(left_x + stamp_w/2, y - 21*mm, ar("التوقيع: ........................"))
        c.drawCentredString(left_x + stamp_w/2, y - 28*mm, ar("التاريخ: ........................"))

        c.save()
        buf.seek(0)

        from flask import send_file
        filename = f"school_drivers_{year}_{month}.pdf"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")


# ============================================================
# DRIVER TRIPS
# ============================================================

@marketing_bp.route("/driver-trips")
@login_required
def driver_trips():
    with get_web_session() as session:
        month = request.args.get("month", datetime.now().month, type=int)
        year = request.args.get("year", datetime.now().year, type=int)
        orders = session.query(WorkOrder).options(
            joinedload(WorkOrder.client), joinedload(WorkOrder.buses)
        ).filter(
            WorkOrder.status.in_(["active", "completed"]),
            extract('month', WorkOrder.departure_date) == month,
            extract('year', WorkOrder.departure_date) == year
        ).order_by(WorkOrder.departure_date.desc()).all()
        trip_data = []
        serial = 0
        for order in orders:
            buses = order.buses if order.buses else []
            if buses:
                for bus in buses:
                    serial += 1
                    discount = ""
                    if order.adjustment_type == "reduce":
                        if order.adjustment_percent:
                            discount = f"{order.adjustment_percent}%"
                        elif order.adjustment_value:
                            discount = f"{order.adjustment_value:,.0f} د.ل"
                    elif order.adjustment_type == "increase":
                        if order.adjustment_percent:
                            discount = f"+{order.adjustment_percent}%"
                        elif order.adjustment_value:
                            discount = f"+{order.adjustment_value:,.0f} د.ل"
                    trip_data.append({
                        "serial": serial,
                        "driver_name": bus.driver_name or "-",
                        "rat": bus.bus_number or "-",
                        "order_number": order.order_number,
                        "created_at": order.created_at.strftime('%Y-%m-%d') if order.created_at else "-",
                        "client": order.client.name_ar if order.client else "-",
                        "trip_from": order.trip_from or "-",
                        "trip_to": order.trip_to or "-",
                        "total_value": order.total_value,
                        "discount": discount,
                        "bus_maintenance": order.bus_maintenance_value,
                        "order_id": order.id,
                    })
            else:
                serial += 1
                discount = ""
                if order.adjustment_type == "reduce":
                    if order.adjustment_percent:
                        discount = f"{order.adjustment_percent}%"
                    elif order.adjustment_value:
                        discount = f"{order.adjustment_value:,.0f} د.ل"
                elif order.adjustment_type == "increase":
                    if order.adjustment_percent:
                        discount = f"+{order.adjustment_percent}%"
                    elif order.adjustment_value:
                        discount = f"+{order.adjustment_value:,.0f} د.ل"
                trip_data.append({
                    "serial": serial,
                    "driver_name": "-",
                    "rat": "-",
                    "order_number": order.order_number,
                    "created_at": order.created_at.strftime('%Y-%m-%d') if order.created_at else "-",
                    "client": order.client.name_ar if order.client else "-",
                    "trip_from": order.trip_from or "-",
                    "trip_to": order.trip_to or "-",
                    "total_value": order.total_value,
                    "discount": discount,
                    "bus_maintenance": order.bus_maintenance_value,
                    "order_id": order.id,
                })
        total_value = sum(t["total_value"] for t in trip_data)
        total_maintenance = sum(t["bus_maintenance"] for t in trip_data)
        return render_template(
            "marketing/driver_trips.html",
            page_title="كشف السائقين",
            trip_data=trip_data,
            total_value=total_value,
            total_maintenance=total_maintenance,
            current_month=month,
            current_year=year,
            today=date.today().strftime('%Y-%m-%d'),
        )


# ============================================================
# API: CHECK DRIVER
# ============================================================

@marketing_bp.route("/api/check-driver", methods=["POST"])
@login_required
def check_driver():
    """API endpoint للتحقق من حالة السائق"""
    data = request.get_json()
    driver_name = data.get("driver_name")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    exclude_order_id = data.get("exclude_order_id")
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    with get_web_session() as session:
        available, message = check_driver_availability(session, driver_name, start_date, end_date, exclude_order_id)
        return jsonify({
            "available": available,
            "message": message
        })


# ============================================================
# DEVELOPMENT ROADMAP
# ============================================================

@marketing_bp.route("/roadmap")
@login_required
def roadmap():
    return render_template("marketing/roadmap.html", page_title="خطة التطوير المستقبلية")


# ============================================================
# API: CHECK BUS
# ============================================================

@marketing_bp.route("/api/check-bus", methods=["POST"])
@login_required
def check_bus():
    """API endpoint للتحقق من حالة الحافلة"""
    data = request.get_json()
    bus_number = data.get("bus_number")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    exclude_order_id = data.get("exclude_order_id")
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    with get_web_session() as session:
        available, message = check_bus_availability(session, bus_number, start_date, end_date, exclude_order_id)
        return jsonify({
            "available": available,
            "message": message
        })


# ============================================================
# TRIP TRACKING
# ============================================================

@marketing_bp.route("/trip-tracking")
@login_required
def trip_tracking():
    with get_web_session() as session:
        today = date.today()
        drivers = session.query(Driver).filter(Driver.is_deleted == False).order_by(Driver.full_name_ar).all()
        vehicle_map = {v.driver_id: v for v in session.query(Vehicle).filter(Vehicle.driver_id.isnot(None)).all()}
        drivers_data = []
        for driver in drivers:
            vehicle = vehicle_map.get(driver.id)
            completed_orders = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status == "active",
                WorkOrder.return_date != None,
                WorkOrder.return_date < today
            ).order_by(WorkOrder.return_date.desc()).all()
            active_orders = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status == "active",
                WorkOrder.departure_date != None,
                WorkOrder.return_date != None,
                WorkOrder.departure_date <= today,
                WorkOrder.return_date >= today
            ).all()
            upcoming_orders = session.query(WorkOrder).join(WorkOrderBus).filter(
                WorkOrderBus.driver_id == driver.id,
                WorkOrder.status.in_(["active", "draft"]),
                WorkOrder.departure_date != None,
                WorkOrder.departure_date > today
            ).order_by(WorkOrder.departure_date).all()
            if vehicle or completed_orders or active_orders or upcoming_orders:
                drivers_data.append({
                    "driver": driver,
                    "vehicle": vehicle,
                    "completed": completed_orders,
                    "active": active_orders,
                    "upcoming": upcoming_orders,
                })
        return render_template("marketing/trip_tracking.html", drivers_data=drivers_data, today=today)


# ============================================================
# WORK ORDER PRINT
# ============================================================

@marketing_bp.route("/work-orders/<order_id>/print")
@login_required
def work_order_print(order_id):
    with get_web_session() as session:
        order = session.query(WorkOrder).get(order_id)
        if not order:
            flash("أمر التشغيل غير موجود", "danger")
            return redirect(url_for("marketing.work_orders_list"))
        all_orders = session.query(WorkOrder).filter(WorkOrder.is_deleted == False).all()
        return render_template(
            "marketing/work_order_print.html",
            order=order,
            all_orders=all_orders,
            today=date.today().strftime('%Y-%m-%d'),
        )


# ============================================================
# API: QUICK ADD DRIVER
# ============================================================

@marketing_bp.route("/api/quick-add-driver", methods=["POST"])
@login_required
def marketing_quick_add_driver():
    from flask import request as req
    data = req.get_json()
    name_ar = (data.get("name_ar") or "").strip()
    if not name_ar:
        return jsonify({"success": False, "message": "اسم السائق مطلوب"}), 400
    with get_web_session() as session:
        last = session.query(Driver.driver_number).order_by(Driver.created_at.desc()).first()
        if last and last[0]:
            import re
            m = re.match(r'^[A-Za-z]*(\d+)$', last[0])
            if m:
                num = int(m.group(1)) + 1
                driver_number = f"D{num:03d}"
            else:
                driver_number = "D001"
        else:
            driver_number = "D001"
        driver = Driver(
            driver_number=driver_number,
            full_name_ar=name_ar,
            phone=data.get("phone", "").strip() or None,
            license_type=data.get("license_type", "").strip() or None,
            status="active",
            created_by=current_user.id if current_user.is_authenticated else None,
        )
        session.add(driver)
        session.commit()
        return jsonify({
            "success": True,
            "id": driver.id,
            "name": driver.full_name_ar,
            "phone": driver.phone or "",
            "license": driver.license_type or "",
        })


# ============================================================
# VEHICLE DISTANCES - المسافات المقطوعة للسيارات
# ============================================================

@marketing_bp.route("/vehicle-distances")
@login_required
def vehicle_distances():
    with get_web_session() as session:
        from src.core.models.vehicle_models import Vehicle
        from sqlalchemy import func, extract

        search = request.args.get("search", "").strip()
        filter_month = request.args.get("month", "")
        filter_year = request.args.get("year", "")

        wo_filter = WorkOrder.is_deleted == False
        if filter_month:
            wo_filter = wo_filter & (extract('month', WorkOrder.departure_date) == int(filter_month))
        if filter_year:
            wo_filter = wo_filter & (extract('year', WorkOrder.departure_date) == int(filter_year))

        vehicles_q = session.query(
            Vehicle.id,
            Vehicle.plate_number,
            Vehicle.emaar_number,
            Vehicle.brand,
            Vehicle.model,
            Vehicle.current_km,
            Vehicle.status,
            func.coalesce(func.sum(WorkOrder.estimated_distance), 0).label("total_estimated_km"),
            func.count(WorkOrder.id).label("order_count"),
        ).outerjoin(
            WorkOrderBus, WorkOrderBus.vehicle_id == Vehicle.id
        ).outerjoin(
            WorkOrder, (WorkOrder.id == WorkOrderBus.work_order_id) & wo_filter
        ).filter(
            Vehicle.status != "deleted"
        )

        if search:
            vehicles_q = vehicles_q.filter(
                (Vehicle.plate_number.contains(search)) |
                (Vehicle.emaar_number.contains(search)) |
                (Vehicle.brand.contains(search)) |
                (Vehicle.model.contains(search))
            )

        vehicles = vehicles_q.group_by(Vehicle.id).order_by(Vehicle.plate_number).all()

        import calendar
        months = [("1", "يناير"), ("2", "فبراير"), ("3", "مارس"), ("4", "أبريل"),
                  ("5", "مايو"), ("6", "يونيو"), ("7", "يوليو"), ("8", "أغسطس"),
                  ("9", "سبتمبر"), ("10", "أكتوبر"), ("11", "نوفمبر"), ("12", "ديسمبر")]
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 5, current_year + 1)]

        return render_template(
            "marketing/vehicle_distances.html",
            page_title="المسافات المقطوعة للسيارات",
            vehicles=vehicles,
            search=search,
            filter_month=filter_month,
            filter_year=filter_year,
            months=months,
            years=years,
            today=date.today().strftime('%Y-%m-%d'),
        )


# ============================================================
# BUS RENTAL PRICES - اسعار ايجار الحافلات
# ============================================================

@marketing_bp.route("/bus-rental-prices")
@login_required
def bus_rental_prices():
    with get_web_session() as session:
        from src.core.models.marketing_models import BusRentalPrice
        from src.core.models.base_models import VehicleType
        prices = session.query(BusRentalPrice).all()
        vehicle_types = session.query(VehicleType).filter(VehicleType.is_active == True).all()
        seats_map = {}
        for vt in vehicle_types:
            if vt.seats_count:
                seats_map[vt.id] = vt.seats_count
        return render_template(
            "marketing/bus_rental_prices.html",
            page_title="اسعار ايجار الحافلات",
            prices=prices,
            vehicle_types=vehicle_types,
            seats_map=seats_map,
        )


@marketing_bp.route("/bus-rental-prices/add", methods=["POST"])
@login_required
def bus_rental_price_add():
    with get_web_session() as session:
        from src.core.models.marketing_models import BusRentalPrice
        vehicle_type_id = request.form.get("vehicle_type_id")
        seats_count = request.form.get("seats_count") or None
        daily_price = float(request.form.get("daily_price") or 0)
        notes = request.form.get("notes") or None
        if not vehicle_type_id or daily_price <= 0:
            flash("يجب اختيار نوع السيارة وادخال سعر صحيح", "danger")
            return redirect(url_for("marketing.bus_rental_prices"))
        existing = session.query(BusRentalPrice).filter(
            BusRentalPrice.vehicle_type_id == vehicle_type_id,
            BusRentalPrice.seats_count == (int(seats_count) if seats_count else None)
        ).first()
        if existing:
            existing.daily_price = daily_price
            existing.notes = notes
            existing.seats_count = int(seats_count) if seats_count else None
            flash("تم تحديث السعر بنجاح", "success")
        else:
            price = BusRentalPrice(
                vehicle_type_id=vehicle_type_id,
                seats_count=int(seats_count) if seats_count else None,
                daily_price=daily_price,
                notes=notes,
                created_by=current_user.id if current_user.is_authenticated else None,
            )
            session.add(price)
            flash("تم اضافة السعر بنجاح", "success")
        session.commit()
        return redirect(url_for("marketing.bus_rental_prices"))


@marketing_bp.route("/bus-rental-prices/<price_id>/delete", methods=["POST"])
@login_required
def bus_rental_price_delete(price_id):
    with get_web_session() as session:
        from src.core.models.marketing_models import BusRentalPrice
        price = session.query(BusRentalPrice).get(price_id)
        if price:
            session.delete(price)
            session.commit()
            flash("تم حذف السعر بنجاح", "success")
        return redirect(url_for("marketing.bus_rental_prices"))


@marketing_bp.route("/api/bus-rental-price/<vehicle_type_id>")
@login_required
def api_bus_rental_price(vehicle_type_id):
    with get_web_session() as session:
        from src.core.models.marketing_models import BusRentalPrice
        price = session.query(BusRentalPrice).filter(
            BusRentalPrice.vehicle_type_id == vehicle_type_id
        ).first()
        if price:
            return jsonify({"success": True, "daily_price": price.daily_price, "seats_count": price.seats_count})
        return jsonify({"success": False, "daily_price": 0, "seats_count": 0})


@marketing_bp.route("/api/vehicle-type-seats/<vehicle_type_id>")
@login_required
def api_vehicle_type_seats(vehicle_type_id):
    with get_web_session() as session:
        from src.core.models.base_models import VehicleType
        vt = session.query(VehicleType).get(vehicle_type_id)
        if vt and vt.seats_count:
            return jsonify({"success": True, "seats_count": vt.seats_count})
        return jsonify({"success": True, "seats_count": 0})


@marketing_bp.route("/api/client-phone/<client_id>")
@login_required
def api_client_phone(client_id):
    with get_web_session() as session:
        client = session.query(MarketingClient).filter_by(id=client_id).first()
        if client:
            return jsonify({"success": True, "phone": client.phone or ""})
        return jsonify({"success": True, "phone": ""})
