import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from src.core.database.connection import get_web_session
from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    CorrespondenceAttachment, Department, Employee, Driver, Customer, User,
    UserCorrespondencePermission, CorrespondenceAction,
)
from src.modules.correspondence.service import CorrespondenceService
from src.modules.correspondence.workflow import CorrespondenceWorkflow, WorkflowState

correspondence_bp = Blueprint("correspondence", __name__, url_prefix="/correspondence")


def _user_can_see(user_id, dept_id, session):
    perms = session.query(UserCorrespondencePermission).filter(
        UserCorrespondencePermission.user_id == user_id,
        UserCorrespondencePermission.can_receive == True,
    ).all()
    if not perms:
        return True
    allowed = [p.target_department_id for p in perms]
    return dept_id in allowed


@correspondence_bp.route("/")
@login_required
def correspondence_list():
    tab = request.args.get("tab", "all")
    search = request.args.get("search", "").strip()
    direction = request.args.get("direction", "").strip()
    type_code = request.args.get("type_code", "").strip()
    status_code = request.args.get("status_code", "").strip()

    session = get_web_session()
    user = session.query(User).filter(User.id == current_user.id).first()
    user_dept = user.department_id if user else None

    service = CorrespondenceService(session)

    if tab == "inbox":
        items = service.get_inbox()
        items = [c for c in items if _user_can_see(current_user.id, c.receiver_department_id, session)]
    elif tab == "outbox":
        items = service.get_outbox()
        items = [c for c in items if c.sender_department_id == user_dept]
    elif tab == "pending":
        items = service.get_pending()
        items = [c for c in items if _user_can_see(current_user.id, c.receiver_department_id, session)]
    elif tab == "archived":
        items = service.search(is_archived=True)
        items = [c for c in items if _user_can_see(current_user.id, c.receiver_department_id, session) or c.sender_department_id == user_dept]
    else:
        items = service.search(query=search or None, direction=direction or None,
                               type_code=type_code or None, status_code=status_code or None)
        items = [c for c in items if _user_can_see(current_user.id, c.receiver_department_id, session) or c.sender_department_id == user_dept]

    cor_types = session.query(CorrespondenceType).filter(CorrespondenceType.is_active == True).all()
    statuses = session.query(CorrespondenceStatus).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()
    workflow = CorrespondenceWorkflow(session)

    return render_template("correspondence/list.html",
        items=items, tab=tab, search=search, direction=direction,
        type_code=type_code, status_code=status_code,
        cor_types=cor_types, statuses=statuses, departments=departments, workflow=workflow)


