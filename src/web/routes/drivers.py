from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import Driver, DriverApprovalMessage, Notification, User, UserSidebarPermission
from src.core.repositories.base_repository import BaseRepository
from datetime import date
from sqlalchemy import func

drivers_bp = Blueprint("drivers", __name__, url_prefix="/drivers")


def _parse_date(val):
    if not val or not val.strip():
        return None
    try:
        from datetime import datetime
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _movement_user_ids(session):
    """كل مستخدم لديه صلاحية قسم الحركة (can_view) + الأدمن"""
    ids = set()
    if current_user.is_admin:
        ids.add(current_user.id)
    rows = session.query(UserSidebarPermission).filter(
        UserSidebarPermission.module_name == "movement",
        UserSidebarPermission.can_view == True,
    ).all()
    for r in rows:
        ids.add(r.user_id)
    return list(ids)


def _notify(session, user_ids, title, message, ntype, ref_id):
    for uid in user_ids:
        if not uid:
            continue
        session.add(Notification(
            user_id=uid,
            title=title,
            message=message,
            notification_type=ntype,
            reference_id=ref_id,
            reference_type="Driver",
        ))


def _admin_user_ids(session):
    """المدير التنفيذي / مدير النظام (is_admin)"""
    from src.core.models.base_models import User
    from src.web.app import user_is_admin
    users = session.query(User).filter(User.is_deleted == False, User.is_active == True).all()
    return [u.id for u in users if user_is_admin(u)]


@drivers_bp.route("/conversations")
@login_required
def drivers_conversations():
    """تتبع محادثات الاعتماد — لل楼主ين (المدير التنفيذي + قسم الحركة)"""
    from src.web.app import user_is_admin
    session = get_web_session()
    inbox = request.args.get("inbox", "").strip()  # mine|pending|rejected|approved|""

    msg_counts = dict(
        session.query(
            DriverApprovalMessage.driver_id,
            func.count(DriverApprovalMessage.id),
        ).group_by(DriverApprovalMessage.driver_id).all()
    )

    last_ids = dict(
        session.query(
            DriverApprovalMessage.driver_id,
            func.max(DriverApprovalMessage.created_at),
        ).group_by(DriverApprovalMessage.driver_id).all()
    )

    last_map = {}
    if last_ids:
        from sqlalchemy import or_
        pairs = session.query(DriverApprovalMessage).filter(
            or_(*[
                (DriverApprovalMessage.driver_id == d) & (DriverApprovalMessage.created_at == t)
                for d, t in last_ids.items()
            ])
        ).all()
        for m in pairs:
            last_map[m.driver_id] = m

    sender_ids = {m.sender_id for m in last_map.values() if m.sender_id}
    sender_names = {}
    admin_ids = set()
    if sender_ids:
        for u in session.query(User).filter(User.id.in_(sender_ids)).all():
            sender_names[u.id] = u.full_name_ar or u.username
            if user_is_admin(u):
                admin_ids.add(u.id)

    current_is_admin = bool(current_user.is_admin)
    q = session.query(Driver).filter(Driver.is_deleted == False)
    if inbox == "pending":
        q = q.filter(Driver.approval_status == "pending")
    elif inbox == "rejected":
        q = q.filter(Driver.approval_status == "rejected")
    elif inbox == "approved":
        q = q.filter(Driver.approval_status == "approved")

    drivers = q.order_by(Driver.updated_at.desc().nullslast(), Driver.created_at.desc()).all()

    rows = []
    for d in drivers:
        last = last_map.get(d.id)
        if inbox == "mine":
            if not last:
                continue
            last_from_admin = last.sender_id in admin_ids
            needs_reply = (last_from_admin and not current_is_admin) or ((not last_from_admin) and current_is_admin)
            if not needs_reply:
                continue
        elif not last and d.approval_status == "approved":
            # لا محادثة ولا بانتظار اعتماد — تجاوز
            if inbox == "":
                # نعرض كل من له محادثة أو pending/rejected فقط في "الكل"
                continue

        needs_reply = False
        last_from_admin = False
        if last:
            last_from_admin = last.sender_id in admin_ids
            needs_reply = (last_from_admin and not current_is_admin) or ((not last_from_admin) and current_is_admin)

        rows.append({
            "driver": d,
            "last": last,
            "count": msg_counts.get(d.id, 0),
            "last_sender": sender_names.get(last.sender_id, "مستخدم") if last else "",
            "last_from_admin": last_from_admin,
            "needs_reply": needs_reply,
        })

    # الكل: فقط المحادثات النشطة أو بانتظار/مرفوض
    if inbox == "":
        rows = [r for r in rows if r["last"] or r["driver"].approval_status in ("pending", "rejected")]

    rows.sort(key=lambda r: (r["last"].created_at if r["last"] else r["driver"].created_at), reverse=True)

    needs_reply_count = 0
    for r in rows:
        if r["needs_reply"]:
            needs_reply_count += 1

    return render_template(
        "drivers/conversations.html",
        rows=rows,
        inbox=inbox,
        needs_reply_count=needs_reply_count,
        current_is_admin=current_is_admin,
    )


