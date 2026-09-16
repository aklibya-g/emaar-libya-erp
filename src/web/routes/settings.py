from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import login_required
from datetime import datetime
import os
import json
import shutil
import sqlite3
from src.core.database.connection import get_web_session
from src.core.models.base_models import Setting, Company
from src.core.repositories.base_repository import BaseRepository

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "emaar_erp.db")

# جداول كل قسم
SECTION_TABLES = {
    "الموارد البشرية": [
        "employees", "employee_contracts", "employee_documents", "employee_attendance",
        "employee_vacations", "employee_loans", "employee_penalties", "salary_scale",
        "salary_scale_items", "employee_salaries", "employee_salary_items",
        "employee_promotions", "training_courses", "employee_trainings",
        "employee_evaluations", "recruitment_requests", "recruitment_applicants",
        "recruitment_interviews", "exit_reexit_requests", "employee_return_to_work",
        "employee Fingerprints", "employee_fingerprints", "employee_courses"
    ],
    "السائقين": [
        "drivers", "driver_documents", "driver_licenses", "driver_trips"
    ],
    "المركبات": [
        "vehicles", "vehicle_maintenances", "vehicle_fuel", "vehicle_documents",
        "vehicle_insurances", "vehicle_inspection", "vehicle_violations",
        "vehicle_driver_logs"
    ],
    "التسويق التجاري": [
        "marketing_clients", "marketing_contracts", "marketing_work_orders",
        "marketing_work_order_buses", "marketing_work_order_annexes",
        "marketing_trips", "marketing_school_driver_entitlements",
        "marketing_monthly_trip_sheets"
    ],
    "الحركة": [],
    "العملاء": ["customers"],
    "المراسلات": ["correspondences", "correspondence_attachments"],
    "المخازن": ["warehouses", "warehouse_items", "warehouse_transactions"],
    "الادارة": ["users", "roles", "departments", "settings", "companies"]
}


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


@settings_bp.route("/")
@login_required
def settings_view():
    session = get_web_session()
    settings_list = session.query(Setting).order_by(Setting.category, Setting.key).all()
    company = session.query(Company).filter(Company.is_deleted == False).first()
    settings_dict = {s.key: s.value for s in settings_list}

    # قائمة النسخ الاحتياطية
    ensure_backup_dir()
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith(".db") or f.endswith(".json"):
            filepath = os.path.join(BACKUP_DIR, f)
            size = os.path.getsize(filepath)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            backups.append({"name": f, "size": size, "date": mtime})

    return render_template("settings/index.html",
                         settings_list=settings_list,
                         settings_dict=settings_dict,
                         company=company,
                         backups=backups,
                         sections=SECTION_TABLES.keys())


@settings_bp.route("/update", methods=["POST"])
@login_required
def settings_update():
    session = get_web_session()
    settings_dict = {
        "company_name_ar": request.form.get("company_name_ar", ""),
        "company_name_en": request.form.get("company_name_en", ""),
        "company_phone": request.form.get("company_phone", ""),
        "company_email": request.form.get("company_email", ""),
        "company_address": request.form.get("company_address", ""),
        "company_city": request.form.get("company_city", ""),
        "numbering_format": request.form.get("numbering_format", ""),
        "numbering_prefix": request.form.get("numbering_prefix", ""),
        "default_language": request.form.get("default_language", "ar"),
        "timezone": request.form.get("timezone", "Africa/Tripoli"),
    }

    company = session.query(Company).filter(Company.is_deleted == False).first()
    if company:
        company.name_ar = settings_dict.get("company_name_ar") or company.name_ar
        company.name_en = settings_dict.get("company_name_en") or company.name_en
        company.phone = settings_dict.get("company_phone") or company.phone
        company.email = settings_dict.get("company_email") or company.email
        company.address = settings_dict.get("company_address") or company.address
        company.city = settings_dict.get("company_city") or company.city
    else:
        from src.core.models.base_models import generate_uuid
        company = Company(
            id=generate_uuid(),
            name_ar=settings_dict.get("company_name_ar") or "شركة اعمار ليبيا لنقل الركاب",
            name_en=settings_dict.get("company_name_en") or "Emaar Libya",
            phone=settings_dict.get("company_phone"),
            email=settings_dict.get("company_email"),
            address=settings_dict.get("company_address"),
            city=settings_dict.get("company_city"),
        )
        session.add(company)

    repo = BaseRepository(session, Setting)
    for key, value in settings_dict.items():
        existing = session.query(Setting).filter(Setting.key == key).first()
        if existing:
            existing.value = value
        else:
            repo.create(key=key, value=value, value_type="string", category="general")

    session.commit()
    flash("تم حفظ الإعدادات بنجاح", "success")
    return redirect(url_for("settings.settings_view"))


