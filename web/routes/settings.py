from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from src.core.database.connection import session_scope
from src.core.models.base_models import Setting, Company
from src.core.repositories.base_repository import BaseRepository

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/")
@login_required
def settings_view():
    with session_scope() as session:
        settings_list = session.query(Setting).order_by(Setting.category, Setting.key).all()
        company = session.query(Company).filter(Company.is_deleted == False).first()
        settings_dict = {s.key: s.value for s in settings_list}
    return render_template("settings/index.html", settings_list=settings_list, settings_dict=settings_dict, company=company)


@settings_bp.route("/update", methods=["POST"])
@login_required
def settings_update():
    with session_scope() as session:
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
                name_ar=settings_dict.get("company_name_ar") or "شركة امارات ليبيا لنقل الركاب",
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

        flash("تم حفظ الإعدادات بنجاح", "success")

    return redirect(url_for("settings.settings_view"))
