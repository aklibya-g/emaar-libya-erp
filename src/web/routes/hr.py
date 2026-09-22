from datetime import date, datetime, time

from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from src.core.database.connection import get_web_session
from src.core.models.base_models import Employee, Department, Notification, User
from src.core.models.hr_models import (
    EmployeeProfile, DocumentCategory, DocumentType, EmployeeDocumentRecord,
    AttendanceRecord, AttendanceStatus, LeaveType, LeaveBalance, LeaveRequest,
    DisciplinaryType, DisciplinaryAction, Contract, Onboarding,
    WorkShift, ShiftAssignment, OvertimeRequest, HRRule, Alert,
    MedicalRecord, Qualification, Experience, DriverLicense, Holiday,
    AttendanceApproval,
)

hr_bp = Blueprint("hr", __name__, url_prefix="/hr")


@hr_bp.route("/")
@login_required
def hr_dashboard():
    session = get_web_session()
    from datetime import date as dt_date, timedelta, datetime
    today = dt_date.today()
    now = datetime.utcnow()
    
    total_employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").count()
    departments = session.query(Department).filter(Department.is_deleted == False).all()
    
    # Today's attendance
    today_attendance = session.query(AttendanceRecord).filter(AttendanceRecord.record_date == today).all()
    present_today = sum(1 for a in today_attendance if a.status == "present")
    late_today = sum(1 for a in today_attendance if a.status == "late")
    absent_today = sum(1 for a in today_attendance if a.status in ["absent", "absent_unexcused"])
    
    # Leave today
    on_leave_today = session.query(LeaveRequest).filter(
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
        LeaveRequest.status == "approved"
    ).count()
    
    # Pending leaves
    pending_leaves = session.query(LeaveRequest).filter(LeaveRequest.status == "pending").count()

    # Pending executive approval
    pending_executive = session.query(LeaveRequest).filter(LeaveRequest.status == "pending_executive").count()

    # Unread notifications
    from src.core.models.base_models import Notification
    unread_notifications = session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()
    
    # Expiring documents (within 30 days)
    expiring_docs = session.query(EmployeeDocumentRecord).filter(
        EmployeeDocumentRecord.expiry_date <= today + timedelta(days=30),
        EmployeeDocumentRecord.expiry_date >= today
    ).count()
    
    # Expiring contracts (within 30 days)
    expiring_contracts = 0
    from src.core.models.hr_models import Contract
    contracts = session.query(Contract).filter(Contract.status == "active").all()
    for c in contracts:
        if c.end_date and c.end_date <= today + timedelta(days=30) and c.end_date >= today:
            expiring_contracts += 1
    
    # Alerts
    alerts = session.query(Alert).filter(Alert.is_dismissed == False).order_by(Alert.created_at.desc()).limit(10).all()
    
    # Driver stats
    from src.core.models.base_models import Driver
    total_drivers = session.query(Driver).filter(Driver.is_deleted == False).count()
    active_drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").count()
    inactive_drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "inactive").count()
    
    return render_template("hr/hr_dashboard.html",
        total_employees=total_employees,
        departments=departments,
        present_today=present_today,
        late_today=late_today,
        absent_today=absent_today,
        on_leave_today=on_leave_today,
        pending_leaves=pending_leaves,
        pending_executive=pending_executive,
        unread_notifications=unread_notifications,
        expiring_docs=expiring_docs,
        expiring_contracts=expiring_contracts,
        alerts=alerts,
        today=today,
        total_drivers=total_drivers,
        active_drivers=active_drivers,
        inactive_drivers=inactive_drivers,
    )


# ============================================================
# EMPLOYEE DIGITAL FILE
# ============================================================

@hr_bp.route("/employees")
@login_required
def hr_employee_list():
    session = get_web_session()
    search = request.args.get("search", "").strip()
    department_id = request.args.get("department_id", "").strip()

    q = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active")
    if search:
        q = q.filter(
            (Employee.full_name_ar.ilike(f"%{search}%"))
            | (Employee.employee_number.ilike(f"%{search}%"))
            | (Employee.phone.ilike(f"%{search}%"))
            | (Employee.national_id.ilike(f"%{search}%"))
        )
    if department_id:
        q = q.filter(Employee.department_id == department_id)

    employees = q.order_by(Employee.full_name_ar).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()

    return render_template(
        "hr/employee_list.html",
        employees=employees,
        departments=departments,
        search=search,
        department_id=department_id,
    )


@hr_bp.route("/employee/<id>")
@login_required
def employee_file(id):
    session = get_web_session()
    employee = session.query(Employee).filter(
        Employee.id == id, Employee.is_deleted == False
    ).first()
    if not employee:
        flash("الموظف غير موجود", "danger")
        return redirect(url_for("hr.hr_employee_list"))

    profile = session.query(EmployeeProfile).filter(
        EmployeeProfile.employee_id == id
    ).first()

    documents = session.query(EmployeeDocumentRecord).filter(
        EmployeeDocumentRecord.employee_id == id
    ).order_by(EmployeeDocumentRecord.created_at.desc()).all()

    attendance = session.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == id
    ).order_by(AttendanceRecord.record_date.desc()).limit(30).all()

    leave_requests = session.query(LeaveRequest).filter(
        LeaveRequest.employee_id == id
    ).order_by(LeaveRequest.created_at.desc()).limit(20).all()

    contracts = session.query(Contract).filter(
        Contract.employee_id == id
    ).order_by(Contract.created_at.desc()).all()

    disciplinary = session.query(DisciplinaryAction).filter(
        DisciplinaryAction.employee_id == id
    ).order_by(DisciplinaryAction.created_at.desc()).all()

    leave_balances = session.query(LeaveBalance).filter(
        LeaveBalance.employee_id == id,
        LeaveBalance.year == date.today().year,
    ).all()

    active_tab = request.args.get("tab", "personal")

    return render_template(
        "hr/employee_file.html",
        employee=employee,
        profile=profile,
        documents=documents,
        attendance=attendance,
        leave_requests=leave_requests,
        contracts=contracts,
        disciplinary=disciplinary,
        leave_balances=leave_balances,
        active_tab=active_tab,
    )


@hr_bp.route("/employee/<id>/profile", methods=["GET", "POST"])
@login_required
def employee_profile(id):
    session = get_web_session()
    employee = session.query(Employee).filter(
        Employee.id == id, Employee.is_deleted == False
    ).first()
    if not employee:
        flash("الموظف غير موجود", "danger")
        return redirect(url_for("hr.hr_employee_list"))

    profile = session.query(EmployeeProfile).filter(
        EmployeeProfile.employee_id == id
    ).first()

    if request.method == "POST":
        if not profile:
            profile = EmployeeProfile(employee_id=id)
            session.add(profile)

        profile.first_name_ar = request.form.get("first_name_ar", "").strip() or None
        profile.father_name_ar = request.form.get("father_name_ar", "").strip() or None
        profile.grandfather_name_ar = request.form.get("grandfather_name_ar", "").strip() or None
        profile.last_name_ar = request.form.get("last_name_ar", "").strip() or None
        profile.first_name_en = request.form.get("first_name_en", "").strip() or None
        profile.father_name_en = request.form.get("father_name_en", "").strip() or None
        profile.grandfather_name_en = request.form.get("grandfather_name_en", "").strip() or None
        profile.last_name_en = request.form.get("last_name_en", "").strip() or None
        profile.passport_number = request.form.get("passport_number", "").strip() or None
        profile.passport_issue_date = _parse_date(request.form.get("passport_issue_date"))
        profile.passport_expiry_date = _parse_date(request.form.get("passport_expiry_date"))
        profile.passport_issue_place = request.form.get("passport_issue_place", "").strip() or None
        profile.place_of_birth = request.form.get("place_of_birth", "").strip() or None
        family_members = request.form.get("family_members_count", "").strip()
        profile.family_members_count = int(family_members) if family_members else None
        profile.secondary_phone = request.form.get("secondary_phone", "").strip() or None
        profile.city = request.form.get("city", "").strip() or None
        profile.region = request.form.get("region", "").strip() or None

        profile.job_title = request.form.get("job_title", "").strip() or None
        profile.job_grade = request.form.get("job_grade", "").strip() or None
        profile.job_level = request.form.get("job_level", "").strip() or None
        profile.start_date = _parse_date(request.form.get("start_date"))
        profile.branch_id = request.form.get("branch_id", "").strip() or None
        profile.cost_center = request.form.get("cost_center", "").strip() or None
        profile.work_hours = request.form.get("work_hours", "").strip() or None
        profile.shift_system = request.form.get("shift_system", "").strip() or None
        profile.rest_days = request.form.get("rest_days", "").strip() or None

        profile.basic_salary = _parse_float(request.form.get("basic_salary"))
        profile.housing_allowance = _parse_float(request.form.get("housing_allowance"))
        profile.transport_allowance = _parse_float(request.form.get("transport_allowance"))
        profile.other_allowances = _parse_float(request.form.get("other_allowances"))
        profile.bank_name = request.form.get("bank_name", "").strip() or None
        profile.bank_account = request.form.get("bank_account", "").strip() or None

        session.commit()
        flash("تم حفظ بيانات الملف الشخصي بنجاح", "success")
        return redirect(url_for("hr.employee_file", id=id, tab="personal"))

    return render_template(
        "hr/employee_profile.html",
        employee=employee,
        profile=profile,
    )


# ============================================================
# DOCUMENTS
# ============================================================

@hr_bp.route("/employee/<id>/documents")
@login_required
def employee_documents(id):
    session = get_web_session()
    employee = session.query(Employee).filter(
        Employee.id == id, Employee.is_deleted == False
    ).first()
    if not employee:
        flash("الموظف غير موجود", "danger")
        return redirect(url_for("hr.hr_employee_list"))

    documents = session.query(EmployeeDocumentRecord).filter(
        EmployeeDocumentRecord.employee_id == id
    ).order_by(EmployeeDocumentRecord.created_at.desc()).all()

    categories = session.query(DocumentCategory).filter(
        DocumentCategory.is_active == True
    ).order_by(DocumentCategory.sort_order).all()

    document_types = session.query(DocumentType).filter(
        DocumentType.is_active == True
    ).all()

    return render_template(
        "hr/documents.html",
        employee=employee,
        documents=documents,
        categories=categories,
        document_types=document_types,
    )


