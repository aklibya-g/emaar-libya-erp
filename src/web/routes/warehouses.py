from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import Warehouse, Item, StockTransaction, ItemCategory, ItemUnit
from src.core.repositories.base_repository import BaseRepository
from datetime import date

warehouses_bp = Blueprint("warehouses", __name__, url_prefix="/warehouses")


@warehouses_bp.route("/")
@login_required
def warehouses_list():
    session = get_web_session()
    warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).order_by(Warehouse.created_at.desc()).all()
    return render_template("warehouses/list.html", warehouses=warehouses)


@warehouses_bp.route("/items")
@login_required
def warehouses_items():
    search = request.args.get("search", "").strip()
    warehouse_id = request.args.get("warehouse_id", "").strip()
    session = get_web_session()
    q = session.query(Item).filter(Item.is_deleted == False)
    if search:
        q = q.filter(
            (Item.name_ar.ilike(f"%{search}%")) |
            (Item.code.ilike(f"%{search}%"))
        )
    if warehouse_id:
        q = q.filter(Item.warehouse_id == warehouse_id)
    items = q.order_by(Item.created_at.desc()).all()
    warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).all()
    return render_template("warehouses/items.html", items=items, warehouses=warehouses, search=search, warehouse_id=warehouse_id)


@warehouses_bp.route("/items/add", methods=["GET", "POST"])
@login_required
def warehouses_item_add():
    session = get_web_session()
    warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).all()
    categories = session.query(ItemCategory).filter(ItemCategory.is_active == True).all()
    units = session.query(ItemUnit).filter(ItemUnit.is_active == True).all()

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name_ar = request.form.get("name_ar", "").strip()
        if not code or not name_ar:
            flash("كود الصنف والاسم بالعربي مطلوبان", "danger")
            return render_template("warehouses/item_form.html", warehouses=warehouses, categories=categories, units=units, item=None)

        repo = BaseRepository(session, Item)
        item = repo.create(
            code=code,
            name_ar=name_ar,
            name_en=request.form.get("name_en", "").strip() or None,
            category_id=request.form.get("category_id", "").strip() or None,
            unit_id=request.form.get("unit_id", "").strip() or None,
            warehouse_id=request.form.get("warehouse_id", "").strip() or None,
            supplier_id=request.form.get("supplier_id", "").strip() or None,
            min_quantity=float(request.form.get("min_quantity") or 0),
            max_quantity=float(request.form.get("max_quantity") or 0),
            current_quantity=float(request.form.get("current_quantity") or 0),
            unit_price=float(request.form.get("unit_price") or 0),
            storage_location=request.form.get("storage_location", "").strip() or None,
            shelf_number=request.form.get("shelf_number", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            status=request.form.get("status", "active"),
            created_by=current_user.id,
        )
        session.commit()
        flash(f"تم إضافة الصنف {name_ar} بنجاح", "success")
        return redirect(url_for("warehouses.warehouses_items"))

    return render_template("warehouses/item_form.html", warehouses=warehouses, categories=categories, units=units, item=None)


@warehouses_bp.route("/items/<id>/edit", methods=["GET", "POST"])
@login_required
def warehouses_item_edit(id):
    session = get_web_session()
    item = session.query(Item).filter(Item.id == id, Item.is_deleted == False).first()
    if not item:
        flash("الصنف غير موجود", "danger")
        return redirect(url_for("warehouses.warehouses_items"))

    warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).all()
    categories = session.query(ItemCategory).filter(ItemCategory.is_active == True).all()
    units = session.query(ItemUnit).filter(ItemUnit.is_active == True).all()

    if request.method == "POST":
        name_ar = request.form.get("name_ar", "").strip()
        if not name_ar:
            flash("الاسم بالعربي مطلوب", "danger")
            return render_template("warehouses/item_form.html", warehouses=warehouses, categories=categories, units=units, item=item)

        repo = BaseRepository(session, Item)
        repo.update(id,
            code=request.form.get("code", "").strip() or item.code,
            name_ar=name_ar,
            name_en=request.form.get("name_en", "").strip() or None,
            category_id=request.form.get("category_id", "").strip() or None,
            unit_id=request.form.get("unit_id", "").strip() or None,
            warehouse_id=request.form.get("warehouse_id", "").strip() or None,
            supplier_id=request.form.get("supplier_id", "").strip() or None,
            min_quantity=float(request.form.get("min_quantity") or 0),
            max_quantity=float(request.form.get("max_quantity") or 0),
            current_quantity=float(request.form.get("current_quantity") or 0),
            unit_price=float(request.form.get("unit_price") or 0),
            storage_location=request.form.get("storage_location", "").strip() or None,
            shelf_number=request.form.get("shelf_number", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            status=request.form.get("status", "active"),
            updated_by=current_user.id,
        )
        session.commit()
        flash(f"تم تعديل الصنف {name_ar} بنجاح", "success")
        return redirect(url_for("warehouses.warehouses_items"))

    return render_template("warehouses/item_form.html", warehouses=warehouses, categories=categories, units=units, item=item)


@warehouses_bp.route("/items/<id>/delete", methods=["POST"])
@login_required
def warehouses_item_delete(id):
    session = get_web_session()
    repo = BaseRepository(session, Item)
    if repo.delete(id, soft=True):
        session.commit()
        flash("تم حذف الصنف بنجاح", "success")
    else:
        flash("لم يتم العثور على الصنف", "danger")
    return redirect(url_for("warehouses.warehouses_items"))


@warehouses_bp.route("/transactions")
@login_required
def warehouses_transactions():
    session = get_web_session()
    transactions = session.query(StockTransaction).order_by(StockTransaction.created_at.desc()).all()
    items = session.query(Item).filter(Item.is_deleted == False).all()
    warehouses = session.query(Warehouse).filter(Warehouse.is_deleted == False).all()
    return render_template("warehouses/transactions.html", transactions=transactions, items=items, warehouses=warehouses)


@warehouses_bp.route("/transactions/add", methods=["POST"])
@login_required
def warehouses_transaction_add():
    session = get_web_session()
    item_id = request.form.get("item_id", "").strip()
    warehouse_id = request.form.get("warehouse_id", "").strip()
    transaction_type = request.form.get("transaction_type", "").strip()
    quantity = request.form.get("quantity", "0").strip()
    trans_date = request.form.get("date", "").strip()

    if not item_id or not warehouse_id or not transaction_type or not quantity:
        flash("يرجى ملء جميع الحقول المطلوبة", "danger")
        return redirect(url_for("warehouses.warehouses_transactions"))

    qty = float(quantity)
    item = session.query(Item).filter(Item.id == item_id).first()
    if item:
        if transaction_type == "IN":
            item.current_quantity += qty
        elif transaction_type == "OUT":
            if item.current_quantity < qty:
                flash("الكمية المطلوبة غير متوفرة في المخزون", "danger")
                return redirect(url_for("warehouses.warehouses_transactions"))
            item.current_quantity -= qty

    trans_num = f"STX-{date.today().strftime('%Y%m%d')}-{StockTransaction.query.count() + 1:05d}"
    repo = BaseRepository(session, StockTransaction)
    repo.create(
        transaction_number=trans_num,
        transaction_type=transaction_type,
        date=trans_date if trans_date else date.today(),
        warehouse_id=warehouse_id,
        item_id=item_id,
        quantity=qty,
        unit_price=float(request.form.get("unit_price") or 0),
        total_price=float(request.form.get("unit_price") or 0) * qty,
        source=request.form.get("source", "").strip() or None,
        destination=request.form.get("destination", "").strip() or None,
        reference_number=request.form.get("reference_number", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
        employee_id=current_user.employee_id,
    )
    session.commit()
    flash("تم إضافة المعاملة بنجاح", "success")

    return redirect(url_for("warehouses.warehouses_transactions"))