@correspondence_bp.route("/add", methods=["GET", "POST"])
@login_required
def correspondence_add():
    from datetime import date as date_type
    session = get_web_session()
    cor_types = session.query(CorrespondenceType).filter(CorrespondenceType.is_active == True).all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()
    employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()

    user = session.query(User).filter(User.id == current_user.id).first()
    sender_dept_name = ""
    if user and user.department_id:
        dept = session.query(Department).filter(Department.id == user.department_id).first()
        if dept:
            sender_dept_name = dept.name_ar

    if request.method == "POST":
        type_code = request.form.get("type_code", "").strip()
        subject = request.form.get("subject", "").strip()

        if not type_code or not subject:
            flash("نوع المراسلة والموضوع مطلوبان", "danger")
            return render_template("correspondence/form.html",
                cor_types=cor_types, departments=departments, employees=employees,
                sender_dept_name=sender_dept_name, correspondence=None, today=date_type.today().strftime("%Y-%m-%d"))

        try:
            service = CorrespondenceService(session)
            due_date = request.form.get("due_date", "").strip()
            cor_date = request.form.get("date", "").strip()
            cor = service.create(
                type_code=type_code,
                subject=subject,
                direction="INT",
                user_id=current_user.id,
                username=current_user.username,
                body=request.form.get("body", "").strip() or None,
                importance=request.form.get("importance", "normal"),
                is_confidential=bool(request.form.get("is_confidential")),
                sender_department_id=request.form.get("sender_department_id", "").strip() or None,
                receiver_department_id=request.form.get("receiver_department_id", "").strip() or None,
                sender_entity=current_user.full_name_ar,
                receiver_entity=None,
                responsible_employee_id=request.form.get("responsible_employee_id", "").strip() or None,
                employee_id=current_user.employee_id,
                driver_id=None,
                customer_id=None,
                cor_date=date_type.fromisoformat(cor_date) if cor_date else date_type.today(),
                due_date=date_type.fromisoformat(due_date) if due_date else None,
                notes=request.form.get("notes", "").strip() or None,
            )
            session.commit()
            flash(f"تم إنشاء المراسلة {cor.reference_number} بنجاح", "success")
            return redirect(url_for("correspondence.correspondence_detail", id=cor.id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            session.rollback()
            flash(f"خطأ: {str(e)}", "danger")

    return render_template("correspondence/form.html",
        cor_types=cor_types, departments=departments, employees=employees,
        sender_dept_name=sender_dept_name, correspondence=None, today=date_type.today().strftime("%Y-%m-%d"))


@correspondence_bp.route("/<id>")
@login_required
def correspondence_detail(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    workflow = CorrespondenceWorkflow(session)
    available_transitions = workflow.get_available_transitions(cor)
    history = workflow.get_workflow_history(id)
    attachments = session.query(CorrespondenceAttachment).filter(
        CorrespondenceAttachment.correspondence_id == id
    ).all()

    replies = session.query(CorrespondenceAction).filter(
        CorrespondenceAction.correspondence_id == id,
        CorrespondenceAction.action_type == "رد",
    ).order_by(CorrespondenceAction.action_date.asc()).all()

    reply_details = []
    for r in replies:
        emp = session.query(Employee).filter(Employee.id == r.from_employee_id).first() if r.from_employee_id else None
        dept = session.query(Department).filter(Department.id == r.from_department_id).first() if r.from_department_id else None
        reply_details.append({
            "action": r,
            "employee": emp.full_name_ar if emp else "غير معروف",
            "department": dept.name_ar if dept else "غير معروف",
            "action_date": r.action_date,
            "notes": r.notes,
        })

    linked = None
    if cor.linked_correspondence_id:
        linked = session.query(Correspondence).filter(
            Correspondence.id == cor.linked_correspondence_id
        ).first()

    employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()
    departments = session.query(Department).filter(Department.is_deleted == False).all()

    from datetime import datetime
    now = datetime.now()

    return render_template("correspondence/detail.html",
        correspondence=cor, available_transitions=available_transitions,
        history=history, attachments=attachments, linked=linked, workflow=workflow,
        replies=reply_details, employees=employees, departments=departments, now=now)


@correspondence_bp.route("/<id>/reply", methods=["POST"])
@login_required
def correspondence_reply(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    notes = request.form.get("notes", "").strip()
    if not notes:
        flash("الرد مطلوب", "danger")
        return redirect(url_for("correspondence.correspondence_detail", id=id))

    user = session.query(User).filter(User.id == current_user.id).first()

    from datetime import datetime
    action = CorrespondenceAction(
        correspondence_id=id,
        action_type="رد",
        from_employee_id=current_user.employee_id,
        from_department_id=user.department_id if user else None,
        action_date=datetime.utcnow(),
        notes=notes,
        created_by=current_user.id,
    )
    session.add(action)
    session.commit()
    flash("تم إضافة الرد بنجاح", "success")
    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/transition/<target>", methods=["POST"])
@login_required
def correspondence_transition(id, target):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    notes = request.form.get("notes", "").strip()
    workflow = CorrespondenceWorkflow(session)
    try:
        workflow.execute_transition(cor, target, employee_id=current_user.employee_id, notes=notes or None)
        session.commit()
        flash(f"تم التحويل بنجاح", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/forward", methods=["POST"])
@login_required
def correspondence_forward(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    to_employee_id = request.form.get("to_employee_id", "").strip()
    to_department_id = request.form.get("to_department_id", "").strip()

    if not to_employee_id:
        flash("يجب اختيار الموظف المستلم", "danger")
        return redirect(url_for("correspondence.correspondence_detail", id=id))

    workflow = CorrespondenceWorkflow(session)
    try:
        workflow.forward(
            cor,
            from_employee_id=current_user.employee_id,
            to_employee_id=to_employee_id,
            to_department_id=to_department_id or None,
            required_action=request.form.get("required_action", "").strip() or None,
            due_date=request.form.get("due_date", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.commit()
        flash("تم الإحالة بنجاح", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/link", methods=["POST"])
@login_required
def correspondence_link(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    ref = request.form.get("reference_number", "").strip()
    if ref:
        linked = session.query(Correspondence).filter(
            Correspondence.reference_number == ref,
            Correspondence.is_deleted == False,
        ).first()
        if linked:
            cor.linked_correspondence_id = linked.id
            session.commit()
            flash(f"تم ربط المراسلة بـ {ref}", "success")
        else:
            flash(f"لم يتم العثور على مراسلة بالرقم {ref}", "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/attach", methods=["POST"])
@login_required
def correspondence_attach(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    file = request.files.get("file")
    if file and file.filename:
        import os, uuid
        upload_dir = os.path.join(os.getcwd(), "data", "uploads", "correspondence")
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, safe_name)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        from src.modules.correspondence.service import CorrespondenceService
        service = CorrespondenceService(session)
        attachment = service.add_attachment(
            correspondence_id=id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            notes=request.form.get("notes", "").strip() or None,
        )
        session.commit()
        flash("تم إرفاق الملف بنجاح", "success")
    else:
        flash("يجب اختيار ملف", "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/attachment/<att_id>/download")
@login_required
def correspondence_download(att_id):
    session = get_web_session()
    att = session.query(CorrespondenceAttachment).filter(CorrespondenceAttachment.id == att_id).first()
    if not att:
        flash("المرفق غير موجود", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    if not os.path.exists(att.file_path):
        flash("الملف غير موجود على الخادم", "danger")
        return redirect(url_for("correspondence.correspondence_detail", id=att.correspondence_id))

    return send_file(att.file_path, as_attachment=True, download_name=att.filename)


@correspondence_bp.route("/attachment/<att_id>/serve")
@login_required
def correspondence_serve_file(att_id):
    session = get_web_session()
    att = session.query(CorrespondenceAttachment).filter(CorrespondenceAttachment.id == att_id).first()
    if not att or not os.path.exists(att.file_path):
        return "", 404

    from flask import make_response
    resp = make_response(send_file(att.file_path))
    resp.headers['Content-Type'] = att.mime_type or 'application/octet-stream'
    return resp


@correspondence_bp.route("/attachment/<att_id>/view")
@login_required
def correspondence_view_file(att_id):
    session = get_web_session()
    att = session.query(CorrespondenceAttachment).filter(CorrespondenceAttachment.id == att_id).first()
    if not att:
        flash("المرفق غير موجود", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    if not os.path.exists(att.file_path):
        flash("الملف غير موجود على الخادم", "danger")
        return redirect(url_for("correspondence.correspondence_detail", id=att.correspondence_id))

    ext = att.filename.rsplit('.', 1)[-1].lower() if '.' in att.filename else ''
    serve_url = url_for('correspondence.correspondence_serve_file', att_id=att.id)
    download_url = url_for('correspondence.correspondence_download', att_id=att.id)

    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
        content_html = f'<img src="{serve_url}" style="max-width:100%;max-height:90vh;object-fit:contain;">'
    elif ext == 'pdf':
        content_html = f'<iframe src="{serve_url}" style="width:100%;height:90vh;border:none;"></iframe>'
    else:
        content_html = f'''
        <div style="text-align:center;padding:60px 20px;">
            <i class="bi bi-file-earmark" style="font-size:5rem;color:var(--text-secondary);"></i>
            <h3 style="margin-top:20px;color:var(--text-primary);">{att.filename}</h3>
            <p style="color:var(--text-secondary);">الملف جاهز للتحميل</p>
            <a href="{download_url}" class="btn btn-primary btn-lg" style="margin-top:15px;padding:12px 40px;border-radius:10px;">
                <i class="bi bi-download me-2"></i>تحميل الملف
            </a>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{att.filename}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#1a1a2e; display:flex; align-items:center; justify-content:center; min-height:100vh; overflow:auto; }}
        .print-btn {{
            position:fixed; bottom:30px; left:50%; transform:translateX(-50%);
            background:linear-gradient(135deg,#667eea,#764ba2);
            color:#fff; border:none; padding:14px 36px; border-radius:50px;
            font-size:16px; font-weight:600; cursor:pointer;
            box-shadow:0 8px 30px rgba(102,126,234,0.5);
            transition:all 0.3s; z-index:9999; display:flex; align-items:center; gap:10px;
        }}
        .print-btn:hover {{ transform:translateX(-50%) translateY(-3px); box-shadow:0 12px 40px rgba(102,126,234,0.7); }}
        .print-btn i {{ font-size:20px; }}
        @media print {{
            .print-btn {{ display:none !important; }}
            body {{ background:#fff; }}
        }}
    </style>
</head>
<body>
    <div style="width:100%;text-align:center;padding:20px;">
        {content_html}
    </div>
    <button class="print-btn" onclick="window.print();">
        <i class="bi bi-printer-fill"></i>طباعة
    </button>
</body>
</html>'''


@correspondence_bp.route("/<id>/pdf")
@login_required
def correspondence_pdf(id):
    session = get_web_session()
    cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
    if not cor:
        flash("المراسلة غير موجودة", "danger")
        return redirect(url_for("correspondence.correspondence_list"))

    from src.modules.correspondence.template_engine import TemplateEngine
    engine = TemplateEngine(session)
    pdf_path = engine.generate_pdf(id)

    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"{cor.reference_number}.pdf")

    flash("فشل في إنشاء ملف PDF", "danger")
    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/delete", methods=["POST"])
@login_required
def correspondence_delete(id):
    session = get_web_session()
    service = CorrespondenceService(session)
    try:
        if service.delete(id, user_id=current_user.id, username=current_user.username):
            session.commit()
            flash("تم حذف المراسلة بنجاح", "success")
        else:
            flash("لم يتم العثور على المراسلة", "danger")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("correspondence.correspondence_list"))


@correspondence_bp.route("/api/type-add", methods=["POST"])
@login_required
def correspondence_type_add():
    from flask import jsonify
    session = get_web_session()
    data = request.get_json()
    name_ar = data.get("name_ar", "").strip()
    code = data.get("code", "").strip()
    prefix = data.get("prefix", "").strip()

    if not name_ar or not code:
        return jsonify({"success": False, "message": "الاسم والكود مطلوبان"})

    existing = session.query(CorrespondenceType).filter(CorrespondenceType.code == code).first()
    if existing:
        return jsonify({"success": False, "message": "الكود موجود مسبقاً"})

    ct = CorrespondenceType(
        name_ar=name_ar,
        code=code,
        direction="INT",
        numbering_prefix=prefix or name_ar[:2],
        is_active=True,
        created_by=current_user.id,
    )
    session.add(ct)
    session.commit()
    return jsonify({"success": True})


@correspondence_bp.route("/api/rephrase", methods=["POST"])
@login_required
def correspondence_rephrase():
    from flask import jsonify
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "message": "النص فارغ"})

    try:
        import g4f
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4o_mini,
            messages=[
                {"role": "system", "content": "أنت مساعد لإعادة صياغة النصوص بالعربية. أعد صياغة النص بشكل مختصر واحترافي فقط. لا تضف أي ملاحظات أو تعليقات إضافية. أعد فقط النص المعاد صياغته."},
                {"role": "user", "content": text}
            ],
            provider=g4f.Provider.Yqcloud
        )
        result = str(response).strip()
        if result:
            return jsonify({"success": True, "text": result})
        return jsonify({"success": False, "message": "لم يتم الحصول على نتيجة"})
    except Exception as e:
        return jsonify({"success": False, "message": f"خطأ: {str(e)}"})


@correspondence_bp.route("/api/employees-by-department/<dept_id>")
@login_required
def correspondence_employees_by_department(dept_id):
    from flask import jsonify
    session = get_web_session()
    employees = session.query(Employee).filter(
        Employee.department_id == dept_id,
        Employee.is_deleted == False,
        Employee.status == "active",
    ).all()
    return jsonify([{"id": e.id, "name": e.full_name_ar} for e in employees])
