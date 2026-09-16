from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.core.models.base_models import User
from src.core.security.auth_service import AuthService
from src.core.database.connection import session_scope


class LoginWindow(QDialog):
    login_success = Signal(User)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 - Emaar Libya ERP")
        self.setFixedSize(420, 520)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #0f1117;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        logo_label = QLabel("\u2601")
        logo_label.setStyleSheet("color: #3b82f6; font-size: 48px;")
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        layout.addSpacing(16)

        title = QLabel("\u0645\u0646\u0638\u0648\u0645\u0629 \u0625\u0639\u0645\u0627\u0631 \u0644\u064A\u0628\u064A\u0627")
        title.setStyleSheet("color: #e4e6eb; font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("\u0644\u0646\u0642\u0644 \u0627\u0644\u0631\u0643\u0627\u0628")
        subtitle.setStyleSheet("color: #6b7280; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(40)

        username_label = QLabel("\u0627\u0644\u0645\u0633\u062A\u062E\u062F\u0645")
        username_label.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 500;")
        layout.addWidget(username_label)

        layout.addSpacing(6)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("\u0623\u062F\u062E\u0644 \u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062A\u062E\u062F\u0645")
        self._username_input.setStyleSheet(
            "QLineEdit { background-color: #1f2937; border: 1px solid #2a2d35; "
            "border-radius: 8px; padding: 10px 14px; color: #e4e6eb; font-size: 14px; }"
            "QLineEdit:focus { border-color: #3b82f6; }"
        )
        self._username_input.setMinimumHeight(44)
        layout.addWidget(self._username_input)

        layout.addSpacing(16)

        password_label = QLabel("\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631")
        password_label.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 500;")
        layout.addWidget(password_label)

        layout.addSpacing(6)

        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("\u0623\u062F\u062E\u0644 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631")
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setStyleSheet(
            "QLineEdit { background-color: #1f2937; border: 1px solid #2a2d35; "
            "border-radius: 8px; padding: 10px 14px; color: #e4e6eb; font-size: 14px; }"
            "QLineEdit:focus { border-color: #3b82f6; }"
        )
        self._password_input.setMinimumHeight(44)
        self._password_input.returnPressed.connect(self._on_login)
        layout.addWidget(self._password_input)

        layout.addSpacing(8)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        layout.addSpacing(20)

        login_btn = QPushButton("\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644")
        login_btn.setMinimumHeight(48)
        login_btn.setStyleSheet(
            "QPushButton { background-color: #1e40af; color: white; border-radius: 8px; "
            "font-size: 15px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2563eb; }"
            "QPushButton:pressed { background-color: #1d4ed8; }"
        )
        login_btn.clicked.connect(self._on_login)
        layout.addWidget(login_btn)

        layout.addStretch()

        version = QLabel("v1.0.0")
        version.setStyleSheet("color: #374151; font-size: 10px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        self._username_input.setFocus()

    def _on_login(self):
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            self._show_error("\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u062F\u062E\u0648\u0644 \u0645\u0637\u0644\u0648\u0628\u0629")
            return

        with session_scope() as session:
            auth_service = AuthService(session)
            user = auth_service.authenticate(username, password)

            if user:
                auth_service.log_audit(
                    user_id=user.id,
                    username=user.username,
                    action="login",
                    module="auth",
                )
                self.login_success.emit(user)
                self.accept()
            else:
                self._show_error(
                    "\u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062A\u062E\u062F\u0645 \u0623\u0648 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u063A\u064A\u0631 \u0635\u062D\u064A\u062D\u0629"
                )

    def _show_error(self, message: str):
        self._error_label.setText(message)
        self._error_label.show()
