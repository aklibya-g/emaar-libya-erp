from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.app.config import settings, ensure_directories
from src.core.database.connection import init_database, session_scope
from src.core.models.base_models import Setting, Company
from src.ui.main.main_window import MainWindow
from src.ui.views.auth.login_window import LoginWindow
from src.ui.views.company.setup_wizard import SetupWizard
from src.ui.views.dashboard.dashboard_view import DashboardView
from src.ui.views.employees.employee_list import EmployeeListView
from src.ui.views.company.department_view import DepartmentListView
from src.ui.views.correspondence.correspondence_list import CorrespondenceListView
from src.ui.themes.dark_theme import DARK_THEME


def is_setup_complete() -> bool:
    try:
        with session_scope() as session:
            s = session.query(Setting).filter(Setting.key == "setup_complete").first()
            return s is not None and s.value == "true"
    except Exception:
        return False


def run_wizard(app: QApplication) -> bool:
    from PySide6.QtWidgets import QDialog
    wizard = SetupWizard()
    result = wizard.exec()
    return result == QDialog.Accepted


def main():
    ensure_directories()
    init_database()

    app = QApplication(sys.argv)
    app.setApplicationName("Emaar Libya ERP")
    app.setOrganizationName("Emaar Libya")
    app.setStyleSheet(DARK_THEME)

    if not is_setup_complete():
        if not run_wizard(app):
            sys.exit(0)

    login = LoginWindow()
    if login.exec() != LoginWindow.Accepted:
        sys.exit(0)

    user = login._user if hasattr(login, "_user") else None
    window = MainWindow(user=user)

    dashboard = DashboardView()
    window.add_page("dashboard", dashboard)

    emp_list = EmployeeListView()
    window.add_page("employees", emp_list)

    dept_list = DepartmentListView()
    window.add_page("departments", dept_list)

    placeholder_modules = [
        "drivers", "customers", "administration",
        "warehouses", "documents", "templates", "signatures",
        "reports", "notifications", "users", "backup", "settings",
    ]
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
    for mod in placeholder_modules:
        placeholder = QWidget()
        vl = QVBoxLayout(placeholder)
        lbl = QLabel(f"\u2714  {mod.replace('_', ' ').title()}")
        lbl.setStyleSheet("color: #e4e6eb; font-size: 24px;")
        lbl.setAlignment(Qt.AlignCenter)
        vl.addWidget(lbl)
        window.add_page(mod, placeholder)

    cor_list = CorrespondenceListView()
    window.add_page("correspondence", cor_list)

    window._sidebar.set_active("dashboard")
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
