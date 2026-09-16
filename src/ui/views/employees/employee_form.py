from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QPushButton, QGridLayout,
    QGroupBox, QScrollArea, QFrame, QMessageBox, QDialog,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from src.core.database.connection import session_scope
from src.core.models.base_models import Employee, Department, Position
from src.core.repositories.base_repository import BaseRepository


class EmployeeForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, employee_id: str = None):
        super().__init__(parent)
        self._employee_id = employee_id
        self._is_edit = employee_id is not None
        self.setWindowTitle(
            "\u062A\u0639\u062F\u064A\u0644 \u0645\u0648\u0638\u0641" if self._is_edit
            else "\u0645\u0648\u0638\u0641 \u062C\u062F\u064A\u062F"
        )
        self.setMinimumSize(700, 750)
        self._setup_ui()
        if self._is_edit:
            self._load_employee()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(10)

        self._number = QLineEdit()
        self._number.setPlaceholderText("\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0648\u0638\u064A\u0641\u064A")
        grid.addWidget(self._label("\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0648\u0638\u064A\u0641\u064A *"), 0, 0)
        grid.addWidget(self._number, 0, 1)

        self._national_id = QLineEdit()
        self._national_id.setPlaceholderText("\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0648\u0637\u0646\u064A")
        grid.addWidget(self._label("\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0648\u0637\u0646\u064A"), 0, 2)
        grid.addWidget(self._national_id, 0, 3)

        self._name_ar = QLineEdit()
        self._name_ar.setPlaceholderText("\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0643\u0627\u0645\u0644")
        grid.addWidget(self._label("\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0639\u0631\u0628\u064A *"), 1, 0)
        grid.addWidget(self._name_ar, 1, 1, 1, 3)

        self._name_en = QLineEdit()
        self._name_en.setPlaceholderText("Full Name")
        grid.addWidget(self._label("\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0625\u0646\u062C\u0644\u064A\u0632\u064A"), 2, 0)
        grid.addWidget(self._name_en, 2, 1, 1, 3)

        self._phone = QLineEdit()
        self._phone.setPlaceholderText("+218 XX XXX XXXX")
        grid.addWidget(self._label("\u0627\u0644\u0647\u0627\u062A\u0641"), 3, 0)
        grid.addWidget(self._phone, 3, 1)

        self._email = QLineEdit()
        self._email.setPlaceholderText("email@example.com")
        grid.addWidget(self._label("\u0627\u0644\u0628\u0631\u064A\u062F \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A"), 3, 2)
        grid.addWidget(self._email, 3, 3)

        self._dob = QDateEdit()
        self._dob.setCalendarPopup(True)
        self._dob.setDate(QDate(1990, 1, 1))
        self._dob.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self._label("\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0645\u064A\u0644\u0627\u062F"), 4, 0)
        grid.addWidget(self._dob, 4, 1)

        self._gender = QComboBox()
        self._gender.addItems(["\u0630\u0643\u0631", "\u0623\u0646\u062B\u0649", "\u0623\u062E\u0631\u0649"])
        grid.addWidget(self._label("\u0627\u0644\u062C\u0646\u0633"), 4, 2)
        grid.addWidget(self._gender, 4, 3)

        self._nationality = QLineEdit()
        self._nationality.setPlaceholderText("\u0644\u064A\u0628\u064A\u0627")
        grid.addWidget(self._label("\u0627\u0644\u062C\u0646\u0633\u064A\u0629"), 5, 0)
        grid.addWidget(self._nationality, 5, 1)

        self._marital = QComboBox()
        self._marital.addItems(["\u0623\u0639\u0632\u0628", "\u063A\u064A\u0631 \u0623\u0639\u0632\u0628"])
        grid.addWidget(self._label("\u0627\u0644\u062D\u0627\u0644\u0629 \u0627\u0644\u0627\u062C\u062A\u0645\u0627\u0639\u064A\u0629"), 5, 2)
        grid.addWidget(self._marital, 5, 3)

        self._department = QComboBox()
        self._load_departments()
        grid.addWidget(self._label("\u0627\u0644\u0642\u0633\u0645 *"), 6, 0)
        grid.addWidget(self._department, 6, 1)

        self._position = QComboBox()
        self._load_positions()
        grid.addWidget(self._label("\u0627\u0644\u0648\u0638\u064A\u0641\u0629"), 6, 2)
        grid.addWidget(self._position, 6, 3)

        self._hire_date = QDateEdit()
        self._hire_date.setCalendarPopup(True)
        self._hire_date.setDate(QDate.currentDate())
        self._hire_date.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self._label("\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u062A\u0639\u064A\u064A\u0646"), 7, 0)
        grid.addWidget(self._hire_date, 7, 1)

        self._contract_type = QComboBox()
        self._contract_type.addItems(["\u0628\u0637\u0648\u0644", "\u0645\u0648\u0636\u0639", "\u0645\u0633\u0627\u0639\u062F", "\u062A\u0643\u0644\u064A\u0641\u064A"])
        grid.addWidget(self._label("\u0646\u0648\u0639 \u0627\u0644\u0639\u0642\u062F"), 7, 2)
        grid.addWidget(self._contract_type, 7, 3)

        self._contract_start = QDateEdit()
        self._contract_start.setCalendarPopup(True)
        self._contract_start.setDate(QDate.currentDate())
        self._contract_start.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self._label("\u0628\u062F\u0621 \u0627\u0644\u0639\u0642\u062F"), 8, 0)
        grid.addWidget(self._contract_start, 8, 1)

        self._contract_end = QDateEdit()
        self._contract_end.setCalendarPopup(True)
        self._contract_end.setDate(QDate.currentDate().addYears(1))
        self._contract_end.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self._label("\u0646\u0647\u0627\u064A\u0629 \u0627\u0644\u0639\u0642\u062F"), 8, 2)
        grid.addWidget(self._contract_end, 8, 3)

        self._salary = QLineEdit()
        self._salary.setPlaceholderText("0.00")
        grid.addWidget(self._label("\u0627\u0644\u0631\u0627\u062A\u0628 (LYD)"), 9, 0)
        grid.addWidget(self._salary, 9, 1)

        self._allowances = QLineEdit()
        self._allowances.setPlaceholderText("0.00")
        grid.addWidget(self._label("\u0627\u0644\u0628\u062F\u0644\u0627\u062A"), 9, 2)
        grid.addWidget(self._allowances, 9, 3)

        self._status = QComboBox()
        self._status.addItems(["\u0646\u0634\u0637", "\u0645\u0639\u0637\u0644\u0649", "\u0645\u062A\u0642\u0627\u0639\u062F", "\u0645\u0639\u0632\u0648\u0644"])
        grid.addWidget(self._label("\u0627\u0644\u062D\u0627\u0644\u0629"), 10, 0)
        grid.addWidget(self._status, 10, 1)

        self._address = QTextEdit()
        self._address.setPlaceholderText("\u0627\u0644\u0639\u0646\u0648\u0627\u0646")
        self._address.setMaximumHeight(80)
        grid.addWidget(self._label("\u0627\u0644\u0639\u0646\u0648\u0627\u0646"), 11, 0)
        grid.addWidget(self._address, 11, 1, 1, 3)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText("\u0645\u0644\u0627\u062D\u0638\u0627\u062A")
        self._notes.setMaximumHeight(80)
        grid.addWidget(self._label("\u0627\u0644\u0645\u0644\u0627\u062D\u0638\u0627\u062A"), 12, 0)
        grid.addWidget(self._notes, 12, 1, 1, 3)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("\u0625\u0644\u063A\u0627\u0621")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("\u062D\u0641\u0638")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def _load_departments(self):
        self._department.clear()
        self._department.addItem("\u0627\u062E\u062A\u0631...")
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Department)
                for dept in repos.get_all():
                    self._department.addItem(dept.name_ar, dept.id)
        except Exception:
            pass

    def _load_positions(self):
        self._position.clear()
        self._position.addItem("\u0627\u062E\u062A\u0631...")
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Position)
                for pos in repos.get_all():
                    self._position.addItem(pos.name_ar, pos.id)
        except Exception:
            pass

    def _load_employee(self):
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Employee)
                emp = repos.get_by_id(self._employee_id)
                if emp:
                    self._number.setText(emp.employee_number)
                    self._national_id.setText(emp.national_id or "")
                    self._name_ar.setText(emp.full_name_ar)
                    self._name_en.setText(emp.full_name_en or "")
                    self._phone.setText(emp.phone or "")
                    self._email.setText(emp.email or "")
                    if emp.date_of_birth:
                        self._dob.setDate(QDate(emp.date_of_birth.year, emp.date_of_birth.month, emp.date_of_birth.day))
                    if emp.hire_date:
                        self._hire_date.setDate(QDate(emp.hire_date.year, emp.hire_date.month, emp.hire_date.day))
                    self._salary.setText(str(emp.salary) if emp.salary else "")
                    self._allowances.setText(str(emp.allowances) if emp.allowances else "")
                    self._address.setText(emp.address or "")
                    self._notes.setText(emp.notes or "")
        except Exception:
            pass

    def _save(self):
        if not self._name_ar.text().strip() or not self._number.text().strip():
            QMessageBox.warning(self, "خطأ", "الرجاء ملء الحقول المطلوبة")
            return

        try:
            with session_scope() as session:
                repos = BaseRepository(session, Employee)
                data = {
                    "employee_number": self._number.text().strip(),
                    "national_id": self._national_id.text().strip() or None,
                    "full_name_ar": self._name_ar.text().strip(),
                    "full_name_en": self._name_en.text().strip() or None,
                    "phone": self._phone.text().strip() or None,
                    "email": self._email.text().strip() or None,
                    "date_of_birth": self._dob.date().toPython(),
                    "gender": self._gender.currentText(),
                    "nationality": self._nationality.text().strip() or None,
                    "marital_status": self._marital.currentText(),
                    "department_id": self._department.currentData(),
                    "position_id": self._position.currentData(),
                    "hire_date": self._hire_date.date().toPython(),
                    "contract_type": self._contract_type.currentText(),
                    "contract_start": self._contract_start.date().toPython(),
                    "contract_end": self._contract_end.date().toPython(),
                    "salary": float(self._salary.text()) if self._salary.text() else None,
                    "allowances": float(self._allowances.text()) if self._allowances.text() else None,
                    "status": self._status.currentText(),
                    "address": self._address.toPlainText().strip() or None,
                    "notes": self._notes.toPlainText().strip() or None,
                }
                if self._is_edit:
                    repos.update(self._employee_id, **data)
                else:
                    repos.create(**data)
                self.saved.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر الحفظ: {str(e)}")