# ============================================================
# BACKUP - نسخ احتياطي
# ============================================================

@settings_bp.route("/backup/full", methods=["POST"])
@login_required
def backup_full():
    """نسخ احتياطي كامل للمنظومة"""
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"full_backup_{timestamp}.db"
    filepath = os.path.join(BACKUP_DIR, filename)

    # نسخ قاعدة البيانات
    shutil.copy2(DB_PATH, filepath)
    size = os.path.getsize(filepath)
    flash(f"تم انشاء نسخة احتياطية كاملة: {filename} ({size // 1024} KB)", "success")
    return redirect(url_for("settings.settings_view"))


@settings_bp.route("/backup/section", methods=["POST"])
@login_required
def backup_section():
    """نسخ احتياطي لقسم معين"""
    ensure_backup_dir()
    section = request.form.get("section", "")
    if section not in SECTION_TABLES:
        flash("قسم غير صحيح", "danger")
        return redirect(url_for("settings.settings_view"))

    tables = SECTION_TABLES.get(section, [])
    if not tables:
        flash(f"لا توجد جداول مرتبطة بقسم {section}", "warning")
        return redirect(url_for("settings.settings_view"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{section}_{timestamp}.json"
    filepath = os.path.join(BACKUP_DIR, filename)

    # تصدير الجداول الى JSON
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    data = {}
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT * FROM {table}")
            rows = [dict(row) for row in cursor.fetchall()]
            data[table] = rows
        except sqlite3.OperationalError:
            data[table] = []
    conn.close()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    size = os.path.getsize(filepath)
    flash(f"تم انشاء نسخة احتياطية لقسم {section}: {filename} ({size // 1024} KB)", "success")
    return redirect(url_for("settings.settings_view"))


@settings_bp.route("/backup/download/<filename>")
@login_required
def backup_download(filename):
    """تحميل نسخة احتياطية"""
    filepath = os.path.normpath(os.path.join(BACKUP_DIR, filename))
    # حماية من Path Traversal
    if not filepath.startswith(os.path.normpath(BACKUP_DIR)):
        flash("مسار غير صحيح", "danger")
        return redirect(url_for("settings.settings_view"))
    if not os.path.exists(filepath):
        flash("الملف غير موجود", "danger")
        return redirect(url_for("settings.settings_view"))
    return send_file(filepath, as_attachment=True)


@settings_bp.route("/backup/delete/<filename>", methods=["POST"])
@login_required
def backup_delete(filename):
    """حذف نسخة احتياطية"""
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f"تم حذف النسخة الاحتياطية: {filename}", "success")
    else:
        flash("الملف غير موجود", "danger")
    return redirect(url_for("settings.settings_view"))


# ============================================================
# RESTORE - استيراد
# ============================================================

@settings_bp.route("/restore/full", methods=["POST"])
@login_required
def restore_full():
    """استعادة نسخة احتياطية كاملة"""
    backup_file = request.form.get("backup_file", "")
    filepath = os.path.normpath(os.path.join(BACKUP_DIR, backup_file))
    
    # حماية من Path Traversal
    if not filepath.startswith(os.path.normpath(BACKUP_DIR)):
        flash("مسار غير صحيح", "danger")
        return redirect(url_for("settings.settings_view"))
    
    if not os.path.exists(filepath) or not backup_file.endswith(".db"):
        flash("ملف غير صحيح", "danger")
        return redirect(url_for("settings.settings_view"))

    # انشاء نسخة احتياطية قبل الاستعادة
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_restore_backup = os.path.join(BACKUP_DIR, f"pre_restore_{timestamp}.db")
    shutil.copy2(DB_PATH, pre_restore_backup)

    # استعادة قاعدة البيانات
    shutil.copy2(filepath, DB_PATH)
    flash(f"تمت استعادة النسخة الاحتياطية: {backup_file}", "success")
    flash("يجب اعادة تشغيل الموقع لتطبيق التغييرات", "warning")
    return redirect(url_for("settings.settings_view"))


@settings_bp.route("/restore/upload", methods=["POST"])
@login_required
def restore_upload():
    """استيراد نسخة احتياطية من ملف"""
    if "backup_file" not in request.files:
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("settings.settings_view"))

    file = request.files["backup_file"]
    if file.filename == "":
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("settings.settings_view"))

    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if file.filename.endswith(".db"):
        # استعادة قاعدة بيانات كاملة
        filename = f"uploaded_full_{timestamp}.db"
        filepath = os.path.join(BACKUP_DIR, filename)
        file.save(filepath)

        # نسخ احتياطي قبل الاستعادة
        pre_backup = os.path.join(BACKUP_DIR, f"pre_restore_{timestamp}.db")
        shutil.copy2(DB_PATH, pre_backup)

        shutil.copy2(filepath, DB_PATH)
        flash(f"تم استيراد وتطبيق النسخة الاحتياطية: {file.filename}", "success")
        flash("يجب اعادة تشغيل الموقع لتطبيق التغييرات", "warning")

    elif file.filename.endswith(".json"):
        # استيراد بيانات قسم
        filename = f"uploaded_section_{timestamp}.json"
        filepath = os.path.join(BACKUP_DIR, filename)
        file.save(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        conn = sqlite3.connect(DB_PATH)
        # قائمة الجداول المسموح بها (حماية من SQL Injection)
        allowed_tables = {
            "marketing_work_orders", "marketing_work_order_buses", "marketing_work_order_annexes",
            "marketing_contracts", "marketing_clients", "marketing_trips",
            "marketing_school_driver_entitlements", "marketing_monthly_trip_sheets",
            "drivers", "driver_documents", "driver_licenses",
            "vehicles", "vehicle_maintenances", "vehicle_fuel", "vehicle_documents",
            "vehicle_insurances", "vehicle_inspection", "vehicle_violations",
            "vehicle_driver_logs",
            "employees", "employee_contracts", "employee_documents", "employee_attendance",
            "employee_vacations", "employee_penalties", "employee_loans",
            "employee_salaries", "employee_salary_items", "employee_promotions",
            "employee_trainings", "employee_evaluations", "employee_fingerprints",
            "employee_courses",
            "salary_scale", "salary_scale_items",
            "correspondences", "correspondence_attachments",
            "warehouses", "warehouse_items", "warehouse_transactions",
            "deleted_items", "users", "departments", "companies",
        }
        for table, rows in data.items():
            if table not in allowed_tables:
                flash(f"جدول غير مسموح به: {table} - تم تخطيه", "warning")
                continue
            if not rows:
                continue
            try:
                # حذف البيانات القديمة
                conn.execute(f"DELETE FROM {table}")
                # ادراج البيانات الجديدة
                if rows:
                    cols = rows[0].keys()
                    placeholders = ",".join(["?" for _ in cols])
                    insert_sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
                    for row in rows:
                        values = [row[c] for c in cols]
                        conn.execute(insert_sql, values)
            except sqlite3.OperationalError as e:
                flash(f"خطأ في استيراد جدول {table}: {str(e)}", "warning")
        conn.commit()
        conn.close()
        flash(f"تم استيراد بيانات من: {file.filename}", "success")
    else:
        flash("نوع الملف غير مدعوم (يدعم .db و .json)", "danger")

    return redirect(url_for("settings.settings_view"))


# ============================================================
# RESET - تصفير جميع البيانات
# ============================================================

@settings_bp.route("/reset-all", methods=["POST"])
@login_required
def reset_all_data():
    """حذف جميع بيانات المنظومة و تصفيرها"""
    from flask_login import current_user
    from src.core.security.auth_service import AuthService

    # التحقق من كلمة المرور
    password = request.form.get("password", "")
    username = current_user.username if current_user.is_authenticated else "admin"
    session = get_web_session()
    auth_service = AuthService(session)
    user = auth_service.authenticate(username, password)

    if not user:
        flash("كلمة المرور غير صحيحة", "danger")
        return redirect(url_for("settings.settings_view"))

    # انشاء نسخة احتياطية قبل التصفير
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_backup = os.path.join(BACKUP_DIR, f"pre_reset_{timestamp}.db")
    shutil.copy2(DB_PATH, pre_backup)

    # قائمة جميع الجداول القابلة للحذف (باستثناء الجداول النظامية)
    all_tables = [
        # اوامر التشغيل
        "marketing_work_order_buses", "marketing_work_order_annexes", "marketing_work_orders",
        # العقود والجهات
        "marketing_contracts", "marketing_clients",
        # الرحلات والمستحقات
        "marketing_trips", "marketing_school_driver_entitlements", "marketing_monthly_trip_sheets",
        # السائقين
        "driver_documents", "driver_licenses", "drivers",
        # المركبات
        "vehicle_maintenances", "vehicle_fuel", "vehicle_documents",
        "vehicle_insurances", "vehicle_inspection", "vehicle_violations",
        "vehicle_driver_logs", "vehicles",
        # الموارد البشرية
        "employee_fingerprints", "employee_courses", "recruitment_interviews",
        "recruitment_applicants", "recruitment_requests", "exit_reexit_requests",
        "employee_return_to_work", "employee_evaluations", "employee_trainings",
        "training_courses", "employee_promotions", "employee_salary_items",
        "employee_salaries", "salary_scale_items", "salary_scale",
        "employee_penalties", "employee_loans", "employee_vacations",
        "employee_attendance", "employee_documents", "employee_contracts", "employees",
        # العملاء
        "customers",
        # المراسلات
        "correspondence_attachments", "correspondences",
        # المخازن
        "warehouse_transactions", "warehouse_items", "warehouses",
        # المحذوفات
        "deleted_items",
    ]

    conn = sqlite3.connect(DB_PATH)
    deleted_count = 0
    for table in all_tables:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count > 0:
                conn.execute(f"DELETE FROM {table}")
                deleted_count += count
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

    flash(f"تم تصفير جميع بيانات المنظومة ({deleted_count} سجل). تم انشاء نسخة احتياطية: pre_reset_{timestamp}.db", "success")
    return redirect(url_for("settings.settings_view"))


# ============================================================
# إدارة خطوات الاعتماد
# ============================================================

@settings_bp.route("/approval-steps")
@login_required
def approval_steps_list():
    """عرض جميع خطوات الاعتماد"""
    from src.core.models.base_models import ApprovalStep, User
    with get_web_session() as session:
        steps = session.query(ApprovalStep).order_by(ApprovalStep.step_order).all()
        users = session.query(User).order_by(User.full_name_ar).all()
        return render_template("settings/approval_steps.html",
                             page_title="إدارة خطوات الاعتماد",
                             steps=steps,
                             users=users)


@settings_bp.route("/approval-steps/add", methods=["POST"])
@login_required
def approval_steps_add():
    """اضافة خطوة اعتماد جديدة"""
    from src.core.models.base_models import ApprovalStep
    with get_web_session() as session:
        step_order = int(request.form.get("step_order", 1))
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        required_approver_id = request.form.get("required_approver_id") or None
        color = request.form.get("color", "#667eea")
        description = request.form.get("description", "").strip()
        
        if not name:
            flash("اسم الخطوة مطلوب", "danger")
            return redirect(url_for("settings.approval_steps_list"))
        
        # التحقق من عدم تكرار الترتيب
        existing = session.query(ApprovalStep).filter(ApprovalStep.step_order == step_order).first()
        if existing:
            # ازاحة الخطوات التالية
            steps_to_shift = session.query(ApprovalStep).filter(
                ApprovalStep.step_order >= step_order
            ).order_by(ApprovalStep.step_order.desc()).all()
            for s in steps_to_shift:
                s.step_order += 1
        
        step = ApprovalStep(
            step_order=step_order,
            name=name,
            department=department or None,
            required_approver_id=required_approver_id,
            color=color,
            description=description or None,
        )
        session.add(step)
        session.commit()
        flash(f"تم اضافة خطوة الاعتماد: {name}", "success")
    return redirect(url_for("settings.approval_steps_list"))


@settings_bp.route("/approval-steps/<step_id>/edit", methods=["POST"])
@login_required
def approval_steps_edit(step_id):
    """تعديل خطوة اعتماد"""
    from src.core.models.base_models import ApprovalStep
    with get_web_session() as session:
        step = session.query(ApprovalStep).get(step_id)
        if not step:
            flash("خطوة الاعتماد غير موجودة", "danger")
            return redirect(url_for("settings.approval_steps_list"))
        
        step.name = request.form.get("name", step.name).strip()
        step.department = request.form.get("department", "").strip() or None
        step.required_approver_id = request.form.get("required_approver_id") or None
        step.color = request.form.get("color", step.color)
        step.description = request.form.get("description", "").strip() or None
        step.is_active = request.form.get("is_active") == "1"
        
        session.commit()
        flash(f"تم تعديل خطوة الاعتماد: {step.name}", "success")
    return redirect(url_for("settings.approval_steps_list"))


@settings_bp.route("/approval-steps/<step_id>/delete", methods=["POST"])
@login_required
def approval_steps_delete(step_id):
    """حذف خطوة اعتماد"""
    from src.core.models.base_models import ApprovalStep
    with get_web_session() as session:
        step = session.query(ApprovalStep).get(step_id)
        if not step:
            flash("خطوة الاعتماد غير موجودة", "danger")
            return redirect(url_for("settings.approval_steps_list"))
        
        name = step.name
        session.delete(step)
        
        # اعادة ترتيب الخطوات المتبقية
        remaining = session.query(ApprovalStep).filter(
            ApprovalStep.step_order > step.step_order
        ).order_by(ApprovalStep.step_order).all()
        for i, s in enumerate(remaining):
            s.step_order = step.step_order + i
        
        session.commit()
        flash(f"تم حذف خطوة الاعتماد: {name}", "success")
    return redirect(url_for("settings.approval_steps_list"))


@settings_bp.route("/approval-steps/<step_id>/toggle", methods=["POST"])
@login_required
def approval_steps_toggle(step_id):
    """تفعيل/تعطيل خطوة اعتماد"""
    from src.core.models.base_models import ApprovalStep
    with get_web_session() as session:
        step = session.query(ApprovalStep).get(step_id)
        if not step:
            flash("خطوة الاعتماد غير موجودة", "danger")
            return redirect(url_for("settings.approval_steps_list"))
        
        step.is_active = not step.is_active
        status = "تم تفعيل" if step.is_active else "تم تعطيل"
        session.commit()
        flash(f"{status} خطوة الاعتماد: {step.name}", "success")
    return redirect(url_for("settings.approval_steps_list"))


@settings_bp.route("/approval-steps/<step_id>/move", methods=["POST"])
@login_required
def approval_steps_move(step_id):
    """تحريك خطوة الاعتماد (اعلى/اسفل)"""
    from src.core.models.base_models import ApprovalStep
    direction = request.form.get("direction", "up")
    with get_web_session() as session:
        step = session.query(ApprovalStep).get(step_id)
        if not step:
            flash("خطوة الاعتماد غير موجودة", "danger")
            return redirect(url_for("settings.approval_steps_list"))
        
        if direction == "up" and step.step_order > 1:
            # التبادل مع الخطوة السابقة
            prev_step = session.query(ApprovalStep).filter(
                ApprovalStep.step_order == step.step_order - 1
            ).first()
            if prev_step:
                prev_step.step_order += 1
                step.step_order -= 1
                session.commit()
                flash(f"تم تحريك {step.name} الى الاعلى", "success")
        elif direction == "down":
            # التبادل مع الخطوة التالية
            next_step = session.query(ApprovalStep).filter(
                ApprovalStep.step_order == step.step_order + 1
            ).first()
            if next_step:
                next_step.step_order -= 1
                step.step_order += 1
                session.commit()
                flash(f"تم تحريك {step.name} الى الاسفل", "success")
    return redirect(url_for("settings.approval_steps_list"))


@settings_bp.route("/api/approval-steps")
def api_approval_steps():
    """API لجلب خطوات الاعتماد النشطة"""
    from src.core.models.base_models import ApprovalStep
    with get_web_session() as session:
        steps = session.query(ApprovalStep).filter(
            ApprovalStep.is_active == True
        ).order_by(ApprovalStep.step_order).all()
        return jsonify([{
            "id": s.id,
            "step_order": s.step_order,
            "name": s.name,
            "department": s.department,
            "color": s.color,
        } for s in steps])