@hr_bp.route("/employee/<id>/documents/add", methods=["POST"])
@login_required
def employee_documents_add(id):
    session = get_web_session()
    employee = session.query(Employee).filter(
        Employee.id == id, Employee.is_deleted == False
    ).first()
    if not employee:
        flash("الموظف غير موجود", "danger")
        return redirect(url_for("hr.hr_employee_list"))

    document_type_id = request.form.get("document_type_id", "").strip()
    title = request.form.get("title", "").strip()
    if not document_type_id or not title:
        flash("نوع المستند والعنوان مطلوبان", "danger")
        return redirect(url_for("hr.employee_documents", id=id))

    doc = EmployeeDocumentRecord(
        employee_id=id,
        document_type_id=document_type_id,
        title=title,
        document_number=request.form.get("document_number", "").strip() or None,
        issue_date=_parse_date(request.form.get("issue_date")),
        expiry_date=_parse_date(request.form.get("expiry_date")),
        issuing_authority=request.form.get("issuing_authority", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
        uploaded_by=current_user.id,
    )
    session.add(doc)
    session.commit()
    flash("تم إضافة المستند بنجاح", "success")
    return redirect(url_for("hr.employee_documents", id=id))


@hr_bp.route("/documents/categories")
@login_required
def document_categories():
    session = get_web_session()
    categories = session.query(DocumentCategory).order_by(
        DocumentCategory.sort_order
    ).all()
    return render_template("hr/document_categories.html", categories=categories)


@hr_bp.route("/documents/categories/add", methods=["POST"])
@login_required
def document_categories_add():
    session = get_web_session()
    name_ar = request.form.get("name_ar", "").strip()
    code = request.form.get("code", "").strip()
    if not name_ar or not code:
        flash("الاسم بالعربي والكود مطلوبان", "danger")
        return redirect(url_for("hr.document_categories"))

    existing = session.query(DocumentCategory).filter(DocumentCategory.code == code).first()
    if existing:
        flash("كود التصنيف موجود مسبقاً", "danger")
        return redirect(url_for("hr.document_categories"))

    category = DocumentCategory(
        name_ar=name_ar,
        name_en=request.form.get("name_en", "").strip() or None,
        code=code,
        sort_order=int(request.form.get("sort_order", 0)),
        is_active=True,
    )
    session.add(category)
    session.commit()
    flash("تم إضافة التصنيف بنجاح", "success")
    return redirect(url_for("hr.document_categories"))


# ============================================================
# ATTENDANCE
# ============================================================

@hr_bp.route("/attendance")
@login_required
def attendance_daily():
    session = get_web_session()
    target_date = request.args.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(target_date)
    except ValueError:
        target_date = date.today()

    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()

    records = {}
    existing = session.query(AttendanceRecord).filter(
        AttendanceRecord.record_date == target_date
    ).all()
    for rec in existing:
        records[rec.employee_id] = rec

    statuses = AttendanceStatus.CHOICES
    return render_template(
        "hr/attendance_daily.html",
        employees=employees,
        records=records,
        target_date=target_date,
        statuses=statuses,
    )


@hr_bp.route("/attendance/monthly")
@login_required
def attendance_monthly():
    session = get_web_session()

    settings = {}
    rows = session.execute(text("SELECT setting_key, setting_value FROM attendance_settings")).fetchall()
    for row in rows:
        settings[row[0]] = row[1]

    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    department_id = request.args.get("department_id", "").strip()
    person_type = request.args.get("type", "employees")
    contract_filter = request.args.get("contract", "all")

    start_day = int(settings.get("start_day", "26"))
    end_day = int(settings.get("end_day", "25"))
    total_days = 30

    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

    if person_type == "drivers":
        from src.core.models.base_models import Driver
        q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active"
        )
        if contract_filter and contract_filter != "all":
            contract_types_list = [c.strip() for c in contract_filter.split(",") if c.strip()]
            if contract_types_list:
                ar_to_en = {"موسمي": "seasonal", "احتياطي": "reserve", "احتياط": "reserve", "ركوبة عامة": "public_transport", "ايجار لغرض التمليك": "rent_to_own"}
                mapped = [ar_to_en.get(c, c) for c in contract_types_list]
                q = q.filter(Driver.contract_type.in_(mapped))
        persons = q.order_by(Driver.full_name_ar).all()
    else:
        employees_q = session.query(Employee).filter(
            Employee.is_deleted == False, Employee.status == "active"
        )
        if department_id:
            employees_q = employees_q.filter(Employee.department_id == department_id)
        persons = employees_q.order_by(Employee.full_name_ar).all()

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    q = session.query(AttendanceRecord).filter(
        AttendanceRecord.record_date >= date(year, month, start_day),
        AttendanceRecord.record_date <= date(next_year, next_month, end_day),
    )
    records = q.all()

    emp_records = {}
    for r in records:
        if r.employee_id not in emp_records:
            emp_records[r.employee_id] = {}
        emp_records[r.employee_id][r.record_date] = r.status

    from datetime import timedelta
    period_dates = []
    current = date(year, month, start_day)
    end_date = date(next_year, next_month, end_day)
    while current <= end_date:
        period_dates.append(current)
        current += timedelta(days=1)

    monthly_data = {}
    for p in persons:
        days = {}
        present_count = 0
        absent_count = 0
        late_count = 0
        leave_count = 0
        order_count = 0
        for i, d in enumerate(period_dates, 1):
            try:
                rec = emp_records.get(p.id, {}).get(d)
                if rec:
                    days[str(i)] = rec
                else:
                    days[str(i)] = "present"
                s = days[str(i)]
                if s == "present":
                    present_count += 1
                elif s in ["absent", "absent_unexcused"]:
                    absent_count += 1
                elif s == "late":
                    late_count += 1
                elif s == "order":
                    order_count += 1
                elif s in ["leave", "annual_leave", "sick_leave", "emergency_leave",
                           "special_leave", "maternity_leave", "unpaid_leave",
                           "hajj_leave", "marriage_leave", "bereavement_leave"]:
                    leave_count += 1
            except Exception:
                days[str(i)] = "present"
                present_count += 1
        if person_type == "drivers":
            monthly_data[p.id] = {
                "name": p.full_name_ar,
                "number": p.driver_number,
                "days": days,
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "order_count": order_count,
                "leave_count": leave_count,
            }
        else:
            monthly_data[p.id] = {
                "name": p.full_name_ar,
                "number": p.employee_number,
                "days": days,
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "order_count": order_count,
                "leave_count": leave_count,
            }

    summary = {
        "present": sum(d["present_count"] for d in monthly_data.values()),
        "absent": sum(d["absent_count"] for d in monthly_data.values()),
        "late": sum(d["late_count"] for d in monthly_data.values()),
        "order": sum(d["order_count"] for d in monthly_data.values()),
        "leave": sum(d["leave_count"] for d in monthly_data.values()),
    }

    departments = session.query(Department).filter(Department.is_deleted == False).all()

    approval = session.query(AttendanceApproval).filter(
        AttendanceApproval.year == year,
        AttendanceApproval.month == month,
        AttendanceApproval.person_type == person_type,
    ).first()

    return render_template(
        "hr/attendance_monthly.html",
        employees=persons,
        monthly_data=monthly_data,
        year=year,
        month=month,
        selected_month=month,
        selected_year=year,
        selected_department=department_id,
        year_range=range(date.today().year - 2, date.today().year + 2),
        months=months_ar,
        total_days=total_days,
        start_day=start_day,
        end_day=end_day,
        departments=departments,
        summary=summary,
        person_type=person_type,
        contract_filter=contract_filter,
        contract_types=[c.strip() for c in contract_filter.split(",") if c.strip()] if contract_filter and contract_filter != "all" else [],
        settings=settings,
        period_dates=period_dates,
        approval=approval,
    )


@hr_bp.route("/attendance/cell-save", methods=["POST"])
@login_required
def attendance_cell_save():
    session = get_web_session()
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400
    emp_id = data.get("employee_id")
    rec_date = data.get("date")
    status = data.get("status")
    if not emp_id or not rec_date or not status:
        return jsonify({"error": "missing fields"}), 400
    try:
        rec_date = date.fromisoformat(rec_date)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    allowed = ["present", "absent", "late", "order", "annual_leave", "sick_leave",
               "emergency_leave", "special_leave", "maternity_leave", "unpaid_leave",
               "hajj_leave", "marriage_leave", "bereavement_leave", "holiday", "rest"]
    if status not in allowed:
        return jsonify({"error": "invalid status"}), 400
    existing = session.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == emp_id,
        AttendanceRecord.record_date == rec_date,
    ).first()
    if existing:
        existing.status = status
    else:
        session.add(AttendanceRecord(
            employee_id=emp_id,
            record_date=rec_date,
            status=status,
            is_manual_entry=True,
            entered_by=current_user.id,
        ))
    session.commit()
    return jsonify({"ok": True})


@hr_bp.route("/attendance/save", methods=["POST"])
@login_required
def attendance_save():
    session = get_web_session()
    target_date = request.form.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(target_date)
    except ValueError:
        flash("تاريخ غير صالح", "danger")
        return redirect(url_for("hr.attendance_daily"))

    employee_ids = request.form.getlist("employee_id")
    for emp_id in employee_ids:
        status = request.form.get(f"status_{emp_id}", "").strip()
        if not status:
            continue

        existing = session.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == emp_id,
            AttendanceRecord.record_date == target_date,
        ).first()

        if existing:
            existing.status = status
            existing.check_in_time = _parse_time(request.form.get(f"check_in_{emp_id}"))
            existing.check_out_time = _parse_time(request.form.get(f"check_out_{emp_id}"))
            existing.delay_minutes = int(request.form.get(f"delay_{emp_id}", 0) or 0)
            existing.early_leave_minutes = int(request.form.get(f"early_leave_{emp_id}", 0) or 0)
            existing.overtime_hours = float(request.form.get(f"overtime_{emp_id}", 0) or 0)
            existing.notes = request.form.get(f"notes_{emp_id}", "").strip() or None
            existing.entered_by = current_user.id
        else:
            record = AttendanceRecord(
                employee_id=emp_id,
                record_date=target_date,
                day_of_week=_get_day_name(target_date),
                status=status,
                check_in_time=_parse_time(request.form.get(f"check_in_{emp_id}")),
                check_out_time=_parse_time(request.form.get(f"check_out_{emp_id}")),
                delay_minutes=int(request.form.get(f"delay_{emp_id}", 0) or 0),
                early_leave_minutes=int(request.form.get(f"early_leave_{emp_id}", 0) or 0),
                overtime_hours=float(request.form.get(f"overtime_{emp_id}", 0) or 0),
                notes=request.form.get(f"notes_{emp_id}", "").strip() or None,
                is_manual_entry=True,
                entered_by=current_user.id,
            )
            session.add(record)

    session.commit()
    flash("تم حفظ سجلات الحضور بنجاح", "success")
    return redirect(url_for("hr.attendance_daily", date=target_date.isoformat()))


@hr_bp.route("/attendance/entry")
@login_required
def attendance_entry():
    session = get_web_session()
    target_date_str = request.args.get("date", date.today().isoformat())
    person_type = request.args.get("type", "employees")
    dept_filter = request.args.get("dept", "all")
    contract_filter = request.args.get("contract", "all")
    try:
        target_date = date.fromisoformat(target_date_str)
    except ValueError:
        target_date = date.today()

    departments_list = session.query(Department).filter(Department.is_deleted == False).all()

    if person_type == "drivers":
        from src.core.models.base_models import Driver
        q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active"
        )
        if contract_filter != "all":
            q = q.filter(Driver.contract_type == contract_filter)
        persons = q.all()
        departments = {}
        for p in persons:
            departments[p.id] = "السائقين"
    else:
        q = session.query(Employee).filter(
            Employee.is_deleted == False, Employee.status == "active"
        )
        if dept_filter != "all":
            q = q.filter(Employee.department_id == dept_filter)
        persons = q.all()
        departments = {}
        for emp in persons:
            dept = session.query(Department).filter(Department.id == emp.department_id).first()
            departments[emp.id] = dept.name_ar if dept else "-"

    existing_records = {}
    records = session.query(AttendanceRecord).filter(
        AttendanceRecord.record_date == target_date
    ).all()
    for rec in records:
        existing_records[rec.employee_id] = rec

    today_leaves = session.query(LeaveRequest).filter(
        LeaveRequest.start_date <= target_date,
        LeaveRequest.end_date >= target_date,
        LeaveRequest.status == "approved"
    ).all()
    leave_employee_ids = {lr.employee_id for lr in today_leaves}

    return render_template(
        "hr/attendance_entry.html",
        persons=persons,
        departments=departments,
        existing_records=existing_records,
        leave_employee_ids=leave_employee_ids,
        target_date=target_date,
        person_type=person_type,
        departments_list=departments_list,
        dept_filter=dept_filter,
        contract_filter=contract_filter,
        page_title="ادخال الحضور اليومي"
    )


