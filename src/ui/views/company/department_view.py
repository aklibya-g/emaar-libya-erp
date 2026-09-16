from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QLineEdit, QTextEdit, QComboBox,
)
from PySide6.QtCore import Signal, Qt

from src.ui.widgets.data_table import DataTable
from src.core.database.connection import session_scope
from src.core.models.base_models import Department, Company
from src.core.repositories.base_repository import BaseRepository


class DepartmentForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, dept_id: str = None):
        super().__init__(parent)
        self._dept_id = dept_id
        self._is_edit = dept_id is not None
        self.setWindowTitle("تعديل قسم" if self._is_edit else "قسم جديد")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        if self._is_edit:
            self._load()

    def _setup_ui(self):
        from PySide6.QtWidgets import QGridLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)

        self._code = QLineEdit()
        self._code.setPlaceholderText("مثال: HR, ADM, FIN")
        grid.addWidget(self._make_label("كود القسم *"), 0, 0)
        grid.addWidget(self._code, 0, 1)

        self._name_ar = QLineEdit()
        self._name_ar.setPlaceholderText("اسم القسم بالعربية")
        grid.addWidget(self._make_label("الاسم العربي *"), 1, 0)
        grid.addWidget(self._name_ar, 1, 1)

        self._name_en = QLineEdit()
        self._name_en.setPlaceholderText("Department Name")
        grid.addWidget(self._make_label("الاسم الإنجليزي"), 2, 0)
        grid.addWidget(self._name_en, 2, 1)

        self._desc = QTextEdit()
        self._desc.setPlaceholderText("وصف القسم")
        self._desc.setMaximumHeight(80)
        grid.addWidget(self._make_label("الوصف"), 3, 0)
        grid.addWidget(self._desc, 3, 1)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        save = QPushButton("حفظ")
        save.setObjectName("successButton")
        save.clicked.connect(self._save)
        btn_layout.addWidget(save)
        layout.addLayout(btn_layout)

    def _make_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("formLabel")
        return l

    def _load(self):
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Department)
                dept = repos.get_by_id(self._dept_id)
                if dept:
                    self._code.setText(dept.code)
                    self._name_ar.setText(dept.name_ar)
                    self._name_en.setText(dept.name_en or "")
                    self._desc.setText(dept.description or "")
        except Exception:
            pass

    def _save(self):
        if not self._code.text().strip() or not self._name_ar.text().strip():
            QMessageBox.warning(self, "خطأ", "الرجاء ملء الحقول المطلوبة")
            return
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Department)
                data = {
                    "code": self._code.text().strip().upper(),
                    "name_ar": self._name_ar.text().strip(),
                    "name_en": self._name_en.text().strip() or None,
                    "description": self._desc.toPlainText().strip() or None,
                }
                if self._is_edit:
                    repos.update(self._dept_id, **data)
                else:
                    company = session.query(Company).first()
                    if company:
                        data["company_id"] = company.id
                    repos.create(**data)
                self.saved.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر الحفظ: {str(e)}")


class DepartmentListView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("الأقسام")
        title.setStyleSheet("color: #e4e6eb; font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ قسم جديد")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add)
        header.addWidget(add_btn)
        layout.addLayout(header)

        columns = [
            {"title": "الكود", "accessor": "code", "width": 100, "center": True},
            {"title": "الاسم", "accessor": "name_ar", "width": 250},
            {"title": "الاسم الإنجليزي", "accessor": "name_en", "width": 200},
            {"title": "الوصف", "accessor": "description", "width": 250},
        ]

        self._table = DataTable(columns)
        self._table.row_double_clicked.connect(self._edit)
        self._table.row_selected.connect(lambda id: setattr(self, '_selected_id', id))
        layout.addWidget(self._table)

        self._selected_id = None
        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("تعديل")
        edit_btn.setObjectName("secondaryButton")
        edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(edit_btn)
        delete_btn = QPushButton("حذف")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def refresh(self):
        try:
            with session_scope() as session:
                repos = BaseRepository(session, Department)
                self._table.set_data(repos.get_all())
        except Exception:
            pass

    def _add(self):
        form = DepartmentForm(self)
        form.saved.connect(self.refresh)
        form.exec()

    def _edit(self, dept_id: str):
        form = DepartmentForm(self, dept_id=dept_id)
        form.saved.connect(self.refresh)
        form.exec()

    def _edit_selected(self):
        if self._selected_id:
            self._edit(self._selected_id)

    def _delete_selected(self):
        if not self._selected_id:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد قسم أولاً")
            return
        reply = QMessageBox.question(
            self, "تأكيد", "هل أنت متأكد؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            with session_scope() as session:
                BaseRepository(session, Department).delete(self._selected_id)
                self.refresh()
                self._selected_id = None
