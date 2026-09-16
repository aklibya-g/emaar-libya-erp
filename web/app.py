from __future__ import annotations

import os
from flask import Flask
from flask_login import LoginManager
from src.core.database.connection import init_database, SessionLocal
from src.core.models.base_models import User
from src.app.config import ensure_directories, settings as app_settings


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


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["SECRET_KEY"] = app_settings.security.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = app_settings.database.url
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    ensure_directories()
    init_database()

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "الرجاء تسجيل الدخول"
    login_manager.login_message_category = "warning"

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

    from web.routes.auth import auth_bp
    from web.routes.dashboard import dashboard_bp
    from web.routes.employees import employees_bp
    from web.routes.correspondence import correspondence_bp
    from web.routes.drivers import drivers_bp
    from web.routes.customers import customers_bp
    from web.routes.warehouses import warehouses_bp
    from web.routes.departments import departments_bp
    from web.routes.settings import settings_bp
    from web.routes.users import users_bp
    from web.routes.reports import reports_bp

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

    @app.context_processor
    def inject_globals():
        return {
            "app_name": "منظومة امارات ليبيا",
            "company_name": "شركة امارات ليبيا لنقل الركاب",
        }

    return app
