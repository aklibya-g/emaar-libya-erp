from flask import Blueprint, render_template
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Employee, Driver, Customer, Department, Warehouse,
    Correspondence, CorrespondenceStatus, User,
)
from sqlalchemy import func, desc

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def dashboard_view():
    with session_scope() as session:
        employee_count = session.query(Employee).filter(Employee.is_deleted == False).count()
        driver_count = session.query(Driver).filter(Driver.is_deleted == False).count()
        customer_count = session.query(Customer).filter(Customer.is_deleted == False).count()
        department_count = session.query(Department).filter(Department.is_deleted == False).count()
        warehouse_count = session.query(Warehouse).filter(Warehouse.is_deleted == False).count()

        total_correspondence = session.query(Correspondence).filter(Correspondence.is_deleted == False).count()
        incoming_count = session.query(Correspondence).filter(
            Correspondence.is_deleted == False, Correspondence.direction == "IN"
        ).count()
        outgoing_count = session.query(Correspondence).filter(
            Correspondence.is_deleted == False, Correspondence.direction == "OUT"
        ).count()
        draft_count = session.query(Correspondence).filter(
            Correspondence.is_deleted == False, Correspondence.is_archived == False
        ).count()

        from datetime import date
        overdue_count = session.query(Correspondence).filter(
            Correspondence.is_deleted == False,
            Correspondence.is_archived == False,
            Correspondence.due_date < date.today(),
        ).count()

        recent_correspondence = session.query(Correspondence).filter(
            Correspondence.is_deleted == False
        ).order_by(desc(Correspondence.created_at)).limit(10).all()

        from src.modules.correspondence.service import CorrespondenceService
        corr_service = CorrespondenceService(session)
        stats = corr_service.get_statistics()
        monthly_trend = corr_service.get_monthly_trend(6)

    return render_template("dashboard/index.html",
        employee_count=employee_count,
        driver_count=driver_count,
        customer_count=customer_count,
        department_count=department_count,
        warehouse_count=warehouse_count,
        total_correspondence=total_correspondence,
        incoming_count=incoming_count,
        outgoing_count=outgoing_count,
        draft_count=draft_count,
        overdue_count=overdue_count,
        recent_correspondence=recent_correspondence,
        stats=stats,
        monthly_trend=monthly_trend,
    )
