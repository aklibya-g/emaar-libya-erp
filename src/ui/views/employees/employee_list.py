from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from src.ui.widgets.data_table import DataTable
from src.ui.views.employees.employee_form import EmployeeForm
from src.core.database.connection import session_scope
from src.core.models.base_models import Employee, Department
from src.core.repositories.base_repository import BaseRepository


class EmployeeListView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("شؤون الموظفين")
        title.setStyleSheet("color: #e4e6eb; font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ موظف جديد")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add_employee)
        header.addWidget(add_btn)

        layout.addLayout(header)

        columns = [
            {"title": "الرقم الوظيفي", "accessor": "employee_number", "width": 120, "center": True},
            {"title": "الاسم", "accessor": "full_name_ar", "width": 200},
            {"title": "القسم", "accessor": lambda e: e.department.name_ar if e.department else "-", "width": 150},
            {"title": "الوظيفة", "accessor": lambda e: e.position.name_ar if e.position else "-", "width": 150},
            {"title": "الهاتف", "accessor": "phone", "width": 130, "center": True},
            {"title": "تاريخ التعيين", "accessor": lambda e: str(e.hire_date) if e.hire_date else "-", "width": 120, "center": True},
            {"title": "الحالة", "accessor": "status", "width": 100, "center": True},
        ]

        self._table = DataTable(columns)
        self._table.row_double_clicked.connect(self._edit_employee)
        self._table.row_selected.connect(self._on_select)
        layout.addWidget(self._table)

        self._selected_id = None
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        edit_btn = QPushButton("تعديل")
        edit_btn.setObjectName("secondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("حذف")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        refresh_btn = QPushButton("تحديث")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)

    def refresh(self):
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Employee)
                employees = repos.get_all()
                self._table.set_data(employees)
        except Exception as e:
            print(f"Error loading employees: {e}")

    def _add_employee(self):
        form = EmployeeForm(self)
        form.saved.connect(self.refresh)
        form.exec()

    def _edit_employee(self, emp_id: str):
        form = EmployeeForm(self, employee_id=emp_id)
        form.saved.connect(self.refresh)
        form.exec()

    def _on_select(self, emp_id: str):
        self._selected_id = emp_id

    def _edit_selected(self):
        if self._selected_id:
            self._edit_employee(self._selected_id)

    def _delete_selected(self):
        if not self._selected_id:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف أولاً")
            return
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا الموظف؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                with session_scope() as session:
                    repos = BaseRepository(session, Employee)
                    repos.delete(self._selected_id)
                    self.refresh()
                    self._selected_id = None
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف: {str(e)}")
