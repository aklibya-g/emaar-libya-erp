from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required
from src.core.database.connection import session_scope
from src.core.models.base_models import Department
from src.modules.reports.correspondence_reports import CorrespondenceReports
from src.modules.correspondence.service import CorrespondenceService
from src.core.models.base_models import Employee, Driver, Warehouse, Item

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def reports_index():
    return render_template("reports/index.html")


@reports_bp.route("/correspondence")
@login_required
def reports_correspondence():
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    department_id = request.args.get("department_id", "").strip()

    with session_scope() as session:
        reports = CorrespondenceReports(session)
        from datetime import date as dt_date
        df = dt_date.fromisoformat(date_from) if date_from else None
        dt = dt_date.fromisoformat(date_to) if date_to else None
        summary = reports.correspondence_summary(date_from=df, date_to=dt, department_id=department_id or None)
        dept_stats = reports.department_statistics()
        emp_workload = reports.employee_workload()
        overdue = reports.overdue_report()
        departments = session.query(Department).filter(Department.is_deleted == False).all()

    return render_template("reports/correspondence.html",
        summary=summary, dept_stats=dept_stats, emp_workload=emp_workload,
        overdue=overdue, departments=departments,
        date_from=date_from, date_to=date_to, department_id=department_id)


@reports_bp.route("/employees")
@login_required
def reports_employees():
    with session_scope() as session:
        employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()
        total = len(employees)
        departments = session.query(Department).filter(Department.is_deleted == False).all()
        dept_counts = {}
        for dept in departments:
            count = sum(1 for e in employees if e.department_id == dept.id)
            if count > 0:
                dept_counts[dept.name_ar] = count
    return render_template("reports/employees.html", employees=employees, total=total, dept_counts=dept_counts, departments=departments)


@reports_bp.route("/drivers")
@login_required
def reports_drivers():
    with session_scope() as session:
        drivers = session.query(Driver).filter(Driver.is_deleted == False).all()
        active = sum(1 for d in drivers if d.status == "active")
        inactive = len(drivers) - active
    return render_template("reports/index.html", drivers=drivers, active=active, inactive=inactive)


@reports_bp.route("/warehouses")
@login_required
def reports_warehouses():
    with session_scope() as session:
        warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).all()
        items = session.query(Item).filter(Item.is_deleted == False).all()
        total_items = len(items)
        low_stock = sum(1 for i in items if i.current_quantity <= i.min_quantity and i.min_quantity > 0)
    return render_template("reports/index.html", warehouses=warehouses, items=items, total_items=total_items, low_stock=low_stock)
