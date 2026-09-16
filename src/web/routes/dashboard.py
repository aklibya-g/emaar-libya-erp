from flask import Blueprint, render_template
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import (
    Employee, Driver, Customer, Department, Warehouse,
    Correspondence, CorrespondenceStatus, User,
)
from src.core.models.hr_models import LeaveRequest, LeaveType
from sqlalchemy import func, desc
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def dashboard_view():
    session = get_web_session()
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
    from src.modules.correspondence.workflow import CorrespondenceWorkflow
    corr_service = CorrespondenceService(session)
    stats = corr_service.get_statistics()
    monthly_trend = corr_service.get_monthly_trend(6)
    workflow = CorrespondenceWorkflow(session)

    pending_leaves_count = session.query(LeaveRequest).filter(
        LeaveRequest.status == "pending"
    ).count()

    approved_leaves_count = session.query(LeaveRequest).filter(
        LeaveRequest.status == "approved"
    ).count()

    rejected_leaves_count = session.query(LeaveRequest).filter(
        LeaveRequest.status == "rejected"
    ).count()

    from src.core.models.base_models import Notification
    unread_notifications = session.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()

    from datetime import datetime, timedelta
    from src.core.models.hr_models import AttendanceApproval
    from src.core.models.marketing_models import Trip, WorkOrder
    from sqlalchemy import extract

    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year

    from src.core.models.marketing_models import FinancialClaim, PaymentReceipt, DriverPayout
    pending_finance_claims = session.query(FinancialClaim).filter(
        FinancialClaim.status.in_(["pending", "partially_paid"])
    ).count()
    pending_finance_amount = session.query(func.sum(FinancialClaim.remaining_amount)).filter(
        FinancialClaim.status.in_(["pending", "partially_paid"])
    ).scalar() or 0
    pending_driver_payouts = session.query(DriverPayout).filter(
        DriverPayout.status == "pending"
    ).count()

    work_order_alerts = []
    draft_orders = session.query(WorkOrder).filter(
        WorkOrder.status == "draft",
        WorkOrder.is_deleted == False
    ).order_by(WorkOrder.created_at.desc()).limit(20).all()
    for order in draft_orders:
        needed = []
        if not order.marketing_approved:
            needed.append("التسويق")
        if not order.movement_approved:
            needed.append("الحركة")
        if not order.finance_approved:
            needed.append("المالي")
        if not order.executive_approved:
            needed.append("المدير التنفيذي")
        if needed:
            work_order_alerts.append({
                "id": order.id,
                "order_number": order.order_number,
                "needed": ", ".join(needed),
            })

    approved_trips = 0
    unapproved_trips = 0

    school_trips_count = session.query(func.count(Trip.id)).filter(
        Trip.trip_type == "school",
        extract('month', Trip.trip_date) == current_month,
        extract('year', Trip.trip_date) == current_year,
    ).scalar() or 0

    trip_marketing = session.query(AttendanceApproval).filter(
        AttendanceApproval.year == current_year,
        AttendanceApproval.month == current_month,
        AttendanceApproval.person_type == "trips_marketing",
        AttendanceApproval.executive_approved == True,
    ).first()
    trip_executive = session.query(AttendanceApproval).filter(
        AttendanceApproval.year == current_year,
        AttendanceApproval.month == current_month,
        AttendanceApproval.person_type == "trips_executive",
        AttendanceApproval.hr_approved == True,
    ).first()

    total_trips_month = session.query(func.count(Trip.id)).filter(
        extract('month', Trip.trip_date) == current_month,
        extract('year', Trip.trip_date) == current_year,
    ).scalar() or 0

    if trip_marketing and trip_executive:
        approved_trips = total_trips_month
        unapproved_trips = 0
    else:
        unapproved_trips = total_trips_month
        approved_trips = 0

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
        workflow=workflow,
        pending_leaves=pending_leaves_count,
        approved_leaves=approved_leaves_count,
        rejected_leaves=rejected_leaves_count,
        unread_notifications=unread_notifications,
        approved_trips=approved_trips,
        unapproved_trips=unapproved_trips,
        total_trips_month=total_trips_month,
        work_order_alerts=work_order_alerts,
        pending_finance_claims=pending_finance_claims,
        pending_finance_amount=pending_finance_amount,
        pending_driver_payouts=pending_driver_payouts,
        school_trips_count=school_trips_count,
        today=date.today(),
    )
