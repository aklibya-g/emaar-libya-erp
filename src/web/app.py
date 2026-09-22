from __future__ import annotations

import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from src.core.database.connection import init_database, SessionLocal, get_web_session, close_web_session
from src.core.models.base_models import User
from src.app.config import ensure_directories, settings as app_settings


def user_is_admin(user) -> bool:
    if getattr(user, "username", None) == "admin":
        return True
    role = getattr(user, "role", None)
    if role:
        role_name = getattr(role, "name", "") or ""
        role_name_ar = getattr(role, "name_ar", "") or ""
        admin_keywords = ["admin", "super", "general manager", "مدير", "نظام", "عام"]
        for kw in admin_keywords:
            if kw.lower() in role_name.lower() or kw.lower() in role_name_ar.lower():
                return True
    return False


class FlaskUser:
    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.full_name_ar = user.full_name_ar
        self.full_name_en = user.full_name_en
        self.role_id = user.role_id
        self.department_id = user.department_id
        self.employee_id = user.employee_id
        self.email = user.email
        self.role = user.role

    def get_id(self):
        return self.id

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_admin(self):
        return user_is_admin(self)

    @property
    def role_name(self):
        return self.role.name if self.role else ""

    @property
    def is_finance(self):
        if self.username == "admin":
            return True
        if self.department and self.department.code == "FIN":
            return True
        if self.role:
            role_name = getattr(self.role, 'name', '') or ''
            role_name_ar = getattr(self.role, 'name_ar', '') or ''
            finance_keywords = ['finance', 'financial', 'مالية', 'مالي']
            for kw in finance_keywords:
                if kw.lower() in role_name.lower() or kw.lower() in role_name_ar.lower():
                    return True
        return False


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["SECRET_KEY"] = app_settings.security.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = app_settings.database.get_url()
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    app.jinja_env.add_extension('jinja2.ext.do')
    app.url_map.strict_slashes = False

    ensure_directories()
    init_database()

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "الرجاء تسجيل الدخول"
    login_manager.login_message_category = "warning"

    csrf = CSRFProtect()
    csrf.init_app(app)
    app.csrf = csrf

    @login_manager.user_loader
    def load_user(user_id: str):
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id, User.is_active == True, User.is_deleted == False).first()
            if user:
                return FlaskUser(user)
            return None
        finally:
            session.close()

    from src.web.routes.auth import auth_bp
    from src.web.routes.dashboard import dashboard_bp
    from src.web.routes.employees import employees_bp
    from src.web.routes.correspondence import correspondence_bp
    from src.web.routes.drivers import drivers_bp
    from src.web.routes.customers import customers_bp
    from src.web.routes.warehouses import warehouses_bp
    from src.web.routes.departments import departments_bp
    from src.web.routes.settings import settings_bp
    from src.web.routes.users import users_bp
    from src.web.routes.reports import reports_bp
    from src.web.routes.hr import hr_bp
    from src.web.routes.driver_hr import driver_hr_bp
    from src.web.routes.vehicles import vehicle_bp
    from src.web.routes.marketing import marketing_bp
    from src.web.routes.movement import movement_bp
    from src.web.routes.recycle_bin import recycle_bp
    from src.web.routes.finance import finance_bp
    from src.web.routes.maintenance import maintenance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(correspondence_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(warehouses_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(driver_hr_bp)
    app.register_blueprint(vehicle_bp)
    app.register_blueprint(marketing_bp)

    csrf.exempt(app.view_functions["hr.attendance_cell_save"])
    csrf.exempt(app.view_functions["hr.attendance_approve"])
    csrf.exempt(app.view_functions["marketing.trips_approve"])
    app.register_blueprint(movement_bp)
    app.register_blueprint(recycle_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(maintenance_bp)
    csrf.exempt(app.view_functions["finance.generate_claims"])
    csrf.exempt(app.view_functions["finance.add_receipt"])
    csrf.exempt(app.view_functions["finance.confirm_receipt"])
    csrf.exempt(app.view_functions["finance.approve_claim"])
    csrf.exempt(app.view_functions["finance.pay_payout"])

    @app.before_request
    def open_session():
        get_web_session()

    @app.teardown_appcontext
    def close_session(exc=None):
        close_web_session()

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from src.web.contract_types import DEFAULT_CONTRACT_TYPES, DEFAULT_ACTIVITY_TYPES, get_contract_types, get_activity_types
        sidebar_perms = {}
        corr_perms = {}
        unread_notifications = 0
        pending_driver_approvals = 0
        is_movement = False
        movement_pending_drivers = 0
        movement_rejected_drivers = 0
        driver_contract_types = DEFAULT_CONTRACT_TYPES
        driver_activity_types = DEFAULT_ACTIVITY_TYPES
        if current_user.is_authenticated:
            session = get_web_session()
            from src.core.models.base_models import UserSidebarPermission, UserCorrespondencePermission, Notification
            for sp in session.query(UserSidebarPermission).filter(UserSidebarPermission.user_id == current_user.id).all():
                sidebar_perms[sp.module_name] = sp
            for cp in session.query(UserCorrespondencePermission).filter(UserCorrespondencePermission.user_id == current_user.id).all():
                corr_perms[cp.target_department_id] = cp
            unread_notifications = session.query(Notification).filter(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            ).count()
            is_movement = any(
                m.module_name == "movement" and m.can_view
                for m in sidebar_perms.values()
            )
            if current_user.is_admin:
                from src.core.models.base_models import Driver as _Driver
                pending_driver_approvals = session.query(_Driver).filter(
                    _Driver.is_deleted == False,
                    _Driver.approval_status == "pending",
                ).count()
            if is_movement:
                from src.core.models.base_models import Driver as _Driver
                movement_pending_drivers = session.query(_Driver).filter(
                    _Driver.is_deleted == False,
                    _Driver.approval_status == "pending",
                ).count()
                movement_rejected_drivers = session.query(_Driver).filter(
                    _Driver.is_deleted == False,
                    _Driver.approval_status == "rejected",
                ).count()
            try:
                driver_contract_types = get_contract_types(session)
                driver_activity_types = get_activity_types(session)
            except Exception:
                driver_contract_types = DEFAULT_CONTRACT_TYPES
                driver_activity_types = DEFAULT_ACTIVITY_TYPES
        return {
            "app_name": "منظومة امارات ليبيا",
            "company_name": "شركة امارات ليبيا لنقل الركاب",
            "sidebar_perms": sidebar_perms,
            "corr_perms": corr_perms,
            "unread_notifications": unread_notifications,
            "pending_driver_approvals": pending_driver_approvals,
            "is_movement": is_movement,
            "movement_pending_drivers": movement_pending_drivers,
            "movement_rejected_drivers": movement_rejected_drivers,
            "driver_contract_types": driver_contract_types,
            "driver_activity_types": driver_activity_types,
        }

    return app
