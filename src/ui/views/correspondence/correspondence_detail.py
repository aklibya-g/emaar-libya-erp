from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QScrollArea, QTextEdit, QComboBox,
    QLineEdit, QDateEdit, QMessageBox, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    CorrespondenceAction, CorrespondenceAttachment,
    Department, Employee, Signature, Stamp,
)
from src.modules.correspondence.service import CorrespondenceService
from src.modules.correspondence.workflow import CorrespondenceWorkflow


class CorrespondenceDetailView(QDialog):
    def __init__(self, parent=None, correspondence_id: str = None):
        super().__init__(parent)
        self._cor_id = correspondence_id
        self.setWindowTitle("تفاصيل المراسلة")
        self.setMinimumSize(900, 800)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self._ref_label = QLabel("")
        self._ref_label.setStyleSheet("color: #60a5fa; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self._ref_label)
        header_layout.addStretch()

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            "padding: 4px 16px; border-radius: 12px; font-weight: bold; font-size: 12px;"
        )
        header_layout.addWidget(self._status_label)

        self._importance_label = QLabel("")
        self._importance_label.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(self._importance_label)

        layout.addLayout(header_layout)

        info_grid = QGridLayout()
        info_grid.setSpacing(8)

        self._type_label = QLabel("-")
        self._date_label = QLabel("-")
        self._direction_label = QLabel("-")
        self._sender_dept_label = QLabel("-")
        self._receiver_dept_label = QLabel("-")
        self._sender_entity_label = QLabel("-")
        self._receiver_entity_label = QLabel("-")
        self._responsible_label = QLabel("-")
        self._due_date_label = QLabel("-")
        self._confidential_label = QLabel("")

        fields = [
            ("النوع:", self._type_label, 0, 0),
            ("التاريخ:", self._date_label, 0, 2),
            ("الاتجاه:", self._direction_label, 1, 0),
            ("القسم المرسل:", self._sender_dept_label, 1, 2),
            ("القسم المستلم:", self._receiver_dept_label, 2, 0),
            ("الجهة المرسلة:", self._sender_entity_label, 2, 2),
            ("الجهة المستلمة:", self._receiver_entity_label, 3, 0),
            ("المسؤول:", self._responsible_label, 3, 2),
            ("موعد الاستحقاق:", self._due_date_label, 4, 0),
        ]
        for text, widget, row, col in fields:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #9ca3af; font-weight: 500;")
            info_grid.addWidget(lbl, row, col)
            widget.setStyleSheet("color: #e4e6eb;")
            info_grid.addWidget(widget, row, col + 1)

        info_grid.addWidget(self._confidential_label, 4, 2, 1, 2)

        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; border: 1px solid #2a2d35;")
        info_frame.setLayout(info_grid)
        layout.addWidget(info_frame)

        subject_frame = QFrame()
        subject_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; border: 1px solid #2a2d35;")
        subject_layout = QVBoxLayout(subject_frame)
        subject_layout.setContentsMargins(16, 12, 16, 12)

        subject_title = QLabel("الموضوع")
        subject_title.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 13px;")
        subject_layout.addWidget(subject_title)

        self._subject_text = QLabel("")
        self._subject_text.setStyleSheet("color: #e4e6eb; font-size: 14px;")
        self._subject_text.setWordWrap(True)
        subject_layout.addWidget(self._subject_text)

        layout.addWidget(subject_frame)

        body_frame = QFrame()
        body_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; border: 1px solid #2a2d35;")
        body_layout = QVBoxLayout(body_frame)
        body_layout.setContentsMargins(16, 12, 16, 12)

        body_title = QLabel("النص")
        body_title.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 13px;")
        body_layout.addWidget(body_title)

        self._body_text = QTextEdit()
        self._body_text.setReadOnly(True)
        self._body_text.setMinimumHeight(120)
        self._body_text.setStyleSheet("background-color: #111318; border: none; color: #e4e6eb;")
        body_layout.addWidget(self._body_text)

        layout.addWidget(body_frame)

        attach_frame = QFrame()
        attach_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; border: 1px solid #2a2d35;")
        attach_layout = QVBoxLayout(attach_frame)
        attach_layout.setContentsMargins(16, 12, 16, 12)

        attach_title = QLabel("المرفقات")
        attach_title.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 13px;")
        attach_layout.addWidget(attach_title)

        self._attach_list = QListWidget()
        self._attach_list.setMaximumHeight(80)
        attach_layout.addWidget(self._attach_list)

        layout.addWidget(attach_frame)

        actions_frame = QFrame()
        actions_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; border: 1px solid #2a2d35;")
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(16, 12, 16, 12)

        actions_title = QLabel("سجل الإجراءات")
        actions_title.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 13px;")
        actions_layout.addWidget(actions_title)

        self._actions_list = QListWidget()
        self._actions_list.setMaximumHeight(150)
        actions_layout.addWidget(self._actions_list)

        layout.addWidget(actions_frame)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._forward_btn = QPushButton("إحالة")
        self._forward_btn.setObjectName("secondaryButton")
        self._forward_btn.clicked.connect(self._forward)
        btn_layout.addWidget(self._forward_btn)

        self._approve_btn = QPushButton("اعتماد")
        self._approve_btn.setObjectName("successButton")
        self._approve_btn.clicked.connect(self._approve)
        btn_layout.addWidget(self._approve_btn)

        self._sign_btn = QPushButton("توقيع")
        self._sign_btn.setObjectName("successButton")
        self._sign_btn.clicked.connect(self._sign)
        btn_layout.addWidget(self._sign_btn)

        self._stamp_btn = QPushButton("ختم")
        self._stamp_btn.setObjectName("successButton")
        self._stamp_btn.clicked.connect(self._stamp)
        btn_layout.addWidget(self._stamp_btn)

        self._print_btn = QPushButton("طباعة PDF")
        self._print_btn.setObjectName("secondaryButton")
        self._print_btn.clicked.connect(self._print)
        btn_layout.addWidget(self._print_btn)

        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    def _load_data(self):
        try:
            with session_scope() as session:
                cor = session.query(Correspondence).filter(
                    Correspondence.id == self._cor_id
                ).first()
                if not cor:
                    return

                self._ref_label.setText(cor.reference_number or "")
                self._subject_text.setText(cor.subject or "")
                self._body_text.setText(cor.body or "")

                if cor.cor_type:
                    self._type_label.setText(cor.cor_type.name_ar)
                if cor.date:
                    self._date_label.setText(str(cor.date))
                self._direction_label.setText({
                    "IN": "وارد", "OUT": "صادر", "INT": "داخلي",
                    "EXT": "خارجي", "MEMO": "مذكرة", "DEC": "قرار",
                    "CIRC": "تعميم", "LET": "خطاب",
                }.get(cor.direction, cor.direction))
                if cor.sender_department:
                    self._sender_dept_label.setText(cor.sender_department.name_ar)
                if cor.receiver_department:
                    self._receiver_dept_label.setText(cor.receiver_department.name_ar)
                self._sender_entity_label.setText(cor.sender_entity or "-")
                self._receiver_entity_label.setText(cor.receiver_entity or "-")
                if cor.responsible_employee:
                    self._responsible_label.setText(cor.responsible_employee.full_name_ar)
                if cor.due_date:
                    self._due_date_label.setText(str(cor.due_date))
                if cor.is_confidential:
                    self._confidential_label.setText("سري")
                    self._confidential_label.setStyleSheet("color: #ef4444; font-weight: bold;")

                importance_map = {"normal": "عادي", "high": "مهم", "critical": "عاجل", "low": "منخفض"}
                self._importance_label.setText(importance_map.get(cor.importance, "عادي"))

                if cor.status:
                    self._status_label.setText(cor.status.name_ar)
                    self._status_label.setStyleSheet(
                        f"padding: 4px 16px; border-radius: 12px; font-weight: bold; font-size: 12px; "
                        f"color: white; background-color: {cor.status.color or '#6b7280'};"
                    )

                attachments = session.query(CorrespondenceAttachment).filter(
                    CorrespondenceAttachment.correspondence_id == self._cor_id
                ).all()
                for att in attachments:
                    self._attach_list.addItem(att.filename)

                actions = session.query(CorrespondenceAction).filter(
                    CorrespondenceAction.correspondence_id == self._cor_id
                ).order_by(CorrespondenceAction.action_date.desc()).all()
                for action in actions:
                    item_text = f"[{action.action_date}] {action.action_type}"
                    if action.notes:
                        item_text += f" - {action.notes}"
                    self._actions_list.addItem(item_text)

                self._update_buttons(cor)
        except Exception as e:
            print(f"Error: {e}")

    def _update_buttons(self, cor):
        if not cor.status:
            return
        code = cor.status.code
        is_final = code in ["ARCHIVED", "CANCELLED"]
        self._forward_btn.setEnabled(not is_final)
        self._approve_btn.setEnabled(code in ["REVIEW", "DRAFT"])
        self._sign_btn.setEnabled(code == "APPROVED")
        self._stamp_btn.setEnabled(code == "SIGNED")

    def _forward(self):
        dialog = ForwardDialog(self, self._cor_id)
        if dialog.exec():
            self._load_data()

    def _approve(self):
        try:
            with session_scope() as session:
                service = CorrespondenceService(session)
                cor = service.get_by_id(self._cor_id)
                if cor:
                    ok, msg = service.workflow.execute_transition(cor, "APPROVED")
                    if ok:
                        QMessageBox.information(self, "نجاح", msg)
                        self._load_data()
                    else:
                        QMessageBox.warning(self, "خطأ", msg)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _sign(self):
        try:
            with session_scope() as session:
                service = CorrespondenceService(session)
                cor = service.get_by_id(self._cor_id)
                if cor:
                    ok, msg = service.workflow.execute_transition(cor, "SIGNED")
                    if ok:
                        QMessageBox.information(self, "نجاح", msg)
                        self._load_data()
                    else:
                        QMessageBox.warning(self, "خطأ", msg)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _stamp(self):
        try:
            with session_scope() as session:
                service = CorrespondenceService(session)
                cor = service.get_by_id(self._cor_id)
                if cor:
                    ok, msg = service.workflow.execute_transition(cor, "STAMPED")
                    if ok:
                        QMessageBox.information(self, "نجاح", msg)
                        self._load_data()
                    else:
                        QMessageBox.warning(self, "خطأ", msg)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _print(self):
        try:
            with session_scope() as session:
                cor = session.query(Correspondence).filter(
                    Correspondence.id == self._cor_id
                ).first()
                if cor:
                    from src.modules.documents.pdf_generator import PDFGenerator
                    generator = PDFGenerator()
                    path = generator.generate_correspondence_pdf(cor)
                    QMessageBox.information(self, "نجاح", f"تم إنشاء PDF:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))


class ForwardDialog(QDialog):
    def __init__(self, parent=None, correspondence_id: str = None):
        super().__init__(parent)
        self._cor_id = correspondence_id
        self.setWindowTitle("إحالة المراسلة")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("إحالة المراسلة"))

        self._to_employee = QComboBox()
        self._load_employees()
        layout.addWidget(self._label("إلى موظف:"))
        layout.addWidget(self._to_employee)

        self._to_dept = QComboBox()
        self._load_departments()
        layout.addWidget(self._label("إلى قسم:"))
        layout.addWidget(self._to_dept)

        self._action = QLineEdit()
        self._action.setPlaceholderText("الإجراء المطلوب")
        layout.addWidget(self._label("الإجراء المطلوب:"))
        layout.addWidget(self._action)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText("ملاحظات")
        self._notes.setMaximumHeight(80)
        layout.addWidget(self._label("ملاحظات:"))
        layout.addWidget(self._notes)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton("إلغاء")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        forward_btn = QPushButton("إحالة")
        forward_btn.setObjectName("successButton")
        forward_btn.clicked.connect(self._forward)
        btn_layout.addWidget(forward_btn)
        layout.addLayout(btn_layout)

    def _label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("formLabel")
        return l

    def _load_employees(self):
        self._to_employee.addItem("اختر موظف...")
        try:
            with session_scope() as session:
                emps = session.query(Employee).filter(Employee.status == "active").all()
                for e in emps:
                    self._to_employee.addItem(e.full_name_ar, e.id)
        except Exception:
            pass

    def _load_departments(self):
        self._to_dept.addItem("اختر قسم...")
        try:
            with session_scope() as session:
                depts = session.query(Department).filter(Department.is_active == True).all()
                for d in depts:
                    self._to_dept.addItem(d.name_ar, d.id)
        except Exception:
            pass

    def _forward(self):
        to_emp = self._to_employee.currentData()
        to_dept = self._to_dept.currentData()
        if not to_emp and not to_dept:
            QMessageBox.warning(self, "خطأ", "الرجاء اختيار موظف أو قسم")
            return
        try:
            with session_scope() as session:
                service = CorrespondenceService(session)
                cor = service.get_by_id(self._cor_id)
                if cor:
                    ok, msg = service.workflow.forward(
                        correspondence=cor,
                        from_employee_id=cor.responsible_employee_id or "",
                        to_employee_id=to_emp or "",
                        to_department_id=to_dept or "",
                        required_action=self._action.text().strip() or None,
                        notes=self._notes.toPlainText().strip() or None,
                    )
                    if ok:
                        QMessageBox.information(self, "نجاح", msg)
                        self.accept()
                    else:
                        QMessageBox.warning(self, "خطأ", msg)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))