@hr_bp.route("/attendance/entry/save", methods=["POST"])
@login_required
def attendance_entry_save():
    session = get_web_session()
    target_date_str = request.form.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(target_date_str)
    except ValueError:
        target_date = date.today()

    employee_ids = request.form.getlist("employee_id")
    for emp_id in employee_ids:
        check_in = request.form.get(f"check_in_{emp_id}", "").strip()
        check_out = request.form.get(f"check_out_{emp_id}", "").strip()
        notes = request.form.get(f"notes_{emp_id}", "").strip()

        if check_in:
            status = "present"
        else:
            status = "absent"

        check_in_time = None
        check_out_time = None
        if check_in:
            try:
                check_in_time = time.fromisoformat(check_in)
            except ValueError:
                pass
        if check_out:
            try:
                check_out_time = time.fromisoformat(check_out)
            except ValueError:
                pass

        existing = session.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == emp_id,
            AttendanceRecord.record_date == target_date,
        ).first()

        if existing:
            existing.status = status
            existing.check_in_time = check_in_time
            existing.check_out_time = check_out_time
            existing.notes = notes or None
            existing.entered_by = current_user.id
            existing.updated_at = datetime.utcnow()
        else:
            record = AttendanceRecord(
                employee_id=emp_id,
                record_date=target_date,
                day_of_week=_get_day_name(target_date),
                status=status,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                notes=notes or None,
                is_manual_entry=True,
                entered_by=current_user.id,
            )
            session.add(record)

    session.commit()
    flash("تم حفظ سجلات الحضور بنجاح", "success")
    return redirect(url_for("hr.attendance_entry", date=target_date.isoformat()))


@hr_bp.route("/attendance/generate")
@login_required
def attendance_generate():
    session = get_web_session()
    target_date = request.args.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(target_date)
    except ValueError:
        target_date = date.today()

    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).all()

    generated = 0
    for emp in employees:
        existing = session.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.record_date == target_date,
        ).first()
        if existing:
            continue

        profile = session.query(EmployeeProfile).filter(
            EmployeeProfile.employee_id == emp.id
        ).first()
        start_date = profile.start_date if profile else emp.hire_date
        if not start_date or target_date < start_date:
            continue

        day_name = _get_day_name(target_date)
        rest_days = (profile.rest_days or "Friday") if profile else "Friday"
        if day_name in rest_days:
            status = AttendanceStatus.WEEKLY_REST
        else:
            status = AttendanceStatus.PRESENT

        record = AttendanceRecord(
            employee_id=emp.id,
            record_date=target_date,
            day_of_week=day_name,
            status=status,
            is_manual_entry=False,
            entered_by=current_user.id,
        )
        session.add(record)
        generated += 1

    session.commit()
    flash(f"تم إنشاء {generated} سجل حضور بنجاح", "success")
    return redirect(url_for("hr.attendance_daily", date=target_date.isoformat()))


@hr_bp.route("/attendance/report")
@login_required
def attendance_report():
    session = get_web_session()

    settings = {}
    rows = session.execute(text("SELECT setting_key, setting_value FROM attendance_settings")).fetchall()
    for row in rows:
        settings[row[0]] = row[1]

    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    department_id = request.args.get("department_id", "").strip()

    default_start = int(settings.get("start_day", "26"))
    default_end = int(settings.get("end_day", "25"))

    start_day = request.args.get("start_day", "").strip()
    end_day = request.args.get("end_day", "").strip()
    start_day = int(start_day) if start_day else default_start
    end_day = int(end_day) if end_day else default_end

    person_types = request.args.getlist("person_type")
    if not person_types:
        person_types = ["employees"]

    from src.core.models.base_models import Driver

    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

    departments = session.query(Department).filter(
        Department.is_deleted == False
    ).order_by(Department.name_ar).all()

    all_persons = []
    person_type_map = {}

    if "employees" in person_types:
        employees_q = session.query(Employee).filter(
            Employee.is_deleted == False, Employee.status == "active"
        )
        if department_id:
            employees_q = employees_q.filter(Employee.department_id == department_id)
        for emp in employees_q.order_by(Employee.full_name_ar).all():
            all_persons.append(emp)
            person_type_map[emp.id] = "employees"

    if "drivers_reserve" in person_types:
        drivers_q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active",
            Driver.contract_type.in_(["احتياط", "reserve"])
        )
        for drv in drivers_q.order_by(Driver.full_name_ar).all():
            all_persons.append(drv)
            person_type_map[drv.id] = "drivers_reserve"

    if "drivers_seasonal" in person_types:
        drivers_q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active",
            Driver.contract_type.in_(["موسمي", "seasonal"])
        )
        for drv in drivers_q.order_by(Driver.full_name_ar).all():
            all_persons.append(drv)
            person_type_map[drv.id] = "drivers_seasonal"

    if "national_transport" in person_types:
        drivers_q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active",
            Driver.contract_type.in_(["ايجار لغرض التمليك", "rent_to_own"])
        )
        for drv in drivers_q.order_by(Driver.full_name_ar).all():
            all_persons.append(drv)
            person_type_map[drv.id] = "national_transport"

    if "drivers_public" in person_types:
        drivers_q = session.query(Driver).filter(
            Driver.is_deleted == False, Driver.status == "active",
            Driver.contract_type.in_(["ركوبة عامة", "public_transport"])
        )
        for drv in drivers_q.order_by(Driver.full_name_ar).all():
            all_persons.append(drv)
            person_type_map[drv.id] = "drivers_public"

    total_days = 30

    if start_day < 1: start_day = 1
    if end_day > total_days: end_day = total_days

    report_data = []
    for person in all_persons:
        pid = person.id
        ptype = person_type_map.get(pid, "employees")
        full_name = getattr(person, 'full_name_ar', '')
        emp_number = getattr(person, 'employee_number', '') or getattr(person, 'driver_number', '') or '-'

        records = session.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == pid,
            AttendanceRecord.record_date >= date(year, month, min(start_day, total_days)),
            AttendanceRecord.record_date <= date(year, month, min(end_day, total_days)),
        ).all()

        rec_map = {}
        for r in records:
            rec_map[r.record_date.day] = r

        stats = {
            "present": 0, "absent": 0, "late": 0, "leave": 0,
            "rest": 0, "mission": 0, "training": 0, "sick": 0,
            "overtime": 0, "total_hours": 0.0
        }

        daily = []
        for day in range(start_day, end_day + 1):
            rec = rec_map.get(day)
            if rec:
                status_short = _get_status_short(rec.status)
                daily.append({
                    "day": day,
                    "status": rec.status,
                    "status_short": status_short,
                    "check_in": rec.check_in_time.strftime('%H:%M') if rec.check_in_time else "-",
                    "check_out": rec.check_out_time.strftime('%H:%M') if rec.check_out_time else "-",
                    "delay": rec.delay_minutes or 0,
                    "work_hours": rec.work_hours or 0,
                })
                if rec.status in ("present", "late", "early_leave", "overtime"):
                    stats["present"] += 1
                    stats["total_hours"] += rec.work_hours or 0
                elif rec.status in ("absent", "absent_excused", "absent_unexcused"):
                    stats["absent"] += 1
                elif rec.status == "late":
                    stats["late"] += 1
                elif rec.status in ("annual_leave", "sick_leave", "emergency_leave",
                                     "special_leave", "maternity_leave", "unpaid_leave",
                                     "hajj_leave", "marriage_leave", "bereavement_leave"):
                    stats["leave"] += 1
                elif rec.status == "weekly_rest":
                    stats["rest"] += 1
                elif rec.status == "mission":
                    stats["mission"] += 1
                elif rec.status == "training":
                    stats["training"] += 1
                elif rec.status == "sick_leave":
                    stats["sick"] += 1
            else:
                daily.append({
                    "day": day, "status": "", "status_short": "-",
                    "check_in": "-", "check_out": "-", "delay": 0, "work_hours": 0,
                })

        report_data.append({
            "person": person,
            "person_type": ptype,
            "full_name": full_name,
            "emp_number": emp_number,
            "daily": daily,
            "stats": stats,
        })

    return render_template("hr/attendance_report.html",
        report_data=report_data,
        year=year, month=month,
        month_name=months_ar[month - 1],
        total_days=total_days,
        start_day=start_day,
        end_day=end_day,
        departments=departments,
        department_id=department_id,
        person_types=person_types,
        settings=settings,
        today=date.today(),
    )


def _get_status_short(status):
    mapping = {
        "present": "ح",
        "absent": "غ",
        "absent_excused": "غ",
        "absent_unexcused": "غ",
        "late": "م",
        "early_leave": "خ",
        "annual_leave": "إ",
        "sick_leave": "إ",
        "emergency_leave": "إ",
        "special_leave": "إ",
        "maternity_leave": "إ",
        "unpaid_leave": "إ",
        "hajj_leave": "إ",
        "marriage_leave": "إ",
        "bereavement_leave": "إ",
        "mission": "مأ",
        "training": "ت",
        "weekly_rest": "ر",
        "official_holiday": "ع",
        "permission": "ص",
        "half_day": "ن",
        "overtime": "إض",
        "order": "أ",
    }
    return mapping.get(status, "-")


def _get_status_color(status):
    mapping = {
        "present": "#22c55e",
        "absent": "#ef4444",
        "absent_excused": "#ef4444",
        "absent_unexcused": "#ef4444",
        "late": "#f59e0b",
        "early_leave": "#f59e0b",
        "annual_leave": "#3b82f6",
        "sick_leave": "#3b82f6",
        "emergency_leave": "#3b82f6",
        "special_leave": "#3b82f6",
        "maternity_leave": "#3b82f6",
        "unpaid_leave": "#3b82f6",
        "hajj_leave": "#3b82f6",
        "marriage_leave": "#3b82f6",
        "bereavement_leave": "#3b82f6",
        "mission": "#8b5cf6",
        "training": "#06b6d4",
        "weekly_rest": "#6b7280",
        "official_holiday": "#6b7280",
        "permission": "#14b8a6",
        "half_day": "#f97316",
        "overtime": "#10b981",
    }
    return mapping.get(status, "#6b7280")


@hr_bp.route("/attendance/approve", methods=["POST"])
@login_required
def attendance_approve():
    session = get_web_session()
    data = request.get_json()
    year = data.get("year", date.today().year)
    month = data.get("month", date.today().month)
    person_type = data.get("person_type", "employees")
    role = data.get("role")

    approval = session.query(AttendanceApproval).filter(
        AttendanceApproval.year == year,
        AttendanceApproval.month == month,
        AttendanceApproval.person_type == person_type,
    ).first()

    if not approval:
        approval = AttendanceApproval(
            year=year, month=month, person_type=person_type
        )
        session.add(approval)

    now = datetime.utcnow()
    if role == "executive":
        if approval.executive_approved:
            approval.executive_approved = False
            approval.executive_approved_by = None
            approval.executive_approved_at = None
        else:
            approval.executive_approved = True
            approval.executive_approved_by = str(current_user.id)
            approval.executive_approved_at = now
    elif role == "hr":
        if approval.hr_approved:
            approval.hr_approved = False
            approval.hr_approved_by = None
            approval.hr_approved_at = None
        else:
            approval.hr_approved = True
            approval.hr_approved_by = str(current_user.id)
            approval.hr_approved_at = now

    session.commit()
    return jsonify({"success": True, "executive": approval.executive_approved, "hr": approval.hr_approved})