@drivers_bp.route("/")
@login_required
def drivers_list():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    approval_filter = request.args.get("approval", "").strip()
    session = get_web_session()
    q = session.query(Driver).filter(Driver.is_deleted == False)
    if search:
        q = q.filter(
            (Driver.full_name_ar.ilike(f"%{search}%")) |
            (Driver.driver_number.ilike(f"%{search}%")) |
            (Driver.phone.ilike(f"%{search}%")) |
            (Driver.license_number.ilike(f"%{search}%"))
        )
    if status_filter in ("active", "inactive"):
        q = q.filter(Driver.status == status_filter)
    if approval_filter in ("pending", "approved", "rejected"):
        q = q.filter(Driver.approval_status == approval_filter)
    drivers = q.order_by(Driver.created_at.desc()).all()
    total = session.query(Driver).filter(Driver.is_deleted == False).count()
    active = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").count()
    inactive = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "inactive").count()
    pending_count = session.query(Driver).filter(
        Driver.is_deleted == False, Driver.approval_status == "pending"
    ).count()
    return render_template(
        "drivers/list.html",
        drivers=drivers,
        search=search,
        status_filter=status_filter,
        approval_filter=approval_filter,
        total_count=total,
        active_count=active,
        inactive_count=inactive,
        pending_count=pending_count,
    )


def _next_driver_number(session):
    from sqlalchemy import func
    import re
    from src.core.models.base_models import Department
    ops_dept = session.query(Department).filter(
        Department.is_deleted == False,
        (Department.code == "OPS") | (Department.name_ar.like("%حركة%")) | (Department.name_ar.like("%عمليات%"))
    ).first()
    dept_code = (ops_dept.code if ops_dept else "OPS")
    max_num = session.query(func.max(Driver.driver_number)).filter(
        Driver.driver_number.like(f"ELT.{dept_code}-%")
    ).scalar()
    if max_num:
        m = re.search(r'(\d+)$', max_num)
        num = int(m.group(1)) + 1 if m else 1
    else:
        num = 1
    driver_number = f"ELT.{dept_code}-{num:03d}"
    while session.query(Driver).filter(Driver.driver_number == driver_number).first():
        num += 1
        driver_number = f"ELT.{dept_code}-{num:03d}"
    return driver_number


