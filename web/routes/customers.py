from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import Customer
from src.core.repositories.base_repository import BaseRepository

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


@customers_bp.route("/")
@login_required
def customers_list():
    search = request.args.get("search", "").strip()
    with session_scope() as session:
        q = session.query(Customer).filter(Customer.is_deleted == False)
        if search:
            q = q.filter(
                (Customer.name_ar.ilike(f"%{search}%")) |
                (Customer.customer_number.ilike(f"%{search}%")) |
                (Customer.phone.ilike(f"%{search}%")) |
                (Customer.company_name.ilike(f"%{search}%"))
            )
        customers = q.order_by(Customer.created_at.desc()).all()
    return render_template("customers/list.html", customers=customers, search=search)


@customers_bp.route("/add", methods=["GET", "POST"])
@login_required
def customers_add():
    with session_scope() as session:
        if request.method == "POST":
            customer_number = request.form.get("customer_number", "").strip()
            name_ar = request.form.get("name_ar", "").strip()
            if not customer_number or not name_ar:
                flash("رقم العميل والاسم بالعربي مطلوبان", "danger")
                return render_template("customers/form.html", customer=None)

            repo = BaseRepository(session, Customer)
            customer = repo.create(
                customer_number=customer_number,
                name_ar=name_ar,
                name_en=request.form.get("name_en", "").strip() or None,
                company_name=request.form.get("company_name", "").strip() or None,
                customer_type=request.form.get("customer_type", "individual"),
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                city=request.form.get("city", "").strip() or None,
                country=request.form.get("country", "Libya").strip() or "Libya",
                notes=request.form.get("notes", "").strip() or None,
                status=request.form.get("status", "active"),
                created_by=current_user.id,
            )
            flash(f"تم إضافة العميل {name_ar} بنجاح", "success")
            return redirect(url_for("customers.customers_detail", id=customer.id))

    return render_template("customers/form.html", customer=None)


@customers_bp.route("/<id>")
@login_required
def customers_detail(id):
    with session_scope() as session:
        customer = session.query(Customer).filter(Customer.id == id, Customer.is_deleted == False).first()
        if not customer:
            flash("العميل غير موجود", "danger")
            return redirect(url_for("customers.customers_list"))
    return render_template("customers/detail.html", customer=customer)


@customers_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def customers_edit(id):
    with session_scope() as session:
        customer = session.query(Customer).filter(Customer.id == id, Customer.is_deleted == False).first()
        if not customer:
            flash("العميل غير موجود", "danger")
            return redirect(url_for("customers.customers_list"))

        if request.method == "POST":
            name_ar = request.form.get("name_ar", "").strip()
            if not name_ar:
                flash("الاسم بالعربي مطلوب", "danger")
                return render_template("customers/form.html", customer=customer)

            repo = BaseRepository(session, Customer)
            repo.update(id,
                customer_number=request.form.get("customer_number", "").strip() or customer.customer_number,
                name_ar=name_ar,
                name_en=request.form.get("name_en", "").strip() or None,
                company_name=request.form.get("company_name", "").strip() or None,
                customer_type=request.form.get("customer_type", "individual"),
                phone=request.form.get("phone", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                city=request.form.get("city", "").strip() or None,
                country=request.form.get("country", "Libya").strip() or "Libya",
                notes=request.form.get("notes", "").strip() or None,
                status=request.form.get("status", "active"),
                updated_by=current_user.id,
            )
            flash(f"تم تعديل بيانات العميل {name_ar} بنجاح", "success")
            return redirect(url_for("customers.customers_detail", id=id))

    return render_template("customers/form.html", customer=customer)


@customers_bp.route("/<id>/delete", methods=["POST"])
@login_required
def customers_delete(id):
    with session_scope() as session:
        repo = BaseRepository(session, Customer)
        if repo.delete(id, soft=True):
            flash("تم حذف العميل بنجاح", "success")
        else:
            flash("لم يتم العثور على العميل", "danger")
    return redirect(url_for("customers.customers_list"))