@hr_bp.route("/attendance/report/pdf")
@login_required
def attendance_report_pdf():
    session = get_web_session()
    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    department_id = request.args.get("department_id", "").strip()
    person_type = request.args.get("person_type", "employees")
    contract_filter = request.args.get("contract", "all")

    settings = {}
    rows = session.execute(text("SELECT setting_key, setting_value FROM attendance_settings")).fetchall()
    for row in rows:
        settings[row[0]] = row[1]
    start_day = int(settings.get("start_day", "26"))
    end_day_setting = int(settings.get("end_day", "25"))
    total_days = 30

    approval = session.query(AttendanceApproval).filter(
        AttendanceApproval.year == year,
        AttendanceApproval.month == month,
        AttendanceApproval.person_type == person_type,
    ).first()

    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

    if person_type == "drivers":
        from src.core.models.base_models import Driver
        q = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active")
        if contract_filter and contract_filter != "all":
            contract_types_list = [c.strip() for c in contract_filter.split(",") if c.strip()]
            if contract_types_list:
                ar_to_en = {"موسمي": "seasonal", "احتياطي": "reserve", "احتياط": "reserve", "ركوبة عامة": "public_transport", "ايجار لغرض التمليك": "rent_to_own"}
                mapped = [ar_to_en.get(c, c) for c in contract_types_list]
                q = q.filter(Driver.contract_type.in_(mapped))
        persons = q.order_by(Driver.full_name_ar).all()
    else:
        employees_q = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active")
        if department_id:
            employees_q = employees_q.filter(Employee.department_id == department_id)
        persons = employees_q.order_by(Employee.full_name_ar).all()

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    from datetime import timedelta
    period_dates = []
    current = date(year, month, start_day)
    end_date = date(next_year, next_month, end_day_setting)
    while current <= end_date:
        period_dates.append(current)
        current += timedelta(days=1)

    q = session.query(AttendanceRecord).filter(
        AttendanceRecord.record_date >= date(year, month, start_day),
        AttendanceRecord.record_date <= date(next_year, next_month, end_day_setting),
    )
    records = q.all()
    emp_records = {}
    for r in records:
        if r.employee_id not in emp_records:
            emp_records[r.employee_id] = {}
        emp_records[r.employee_id][r.record_date] = r.status

    report_data = []
    for p in persons:
        days = {}
        present_count = 0
        absent_count = 0
        order_count = 0
        leave_count = 0
        for i, d in enumerate(period_dates, 1):
            rec = emp_records.get(p.id, {}).get(d)
            if rec:
                days[str(i)] = rec
            else:
                days[str(i)] = "present"
            s = days[str(i)]
            if s == "present": present_count += 1
            elif s in ["absent", "absent_unexcused"]: absent_count += 1
            elif s == "order": order_count += 1
            elif s in ["leave", "annual_leave", "sick_leave", "emergency_leave",
                       "special_leave", "maternity_leave", "unpaid_leave",
                       "hajj_leave", "marriage_leave", "bereavement_leave"]: leave_count += 1
        emp_name = p.full_name_ar or ""
        emp_num = p.driver_number if person_type == "drivers" else p.employee_number
        report_data.append({
            "name": emp_name, "number": emp_num or "",
            "days": days, "present": present_count, "absent": absent_count,
            "order": order_count, "leave": leave_count,
        })
    type_label = "السائقين" if person_type == "drivers" else "الموظفين"

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

    margin = 10 * mm
    name_w = 38 * mm
    num_w = 16 * mm
    fixed_w = name_w + num_w
    stats_w = 36 * mm
    avail = page_w - margin * 2 - fixed_w - stats_w
    col_w = avail / total_days

    hdr_h = 8 * mm
    row_h = 6 * mm

    navy = colors.HexColor("#0f172a")
    navy_l = colors.HexColor("#1e293b")
    blue = colors.HexColor("#2563eb")
    green = colors.HexColor("#16a34a")
    red = colors.HexColor("#dc2626")
    purple = colors.HexColor("#7c3aed")
    blue_s = colors.HexColor("#2563eb")
    amber = colors.HexColor("#d97706")
    slate = colors.HexColor("#64748b")
    bg_alt = colors.HexColor("#f1f5f9")
    line_c = colors.HexColor("#e2e8f0")
    white = colors.white

    sc = {
        "present": green, "absent": red, "absent_unexcused": red,
        "late": amber, "order": purple,
        "annual_leave": blue_s, "sick_leave": blue_s, "emergency_leave": blue_s,
        "special_leave": blue_s, "maternity_leave": blue_s, "unpaid_leave": blue_s,
        "hajj_leave": blue_s, "marriage_leave": blue_s, "bereavement_leave": blue_s,
        "leave": blue_s, "holiday": slate,
    }

    def draw_top_bar(y):
        c.setFillColor(navy)
        c.rect(0, y - 2*mm, page_w, 18*mm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 18)
        c.drawCentredString(page_w/2, y + 5*mm, ar("شركة اعمار ليبيا لنقل الركاب"))
        c.setFont("Ar", 9)
        c.drawCentredString(page_w/2, y - 1*mm, ar("شركة اعمار ليبيا القابضة"))
        c.setFillColor(colors.HexColor("#3b82f6"))
        c.rect(0, y - 2*mm, page_w, 1*mm, fill=1, stroke=0)
        return y - 20 * mm

    def draw_title(y, cont=False):
        title = f"كشف الحضور والانصراف — {type_label} — {months_ar[month-1]} {year}"
        if cont:
            title += " (استمرار)"
        c.setFillColor(navy)
        c.roundRect(margin, y - 4*mm, page_w - margin*2, 10*mm, 3, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 12)
        c.drawCentredString(page_w/2, y - 0.5*mm, ar(title))
        return y - 14 * mm

    def draw_cols(y):
        x = margin
        c.setFillColor(navy_l)
        c.roundRect(x, y - hdr_h, name_w + num_w, hdr_h, 2, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("ArBd", 7)
        c.drawCentredString(x + name_w/2, y - hdr_h + 2.5*mm, ar("اسم الموظف"))
        c.drawCentredString(x + name_w + num_w/2, y - hdr_h + 2.5*mm, ar("الرقم"))

        for i in range(total_days):
            dx = x + fixed_w + i * col_w
            if period_dates[i].weekday() >= 5:
                c.setFillColor(colors.HexColor("#fef2f2"))
                c.rect(dx, y - hdr_h, col_w, hdr_h, fill=1, stroke=0)
            else:
                c.setFillColor(navy if i % 2 == 0 else navy_l)
                c.rect(dx, y - hdr_h, col_w, hdr_h, fill=1, stroke=0)
            c.setFillColor(white if period_dates[i].weekday() < 5 else red)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(dx + col_w/2, y - hdr_h + 2.5*mm, str(period_dates[i].day))

        sx = x + fixed_w + total_days * col_w
        sw = stats_w / 4
        labels = [("الحضور", green), ("الغياب", red), ("أوامر", purple), ("إجازات", blue_s)]
        for i, (lbl, clr) in enumerate(labels):
            c.setFillColor(clr)
            c.rect(sx + i*sw, y - hdr_h, sw, hdr_h, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("ArBd", 6.5)
            c.drawCentredString(sx + i*sw + sw/2, y - hdr_h + 2.5*mm, ar(lbl))
        return y - hdr_h

    y = page_h - 8 * mm
    y = draw_top_bar(y)
    y = draw_title(y)
    c.setStrokeColor(green)
    c.setLineWidth(1.5)
    c.line(margin, y, page_w - margin, y)
    y -= 2 * mm
    y = draw_cols(y)

    for idx, row in enumerate(report_data):
        if y < 28 * mm:
            c.showPage()
            y = page_h - 8 * mm
            y = draw_top_bar(y)
            y = draw_title(y, True)
            c.setStrokeColor(green)
            c.setLineWidth(1.5)
            c.line(margin, y, page_w - margin, y)
            y -= 2 * mm
            y = draw_cols(y)

        if idx % 2 == 0:
            c.setFillColor(bg_alt)
            c.rect(margin, y - row_h, fixed_w + total_days*col_w + stats_w, row_h, fill=1, stroke=0)

        c.setStrokeColor(line_c)
        c.setLineWidth(0.3)
        c.line(margin, y - row_h, margin + fixed_w + total_days*col_w + stats_w, y - row_h)

        x = margin
        c.setFillColor(navy)
        c.setFont("Ar", 6)
        name_text = ar(row["name"][:20])
        c.drawRightString(x + name_w - 2*mm, y - row_h + 2*mm, name_text)
        c.setFont("Helvetica", 4.5)
        c.setFillColor(slate)
        c.drawCentredString(x + name_w + num_w/2, y - row_h + 2*mm, row["number"][:12])

        for i in range(1, total_days + 1):
            st = row["days"].get(str(i), "present")
            dx = x + fixed_w + (i-1) * col_w
            if period_dates[i-1].weekday() >= 5:
                c.setFillColor(colors.HexColor("#fef2f2"))
                c.rect(dx, y - row_h, col_w, row_h, fill=1, stroke=0)
            clr = sc.get(st, slate)
            sw_cell = 4.5 * mm
            sh_cell = 4 * mm
            cx = dx + (col_w - sw_cell) / 2
            cy = y - row_h + (row_h - sh_cell) / 2
            c.setFillColor(clr)
            c.roundRect(cx, cy, sw_cell, sh_cell, 1, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("ArBd", 6)
            short = _get_status_short(st)
            c.drawCentredString(cx + sw_cell/2, cy + 1*mm, short)

        sx = x + fixed_w + total_days * col_w
        sw = stats_w / 4
        for i, (val, clr) in enumerate([(row["present"], green), (row["absent"], red), (row["order"], purple), (row["leave"], blue_s)]):
            c.setFillColor(clr)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(sx + i*sw + sw/2, y - row_h + 2*mm, str(val))
        y -= row_h

    y -= 4 * mm
    c.setStrokeColor(green)
    c.setLineWidth(1.5)
    c.line(margin, y, page_w - margin, y)
    y -= 5 * mm

    c.setFillColor(navy)
    c.roundRect(margin, y - 3*mm, page_w - margin*2, 8*mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("ArBd", 8)
    c.drawRightString(page_w - margin - 3*mm, y, ar("الاجمالي الكلي:"))
    total_p = sum(r["present"] for r in report_data)
    total_a = sum(r["absent"] for r in report_data)
    total_o = sum(r["order"] for r in report_data)
    total_l = sum(r["leave"] for r in report_data)
    sx = margin + fixed_w + total_days * col_w
    sw = stats_w / 4
    for i, (val, clr) in enumerate([(total_p, green), (total_a, red), (total_o, purple), (total_l, blue_s)]):
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(sx + i*sw + sw/2, y, str(val))

    y -= 8 * mm
    c.setFillColor(slate)
    c.setFont("Ar", 7)
    c.drawRightString(page_w - margin, y, ar(f"عدد {type_label}: {len(report_data)}  |  تاريخ الطباعة: {date.today().strftime('%Y-%m-%d')}"))

    y -= 10 * mm
    c.setStrokeColor(line_c)
    c.setLineWidth(0.4)

    exec_approved = approval and approval.executive_approved
    hr_approved = approval and approval.hr_approved

    sig_items = [
        {"label": ar("المدير التنفيذي"), "x": page_w - margin - 55*mm, "approved": exec_approved},
        {"label": ar("مدير قسم الشؤون الادارية"), "x": page_w/2 - 25*mm, "approved": hr_approved},
        {"label": ar("المسؤول المباشر"), "x": margin, "approved": False},
    ]
    for item in sig_items:
        pos = item["x"]
        c.line(pos, y, pos + 50*mm, y)
        c.setFont("Ar", 6)
        c.setFillColor(slate)
        c.drawCentredString(pos + 25*mm, y - 4*mm, item["label"])

        if item["approved"]:
            c.saveState()
            c.translate(pos + 25*mm, y + 4*mm)
            c.rotate(15)
            c.setFillColor(colors.HexColor("#16a34a"))
            c.setFont("ArBd", 14)
            c.drawCentredString(0, 0, ar("معتمد"))
            c.setStrokeColor(colors.HexColor("#16a34a"))
            c.setLineWidth(1.5)
            c.roundRect(-18*mm, -3*mm, 36*mm, 6*mm, 3, stroke=1, fill=0)
            c.restoreState()

    c.save()
    buf.seek(0)

    response = make_response(buf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=attendance_{year}_{month}.pdf"
    return response


# ============================================================
# CONTRACT TYPES & CLASSIFICATIONS
# ============================================================

@hr_bp.route("/contract-types")
@login_required
def contract_types_page():
    from src.web.contract_types import get_contract_types, get_activity_types
    session = get_web_session()
    contract_types = get_contract_types(session)
    activity_types = get_activity_types(session)
    return render_template(
        "hr/contract_types.html",
        contract_types=contract_types,
        activity_types=activity_types,
    )


@hr_bp.route("/contract-types/add", methods=["POST"])
@login_required
def contract_type_add():
    from src.web.contract_types import add_type
    session = get_web_session()
    kind = request.form.get("kind", "contract").strip()
    label = request.form.get("label", "").strip()
    value = request.form.get("value", "").strip() or None
    ok, msg = add_type(kind, label, value=value, session=session)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("hr.contract_types_page"))


@hr_bp.route("/contract-types/delete", methods=["POST"])
@login_required
def contract_type_delete():
    from src.web.contract_types import delete_type
    session = get_web_session()
    kind = request.form.get("kind", "contract").strip()
    value = request.form.get("value", "").strip()
    ok, msg = delete_type(kind, value, session=session)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("hr.contract_types_page"))


@hr_bp.route("/contract-types/api", methods=["POST"])
@login_required
def contract_type_api():
    from src.web.contract_types import add_type, delete_type, get_contract_types, get_activity_types
    session = get_web_session()
    data = request.get_json(silent=True) or {}
    action = data.get("action", request.form.get("action", ""))
    kind = data.get("kind", request.form.get("kind", "contract"))
    if action == "add":
        ok, msg = add_type(kind, data.get("label", ""), value=data.get("value") or None, session=session)
        return jsonify({"ok": ok, "message": msg})
    if action == "delete":
        ok, msg = delete_type(kind, data.get("value", ""), session=session)
        return jsonify({"ok": ok, "message": msg})
    if action == "list":
        pairs = get_activity_types(session) if kind == "activity" else get_contract_types(session)
        return jsonify({"ok": True, "items": [{"value": v, "label": l} for v, l in pairs]})
    return jsonify({"ok": False, "message": "إجراء غير صحيح"}), 400


# ============================================================
# ATTENDANCE SETTINGS
# ============================================================

@hr_bp.route("/attendance/settings")
@login_required
def attendance_settings():
    session = get_web_session()
    settings = {}
    rows = session.execute(text("SELECT setting_key, setting_value FROM attendance_settings")).fetchall()
    for row in rows:
        settings[row[0]] = row[1]
    return render_template("hr/attendance_settings.html", settings=settings, page_title="إعدادات سجلات الحضور والانصراف")


@hr_bp.route("/attendance/settings", methods=["POST"])
@login_required
def attendance_settings_save():
    session = get_web_session()
    from datetime import datetime as dt_now
    updates = {
        'start_day': request.form.get('start_day', '26'),
        'end_day': request.form.get('end_day', '25'),
        'enable_employees': 'true' if request.form.get('enable_employees') else 'false',
        'enable_drivers_reserve': 'true' if request.form.get('enable_drivers_reserve') else 'false',
        'enable_drivers_seasonal': 'true' if request.form.get('enable_drivers_seasonal') else 'false',
        'enable_national_transport': 'true' if request.form.get('enable_national_transport') else 'false',
        'enable_drivers_public': 'true' if request.form.get('enable_drivers_public') else 'false',
        'default_attendance': request.form.get('default_attendance', 'present'),
        'total_days': '30',
        'leave_annual': request.form.get('leave_annual', '30'),
        'leave_sick': request.form.get('leave_sick', '15'),
        'leave_emergency': request.form.get('leave_emergency', '7'),
        'leave_unpaid': request.form.get('leave_unpaid', '30'),
        'leave_hajj': request.form.get('leave_hajj', '15'),
        'leave_marriage': request.form.get('leave_marriage', '5'),
        'leave_bereavement': request.form.get('leave_bereavement', '5'),
        'leave_maternity': request.form.get('leave_maternity', '60'),
    }
    for k, v in updates.items():
        session.execute(
            text("UPDATE attendance_settings SET setting_value = :v, updated_at = :u WHERE setting_key = :k"),
            {'k': k, 'v': v, 'u': dt_now.utcnow()}
        )
    session.commit()
    flash("تم حفظ الإعدادات بنجاح", "success")
    return redirect(url_for("hr.attendance_settings"))


# ============================================================
# LEAVE MANAGEMENT
# ============================================================

@hr_bp.route("/leave")
@login_required
def leave_list():
    session = get_web_session()
    tab = request.args.get("tab", "all").strip()

    q = session.query(LeaveRequest).join(Employee, LeaveRequest.employee_id == Employee.id)
    if tab and tab != "all":
        q = q.filter(LeaveRequest.status == tab)

    leaves = q.order_by(LeaveRequest.created_at.desc()).all()

    return render_template("hr/leave_list.html", leaves=leaves, tab=tab)


@hr_bp.route("/leave/request", methods=["GET", "POST"])
@login_required
def leave_request_form():
    session = get_web_session()
    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()
    leave_types = session.query(LeaveType).filter(
        LeaveType.is_active == True
    ).order_by(LeaveType.sort_order).all()

    current_year = date.today().year
    leave_balances_all = {}
    for emp in employees:
        balances = session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == emp.id,
            LeaveBalance.year == current_year,
        ).all()
        existing_lt_ids = {b.leave_type_id for b in balances}
        for lt in leave_types:
            if lt.id not in existing_lt_ids and lt.default_days and lt.default_days > 0:
                new_balance = LeaveBalance(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    year=current_year,
                    entitled_days=lt.default_days,
                    used_days=0,
                    carried_over=0,
                    adjusted=0,
                )
                session.add(new_balance)
                balances = list(balances) + [new_balance]
        emp_data = {}
        for b in balances:
            lt = b.leave_type
            emp_data[lt.name_ar if lt else ""] = {
                "total": b.entitled_days + b.carried_over + b.adjusted,
                "used": b.used_days,
                "remaining": b.remaining_days,
            }
        leave_balances_all[emp.id] = emp_data
    session.commit()

    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        leave_type_id = request.form.get("leave_type_id", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        reason = request.form.get("reason", "").strip()
        notes = request.form.get("notes", "").strip()

        if not employee_id or not leave_type_id or not start_date_str or not end_date_str:
            flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
            return render_template(
                "hr/leave_request_form.html",
                employees=employees,
                leave_types=leave_types,
                leave_balances_all=leave_balances_all,
            )

        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        total_days = (end_date - start_date).days + 1

        employee = session.query(Employee).filter(Employee.id == employee_id).first()
        leave_type = session.query(LeaveType).filter(LeaveType.id == leave_type_id).first()

        balances_data = session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == current_year,
        ).all()
        balances = []
        for b in balances_data:
            lt = b.leave_type
            balances.append({
                "name": lt.name_ar if lt else "",
                "entitled": b.entitled_days + b.carried_over + b.adjusted,
                "used": b.used_days,
                "remaining": b.remaining_days,
                "is_selected": lt.id == leave_type_id if lt else False,
                "after": b.remaining_days - total_days if lt and lt.id == leave_type_id else b.remaining_days,
            })

        return render_template(
            "hr/leave_preview.html",
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            notes=notes,
            balances=balances,
        )

    return render_template(
        "hr/leave_request_form.html",
        employees=employees,
        leave_types=leave_types,
        leave_balances_all=leave_balances_all,
    )


@hr_bp.route("/leave/request/confirm", methods=["POST"])
@login_required
def leave_request_confirm():
    session = get_web_session()
    employee_id = request.form.get("employee_id", "").strip()
    leave_type_id = request.form.get("leave_type_id", "").strip()
    start_date_str = request.form.get("start_date", "").strip()
    end_date_str = request.form.get("end_date", "").strip()

    if not employee_id or not leave_type_id or not start_date_str or not end_date_str:
        flash("بيانات غير مكتملة", "danger")
        return redirect(url_for("hr.leave_request_form"))

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)
    total_days = (end_date - start_date).days + 1

    leave_request = LeaveRequest(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=request.form.get("reason", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
        status="pending",
        created_by=current_user.id,
    )
    session.add(leave_request)
    session.commit()
    flash("تم إرسال طلب الإجازة بنجاح — في انتظار موافقة المدير التنفيذي", "success")
    return redirect(url_for("hr.leave_list"))


@hr_bp.route("/leave/<id>")
@login_required
def leave_detail(id):
    session = get_web_session()
    leave = session.query(LeaveRequest).filter(LeaveRequest.id == id).first()
    if not leave:
        flash("طلب الإجازة غير موجود", "danger")
        return redirect(url_for("hr.leave_list"))

    balances_data = session.query(LeaveBalance).filter(
        LeaveBalance.employee_id == leave.employee_id,
        LeaveBalance.year == leave.start_date.year,
    ).all()
    balances = []
    for b in balances_data:
        lt = b.leave_type
        balances.append({
            "name": lt.name_ar if lt else "",
            "entitled": b.entitled_days + b.carried_over + b.adjusted,
            "used": b.used_days,
            "remaining": b.remaining_days,
            "is_leave_type": lt.id == leave.leave_type_id if lt else False,
        })

    return render_template("hr/leave_detail.html", leave=leave, balances=balances)


@hr_bp.route("/leave/<id>/approve", methods=["POST"])
@login_required
def leave_approve(id):
    session = get_web_session()
    leave_request = session.query(LeaveRequest).filter(LeaveRequest.id == id).first()
    if not leave_request:
        flash("طلب الإجازة غير موجود", "danger")
        return redirect(url_for("hr.leave_list"))

    if leave_request.status == "pending":
        leave_request.status = "pending_executive"
        leave_request.hr_approved = True
        leave_request.hr_notes = request.form.get("hr_notes", "").strip() or None
        leave_request.hr_approved_at = datetime.utcnow()

        employee = session.query(Employee).filter(Employee.id == leave_request.employee_id).first()
        leave_type = session.query(LeaveType).filter(LeaveType.id == leave_request.leave_type_id).first()
        emp_name = employee.full_name_ar if employee else "موظف"
        lt_name = leave_type.name_ar if leave_type else ""
        notify_users = session.query(User).filter(
            User.is_deleted == False
        ).all()
        for u in notify_users:
            session.add(Notification(
                user_id=u.id,
                title="طلب إجازة بانتظار الاعتماد",
                message=f"طلب إجازة {lt_name} للموظف {emp_name} — من {leave_request.start_date} إلى {leave_request.end_date} ({leave_request.total_days} يوم)",
                notification_type="leave_pending_executive",
                reference_id=leave_request.id,
                reference_type="LeaveRequest",
            ))

        session.commit()
        flash("تمت موافقة قسم الشؤون الادارية — في انتظار موافقة المدير التنفيذي", "success")
    elif leave_request.status == "pending_executive":
        leave_request.status = "approved"
        leave_request.final_approved_by = current_user.id
        leave_request.final_approved_at = datetime.utcnow()

        leave_type = session.query(LeaveType).filter(LeaveType.id == leave_request.leave_type_id).first()
        leave_status_map = {
            "سنوية": "annual_leave", "sick": "sick_leave", "مرضية": "sick_leave",
            "طارئة": "emergency_leave", "خاصة": "special_leave", "أمومة": "maternity_leave",
            "بدون راتب": "unpaid_leave", "حج": "hajj_leave", "زواج": "marriage_leave",
            "وفاة": "bereavement_leave",
        }
        att_status = "annual_leave"
        if leave_type:
            for key, val in leave_status_map.items():
                if key in (leave_type.name_ar or ""):
                    att_status = val
                    break

        from datetime import timedelta
        current_day = leave_request.start_date
        while current_day <= leave_request.end_date:
            existing = session.query(AttendanceRecord).filter(
                AttendanceRecord.employee_id == leave_request.employee_id,
                AttendanceRecord.record_date == current_day,
            ).first()
            if existing:
                existing.status = att_status
                existing.notes = f"إجازة معتمدة - {leave_request.id}"
            else:
                session.add(AttendanceRecord(
                    employee_id=leave_request.employee_id,
                    record_date=current_day,
                    status=att_status,
                    notes=f"إجازة معتمدة - {leave_request.id}",
                    entered_by=current_user.id,
                    is_manual_entry=True,
                ))
            current_day += timedelta(days=1)

        balance = session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == leave_request.employee_id,
            LeaveBalance.leave_type_id == leave_request.leave_type_id,
            LeaveBalance.year == leave_request.start_date.year,
        ).first()
        if balance:
            balance.used_days += leave_request.total_days

        session.commit()
        flash("تم اعتماد طلب الإجازة نهائياً وإضافته لسجل الحضور", "success")
    else:
        flash("لا يمكن الموافقة على هذا الطلب", "warning")

    return redirect(url_for("hr.leave_list"))


@hr_bp.route("/leave/<id>/reject", methods=["POST"])
@login_required
def leave_reject(id):
    session = get_web_session()
    leave_request = session.query(LeaveRequest).filter(LeaveRequest.id == id).first()
    if not leave_request:
        flash("طلب الإجازة غير موجود", "danger")
        return redirect(url_for("hr.leave_list"))

    old_status = leave_request.status
    rejection_reason = request.form.get("rejection_reason", "").strip() or None

    leave_request.status = "rejected"
    leave_request.rejection_reason = rejection_reason
    leave_request.rejected_by = current_user.id
    leave_request.rejected_at = datetime.utcnow()

    if old_status == "pending":
        leave_request.hr_approved = False
        leave_request.hr_approved_at = datetime.utcnow()

    if old_status == "approved":
        balance = session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == leave_request.employee_id,
            LeaveBalance.leave_type_id == leave_request.leave_type_id,
            LeaveBalance.year == leave_request.start_date.year,
        ).first()
        if balance and balance.used_days >= leave_request.total_days:
            balance.used_days -= leave_request.total_days

    session.commit()
    flash("تم رفض طلب الإجازة" + (" — تم إرجاع الأيام للرصيد" if old_status == "approved" else ""), "warning")
    return redirect(url_for("hr.leave_list"))


