from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QPushButton, QGridLayout,
    QScrollArea, QFrame, QMessageBox, QFileDialog, QCheckBox,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    Department, Employee, Company, Signature, Stamp,
)
from src.core.repositories.base_repository import BaseRepository
from src.modules.correspondence.service import CorrespondenceService


class CorrespondenceForm(QDialog):
    saved = Signal(str)

    def __init__(self, parent=None, correspondence_id: str = None):
        super().__init__(parent)
        self._cor_id = correspondence_id
        self._is_edit = correspondence_id is not None
        self.setWindowTitle(
            "تعديل مراسلة" if self._is_edit else "إنشاء مراسلة جديدة"
        )
        self.setMinimumSize(800, 800)
        self._setup_ui()
        if self._is_edit:
            self._load_data()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        section1 = QLabel("بيانات المراسلة")
        section1.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold; border-bottom: 1px solid #2a2d35; padding-bottom: 6px;")
        layout.addWidget(section1)

        grid = QGridLayout()
        grid.setSpacing(10)

        self._type = QComboBox()
        self._type.setMinimumWidth(200)
        self._load_types()
        grid.addWidget(self._label("نوع المراسلة *"), 0, 0)
        grid.addWidget(self._type, 0, 1)

        self._ref_display = QLabel("-")
        self._ref_display.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 13px; padding: 8px; background: #1f2937; border-radius: 6px;")
        grid.addWidget(self._label("الرقم الإشاري:"), 0, 2)
        grid.addWidget(self._ref_display, 0, 3)

        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate())
        self._date.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self._label("التاريخ *"), 1, 0)
        grid.addWidget(self._date, 1, 1)

        self._importance = QComboBox()
        self._importance.addItems(["عادي", "مهم", "عاجل", "سري"])
        grid.addWidget(self._label("الأهمية"), 1, 2)
        grid.addWidget(self._importance, 1, 3)

        self._confidential = QCheckBox("سري")
        grid.addWidget(self._confidential, 2, 0, 1, 2)

        layout.addLayout(grid)

        section2 = QLabel("الجهات")
        section2.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold; border-bottom: 1px solid #2a2d35; padding-bottom: 6px; margin-top: 8px;")
        layout.addWidget(section2)

        grid2 = QGridLayout()
        grid2.setSpacing(10)

        self._sender_dept = QComboBox()
        self._sender_dept.setMinimumWidth(200)
        self._load_departments()
        grid2.addWidget(self._label("القسم المرسل"), 0, 0)
        grid2.addWidget(self._sender_dept, 0, 1)

        self._receiver_dept = QComboBox()
        self._receiver_dept.setMinimumWidth(200)
        self._load_departments()
        grid2.addWidget(self._label("القسم المستلم"), 0, 2)
        grid2.addWidget(self._receiver_dept, 0, 3)

        self._sender_entity = QLineEdit()
        self._sender_entity.setPlaceholderText("الجهة المرسلة ( إن وجدت )")
        grid2.addWidget(self._label("الجهة المرسلة"), 1, 0)
        grid2.addWidget(self._sender_entity, 1, 1, 1, 3)

        self._receiver_entity = QLineEdit()
        self._receiver_entity.setPlaceholderText("الجهة المستلمة")
        grid2.addWidget(self._label("الجهة المستلمة"), 2, 0)
        grid2.addWidget(self._receiver_entity, 2, 1, 1, 3)

        self._responsible = QComboBox()
        self._responsible.setMinimumWidth(200)
        self._load_employees()
        grid2.addWidget(self._label("الموظف المسؤول"), 3, 0)
        grid2.addWidget(self._responsible, 3, 1)

        self._due_date = QDateEdit()
        self._due_date.setCalendarPopup(True)
        self._due_date.setDate(QDate.currentDate().addDays(7))
        self._due_date.setDisplayFormat("yyyy-MM-dd")
        grid2.addWidget(self._label("موعد الاستحقاق"), 3, 2)
        grid2.addWidget(self._due_date, 3, 3)

        layout.addLayout(grid2)

        section3 = QLabel("المحتوى")
        section3.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold; border-bottom: 1px solid #2a2d35; padding-bottom: 6px; margin-top: 8px;")
        layout.addWidget(section3)

        self._subject = QLineEdit()
        self._subject.setPlaceholderText("موضوع المراسلة")
        layout.addWidget(self._label("الموضوع *"))
        layout.addWidget(self._subject)

        self._body = QTextEdit()
        self._body.setPlaceholderText("نص المراسلة...")
        self._body.setMinimumHeight(200)
        layout.addWidget(self._label("النص"))
        layout.addWidget(self._body)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText("ملاحظات داخلية...")
        self._notes.setMaximumHeight(80)
        layout.addWidget(self._label("ملاحظات"))
        layout.addWidget(self._notes)

        section4 = QLabel("المرفقات")
        section4.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold; border-bottom: 1px solid #2a2d35; padding-bottom: 6px; margin-top: 8px;")
        layout.addWidget(section4)

        att_layout = QHBoxLayout()
        self._attach_btn = QPushButton("إرفاق ملف")
        self._attach_btn.setObjectName("secondaryButton")
        self._attach_btn.clicked.connect(self._attach_file)
        att_layout.addWidget(self._attach_btn)

        self._attach_list = QListWidget()
        self._attach_list.setMaximumHeight(100)
        att_layout.addWidget(self._attach_list)
        layout.addLayout(att_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_draft = QPushButton("حفظ كمسودة")
        save_draft.setObjectName("secondaryButton")
        save_draft.clicked.connect(lambda: self._save("draft"))
        btn_layout.addWidget(save_draft)

        save_send = QPushButton("حفظ وإرسال")
        save_send.setObjectName("successButton")
        save_send.clicked.connect(lambda: self._save("send"))
        btn_layout.addWidget(save_send)

        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

        self._type.currentIndexChanged.connect(self._on_type_changed)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def _load_types(self):
        self._type.clear()
        self._type.addItem("اختر النوع...")
        try:
            with session_scope() as session:
                types = session.query(CorrespondenceType).filter(
                    CorrespondenceType.is_active == True
                ).all()
                for t in types:
                    self._type.addItem(f"{t.name_ar} ({t.code})", t.code)
        except Exception:
            pass

    def _load_departments(self):
        pass

    def _load_employees(self):
        pass

    def _on_type_changed(self, index):
        if index > 0:
            type_code = self._type.currentData()
            try:
                with session_scope() as session:
                    from src.modules.correspondence.numbering import NumberingEngine
                    engine = NumberingEngine(session)
                    ref = engine.preview(type_code)
                    self._ref_display.setText(ref)
            except Exception:
                self._ref_display.setText("خطأ في التوليد")

    def _attach_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختيار المرفقات", "", "All Files (*);;PDF (*.pdf);;Images (*.png *.jpg)"
        )
        for f in files:
            item = QListWidgetItem(f.split("/")[-1].split("\\")[-1])
            item.setData(Qt.UserRole, f)
            self._attach_list.addItem(item)

    def _load_data(self):
        try:
            with session_scope() as session:
                cor = session.query(Correspondence).filter(
                    Correspondence.id == self._cor_id
                ).first()
                if cor:
                    self._ref_display.setText(cor.reference_number or "")
                    if cor.date:
                        self._date.setDate(QDate(cor.date.year, cor.date.month, cor.date.day))
                    self._subject.setText(cor.subject or "")
                    self._body.setText(cor.body or "")
                    self._sender_entity.setText(cor.sender_entity or "")
                    self._receiver_entity.setText(cor.receiver_entity or "")
                    self._notes.setText(cor.notes or "")
                    importance_map = {"normal": "عادي", "high": "مهم", "critical": "عاجل", "low": "منخفض"}
                    idx = self._importance.findText(importance_map.get(cor.importance, "عادي"))
                    if idx >= 0:
                        self._importance.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل البيانات: {str(e)}")

    def _save(self, action: str):
        if not self._subject.text().strip():
            QMessageBox.warning(self, "خطأ", "الرجاء إدخال الموضوع")
            return

        try:
            type_code = self._type.currentData()
            if not type_code:
                QMessageBox.warning(self, "خطأ", "الرجاء اختيار نوع المراسلة")
                return

            importance_map = {"عادي": "normal", "مهم": "high", "عاجل": "critical", "منخفض": "low"}

            with session_scope() as session:
                service = CorrespondenceService(session)
                cor = service.create(
                    type_code=type_code,
                    subject=self._subject.text().strip(),
                    direction="OUT",
                    body=self._body.toPlainText().strip(),
                    importance=importance_map.get(self._importance.currentText(), "normal"),
                    is_confidential=self._confidential.isChecked(),
                    sender_entity=self._sender_entity.text().strip() or None,
                    receiver_entity=self._receiver_entity.text().strip() or None,
                    due_date=self._due_date.date().toPython(),
                    notes=self._notes.toPlainText().strip() or None,
                )

                for i in range(self._attach_list.count()):
                    item = self._attach_list.item(i)
                    file_path = item.data(Qt.UserRole)
                    if file_path:
                        service.add_attachment(
                            correspondence_id=cor.id,
                            filename=item.text(),
                            file_path=file_path,
                        )

                self.saved.emit(cor.id)
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر الحفظ: {str(e)}")
