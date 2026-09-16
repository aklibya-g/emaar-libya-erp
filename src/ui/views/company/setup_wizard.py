from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QWidget, QGridLayout,
    QTextEdit, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from src.core.database.connection import session_scope
from src.core.models.base_models import Company, Department, Role, User
from src.core.repositories.base_repository import BaseRepository
from src.core.security.auth_service import hash_password


class SetupWizard(QDialog):
    setup_complete = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إعداد النظام - Emaar Libya ERP")
        self.setMinimumSize(650, 550)
        self._current_step = 0
        self._data = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #1a1d23;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header = QLabel("إعداد النظام الأولي")
        header.setStyleSheet("color: #e4e6eb; font-size: 22px; font-weight: bold;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self._step_label = QLabel("الخطوة 1 من 4: بيانات الشركة")
        self._step_label.setStyleSheet("color: #60a5fa; font-size: 13px;")
        self._step_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._step_label)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._step_company())
        self._stack.addWidget(self._step_admin())
        self._stack.addWidget(self._step_departments())
        self._stack.addWidget(self._step_complete())

        nav = QHBoxLayout()
        nav.addStretch()

        self._prev_btn = QPushButton("السابق")
        self._prev_btn.setObjectName("secondaryButton")
        self._prev_btn.clicked.connect(self._prev_step)
        self._prev_btn.setEnabled(False)
        nav.addWidget(self._prev_btn)

        self._next_btn = QPushButton("التالي")
        self._next_btn.clicked.connect(self._next_step)
        nav.addWidget(self._next_btn)

        layout.addLayout(nav)

    def _step_company(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        self._comp_name = QLineEdit()
        self._comp_name.setPlaceholderText("شركة إعمار ليبيا لنقل الركاب")
        layout.addWidget(self._make_label("اسم الشركة *"))
        layout.addWidget(self._comp_name)

        self._comp_name_en = QLineEdit()
        self._comp_name_en.setPlaceholderText("Emaar Libya Passenger Transport")
        layout.addWidget(self._make_label("الاسم الإنجليزي"))
        layout.addWidget(self._comp_name_en)

        self._comp_address = QLineEdit()
        self._comp_address.setPlaceholderText("طرابلس، ليبيا")
        layout.addWidget(self._make_label("العنوان"))
        layout.addWidget(self._comp_address)

        self._comp_phone = QLineEdit()
        self._comp_phone.setPlaceholderText("+218 XX XXX XXXX")
        layout.addWidget(self._make_label("الهاتف"))
        layout.addWidget(self._comp_phone)

        self._comp_email = QLineEdit()
        self._comp_email.setPlaceholderText("info@emaarlibya.com")
        layout.addWidget(self._make_label("البريد الإلكتروني"))
        layout.addWidget(self._comp_email)

        return w

    def _step_admin(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        title = QLabel("إنشاء حساب المسؤول الأول")
        title.setStyleSheet("color: #e4e6eb; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self._admin_name = QLineEdit()
        self._admin_name.setPlaceholderText("الاسم الكامل")
        layout.addWidget(self._make_label("الاسم الكامل *"))
        layout.addWidget(self._admin_name)

        self._admin_username = QLineEdit()
        self._admin_username.setPlaceholderText("admin")
        layout.addWidget(self._make_label("اسم المستخدم *"))
        layout.addWidget(self._admin_username)

        self._admin_pass = QLineEdit()
        self._admin_pass.setEchoMode(QLineEdit.Password)
        self._admin_pass.setPlaceholderText("كلمة المرور")
        layout.addWidget(self._make_label("كلمة المرور *"))
        layout.addWidget(self._admin_pass)

        self._admin_pass2 = QLineEdit()
        self._admin_pass2.setEchoMode(QLineEdit.Password)
        self._admin_pass2.setPlaceholderText("تأكيد كلمة المرور")
        layout.addWidget(self._make_label("تأكيد كلمة المرور *"))
        layout.addWidget(self._admin_pass2)

        return w

    def _step_departments(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        title = QLabel("الأقسام الافتراضية")
        title.setStyleSheet("color: #e4e6eb; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        default_depts = [
            ("ADM", "الشؤون الإدارية", "Administrative Affairs"),
            ("HR", "الموارد البشرية", "Human Resources"),
            ("FIN", "المالية", "Finance"),
            ("OPS", "التشغيل والنقل", "Operations & Transport"),
            ("WH", "المخازن", "Warehouses"),
            ("IT", "تقنية المعلومات", "Information Technology"),
            ("COR", "المراسلات والأرشيف", "Correspondence & Archive"),
        ]
        self._dept_entries = []
        for code, ar, en in default_depts:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{code}:"))
            inp = QLineEdit(ar)
            inp.setMinimumWidth(250)
            row.addWidget(inp)
            row.addWidget(QLabel(en))
            row.addStretch()
            layout.addLayout(row)
            self._dept_entries.append((code, inp, en))

        layout.addStretch()
        return w

    def _step_complete(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)

        done = QLabel("✓")
        done.setStyleSheet("color: #10b981; font-size: 64px;")
        done.setAlignment(Qt.AlignCenter)
        layout.addWidget(done)

        t = QLabel("تم الإعداد بنجاح!")
        t.setStyleSheet("color: #e4e6eb; font-size: 20px; font-weight: bold;")
        t.setAlignment(Qt.AlignCenter)
        layout.addWidget(t)

        sub = QLabel("يمكنك الآن استخدام النظام")
        sub.setStyleSheet("color: #6b7280; font-size: 14px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        return w

    def _make_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 500;")
        return l

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._stack.setCurrentIndex(self._current_step)
            self._update_nav()

    def _next_step(self):
        if self._current_step == 0:
            if not self._comp_name.text().strip():
                QMessageBox.warning(self, "خطأ", "الرجاء إدخال اسم الشركة")
                return
        elif self._current_step == 1:
            if not all([self._admin_name.text(), self._admin_username.text(), self._admin_pass.text()]):
                QMessageBox.warning(self, "خطأ", "الرجاء ملء جميع الحقول")
                return
            if self._admin_pass.text() != self._admin_pass2.text():
                QMessageBox.warning(self, "خطأ", "كلمتا المرور غير متطابقتين")
                return

        self._current_step += 1
        self._stack.setCurrentIndex(self._current_step)
        self._update_nav()

        if self._current_step == 3:
            self._save_data()

    def _update_nav(self):
        self._prev_btn.setEnabled(self._current_step > 0)
        if self._current_step == 3:
            self._next_btn.setText("ابدأ الاستخدام")
            self._next_btn.clicked.disconnect()
            self._next_btn.clicked.connect(self._finish)
        else:
            self._next_btn.setText("التالي")

        step_titles = [
            "الخطوة 1 من 4: بيانات الشركة",
            "الخطوة 2 من 4: حساب المسؤول",
            "الخطوة 3 من 4: الأقسام",
            "الخطوة 4 من 4: ملخص",
        ]
        self._step_label.setText(step_titles[self._current_step])

    def _save_data(self):
        try:
            with session_scope() as session:
                company_repo = BaseRepository(session, Company)
                company = company_repo.create(
                    name_ar=self._comp_name.text().strip(),
                    name_en=self._comp_name_en.text().strip() or None,
                    address=self._comp_address.text().strip() or None,
                    phone=self._comp_phone.text().strip() or None,
                    email=self._comp_email.text().strip() or None,
                    country="Libya",
                )

                super_admin_role = BaseRepository(session, Role).create(
                    name="Super Admin",
                    name_ar="مسؤول النظام",
                    description="صلاحيات كاملة",
                    is_system=True,
                )

                BaseRepository(session, User).create(
                    username=self._admin_username.text().strip(),
                    password_hash=hash_password(self._admin_pass.text()),
                    full_name_ar=self._admin_name.text().strip(),
                    role_id=super_admin_role.id,
                )

                dept_repo = BaseRepository(session, Department)
                for code, inp, en_name in self._dept_entries:
                    name = inp.text().strip()
                    if name:
                        dept_repo.create(
                            code=code,
                            name_ar=name,
                            name_en=en_name,
                            company_id=company.id,
                        )

                from src.core.models.base_models import Setting
                settings_repo = BaseRepository(session, Setting)
                settings_repo.create(
                    key="company_name",
                    value=self._comp_name.text().strip(),
                    category="company",
                )
                settings_repo.create(key="setup_complete", value="true", category="system")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ البيانات: {str(e)}")

    def _finish(self):
        self.setup_complete.emit()
        self.accept()
