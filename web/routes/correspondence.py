import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    CorrespondenceAttachment, Department, Employee, Driver, Customer,
)
from src.modules.correspondence.service import CorrespondenceService
from src.modules.correspondence.workflow import CorrespondenceWorkflow, WorkflowState

correspondence_bp = Blueprint("correspondence", __name__, url_prefix="/correspondence")


@correspondence_bp.route("/")
@login_required
def correspondence_list():
    tab = request.args.get("tab", "all")
    search = request.args.get("search", "").strip()
    direction = request.args.get("direction", "").strip()
    type_code = request.args.get("type_code", "").strip()
    status_code = request.args.get("status_code", "").strip()

    with session_scope() as session:
        service = CorrespondenceService(session)
        if tab == "inbox":
            items = service.get_inbox()
        elif tab == "outbox":
            items = service.get_outbox()
        elif tab == "pending":
            items = service.get_pending()
        elif tab == "archived":
            items = service.search(is_archived=True)
        else:
            items = service.search(query=search or None, direction=direction or None,
                                   type_code=type_code or None, status_code=status_code or None)

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
    with session_scope() as session:
        cor_types = session.query(CorrespondenceType).filter(CorrespondenceType.is_active == True).all()
        departments = session.query(Department).filter(Department.is_deleted == False).all()
        employees = session.query(Employee).filter(Employee.is_deleted == False, Employee.status == "active").all()
        drivers = session.query(Driver).filter(Driver.is_deleted == False, Driver.status == "active").all()
        customers = session.query(Customer).filter(Customer.is_deleted == False, Customer.status == "active").all()

        if request.method == "POST":
            type_code = request.form.get("type_code", "").strip()
            subject = request.form.get("subject", "").strip()
            direction = request.form.get("direction", "INT").strip()

            if not type_code or not subject:
                flash("نوع المراسلة والموضوع مطلوبان", "danger")
                return render_template("correspondence/form.html",
                    cor_types=cor_types, departments=departments, employees=employees,
                    drivers=drivers, customers=customers, correspondence=None)

            try:
                service = CorrespondenceService(session)
                from datetime import date
                due_date = request.form.get("due_date", "").strip()
                cor = service.create(
                    type_code=type_code,
                    subject=subject,
                    direction=direction,
                    user_id=current_user.id,
                    username=current_user.username,
                    body=request.form.get("body", "").strip() or None,
                    importance=request.form.get("importance", "normal"),
                    is_confidential=bool(request.form.get("is_confidential")),
                    sender_department_id=request.form.get("sender_department_id", "").strip() or None,
                    receiver_department_id=request.form.get("receiver_department_id", "").strip() or None,
                    sender_entity=request.form.get("sender_entity", "").strip() or None,
                    receiver_entity=request.form.get("receiver_entity", "").strip() or None,
                    responsible_employee_id=request.form.get("responsible_employee_id", "").strip() or None,
                    employee_id=current_user.employee_id,
                    driver_id=request.form.get("driver_id", "").strip() or None,
                    customer_id=request.form.get("customer_id", "").strip() or None,
                    due_date=due_date if due_date else None,
                    notes=request.form.get("notes", "").strip() or None,
                )
                flash(f"تم إنشاء المراسلة {cor.reference_number} بنجاح", "success")
                return redirect(url_for("correspondence.correspondence_detail", id=cor.id))
            except ValueError as e:
                flash(str(e), "danger")

    return render_template("correspondence/form.html",
        cor_types=cor_types, departments=departments, employees=employees,
        drivers=drivers, customers=customers, correspondence=None)


@correspondence_bp.route("/<id>")
@login_required
def correspondence_detail(id):
    with session_scope() as session:
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
        linked = None
        if cor.linked_correspondence_id:
            linked = session.query(Correspondence).filter(
                Correspondence.id == cor.linked_correspondence_id
            ).first()

    return render_template("correspondence/detail.html",
        correspondence=cor, available_transitions=available_transitions,
        history=history, attachments=attachments, linked=linked, workflow=workflow)


