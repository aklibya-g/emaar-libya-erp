import sys
sys.path.insert(0, 'E:/EmarrCoSys')

from src.core.database.connection import SessionLocal
from src.core.models.hr_models import (
    LeaveType, DocumentCategory, DocumentType, WorkShift,
    DisciplinaryType, HRRule, Holiday,
)


def seed_hr_data():
    session = SessionLocal()
    try:
        # Leave Types
        leave_types = [
            ("annual", "إجازة سنوية", "Annual Leave", 30, True, False, None, False),
            ("sick", "إجازة مرضية", "Sick Leave", 15, True, False, None, True),
            ("emergency", "إجازة طارئة", "Emergency Leave", 12, True, False, 3, False),
            ("special", "إجازة خاصة", "Special Leave", 7, True, False, None, False),
            ("maternity", "إجازة أمومة", "Maternity Leave", 90, True, False, None, True),
            ("unpaid", "إجازة بدون مرتب", "Unpaid Leave", 0, False, False, None, False),
            ("hajj", "إجازة حج", "Hajj Leave", 15, True, False, None, True),
            ("marriage", "إجازة زواج", "Marriage Leave", 3, True, False, None, True),
            ("bereavement", "إجازة وفاة", "Bereavement Leave", 5, True, False, None, False),
            ("mission", "مأمورية", "Mission", 0, True, False, None, True),
        ]
        for code, name_ar, name_en, days, paid, accum, max_consec, req_doc in leave_types:
            if not session.query(LeaveType).filter(LeaveType.code == code).first():
                session.add(LeaveType(
                    code=code, name_ar=name_ar, name_en=name_en,
                    default_days=days, is_paid=paid, is_accumulative=accum,
                    max_consecutive_days=max_consec, requires_document=req_doc,
                ))
        print(f"  Leave types: {len(leave_types)}")

        # Document Categories
        doc_categories = [
            ("identity", "الهوية", "Identity", 1),
            ("passport", "جواز السفر", "Passport", 2),
            ("national_id", "الرقم الوطني", "National ID", 3),
            ("personal_card", "البطاقة الشخصية", "Personal Card", 4),
            ("birth_cert", "شهادة الميلاد", "Birth Certificate", 5),
            ("family_status", "الوضع العائلي", "Family Status", 6),
            ("employment", "مستندات التوظيف", "Employment Documents", 7),
            ("qualification", "المؤهلات العلمية", "Qualifications", 8),
            ("contract", "عقد العمل", "Employment Contract", 9),
            ("health", "المستندات الصحية", "Health Documents", 10),
            ("onboarding", "المباشرة", "Onboarding", 11),
            ("leaves", "الإجازات", "Leave Documents", 12),
            ("disciplinary", "الجزاءات", "Disciplinary", 13),
            ("promotions", "الترقيات", "Promotions", 14),
            ("transfers", "النقل", "Transfers", 15),
            ("other", "أخرى", "Other", 16),
        ]
        cat_ids = {}
        for code, name_ar, name_en, sort in doc_categories:
            existing = session.query(DocumentCategory).filter(DocumentCategory.code == code).first()
            if not existing:
                cat = DocumentCategory(code=code, name_ar=name_ar, name_en=name_en, sort_order=sort)
                session.add(cat)
                session.flush()
                cat_ids[code] = cat.id
            else:
                cat_ids[code] = existing.id
        print(f"  Document categories: {len(doc_categories)}")

        # Document Types
        doc_types = [
            ("identity", "passport", "جواز السفر", "Passport", True, True, 60),
            ("identity", "national_id_card", "الرقم الوطني", "National ID", True, True, 60),
            ("identity", "personal_card", "البطاقة الشخصية", "Personal Card", True, True, 60),
            ("identity", "birth_cert", "شهادة الميلاد", "Birth Certificate", True, False, None),
            ("identity", "family_status_doc", "الوضع العائلي", "Family Status", False, True, 12),
            ("employment", "cv", "السيرة الذاتية", "CV", True, False, None),
            ("employment", "appointment_dec", "قرار التعيين", "Appointment Decision", True, False, None),
            ("employment", "start_work_dec", "قرار المباشرة", "Start Work Decision", True, False, None),
            ("contract", "employment_contract", "عقد العمل", "Employment Contract", True, True, 12),
            ("health", "health_cert", "الشهادة الصحية", "Health Certificate", True, True, 12),
            ("health", "medical_exam", "الفحص الطبي", "Medical Exam", False, True, 12),
            ("health", "fitness_cert", "اللياقة الطبية", "Fitness Certificate", False, True, 12),
            ("qualification", "degree", "المؤهل العلمي", "Academic Degree", True, False, None),
            ("qualification", "experience_cert", "شهادة خبرة", "Experience Certificate", False, False, None),
            ("qualification", "training_cert", "شهادة تدريب", "Training Certificate", False, False, None),
        ]
        for cat_code, type_code, name_ar, name_en, required, has_expiry, validity in doc_types:
            if cat_code in cat_ids:
                existing = session.query(DocumentType).filter(
                    DocumentType.category_id == cat_ids[cat_code],
                    DocumentType.code == type_code
                ).first()
                if not existing:
                    session.add(DocumentType(
                        category_id=cat_ids[cat_code], code=type_code,
                        name_ar=name_ar, name_en=name_en,
                        is_required=required, has_expiry=has_expiry,
                        default_validity_months=validity,
                    ))
        print(f"  Document types: {len(doc_types)}")

        # Work Shifts
        shifts = [
            ("morning", "وردية صباحية", "Morning Shift", "08:00", "14:00", 30),
            ("evening", "وردية مسائية", "Evening Shift", "14:00", "20:00", 30),
            ("night", "وردية ليلية", "Night Shift", "20:00", "02:00", 30),
            ("full_day", "دوام كامل", "Full Day", "08:00", "14:00", 60),
        ]
        for code, name_ar, name_en, start, end, brk in shifts:
            if not session.query(WorkShift).filter(WorkShift.code == code).first():
                from datetime import time as dt_time
                sh, sm = map(int, start.split(':'))
                eh, em = map(int, end.split(':'))
                session.add(WorkShift(
                    code=code, name_ar=name_ar, name_en=name_en,
                    start_time=dt_time(sh, sm), end_time=dt_time(eh, em),
                    break_minutes=brk,
                ))
        print(f"  Work shifts: {len(shifts)}")

        # Disciplinary Types
        disc_types = [
            ("verbal_warning", "إنذار شفهي", "Verbal Warning", 1, False, None),
            ("written_warning", "إنذار كتابي", "Written Warning", 2, False, None),
            ("final_warning", "إنذار نهائي", "Final Warning", 3, False, None),
            ("deduction", "خصم من الراتب", "Salary Deduction", 2, True, 5),
            ("suspension", "إيقاف عن العمل", "Suspension", 3, True, 15),
            ("termination", "إنهاء خدمة", "Termination", 3, False, None),
        ]
        for code, name_ar, name_en, severity, can_deduct, max_days in disc_types:
            if not session.query(DisciplinaryType).filter(DisciplinaryType.code == code).first():
                session.add(DisciplinaryType(
                    code=code, name_ar=name_ar, name_en=name_en,
                    severity_level=severity, can_deduct_salary=can_deduct,
                    max_deduction_days=max_days,
                ))
        print(f"  Disciplinary types: {len(disc_types)}")

        # HR Rules
        hr_rules = [
            ("attendance", "work_start_time", "08:00", "time", "بداية الدوام"),
            ("attendance", "work_end_time", "14:00", "time", "نهاية الدوام"),
            ("attendance", "grace_period_minutes", "10", "int", "فترة السماح بال دقائق"),
            ("attendance", "late_threshold_minor", "30", "int", "حد التأخير الجسيم (دقيقة)"),
            ("attendance", "weekly_work_days", "6", "int", "عدد أيام العمل الأسبوعية"),
            ("attendance", "weekend_day", "Friday", "string", "إجازة أسبوعية"),
            ("overtime", "max_daily_overtime", "4", "float", "حد العمل الإضافي اليومي (ساعات)"),
            ("overtime", "overtime_rate", "1.5", "float", "معدل أجر العمل الإضافي"),
            ("overtime", "weekend_overtime_rate", "2.0", "float", "معدل أجر العمل الإضافي أيام الراحة"),
            ("leave", "max_carry_over_days", "10", "int", "حد الإجازات المحولة للسنة التالية"),
            ("leave", "min_leave_notice_days", "3", "int", "الحد الأدنى لإشعار الإجازة"),
            ("general", "company_name", "شركة امارات ليبيا لنقل الركاب", "string", "اسم الشركة"),
            ("general", "legal_reference", "قانون علاقات العمل رقم 12 لسنة 2010", "string", "المرجع القانوني"),
        ]
        for cat, key, val, vtype, desc in hr_rules:
            if not session.query(HRRule).filter(HRRule.category == cat, HRRule.rule_key == key).first():
                session.add(HRRule(
                    category=cat, rule_key=key, rule_value=val,
                    rule_value_type=vtype, description_ar=desc,
                ))
        print(f"  HR rules: {len(hr_rules)}")

        # Holidays 2026
        holidays_2026 = [
            ("رأس السنة الهجرية", "2026-07-17"),
            ("عيد المولد النبوي", "2026-09-05"),
            ("استقلال ليبيا", "2026-12-24"),
        ]
        for name, date_str in holidays_2026:
            from datetime import date as dt_date
            h_date = dt_date.fromisoformat(date_str)
            if not session.query(Holiday).filter(Holiday.holiday_date == h_date).first():
                session.add(Holiday(name_ar=name, holiday_date=h_date, year=2026, is_recurring=False))
        print(f"  Holidays: {len(holidays_2026)}")

        session.commit()
        print("\nHR seed data completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_hr_data()