@drivers_bp.route("/add", methods=["GET", "POST"])
@login_required
def drivers_add():
    session = get_web_session()
    if request.method == "POST":
        try:
            full_name_ar = request.form.get("full_name_ar", "").strip()
            if not full_name_ar:
                flash("الاسم بالعربي مطلوب", "danger")
                return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

            if not request.form.get("join_date", "").strip():
                flash("تاريخ المباشرة مطلوب", "danger")
                return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

            driver_number = request.form.get("driver_number", "").strip()
            if not driver_number:
                driver_number = _next_driver_number(session)
            else:
                existing = session.query(Driver).filter(Driver.driver_number == driver_number).first()
                if existing:
                    flash(f"الرقم الوظيفي {driver_number} مستخدم مسبقاً", "danger")
                    return render_template("drivers/form.html", driver=None)

            # الحالة الافتراضي نشط، لكن الاعتماد pending دائماً للجديد
            status = request.form.get("status", "active") or "active"
            approval_note = request.form.get("approval_note", "").strip()

            repo = BaseRepository(session, Driver)
            driver = repo.create(
                driver_number=driver_number,
                full_name_ar=full_name_ar,
                full_name_en=request.form.get("full_name_en", "").strip() or None,
                national_id=request.form.get("national_id", "").strip() or None,
                id_type=request.form.get("id_type", "").strip() or None,
                id_number=request.form.get("id_number", "").strip() or None,
                mother_name=request.form.get("mother_name", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                phone2=request.form.get("phone2", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                license_number=request.form.get("license_number", "").strip() or None,
                license_type=request.form.get("license_type", "").strip() or None,
                license_issue_date=_parse_date(request.form.get("license_issue_date")),
                license_expiry_date=_parse_date(request.form.get("license_expiry_date")),
                license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
                join_date=_parse_date(request.form.get("join_date")),
                contract_type=request.form.get("contract_type", "").strip() or None,
                activity_type=request.form.get("activity_type", "").strip() or None,
                status=status,
                approval_status="pending",
                notes=request.form.get("notes", "").strip() or None,
                created_by=current_user.id,
            )
            session.flush()

            # رسالة الإرسال الأولى في المحادثة
            initial_msg = approval_note or f"تمت إضافة السائق {full_name_ar} من قسم الحركة — بانتظار اعتماد المدير التنفيذي"
            session.add(DriverApprovalMessage(
                driver_id=driver.id,
                sender_id=current_user.id,
                message=initial_msg,
                msg_type="submit",
            ))

            # إشعار المدير التنفيذي
            _notify(
                session,
                _admin_user_ids(session),
                "سائق جديد بانتظار الاعتماد",
                f"تمت إضافة السائق: {full_name_ar} ({driver_number}) — برجاء الموافقة عليه",
                "driver_pending_executive",
                driver.id,
            )
            session.commit()
            flash(f"تمت إضافة السائق {full_name_ar} — بانتظار اعتماد المدير التنفيذي", "success")
            return redirect(url_for("drivers.drivers_detail", id=driver.id))
        except Exception as e:
            session.rollback()
            import traceback
            traceback.print_exc()
            flash(f"خطأ في حفظ البيانات: {str(e)}", "danger")
            return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))

    return render_template("drivers/form.html", driver=None, next_number=_next_driver_number(session))


@drivers_bp.route("/<id>")
@login_required
def drivers_detail(id):
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))
    messages = session.query(DriverApprovalMessage).filter(
        DriverApprovalMessage.driver_id == id
    ).order_by(DriverApprovalMessage.created_at.asc()).all()
    senders = {}
    admin_senders = set()
    for m in messages:
        if m.sender_id and m.sender_id not in senders:
            u = session.query(User).filter(User.id == m.sender_id).first()
            if u:
                senders[m.sender_id] = u.full_name_ar or u.username
                from src.web.app import user_is_admin
                if user_is_admin(u):
                    admin_senders.add(m.sender_id)
    # تمرير تلقائي لأسفل المحادثة
    return render_template(
        "drivers/detail.html",
        driver=driver,
        approval_messages=messages,
        senders=senders,
        admin_senders=admin_senders,
        chat_focus=True,
    )