@hr_bp.route("/leave/<id>/cancel", methods=["POST"])
@login_required
def leave_cancel(id):
    session = get_web_session()
    leave_request = session.query(LeaveRequest).filter(LeaveRequest.id == id).first()
    if not leave_request:
        flash("طلب الإجازة غير موجود", "danger")
        return redirect(url_for("hr.leave_list"))

    if leave_request.status not in ("pending", "pending_executive"):
        flash("لا يمكن إلغاء هذا الطلب", "warning")
        return redirect(url_for("hr.leave_list"))

    leave_request.status = "cancelled"
    session.commit()
    flash("تم إلغاء طلب الإجازة", "warning")
    return redirect(url_for("hr.leave_list"))


@hr_bp.route("/leave/balances")
@login_required
def leave_balances():
    session = get_web_session()
    year = int(request.args.get("year", date.today().year))
    employee_id = request.args.get("employee_id", "").strip()

    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()

    leave_types = session.query(LeaveType).filter(
        LeaveType.is_active == True
    ).all()

    q = session.query(LeaveBalance).filter(LeaveBalance.year == year)
    if employee_id:
        q = q.filter(LeaveBalance.employee_id == employee_id)

    balances = q.all()

    return render_template(
        "hr/leave_balances.html",
        employees=employees,
        leave_types=leave_types,
        balances=balances,
        year=year,
        employee_id=employee_id,
    )