@correspondence_bp.route("/<id>/transition/<target>", methods=["POST"])
@login_required
def correspondence_transition(id, target):
    with session_scope() as session:
        cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
        if not cor:
            flash("المراسلة غير موجودة", "danger")
            return redirect(url_for("correspondence.correspondence_list"))

        workflow = CorrespondenceWorkflow(session)
        notes = request.form.get("notes", "").strip()
        ok, msg = workflow.execute_transition(
            cor, target, employee_id=current_user.employee_id, notes=notes)
        if ok:
            flash(msg, "success")
        else:
            flash(msg, "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/forward", methods=["POST"])
@login_required
def correspondence_forward(id):
    with session_scope() as session:
        cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
        if not cor:
            flash("المراسلة غير موجودة", "danger")
            return redirect(url_for("correspondence.correspondence_list"))

        to_employee_id = request.form.get("to_employee_id", "").strip()
        to_department_id = request.form.get("to_department_id", "").strip()
        required_action = request.form.get("required_action", "").strip()
        due_date = request.form.get("due_date", "").strip() or None
        notes = request.form.get("notes", "").strip()

        if not to_employee_id:
            flash("يجب اختيار الموظف المحال إليه", "danger")
            return redirect(url_for("correspondence.correspondence_detail", id=id))

        workflow = CorrespondenceWorkflow(session)
        ok, msg = workflow.forward(
            cor, from_employee_id=current_user.employee_id,
            to_employee_id=to_employee_id,
            to_department_id=to_department_id,
            required_action=required_action or None,
            due_date=due_date,
            notes=notes or None,
        )
        if ok:
            flash(msg, "success")
        else:
            flash(msg, "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/link", methods=["POST"])
@login_required
def correspondence_link(id):
    with session_scope() as session:
        target_ref = request.form.get("target_reference", "").strip()
        if not target_ref:
            flash("يرجى إدخال الرقم الإشاري للمراسلة المراد ربطها", "danger")
            return redirect(url_for("correspondence.correspondence_detail", id=id))

        target = session.query(Correspondence).filter(
            Correspondence.reference_number == target_ref,
            Correspondence.is_deleted == False
        ).first()
        if not target:
            flash("لم يتم العثور على المراسلة بهذا الرقم", "danger")
            return redirect(url_for("correspondence.correspondence_detail", id=id))

        service = CorrespondenceService(session)
        if service.link_correspondences(id, target.id, user_id=current_user.id, username=current_user.username):
            flash("تم ربط المراسلة بنجاح", "success")
        else:
            flash("فشل في الربط", "danger")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/attach", methods=["POST"])
@login_required
def correspondence_attach(id):
    with session_scope() as session:
        file = request.files.get("attachment")
        if not file or not file.filename:
            flash("يرجى اختيار ملف", "danger")
            return redirect(url_for("correspondence.correspondence_detail", id=id))

        upload_dir = os.path.join(current_app.static_folder, "uploads", "correspondence", id)
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        service = CorrespondenceService(session)
        service.add_attachment(
            correspondence_id=id,
            filename=file.filename,
            file_path=f"uploads/correspondence/{id}/{filename}",
            file_size=os.path.getsize(file_path),
            mime_type=file.content_type,
            notes=request.form.get("notes", "").strip() or None,
        )
        flash("تم إرفاق الملف بنجاح", "success")

    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/pdf")
@login_required
def correspondence_pdf(id):
    with session_scope() as session:
        cor = session.query(Correspondence).filter(Correspondence.id == id, Correspondence.is_deleted == False).first()
        if not cor:
            flash("المراسلة غير موجودة", "danger")
            return redirect(url_for("correspondence.correspondence_list"))

        from src.core.models.base_models import Company
        company = session.query(Company).first()

        from src.modules.documents.pdf_generator import PDFGenerator
        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.generate_correspondence_pdf(cor, company)

        if os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True,
                download_name=os.path.basename(pdf_path), mimetype="application/pdf")

    flash("فشل في إنشاء ملف PDF", "danger")
    return redirect(url_for("correspondence.correspondence_detail", id=id))


@correspondence_bp.route("/<id>/delete", methods=["POST"])
@login_required
def correspondence_delete(id):
    with session_scope() as session:
        service = CorrespondenceService(session)
        try:
            if service.delete(id, user_id=current_user.id, username=current_user.username):
                flash("تم حذف المراسلة بنجاح", "success")
            else:
                flash("لم يتم العثور على المراسلة", "danger")
        except ValueError as e:
            flash(str(e), "danger")

    return redirect(url_for("correspondence.correspondence_list"))