@drivers_bp.route("/<id>/edit", methods=["GET", "POST"])
@login_required
def drivers_edit(id):
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))

    if request.method == "POST":
        full_name_ar = request.form.get("full_name_ar", "").strip()
        if not full_name_ar:
            flash("الاسم بالعربي مطلوب", "danger")
            return render_template("drivers/form.html", driver=driver)

        new_driver_number = request.form.get("driver_number", "").strip() or driver.driver_number
        if new_driver_number != driver.driver_number:
            existing = session.query(Driver).filter(Driver.driver_number == new_driver_number, Driver.id != id).first()
            if existing:
                flash(f"الرقم الوظيفي {new_driver_number} مستخدم مسبقاً", "danger")
                return render_template("drivers/form.html", driver=driver)

        # الحفظ لا يغيّر حالة الاعتماد الحالية (pending يبقى pending حتى يقرر الأدمن)
        status = request.form.get("status", driver.status) or driver.status

        repo = BaseRepository(session, Driver)
        repo.update(id,
            driver_number=new_driver_number,
            full_name_ar=full_name_ar,
            full_name_en=request.form.get("full_name_en", "").strip() or None,
            national_id=request.form.get("national_id", "").strip() or None,
            id_type=request.form.get("id_type", "").strip() or None,
            id_number=request.form.get("id_number", "").strip() or None,
            mother_name=request.form.get("mother_name", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            phone2=request.form.get("phone2", "").strip() or None,
            address=request.form.get("address", "").strip() or None,
            license_number=request.form.get("license_number", "").strip() or None,
            license_type=request.form.get("license_type", "").strip() or None,
            license_issue_date=_parse_date(request.form.get("license_issue_date")),
            license_expiry_date=_parse_date(request.form.get("license_expiry_date")),
            license_issuing_authority=request.form.get("license_issuing_authority", "").strip() or None,
            join_date=_parse_date(request.form.get("join_date")),
            contract_type=request.form.get("contract_type", "").strip() or None,
            activity_type=request.form.get("activity_type", "").strip() or None,
            status=status,
            notes=request.form.get("notes", "").strip() or None,
            updated_by=current_user.id,
        )
        session.commit()
        flash(f"تم تعديل بيانات السائق {full_name_ar} بنجاح", "success")
        return redirect(url_for("drivers.drivers_detail", id=id))

    return render_template("drivers/form.html", driver=driver)


@drivers_bp.route("/<id>/approve", methods=["POST"])
@login_required
def drivers_approve(id):
    if not current_user.is_admin:
        flash("الاعتماد متاح لمدير النظام فقط", "danger")
        return redirect(url_for("drivers.drivers_list"))
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))
    if driver.approval_status == "approved":
        flash("السائق معتمد مسبقاً", "info")
        return redirect(url_for("drivers.drivers_detail", id=id))

    note = request.form.get("message", "").strip() or "تم الاعتماد بواسطة المدير التنفيذي"
    driver.approval_status = "approved"
    driver.status = "active"
    driver.updated_by = current_user.id
    session.add(DriverApprovalMessage(
        driver_id=driver.id,
        sender_id=current_user.id,
        message=note,
        msg_type="approve",
    ))
    _notify(
        session,
        _movement_user_ids(session),
        "تم اعتماد السائق",
        f"تم اعتماد السائق: {driver.full_name_ar} ({driver.driver_number}) من قبل المدير التنفيذي",
        "driver_approved",
        driver.id,
    )
    session.commit()
    flash(f"تم اعتماد السائق {driver.full_name_ar} — حالته نشط", "success")
    return redirect(url_for("drivers.drivers_detail", id=id))


@drivers_bp.route("/<id>/reject", methods=["POST"])
@login_required
def drivers_reject(id):
    if not current_user.is_admin:
        flash("الرفض متاح لمدير النظام فقط", "danger")
        return redirect(url_for("drivers.drivers_list"))
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))

    reason = request.form.get("reject_reason", "").strip()
    if not reason:
        flash("سبب الرفض مطلوب", "danger")
        return redirect(url_for("drivers.drivers_detail", id=id))

    driver.approval_status = "rejected"
    driver.status = "inactive"
    driver.updated_by = current_user.id
    session.add(DriverApprovalMessage(
        driver_id=driver.id,
        sender_id=current_user.id,
        message=f"تم الرفض: {reason}",
        msg_type="reject",
    ))
    _notify(
        session,
        _movement_user_ids(session),
        "تم رفض سائق من قبل المدير التنفيذي",
        f"تم رفض السائق: {driver.full_name_ar} ({driver.driver_number}) — السبب: {reason}",
        "driver_rejected",
        driver.id,
    )
    session.commit()
    flash(f"تم رفض السائق {driver.full_name_ar} — أصبح متوقفاً", "warning")
    return redirect(url_for("drivers.drivers_detail", id=id))