# ============================================================
# DISCIPLINARY ACTIONS
# ============================================================

@hr_bp.route("/disciplinary")
@login_required
def disciplinary_list():
    session = get_web_session()
    actions = session.query(DisciplinaryAction).join(
        Employee, DisciplinaryAction.employee_id == Employee.id
    ).order_by(DisciplinaryAction.created_at.desc()).all()
    return render_template("hr/disciplinary_list.html", actions=actions)


@hr_bp.route("/disciplinary/add", methods=["GET", "POST"])
@login_required
def disciplinary_add():
    session = get_web_session()
    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()
    disciplinary_types = session.query(DisciplinaryType).filter(
        DisciplinaryType.is_active == True
    ).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        disciplinary_type_id = request.form.get("disciplinary_type_id", "").strip()
        decision_number = request.form.get("decision_number", "").strip()
        violation_date_str = request.form.get("violation_date", "").strip()
        violation_description = request.form.get("violation_description", "").strip()
        decision = request.form.get("decision", "").strip()
        effective_date_str = request.form.get("effective_date", "").strip()

        if not all([employee_id, disciplinary_type_id, decision_number, violation_date_str, violation_description, decision, effective_date_str]):
            flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
            return render_template(
                "hr/disciplinary_form.html",
                employees=employees,
                disciplinary_types=disciplinary_types,
            )

        action = DisciplinaryAction(
            employee_id=employee_id,
            disciplinary_type_id=disciplinary_type_id,
            decision_number=decision_number,
            violation_date=date.fromisoformat(violation_date_str),
            violation_description=violation_description,
            decision=decision,
            effective_date=date.fromisoformat(effective_date_str),
            article_reference=request.form.get("article_reference", "").strip() or None,
            investigation_notes=request.form.get("investigation_notes", "").strip() or None,
            deduction_days=int(request.form.get("deduction_days") or 0) or None,
            deduction_amount=_parse_float(request.form.get("deduction_amount")),
            issued_by=request.form.get("issued_by", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            created_by=current_user.id,
        )
        session.add(action)
        session.commit()
        flash("تم إضافة الإجراء التأديبي بنجاح", "success")
        return redirect(url_for("hr.disciplinary_list"))

    return render_template(
        "hr/disciplinary_form.html",
        employees=employees,
        disciplinary_types=disciplinary_types,
    )


# ============================================================
# CONTRACTS
# ============================================================

@hr_bp.route("/contracts")
@login_required
def contracts_list():
    session = get_web_session()
    contract_type_filter = request.args.get("contract_type", "").strip()
    search = request.args.get("search", "").strip()
    
    results = []
    
    # Employee contracts
    if contract_type_filter != "driver":
        emp_q = session.query(Contract).join(Employee, Contract.employee_id == Employee.id)
        emp_contracts = emp_q.order_by(Contract.created_at.desc()).all()
        
        for c in emp_contracts:
            name = c.employee.full_name_ar if c.employee else ""
            num = c.employee.employee_number if c.employee else ""
            if search and search not in name and search not in (c.contract_number or "") and search not in num:
                continue
            results.append({
                "id": c.id,
                "contract_number": c.contract_number or "",
                "person_name": name,
                "person_number": num,
                "contract_type": c.contract_type or "",
                "start_date": c.start_date,
                "end_date": c.end_date,
                "status": c.status or "",
                "type_label": "موظف",
                "print_url": url_for("hr.contract_print", contract_id=c.id),
                "detail_url": url_for("hr.contracts_edit", id=c.id),
                "edit_url": url_for("hr.contracts_edit", id=c.id),
            })
    
    # Driver contracts
    if contract_type_filter != "employee":
        from src.core.models.hr_models import DriverContract
        from src.core.models.base_models import Driver
        drv_q = session.query(DriverContract).join(Driver, DriverContract.driver_id == Driver.id)
        drv_contracts = drv_q.order_by(DriverContract.created_at.desc()).all()
        
        for c in drv_contracts:
            name = c.driver.full_name_ar if c.driver else ""
            num = c.driver.driver_number if c.driver else ""
            if search and search not in name and search not in (c.contract_number or "") and search not in num:
                continue
            type_map = {"reserve": "احتياط", "seasonal": "موسمي", "public_transport": "ركوبة عامة", "rent_to_own": "ايجار لغرض التمليك"}
            results.append({
                "id": c.id,
                "contract_number": c.contract_number or "",
                "person_name": name,
                "person_number": num,
                "contract_type": type_map.get(c.contract_type, c.contract_type or ""),
                "start_date": c.start_date,
                "end_date": c.end_date,
                "status": c.status or "",
                "type_label": "سائق",
                "print_url": url_for("hr.driver_contract_print", contract_id=c.id),
                "detail_url": url_for("hr.driver_contracts_edit", id=c.id),
                "edit_url": url_for("hr.driver_contracts_edit", id=c.id),
            })
    
    results.sort(key=lambda x: x["start_date"] or "", reverse=True)
    
    return render_template("hr/contracts_list.html", contracts=results, search=search, contract_type_filter=contract_type_filter)


@hr_bp.route("/contracts/add", methods=["GET", "POST"])
@login_required
def contracts_add():
    session = get_web_session()
    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        contract_number = request.form.get("contract_number", "").strip()
        contract_type = request.form.get("contract_type", "").strip()
        start_date_str = request.form.get("start_date", "").strip()

        if not all([employee_id, contract_number, contract_type, start_date_str]):
            flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
            return render_template("hr/contract_form.html", employees=employees, contract=None)

        contract = Contract(
            employee_id=employee_id,
            contract_number=contract_number,
            contract_type=contract_type,
            start_date=date.fromisoformat(start_date_str),
            end_date=_parse_date(request.form.get("end_date")),
            probation_period_months=int(request.form.get("probation_period_months") or 0) or None,
            salary=_parse_float(request.form.get("salary")),
            allowances=_parse_float(request.form.get("allowances")),
            benefits=request.form.get("benefits", "").strip() or None,
            terms_and_conditions=request.form.get("terms_and_conditions", "").strip() or None,
            status=request.form.get("status", "active"),
            approved_by=request.form.get("approved_by", "").strip() or None,
            approval_date=_parse_date(request.form.get("approval_date")),
            notes=request.form.get("notes", "").strip() or None,
            created_by=current_user.id,
        )
        session.add(contract)
        session.commit()
        flash("تم إضافة العقد بنجاح", "success")
        return redirect(url_for("hr.contracts_list"))

    return render_template("hr/contract_form.html", employees=employees, contract=None)


# ============================================================
# SHIFTS
# ============================================================

@hr_bp.route("/shifts")
@login_required
def shifts_list():
    session = get_web_session()
    shifts = session.query(WorkShift).order_by(WorkShift.created_at.desc()).all()
    assignments = session.query(ShiftAssignment).join(
        Employee, ShiftAssignment.employee_id == Employee.id
    ).join(WorkShift, ShiftAssignment.shift_id == WorkShift.id).filter(
        ShiftAssignment.is_active == True
    ).all()

    return render_template("hr/shifts.html", shifts=shifts, assignments=assignments)


@hr_bp.route("/shifts/assign", methods=["GET", "POST"])
@login_required
def shifts_assign():
    session = get_web_session()
    employees = session.query(Employee).filter(
        Employee.is_deleted == False, Employee.status == "active"
    ).order_by(Employee.full_name_ar).all()
    shifts = session.query(WorkShift).filter(
        WorkShift.is_active == True
    ).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        shift_id = request.form.get("shift_id", "").strip()
        effective_from_str = request.form.get("effective_from", "").strip()

        if not all([employee_id, shift_id, effective_from_str]):
            flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
            return render_template(
                "hr/shift_assign.html",
                employees=employees,
                shifts=shifts,
            )

        assignment = ShiftAssignment(
            employee_id=employee_id,
            shift_id=shift_id,
            effective_from=date.fromisoformat(effective_from_str),
            effective_to=_parse_date(request.form.get("effective_to")),
            day_of_week=request.form.get("day_of_week", "").strip() or None,
            is_active=True,
        )
        session.add(assignment)
        session.commit()
        flash("تم تعيين الوردية بنجاح", "success")
        return redirect(url_for("hr.shifts_list"))

    return render_template(
        "hr/shift_assign.html",
        employees=employees,
        shifts=shifts,
    )


# ============================================================
# HR RULES SETTINGS
# ============================================================

@hr_bp.route("/rules")
@login_required
def rules_list():
    session = get_web_session()
    rules = session.query(HRRule).order_by(
        HRRule.category, HRRule.rule_key
    ).all()

    categories = {}
    for rule in rules:
        if rule.category not in categories:
            categories[rule.category] = []
        categories[rule.category].append(rule)

    return render_template("hr/hr_rules.html", categories=categories)


@hr_bp.route("/rules/save", methods=["POST"])
@login_required
def rules_save():
    session = get_web_session()
    rule_keys = request.form.getlist("rule_key")
    rule_values = request.form.getlist("rule_value")
    rule_ids = request.form.getlist("rule_id")

    for i, rule_key in enumerate(rule_keys):
        if not rule_key.strip():
            continue

        rule_value = rule_values[i] if i < len(rule_values) else ""
        rule_id = rule_ids[i] if i < len(rule_ids) else ""

        if rule_id:
            rule = session.query(HRRule).filter(HRRule.id == rule_id).first()
            if rule:
                rule.rule_value = rule_value.strip()
        else:
            category = request.form.get(f"category_{rule_key}", "").strip() or "general"
            existing = session.query(HRRule).filter(
                HRRule.category == category, HRRule.rule_key == rule_key.strip()
            ).first()
            if existing:
                existing.rule_value = rule_value.strip()
            else:
                new_rule = HRRule(
                    category=category,
                    rule_key=rule_key.strip(),
                    rule_value=rule_value.strip(),
                    rule_value_type=request.form.get(f"type_{rule_key}", "string").strip(),
                    description_ar=request.form.get(f"desc_{rule_key}", "").strip() or None,
                    is_active=True,
                )
                session.add(new_rule)

    session.commit()
    flash("تم حفظ القواعد بنجاح", "success")
    return redirect(url_for("hr.rules_list"))


# ============================================================
# DOCUMENT MANAGEMENT
# ============================================================

@hr_bp.route("/document/<id>/download")
@login_required
def document_download(id):
    session = get_web_session()
    doc = session.query(EmployeeDocumentRecord).filter(EmployeeDocumentRecord.id == id).first()
    if not doc:
        flash("المستند غير موجود", "danger")
        return redirect(url_for("hr.hr_employee_list"))
    flash(f"تحميل المستند: {doc.title}", "info")
    return redirect(url_for("hr.employee_documents", id=doc.employee_id))


@hr_bp.route("/documents/categories/save", methods=["POST"])
@login_required
def document_category_save():
    session = get_web_session()
    cat_id = request.form.get("id", "").strip()
    name_ar = request.form.get("name_ar", "").strip()
    code = request.form.get("code", "").strip()
    if not name_ar or not code:
        flash("الاسم والكود مطلوبان", "danger")
        return redirect(url_for("hr.document_categories"))

    if cat_id:
        cat = session.query(DocumentCategory).filter(DocumentCategory.id == cat_id).first()
        if cat:
            cat.name_ar = name_ar
            cat.code = code
            cat.name_en = request.form.get("name_en", "").strip() or None
            cat.sort_order = int(request.form.get("sort_order", 0))
    else:
        existing = session.query(DocumentCategory).filter(DocumentCategory.code == code).first()
        if existing:
            flash("كود التصنيف موجود مسبقاً", "danger")
            return redirect(url_for("hr.document_categories"))
        cat = DocumentCategory(
            name_ar=name_ar,
            name_en=request.form.get("name_en", "").strip() or None,
            code=code,
            sort_order=int(request.form.get("sort_order", 0)),
            is_active=True,
        )
        session.add(cat)

    session.commit()
    flash("تم حفظ التصنيف بنجاح", "success")
    return redirect(url_for("hr.document_categories"))


@hr_bp.route("/documents/categories/<id>/delete", methods=["POST"])
@login_required
def document_category_delete(id):
    session = get_web_session()
    cat = session.query(DocumentCategory).filter(DocumentCategory.id == id).first()
    if cat:
        from src.web.routes.recycle_bin import add_to_recycle_bin
        add_to_recycle_bin(session, "document_category", cat.id, item_number=cat.name, item_title=cat.name)
        session.delete(cat)
        session.commit()
        flash("تم حذف التصنيف بنجاح", "success")
    return redirect(url_for("hr.document_categories"))


# ============================================================
# CONTRACT DETAIL / DELETE
# ============================================================

@hr_bp.route("/contract/<id>")
@login_required
def contract_detail(id):
    session = get_web_session()
    contract = session.query(Contract).filter(Contract.id == id).first()
    if not contract:
        flash("العقد غير موجود", "danger")
        return redirect(url_for("hr.contracts_list"))
    employee = session.query(Employee).filter(Employee.id == contract.employee_id).first()
    return render_template("hr/contracts_list.html", contracts=[contract])


@hr_bp.route("/contract/<id>/delete", methods=["POST"])
@login_required
def contract_delete(id):
    session = get_web_session()
    contract = session.query(Contract).filter(Contract.id == id).first()
    if contract:
        from src.web.routes.recycle_bin import add_to_recycle_bin
        add_to_recycle_bin(session, "hr_contract", contract.id, item_number=contract.contract_number if hasattr(contract, 'contract_number') else str(id), item_title=contract.title if hasattr(contract, 'title') else str(id))
        session.delete(contract)
        session.commit()
        flash("تم حذف العقد بنجاح", "success")
    return redirect(url_for("hr.contracts_list"))


@hr_bp.route("/contract/<contract_id>/print")
@login_required
def contract_print(contract_id):
    session = get_web_session()
    contract = session.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        flash("العقد غير موجود", "danger")
        return redirect(url_for("hr.contracts_list"))
    employee = contract.employee
    from datetime import datetime
    now_date = datetime.now().strftime('%d/%m/%Y')
    return render_template("hr/contract_print.html", contract=contract, employee=employee, now_date=now_date)


# ============================================================
# DRIVER CONTRACTS (عقود السائقين)
# ============================================================

from src.core.models.hr_models import DriverContract

@hr_bp.route("/driver-contracts")
@login_required
def driver_contracts_list():
    session = get_web_session()
    from src.core.models.base_models import Driver
    contracts = session.query(DriverContract).join(
        Driver, DriverContract.driver_id == Driver.id
    ).order_by(DriverContract.created_at.desc()).all()
    return render_template("hr/driver_contracts_list.html", contracts=contracts)


@hr_bp.route("/driver-contracts/add", methods=["GET", "POST"])
@login_required
def driver_contracts_add():
    session = get_web_session()
    from src.core.models.base_models import Driver
    drivers = session.query(Driver).filter(
        Driver.is_deleted == False,
        Driver.status == "active",
        Driver.approval_status == "approved",
    ).order_by(Driver.created_at.desc()).all()

    if request.method == "POST":
        driver_id = request.form.get("driver_id", "").strip()
        contract_type = request.form.get("contract_type", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        contract_number = request.form.get("contract_number", "").strip() or None

        if not all([driver_id, contract_type, start_date_str]):
            flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
            return render_template("hr/driver_contract_form.html", drivers=drivers, contract=None)

        drv_check = session.query(Driver).filter(Driver.id == driver_id).first()
        if drv_check and (drv_check.approval_status != "approved" or drv_check.status != "active"):
            flash("لا يمكن إنشاء عقد — السائق غير معتمد من المدير التنفيذي", "danger")
            return render_template("hr/driver_contract_form.html", drivers=drivers, contract=None)

        if not contract_number:
            from sqlalchemy import func
            max_num = session.query(func.max(DriverContract.contract_number)).filter(
                DriverContract.contract_number.isnot(None)
            ).scalar()
            if max_num and max_num.startswith("DC"):
                try:
                    num = int(max_num[2:]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            contract_number = f"DC{num:04d}"

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date_str = request.form.get("end_date", "").strip()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

        contract = DriverContract(
            driver_id=driver_id,
            contract_number=contract_number,
            contract_type=contract_type,
            activity_type=request.form.get("activity_type", "").strip() or None,
            start_date=start_date,
            end_date=end_date,
            salary=float(request.form.get("salary") or 0),
            allowances=float(request.form.get("allowances") or 0),
            terms_and_conditions=request.form.get("terms_and_conditions", "").strip() or None,
            approved_by=request.form.get("approved_by", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            status="active",
            created_by=current_user.id,
        )
        session.add(contract)
        session.commit()
        flash(f"تم إضافة عقد السائق بنجاح - رقم {contract_number}", "success")
        return redirect(url_for("hr.driver_contracts_list"))

    return render_template("hr/driver_contract_form.html", drivers=drivers, contract=None)


@hr_bp.route("/driver-contracts/<id>/edit", methods=["GET", "POST"])
@login_required
def driver_contracts_edit(id):
    session = get_web_session()
    from src.core.models.base_models import Driver
    contract = session.query(DriverContract).filter(DriverContract.id == id).first()
    if not contract:
        flash("العقد غير موجود", "danger")
        return redirect(url_for("hr.driver_contracts_list"))

    drivers = session.query(Driver).filter(Driver.is_deleted == False).order_by(Driver.created_at.desc()).all()

    if request.method == "POST":
        contract.driver_id = request.form.get("driver_id", contract.driver_id).strip()
        contract.contract_type = request.form.get("contract_type", contract.contract_type).strip()
        contract.activity_type = request.form.get("activity_type", "").strip() or None
        start_date_str = request.form.get("start_date", "").strip()
        if start_date_str:
            contract.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date_str = request.form.get("end_date", "").strip()
        contract.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
        contract.salary = float(request.form.get("salary") or contract.salary or 0)
        contract.allowances = float(request.form.get("allowances") or contract.allowances or 0)
        contract.terms_and_conditions = request.form.get("terms_and_conditions", "").strip() or None
        contract.approved_by = request.form.get("approved_by", "").strip() or None
        contract.notes = request.form.get("notes", "").strip() or None
        contract.status = request.form.get("status", contract.status)
        session.commit()
        flash("تم تعديل العقد بنجاح", "success")
        return redirect(url_for("hr.driver_contracts_list"))

    return render_template("hr/driver_contract_form.html", drivers=drivers, contract=contract)


@hr_bp.route("/api/driver/<driver_id>")
@login_required
def api_driver_info(driver_id):
    from flask import jsonify
    from src.core.models.base_models import Driver
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        return jsonify({"success": False}), 404
    return jsonify({
        "success": True,
        "id": driver.id,
        "full_name_ar": driver.full_name_ar,
        "driver_number": driver.driver_number,
        "phone": driver.phone or "",
        "license_type": driver.license_type or "",
        "join_date": driver.join_date.strftime('%Y-%m-%d') if driver.join_date else "",
        "national_id": driver.national_id or "",
        "status": driver.status or "active",
        "contract_type": driver.contract_type or "",
        "activity_type": driver.activity_type or "",
        "id_type": driver.id_type or "",
        "id_number": driver.id_number or "",
    })


@hr_bp.route("/driver-contract/<contract_id>/print")
@login_required
def driver_contract_print(contract_id):
    session = get_web_session()
    from src.core.models.hr_models import DriverContract
    from src.core.models.base_models import Driver
    contract = session.query(DriverContract).filter(DriverContract.id == contract_id).first()
    if not contract:
        flash("العقد غير موجود", "danger")
        return redirect(url_for("hr.contracts_list"))
    driver = contract.driver
    from datetime import datetime
    now_date = datetime.now().strftime('%d/%m/%Y')
    return render_template("hr/driver_contract_print.html", contract=contract, driver=driver, now_date=now_date)


# ============================================================
# SHIFT CRUD
# ============================================================

@hr_bp.route("/shifts/save", methods=["POST"])
@login_required
def shift_save():
    session = get_web_session()
    shift_id = request.form.get("shift_id", "").strip()
    name = request.form.get("name", "").strip()
    start_time_str = request.form.get("start_time", "").strip()
    end_time_str = request.form.get("end_time", "").strip()
    notes = request.form.get("notes", "").strip() or None

    if not name or not start_time_str or not end_time_str:
        flash("جميع الحقول المطلوبة يجب ملؤها", "danger")
        return redirect(url_for("hr.shifts_list"))

    if shift_id:
        shift = session.query(WorkShift).filter(WorkShift.id == shift_id).first()
        if shift:
            shift.name = name
            shift.start_time = _parse_time(start_time_str)
            shift.end_time = _parse_time(end_time_str)
            shift.notes = notes
    else:
        shift = WorkShift(
            name=name,
            start_time=_parse_time(start_time_str),
            end_time=_parse_time(end_time_str),
            notes=notes,
            is_active=True,
        )
        session.add(shift)

    session.commit()
    flash("تم حفظ الوردية بنجاح", "success")
    return redirect(url_for("hr.shifts_list"))


@hr_bp.route("/shifts/<id>/delete", methods=["POST"])
@login_required
def shift_delete(id):
    session = get_web_session()
    shift = session.query(WorkShift).filter(WorkShift.id == id).first()
    if shift:
        from src.web.routes.recycle_bin import add_to_recycle_bin
        add_to_recycle_bin(session, "work_shift", shift.id, item_number=shift.name if hasattr(shift, 'name') else str(id), item_title=shift.name if hasattr(shift, 'name') else str(id))
        session.delete(shift)
        session.commit()
        flash("تم حذف الوردية بنجاح", "success")
    return redirect(url_for("hr.shifts_list"))


# ============================================================
# LEAVE DETAIL
# ============================================================


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _parse_date(value):
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def _parse_time(value):
    if not value or not value.strip():
        return None
    try:
        return time.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def _parse_float(value):
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None


def _get_day_name(d):
    days_ar = {
        0: "الإثنين",
        1: "الثلاثاء",
        2: "الأربعاء",
        3: "الخميس",
        4: "الجمعة",
        5: "السبت",
        6: "الأحد",
    }
    return days_ar.get(d.weekday(), "")


# ============================================================
# EMPLOYEE LOANS (سلف الموظفين)
# ============================================================

from src.core.models.hr_models import EmployeeLoan, EmployeeLoanPayment

@hr_bp.route("/loans")
@login_required
def loans_list():
    session = get_web_session()
    status = request.args.get("status", None)
    query = session.query(EmployeeLoan)

    if status:
        query = query.filter(EmployeeLoan.status == status)

    loans = query.order_by(EmployeeLoan.created_at.desc()).all()

    total_amount = sum(l.amount for l in loans)
    total_remaining = sum(l.remaining_amount for l in loans)
    active_loans = sum(1 for l in loans if l.status == "active")

    employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()

    return render_template("hr/loans_list.html",
                         page_title="سلف الموظفين",
                         loans=loans,
                         employees=employees,
                         total_amount=total_amount,
                         total_remaining=total_remaining,
                         active_loans=active_loans,
                         current_status=status)


@hr_bp.route("/loans/add", methods=["GET", "POST"])
@login_required
def loan_add():
    session = get_web_session()
    if request.method == "POST":
        # توليد رقم السلفة
        from sqlalchemy import func
        max_num = session.query(func.max(EmployeeLoan.loan_number)).scalar()
        if max_num and max_num.startswith("LN"):
            try:
                num = int(max_num[2:]) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        loan_number = f"LN{num:04d}"

        employee_id = request.form.get("employee_id")
        amount = float(request.form.get("amount", 0))
        monthly_deduction = float(request.form.get("monthly_deduction", 0))

        loan = EmployeeLoan(
            loan_number=loan_number,
            employee_id=employee_id,
            loan_type=request.form.get("loan_type", "advance"),
            amount=amount,
            remaining_amount=amount,
            monthly_deduction=monthly_deduction,
            loan_date=datetime.strptime(request.form.get("loan_date"), "%Y-%m-%d").date(),
            due_date=datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date() if request.form.get("due_date") else None,
            reason=request.form.get("reason"),
            notes=request.form.get("notes"),
            approved_by=request.form.get("approved_by"),
        )
        session.add(loan)
        session.commit()
        flash(f"تم اضافة سلفة رقم {loan_number} بنجاح", "success")
        return redirect(url_for("hr.loans_list"))

    employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()
    return render_template("hr/loan_form.html",
                         page_title="اضافة سلفة",
                         loan=None,
                         employees=employees)


@hr_bp.route("/loans/<loan_id>/edit", methods=["GET", "POST"])
@login_required
def loan_edit(loan_id):
    session = get_web_session()
    loan = session.query(EmployeeLoan).get(loan_id)
    if not loan:
        flash("السلفة غير موجودة", "danger")
        return redirect(url_for("hr.loans_list"))

    if request.method == "POST":
        loan.loan_type = request.form.get("loan_type", loan.loan_type)
        loan.amount = float(request.form.get("amount", loan.amount))
        loan.monthly_deduction = float(request.form.get("monthly_deduction", loan.monthly_deduction))
        loan.loan_date = datetime.strptime(request.form.get("loan_date"), "%Y-%m-%d").date()
        loan.due_date = datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date() if request.form.get("due_date") else None
        loan.status = request.form.get("status", loan.status)
        loan.reason = request.form.get("reason")
        loan.notes = request.form.get("notes")
        loan.approved_by = request.form.get("approved_by")
        session.commit()
        flash(f"تم تعديل السلفة رقم {loan.loan_number} بنجاح", "success")
        return redirect(url_for("hr.loans_list"))

    employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()
    return render_template("hr/loan_form.html",
                         page_title=f"تعديل سلفة {loan.loan_number}",
                         loan=loan,
                         employees=employees)


@hr_bp.route("/loans/<loan_id>/payment", methods=["POST"])
@login_required
def loan_payment(loan_id):
    session = get_web_session()
    loan = session.query(EmployeeLoan).get(loan_id)
    if not loan:
        flash("السلفة غير موجودة", "danger")
        return redirect(url_for("hr.loans_list"))

    amount = float(request.form.get("amount", 0))
    if amount <= 0:
        flash("المبلغ يجب ان يكون اكبر من صفر", "danger")
        return redirect(url_for("hr.loans_list"))

    # توليد رقم الدفعة
    last_payment = session.query(EmployeeLoanPayment).filter(EmployeeLoanPayment.loan_id == loan.id).count()
    payment = EmployeeLoanPayment(
        loan_id=loan.id,
        payment_number=last_payment + 1,
        amount=amount,
        payment_date=datetime.strptime(request.form.get("payment_date"), "%Y-%m-%d").date(),
        notes=request.form.get("notes"),
    )
    session.add(payment)

    # تحديث المبلغ المتبقي
    loan.remaining_amount = max(0, loan.remaining_amount - amount)
    if loan.remaining_amount <= 0:
        loan.status = "completed"

    session.commit()
    flash(f"تم تسجيل دفعة بقيمة {amount:,.0f} د.ل للسلفة رقم {loan.loan_number}", "success")
    return redirect(url_for("hr.loans_list"))


@hr_bp.route("/loans/<loan_id>/delete", methods=["POST"])
@login_required
def loan_delete(loan_id):
    session = get_web_session()
    loan = session.query(EmployeeLoan).get(loan_id)
    if not loan:
        flash("السلفة غير موجودة", "danger")
        return redirect(url_for("hr.loans_list"))

    loan_number = loan.loan_number
    from src.web.routes.recycle_bin import add_to_recycle_bin
    add_to_recycle_bin(session, "employee_loan", loan.id, item_number=loan_number, item_title=f"سلفة {loan_number}")
    session.delete(loan)
    session.commit()
    flash(f"تم حذف السلفة رقم {loan_number}", "success")
    return redirect(url_for("hr.loans_list"))


@hr_bp.route("/drivers-list")
@login_required
def hr_drivers_list():
    from src.core.models.base_models import Driver
    session = get_web_session()
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    q = session.query(Driver).filter(Driver.is_deleted == False)
    if search:
        q = q.filter(
            (Driver.full_name_ar.ilike(f"%{search}%"))
            | (Driver.driver_number.ilike(f"%{search}%"))
            | (Driver.phone.ilike(f"%{search}%"))
        )
    if status_filter:
        q = q.filter(Driver.status == status_filter)
    drivers = q.order_by(Driver.created_at.desc()).all()
    return render_template("hr/drivers_list_hr.html", drivers=drivers, search=search, status_filter=status_filter)


# ============================================================
# NOTIFICATIONS
# ============================================================

@hr_bp.route("/notifications")
@login_required
def notifications_list():
    session = get_web_session()
    notifications = session.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(100).all()
    unread_count = session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()
    return render_template("hr/notifications.html", notifications=notifications, unread_count=unread_count)


@hr_bp.route("/notifications/read/<id>", methods=["POST"])
@login_required
def notification_read(id):
    session = get_web_session()
    notif = session.query(Notification).filter(
        Notification.id == id,
        Notification.user_id == current_user.id,
    ).first()
    if notif:
        notif.is_read = True
        notif.read_at = datetime.utcnow()
        session.commit()
        if notif.notification_type == "leave_pending_executive" and notif.reference_id:
            return redirect(url_for("hr.leave_list", tab="pending_executive"))
        if notif.notification_type == "finance_claim_pending" and notif.reference_id:
            return redirect(url_for("finance.claim_detail", claim_id=notif.reference_id))
        if notif.notification_type in ("driver_pending_executive", "driver_approved", "driver_rejected", "driver_comment") and notif.reference_id:
            return redirect(url_for("drivers.drivers_detail", id=notif.reference_id))
    return redirect(url_for("hr.notifications_list"))


@hr_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    session = get_web_session()
    session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    session.commit()
    flash("تم تحديد الكل كمقروء", "success")
    return redirect(url_for("hr.notifications_list"))


@hr_bp.route("/notifications/count")
@login_required
def notifications_count():
    session = get_web_session()
    unread_q = session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    )
    count = unread_q.count()
    latest = unread_q.order_by(Notification.created_at.desc()).first()
    payload = {"count": count, "is_admin": bool(current_user.is_admin)}
    if latest:
        payload["latest"] = {
            "title": latest.title or "",
            "message": latest.message or "",
            "type": latest.notification_type or "",
            "url": url_for("hr.notifications_list"),
        }
    return jsonify(payload)
