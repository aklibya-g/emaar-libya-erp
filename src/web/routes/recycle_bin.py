from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
import shutil
import os

from src.core.database.connection import get_web_session
from src.core.models.base_models import DeletedItem
from src.core.models.marketing_models import WorkOrder, WorkOrderBus

recycle_bp = Blueprint("recycle", __name__, url_prefix="/recycle-bin")


def add_to_recycle_bin(session, item_type, item_id, item_number=None, item_title=None):
    """اضافة عنصر الى سلة المحذوفات"""
    deleted = DeletedItem(
        item_type=item_type,
        item_id=item_id,
        item_number=item_number,
        item_title=item_title,
        deleted_by=current_user.full_name_ar if current_user.is_authenticated else None,
        deleted_by_user_id=current_user.id if current_user.is_authenticated else None,
    )
    session.add(deleted)


@recycle_bp.route("/")
@login_required
def recycle_bin():
    with get_web_session() as session:
        items = session.query(DeletedItem).order_by(DeletedItem.created_at.desc()).all()
        return render_template("recycle_bin/index.html",
                             page_title="سلة المحذوفات",
                             items=items)


@recycle_bp.route("/restore/<item_id>", methods=["POST"])
@login_required
def restore_item(item_id):
    with get_web_session() as session:
        deleted = session.query(DeletedItem).get(item_id)
        if not deleted:
            flash("العنصر غير موجود", "danger")
            return redirect(url_for("recycle.recycle_bin"))

        if deleted.item_type == "work_order":
            # استعادة امر التشغيل
            order = session.query(WorkOrder).filter(WorkOrder.id == deleted.item_id).first()
            if order:
                order.is_deleted = False
                session.commit()
                flash(f"تمت استعادة أمر التشغيل رقم {order.order_number}", "success")
            else:
                flash("أمر التشغيل غير موجود في قاعدة البيانات", "danger")

        elif deleted.item_type == "contract":
            from src.core.models.marketing_models import MarketingContract
            contract = session.query(MarketingContract).filter(MarketingContract.id == deleted.item_id).first()
            if contract:
                session.delete(deleted)
                session.commit()
                flash(f"تمت استعادة العقد رقم {contract.contract_number}", "success")
            else:
                flash("العقد غير موجود في قاعدة البيانات", "danger")

        elif deleted.item_type == "client":
            from src.core.models.marketing_models import MarketingClient
            client = session.query(MarketingClient).filter(MarketingClient.id == deleted.item_id).first()
            if client:
                session.delete(deleted)
                session.commit()
                flash(f"تمت استعادة الجهة {client.name_ar}", "success")
            else:
                flash("الجهة غير موجودة في قاعدة البيانات", "danger")

        else:
            # حذف نهائي من سلة المحذوفات فقط
            session.delete(deleted)
            session.commit()
            flash("تمت الاستعادة", "success")

        return redirect(url_for("recycle.recycle_bin"))


@recycle_bp.route("/permanent-delete/<item_id>", methods=["POST"])
@login_required
def permanent_delete(item_id):
    with get_web_session() as session:
        deleted = session.query(DeletedItem).get(item_id)
        if not deleted:
            flash("العنصر غير موجود", "danger")
            return redirect(url_for("recycle.recycle_bin"))

        item_type = deleted.item_type
        item_number = deleted.item_number

        session.delete(deleted)
        session.commit()
        flash(f"تم حذف {item_type} رقم {item_number} نهائياً", "success")

        return redirect(url_for("recycle.recycle_bin"))


@recycle_bp.route("/clear-all", methods=["POST"])
@login_required
def clear_all():
    with get_web_session() as session:
        count = session.query(DeletedItem).count()
        session.query(DeletedItem).delete()
        session.commit()
        flash(f"تم حذف جميع العناصر ({count}) من سلة المحذوفات نهائياً", "success")
        return redirect(url_for("recycle.recycle_bin"))


@recycle_bp.route("/api/count")
@login_required
def recycle_count():
    with get_web_session() as session:
        count = session.query(DeletedItem).count()
        return jsonify({"count": count})
