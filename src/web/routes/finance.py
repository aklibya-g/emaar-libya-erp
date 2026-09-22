from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.marketing_models import (
    FinancialClaim, PaymentReceipt, DriverPayout,
    WorkOrder, WorkOrderBus, MarketingClient, MarketingContract,
    SchoolDriverEntitlement,
)
from src.core.models.base_models import Driver
from sqlalchemy import func, extract, desc
from datetime import date, datetime

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")


def _next_number(session, prefix, table, field):
    last = session.query(table).order_by(desc(table.id)).first()
    if last and getattr(last, field, None):
        try:
            num = int(getattr(last, field).split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    year = date.today().year
    return f"{prefix}-{year}-{num:04d}"


# ============================================================
# DASHBOARD
# ============================================================

@finance_bp.route("/")
@login_required
def finance_dashboard():
    with get_web_session() as session:
        today = date.today()
        current_month = today.month
        current_year = today.year

        total_claims = session.query(FinancialClaim).count()
        pending_claims = session.query(FinancialClaim).filter(
            FinancialClaim.status.in_(["pending", "partially_paid"])
        ).count()
        fully_paid_claims = session.query(FinancialClaim).filter(
            FinancialClaim.status == "fully_paid"
        ).count()

        total_revenue = session.query(func.sum(FinancialClaim.final_value)).scalar() or 0
        total_received = session.query(func.sum(FinancialClaim.received_amount)).scalar() or 0
        total_remaining = session.query(func.sum(FinancialClaim.remaining_amount)).filter(
            FinancialClaim.remaining_amount > 0
        ).scalar() or 0

        month_revenue = session.query(func.sum(FinancialClaim.final_value)).filter(
            extract('month', FinancialClaim.claim_date) == current_month,
            extract('year', FinancialClaim.claim_date) == current_year
        ).scalar() or 0
        month_received = session.query(func.sum(PaymentReceipt.amount_received)).filter(
            extract('month', PaymentReceipt.receipt_date) == current_month,
            extract('year', PaymentReceipt.receipt_date) == current_year,
            PaymentReceipt.status == "confirmed"
        ).scalar() or 0

        total_driver_payouts = session.query(func.sum(DriverPayout.total_amount)).filter(
            DriverPayout.status == "paid"
        ).scalar() or 0
        month_driver_payouts = session.query(func.sum(DriverPayout.total_amount)).filter(
            DriverPayout.status == "paid",
            extract('month', DriverPayout.paid_at) == current_month,
            extract('year', DriverPayout.paid_at) == current_year
        ).scalar() or 0

        net_profit = total_received - total_driver_payouts
        month_profit = month_received - month_driver_payouts

        pending_receipts = session.query(PaymentReceipt).filter(
            PaymentReceipt.status == "draft"
        ).count()
        pending_payouts = session.query(DriverPayout).filter(
            DriverPayout.status == "pending"
        ).count()

        debts_by_client_raw = session.query(
            MarketingClient.name_ar,
            MarketingClient.id,
            func.sum(FinancialClaim.remaining_amount).label("remaining"),
        ).join(
            FinancialClaim, FinancialClaim.client_id == MarketingClient.id
        ).filter(
            FinancialClaim.remaining_amount > 0
        ).group_by(MarketingClient.id, MarketingClient.name_ar).order_by(
            desc(func.sum(FinancialClaim.remaining_amount))
        ).limit(10).all()

        debts_by_client = [{"client_name": r[0], "client_id": r[1], "remaining": r[2]} for r in debts_by_client_raw]

        monthly_data = []
        for i in range(5, -1, -1):
            m = (current_month - i - 1) % 12 + 1
            y = current_year if current_month - i > 0 else current_year - 1
            rev = session.query(func.sum(FinancialClaim.final_value)).filter(
                extract('month', FinancialClaim.claim_date) == m,
                extract('year', FinancialClaim.claim_date) == y
            ).scalar() or 0
            rec = session.query(func.sum(PaymentReceipt.amount_received)).filter(
                extract('month', PaymentReceipt.receipt_date) == m,
                extract('year', PaymentReceipt.receipt_date) == y,
                PaymentReceipt.status == "confirmed"
            ).scalar() or 0
            pay = session.query(func.sum(DriverPayout.total_amount)).filter(
                DriverPayout.status == "paid",
                extract('month', DriverPayout.paid_at) == m,
                extract('year', DriverPayout.paid_at) == y
            ).scalar() or 0
            monthly_data.append({
                "month": m, "year": y,
                "revenue": rev, "received": rec, "payouts": pay,
                "profit": rec - pay
            })

        recent_claims = session.query(FinancialClaim).order_by(
            desc(FinancialClaim.created_at)
        ).limit(10).all()

        return render_template("finance/dashboard.html",
            page_title="لوحة تحكم المالية",
            total_claims=total_claims,
            pending_claims=pending_claims,
            fully_paid_claims=fully_paid_claims,
            total_revenue=total_revenue,
            total_received=total_received,
            total_remaining=total_remaining,
            month_revenue=month_revenue,
            month_received=month_received,
            total_driver_payouts=total_driver_payouts,
            month_driver_payouts=month_driver_payouts,
            net_profit=net_profit,
            month_profit=month_profit,
            pending_receipts=pending_receipts,
            pending_payouts=pending_payouts,
            debts_by_client=debts_by_client,
            monthly_data=monthly_data,
            recent_claims=recent_claims,
            today=today,
        )


# ============================================================
# FINANCE ALERTS API (تنبيهات التحصيل)
# ============================================================

@finance_bp.route("/api/alerts")
@login_required
def finance_alerts():
    with get_web_session() as session:
        today = date.today()

        pending_claims = session.query(FinancialClaim).filter(
            FinancialClaim.status.in_(["pending", "partially_paid"]),
            FinancialClaim.remaining_amount > 0,
        ).order_by(desc(FinancialClaim.claim_date)).all()

        alerts = []
        for claim in pending_claims:
            client = session.query(MarketingClient).filter(MarketingClient.id == claim.client_id).first()
            days_old = (today - claim.claim_date).days if claim.claim_date else 0
            severity = "info"
            if days_old > 30:
                severity = "danger"
            elif days_old > 14:
                severity = "warning"
            alerts.append({
                "id": claim.id,
                "claim_number": claim.claim_number,
                "client_name": client.name_ar if client else "-",
                "remaining": claim.remaining_amount,
                "claim_date": claim.claim_date.strftime("%Y-%m-%d") if claim.claim_date else "",
                "days_old": days_old,
                "severity": severity,
                "order_number": claim.order_number or "-",
            })

        return jsonify({"alerts": alerts, "count": len(alerts)})


# ============================================================
# FINANCIAL CLAIMS (المطالبات المالية)
# ============================================================

@finance_bp.route("/claims")
@login_required
def claims_list():
    with get_web_session() as session:
        status = request.args.get("status", None)
        client_id = request.args.get("client_id", None)
        month = request.args.get("month", None)
        year = request.args.get("year", None)

        query = session.query(FinancialClaim)
        if status:
            query = query.filter(FinancialClaim.status == status)
        if client_id:
            query = query.filter(FinancialClaim.client_id == client_id)
        if month:
            query = query.filter(extract('month', FinancialClaim.claim_date) == int(month))
        if year:
            query = query.filter(extract('year', FinancialClaim.claim_date) == int(year))

        claims = query.order_by(desc(FinancialClaim.claim_date)).all()
        clients = session.query(MarketingClient).filter(MarketingClient.is_active == True).order_by(MarketingClient.name_ar).all()

        return render_template("finance/claims_list.html",
            page_title="المطالبات المالية",
            claims=claims,
            clients=clients,
            current_status=status,
            current_client=client_id,
            current_month=month,
            current_year=year,
        )


@finance_bp.route("/claims/<claim_id>")
@login_required
def claim_detail(claim_id):
    with get_web_session() as session:
        claim = session.query(FinancialClaim).filter(FinancialClaim.id == claim_id).first()
        if not claim:
            flash("المطالبة غير موجودة", "danger")
            return redirect(url_for("finance.claims_list"))

        receipts = session.query(PaymentReceipt).filter(
            PaymentReceipt.financial_claim_id == claim_id
        ).order_by(desc(PaymentReceipt.receipt_date)).all()

        return render_template("finance/claim_detail.html",
            page_title=f"المطالبة المالية - {claim.claim_number}",
            claim=claim,
            receipts=receipts,
        )


@finance_bp.route("/claims/<claim_id>/add-receipt", methods=["GET", "POST"])
@login_required
def add_receipt(claim_id):
    with get_web_session() as session:
        claim = session.query(FinancialClaim).filter(FinancialClaim.id == claim_id).first()
        if not claim:
            flash("المطالبة غير موجودة", "danger")
            return redirect(url_for("finance.claims_list"))

        if request.method == "POST":
            amount = float(request.form.get("amount_received", 0) or 0)
            if amount <= 0:
                flash("المبلغ يجب ان يكون اكبر من صفر", "danger")
                return redirect(url_for("finance.add_receipt", claim_id=claim_id))

            if amount > claim.remaining_amount:
                flash(f"المبلغ ({amount}) اكبر من المتبقي ({claim.remaining_amount})", "danger")
                return redirect(url_for("finance.add_receipt", claim_id=claim_id))

            receipt = PaymentReceipt(
                receipt_number=_next_number(session, "REC", PaymentReceipt, "receipt_number"),
                financial_claim_id=claim.id,
                work_order_id=claim.work_order_id,
                client_id=claim.client_id,
                receipt_date=date.today(),
                amount_received=amount,
                payment_method=request.form.get("payment_method", "cash"),
                payment_reference=request.form.get("payment_reference", "").strip() or None,
                bank_name=request.form.get("bank_name", "").strip() or None,
                notes=request.form.get("notes", "").strip() or None,
                status="draft",
                created_by=current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username,
            )
            session.add(receipt)
            session.commit()
            flash(f"تم اضافة سند الاستلام {receipt.receipt_number}", "success")
            return redirect(url_for("finance.claim_detail", claim_id=claim_id))

        return render_template("finance/add_receipt.html",
            page_title="تسجيل استلام مبلغ",
            claim=claim,
        )


@finance_bp.route("/receipts/<receipt_id>/confirm", methods=["POST"])
@login_required
def confirm_receipt(receipt_id):
    with get_web_session() as session:
        receipt = session.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
        if not receipt:
            flash("سند الاستلام غير موجود", "danger")
            return redirect(url_for("finance.claims_list"))

        receipt.status = "confirmed"
        receipt.confirmed_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
        receipt.confirmed_at = datetime.utcnow()

        claim = session.query(FinancialClaim).filter(FinancialClaim.id == receipt.financial_claim_id).first()
        if claim:
            total_received = session.query(func.sum(PaymentReceipt.amount_received)).filter(
                PaymentReceipt.financial_claim_id == claim.id,
                PaymentReceipt.status == "confirmed"
            ).scalar() or 0
            total_received += receipt.amount_received

            claim.received_amount = total_received
            claim.remaining_amount = max(0, claim.final_value - total_received)
            if claim.remaining_amount <= 0:
                claim.is_fully_paid = True
                claim.status = "fully_paid"
            else:
                claim.status = "partially_paid"

        session.commit()
        flash(f"تم تأكيد سند الاستلام {receipt.receipt_number}", "success")
        return redirect(url_for("finance.claim_detail", claim_id=receipt.financial_claim_id))


@finance_bp.route("/claims/<claim_id>/approve", methods=["POST"])
@login_required
def approve_claim(claim_id):
    if not current_user.is_finance and not current_user.is_admin:
        flash("ليس لديك صلاحية لاعتماد المطالبات المالية", "danger")
        return redirect(url_for("finance.claim_detail", claim_id=claim_id))

    with get_web_session() as session:
        claim = session.query(FinancialClaim).filter(FinancialClaim.id == claim_id).first()
        if not claim:
            flash("المطالبة غير موجودة", "danger")
            return redirect(url_for("finance.claims_list"))

        wo = session.query(WorkOrder).filter(WorkOrder.id == claim.work_order_id).first()
        if wo:
            wo.finance_approved = True
            wo.finance_approved_at = datetime.utcnow()
            wo.finance_approved_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
            if wo.finance_approved and wo.marketing_approved and wo.movement_approved:
                wo.status = "finance_approved"

        if claim.status == "pending":
            claim.status = "collecting"
        session.commit()
        flash("تم اعتماد المطالبة المالية", "success")
        return redirect(url_for("finance.claim_detail", claim_id=claim_id))


@finance_bp.route("/claims/<claim_id>/print")
@login_required
def claim_print(claim_id):
    with get_web_session() as session:
        claim = session.query(FinancialClaim).filter(FinancialClaim.id == claim_id).first()
        if not claim:
            flash("المطالبة غير موجودة", "danger")
            return redirect(url_for("finance.claims_list"))

        receipts = session.query(PaymentReceipt).filter(
            PaymentReceipt.financial_claim_id == claim_id
        ).order_by(desc(PaymentReceipt.receipt_date)).all()

        wo = session.query(WorkOrder).filter(WorkOrder.id == claim.work_order_id).first()
        finance_approved_by = wo.finance_approved_by if wo else None
        finance_approved_at = wo.finance_approved_at if wo else None

        return render_template("finance/claim_print.html",
            claim=claim,
            receipts=receipts,
            finance_approved_by=finance_approved_by,
            finance_approved_at=finance_approved_at,
            now_date=date.today(),
        )


# ============================================================
# RECEIPTS LIST (سندات الاستلام)
# ============================================================

@finance_bp.route("/receipts")
@login_required
def receipts_list():
    with get_web_session() as session:
        status = request.args.get("status", None)
        query = session.query(PaymentReceipt)
        if status:
            query = query.filter(PaymentReceipt.status == status)
        receipts = query.order_by(desc(PaymentReceipt.receipt_date)).all()
        return render_template("finance/receipts_list.html",
            page_title="سندات الاستلام",
            receipts=receipts,
            current_status=status,
        )


# ============================================================
# DRIVER PAYOUTS (سندات صرف السائقين)
# ============================================================

@finance_bp.route("/payouts")
@login_required
def payouts_list():
    with get_web_session() as session:
        status = request.args.get("status", None)
        query = session.query(DriverPayout)
        if status:
            query = query.filter(DriverPayout.status == status)
        payouts = query.order_by(desc(DriverPayout.created_at)).all()

        total_pending = session.query(func.sum(DriverPayout.total_amount)).filter(
            DriverPayout.status == "pending"
        ).scalar() or 0
        total_paid = session.query(func.sum(DriverPayout.total_amount)).filter(
            DriverPayout.status == "paid"
        ).scalar() or 0

        return render_template("finance/payouts_list.html",
            page_title="سندات صرف السائقين",
            payouts=payouts,
            current_status=status,
            total_pending=total_pending,
            total_paid=total_paid,
        )


@finance_bp.route("/payouts/<payout_id>/pay", methods=["POST"])
@login_required
def pay_payout(payout_id):
    with get_web_session() as session:
        payout = session.query(DriverPayout).filter(DriverPayout.id == payout_id).first()
        if not payout:
            flash("سند الصرف غير موجود", "danger")
            return redirect(url_for("finance.payouts_list"))

        payout.status = "paid"
        payout.payment_method = request.form.get("payment_method", "cash")
        payout.paid_at = date.today()
        payout.paid_by = current_user.full_name_ar if hasattr(current_user, 'full_name_ar') else current_user.username
        session.commit()
        flash(f"تم صرف {payout.total_amount} د.ل للسائق {payout.driver_name}", "success")
        return redirect(url_for("finance.payouts_list"))


# ============================================================
# DEBTS (ديون الجهات)
# ============================================================

@finance_bp.route("/debts")
@login_required
def debts():
    with get_web_session() as session:
        client_id = request.args.get("client_id", None)

        query = session.query(
            MarketingClient.id,
            MarketingClient.name_ar,
            func.count(FinancialClaim.id).label("claims_count"),
            func.sum(FinancialClaim.final_value).label("total_value"),
            func.sum(FinancialClaim.received_amount).label("total_received"),
            func.sum(FinancialClaim.remaining_amount).label("total_remaining"),
        ).join(
            FinancialClaim, FinancialClaim.client_id == MarketingClient.id
        ).filter(
            FinancialClaim.remaining_amount > 0
        ).group_by(MarketingClient.id, MarketingClient.name_ar)

        if client_id:
            query = query.filter(MarketingClient.id == client_id)

        debts_data = query.order_by(desc(func.sum(FinancialClaim.remaining_amount))).all()

        total_debts = sum(d[5] or 0 for d in debts_data)
        total_received = sum(d[4] or 0 for d in debts_data)

        clients = session.query(MarketingClient).filter(MarketingClient.is_active == True).order_by(MarketingClient.name_ar).all()

        return render_template("finance/debts.html",
            page_title="ديون الجهات",
            debts_data=debts_data,
            total_debts=total_debts,
            total_received=total_received,
            clients=clients,
            current_client=client_id,
        )


@finance_bp.route("/debts/client/<client_id>")
@login_required
def client_debt_detail(client_id):
    with get_web_session() as session:
        client = session.query(MarketingClient).filter(MarketingClient.id == client_id).first()
        if not client:
            flash("الجهة غير موجودة", "danger")
            return redirect(url_for("finance.debts"))

        claims = session.query(FinancialClaim).filter(
            FinancialClaim.client_id == client_id,
            FinancialClaim.remaining_amount > 0
        ).order_by(desc(FinancialClaim.claim_date)).all()

        receipts = session.query(PaymentReceipt).filter(
            PaymentReceipt.client_id == client_id,
            PaymentReceipt.status == "confirmed"
        ).order_by(desc(PaymentReceipt.receipt_date)).all()

        total_remaining = sum(c.remaining_amount for c in claims)

        return render_template("finance/client_debt_detail.html",
            page_title=f"مديونية - {client.name_ar}",
            client=client,
            claims=claims,
            receipts=receipts,
            total_remaining=total_remaining,
        )


# ============================================================
# REPORTS (التقارير المالية)
# ============================================================

@finance_bp.route("/reports")
@login_required
def reports():
    with get_web_session() as session:
        today = date.today()
        current_year = today.year

        monthly_profits = []
        for m in range(1, 13):
            revenue = session.query(func.sum(FinancialClaim.final_value)).filter(
                extract('month', FinancialClaim.claim_date) == m,
                extract('year', FinancialClaim.claim_date) == current_year
            ).scalar() or 0
            received = session.query(func.sum(PaymentReceipt.amount_received)).filter(
                extract('month', PaymentReceipt.receipt_date) == m,
                extract('year', PaymentReceipt.receipt_date) == current_year,
                PaymentReceipt.status == "confirmed"
            ).scalar() or 0
            payouts = session.query(func.sum(DriverPayout.total_amount)).filter(
                DriverPayout.status == "paid",
                extract('month', DriverPayout.paid_at) == m,
                extract('year', DriverPayout.paid_at) == current_year
            ).scalar() or 0
            monthly_profits.append({
                "month": m, "revenue": revenue, "received": received,
                "payouts": payouts, "profit": received - payouts
            })

        driver_shares = session.query(
            DriverPayout.driver_name,
            func.sum(DriverPayout.total_amount).label("total"),
            func.count(DriverPayout.id).label("count")
        ).filter(
            DriverPayout.status == "paid",
            extract('year', DriverPayout.paid_at) == current_year
        ).group_by(DriverPayout.driver_name).order_by(
            desc(func.sum(DriverPayout.total_amount))
        ).all()

        total_revenue = sum(p["revenue"] for p in monthly_profits)
        total_received = sum(p["received"] for p in monthly_profits)
        total_payouts = sum(p["payouts"] for p in monthly_profits)
        total_profit = total_received - total_payouts

        return render_template("finance/reports.html",
            page_title="التقارير المالية",
            monthly_profits=monthly_profits,
            driver_shares=driver_shares,
            total_revenue=total_revenue,
            total_received=total_received,
            total_payouts=total_payouts,
            total_profit=total_profit,
            current_year=current_year,
        )


# ============================================================
# AUTO-GENERATE CLAIMS (توليد مطالبات تلقائية)
# ============================================================

@finance_bp.route("/generate-claims", methods=["POST"])
@login_required
def generate_claims():
    with get_web_session() as session:
        approved_orders = session.query(WorkOrder).filter(
            WorkOrder.movement_approved == True,
            WorkOrder.finance_approved == False,
            WorkOrder.is_deleted == False,
            WorkOrder.status.in_(["movement_approved", "marketing_approved"])
        ).all()

        created = 0
        for wo in approved_orders:
            existing = session.query(FinancialClaim).filter(
                FinancialClaim.work_order_id == wo.id
            ).first()
            if existing:
                continue

            client = session.query(MarketingClient).filter(MarketingClient.id == wo.client_id).first()
            route_parts = []
            if wo.trip_from:
                route_parts.append(wo.trip_from)
            if wo.trip_to:
                route_parts.append(wo.trip_to)
            route_desc = " ← ".join(route_parts) if route_parts else wo.destination or "-"

            claim = FinancialClaim(
                claim_number=_next_number(session, "FC", FinancialClaim, "claim_number"),
                work_order_id=wo.id,
                client_id=wo.client_id,
                contract_id=wo.contract_id,
                claim_date=date.today(),
                order_number=wo.order_number,
                destination=wo.destination,
                contact_phone=wo.contact_phone,
                trip_route=wo.trip_route,
                trip_from=wo.trip_from,
                trip_to=wo.trip_to,
                route_description=route_desc,
                duration_days=wo.duration_days or 1,
                departure_date=wo.departure_date,
                return_date=wo.return_date,
                bus_count=wo.bus_count_requested or 0,
                trip_type=wo.trip_type or "internal",
                bus_rental_value=wo.bus_rental_value or 0,
                bus_maintenance_value=wo.bus_maintenance_value or 0,
                driver_transport_value=wo.driver_transport_value or 0,
                trip_price=wo.trip_price or 0,
                estimated_distance=wo.estimated_distance,
                total_value=wo.total_value or 0,
                adjustment_percent=wo.adjustment_percent,
                adjustment_value=wo.adjustment_value or 0,
                adjustment_type=wo.adjustment_type,
                executive_discount_value=wo.executive_discount_value or 0,
                final_value=wo.final_value or wo.total_value or 0,
                remaining_amount=wo.final_value or wo.total_value or 0,
                status="pending",
                created_by="النظام",
            )
            session.add(claim)
            created += 1

        session.commit()
        flash(f"تم توليد {created} مطالبة مالية جديدة", "success")
        return redirect(url_for("finance.claims_list"))