@drivers_bp.route("/<id>/resend", methods=["POST"])
@login_required
def drivers_resend(id):
    """الحركة تعيد الإرسال بعد الرفض/التعديل"""
    if not current_user.is_admin:
        # السماح للحركة بإعادة الإرسال أيضاً
        sp = None
        session0 = get_web_session()
        sp = session0.query(UserSidebarPermission).filter(
            UserSidebarPermission.user_id == current_user.id,
            UserSidebarPermission.module_name == "movement",
            UserSidebarPermission.can_view == True,
        ).first()
        if not sp and not current_user.is_admin:
            flash("غير مصرح لك بإعادة الإرسال", "danger")
            return redirect(url_for("drivers.drivers_list"))
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        flash("السائق غير موجود", "danger")
        return redirect(url_for("drivers.drivers_list"))
    if driver.approval_status == "pending":
        flash("السائق معلّق بانتظار الاعتماد بالفعل", "info")
        return redirect(url_for("drivers.drivers_detail", id=id))

    msg = request.form.get("message", "").strip() or "تم تعديل البيانات وإعادة الإرسال للمراجعة"
    driver.approval_status = "pending"
    driver.status = "active"
    driver.updated_by = current_user.id
    session.add(DriverApprovalMessage(
        driver_id=driver.id,
        sender_id=current_user.id,
        message=msg,
        msg_type="resend",
    ))
    _notify(
        session,
        _admin_user_ids(session),
        "تمت إعادة إرسال سائق للمراجعة",
        f"السائق: {driver.full_name_ar} ({driver.driver_number}) — بانتظار الموافقة",
        "driver_pending_executive",
        driver.id,
    )
    session.commit()
    flash("تمت إعادة الإرسال للمدير التنفيذي", "success")
    return redirect(url_for("drivers.drivers_detail", id=id))


@drivers_bp.route("/<id>/message", methods=["POST"])
@login_required
def drivers_message(id):
    """إضافة رسالة/ملاحظة في محادثة الاعتماد"""
    session = get_web_session()
    driver = session.query(Driver).filter(Driver.id == id, Driver.is_deleted == False).first()
    if not driver:
        return jsonify({"ok": False, "error": "not found"}), 404
    text = request.form.get("message", "").strip()
    if not text and request.is_json:
        text = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not text:
        flash("اكتب رسالة أولاً", "danger")
        return redirect(url_for("drivers.drivers_detail", id=id))
    session.add(DriverApprovalMessage(
        driver_id=driver.id,
        sender_id=current_user.id,
        message=text,
        msg_type="comment",
    ))
    # إشعار الطرف الآخر
    if current_user.is_admin:
        targets = _movement_user_ids(session)
        title = "رسالة جديدة من المدير التنفيذي"
    else:
        targets = _admin_user_ids(session)
        title = "رسالة جديدة بخصوص سائق"
    _notify(session, targets, title, f"{driver.full_name_ar}: {text}", "driver_comment", driver.id)
    session.commit()
    flash("تمت إضافة الرسالة", "success")
    return redirect(url_for("drivers.drivers_detail", id=id))


@drivers_bp.route("/<id>/delete", methods=["POST"])
@login_required
def drivers_delete(id):
    session = get_web_session()
    repo = BaseRepository(session, Driver)
    if repo.delete(id, soft=True):
        session.commit()
        flash("تم حذف السائق بنجاح", "success")
    else:
        flash("لم يتم العثور على السائق", "danger")
    return redirect(url_for("drivers.drivers_list"))


@drivers_bp.route("/delete-all", methods=["POST"])
@login_required
def drivers_delete_all():
    if not current_user.is_admin:
        flash("هذه العملية متاحة لمدير النظام فقط", "danger")
        return redirect(url_for("drivers.drivers_list"))
    confirm = request.form.get("typed_confirm", request.form.get("confirm", "")).strip()
    if confirm != "DELETE":
        flash('يرجى كتابة DELETE في مربع التأكيد', "danger")
        return redirect(url_for("drivers.drivers_list"))
    session = get_web_session()
    count = session.query(Driver).filter(Driver.is_deleted == False).count()
    session.query(Driver).filter(Driver.is_deleted == False).update({"is_deleted": True}, synchronize_session=False)
    session.commit()
    flash(f"تم حذف جميع السائقين ({count}) بنجاح", "success")
    return redirect(url_for("drivers.drivers_list"))
