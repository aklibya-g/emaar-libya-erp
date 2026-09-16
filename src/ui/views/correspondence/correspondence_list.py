from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QMessageBox, QTabWidget, QDateEdit,
    QSplitter, QFrame,
)
from PySide6.QtCore import Qt, Signal, QDate

from src.ui.widgets.data_table import DataTable
from src.ui.views.correspondence.correspondence_form import CorrespondenceForm
from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    Department, Employee,
)
from src.modules.correspondence.service import CorrespondenceService


class CorrespondenceListView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_id = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("المراسلات")
        title.setStyleSheet("color: #e4e6eb; font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        header.addWidget(self._stats_label)

        add_btn = QPushButton("+ مراسلة جديدة")
        add_btn.setObjectName("successButton")
        add_btn.clicked.connect(self._add)
        header.addWidget(add_btn)

        layout.addLayout(header)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالرقم أو الموضوع أو الجهة...")
        self._search.setMinimumWidth(300)
        self._search.textChanged.connect(self._on_search)
        filters_layout.addWidget(self._search)

        self._dir_filter = QComboBox()
        self._dir_filter.addItems(["الكل", "وارد", "صادر", "داخلي", "خارجي", "مذكرة", "قرار", "تعميم", "خطاب"])
        self._dir_filter.currentIndexChanged.connect(self._apply_filters)
        filters_layout.addWidget(self._dir_filter)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["الكل", "مسودة", "قيد المراجعة", "معتمد", "موقع", "مختم", "تم الإرسال", "تم الاستلام", "محال", "تم التنفيذ", "مؤرشف", "ملغي"])
        self._status_filter.currentIndexChanged.connect(self._apply_filters)
        filters_layout.addWidget(self._status_filter)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.dateChanged.connect(self._apply_filters)
        filters_layout.addWidget(QLabel("من:"))
        filters_layout.addWidget(self._date_from)

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.dateChanged.connect(self._apply_filters)
        filters_layout.addWidget(QLabel("إلى:"))
        filters_layout.addWidget(self._date_to)

        self._overdue_check = QPushButton("المتأخرة فقط")
        self._overdue_check.setCheckable(True)
        self._overdue_check.clicked.connect(self._apply_filters)
        filters_layout.addWidget(self._overdue_check)

        filters_layout.addStretch()
        layout.addLayout(filters_layout)

        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._on_tab_changed)

        columns = [
            {"title": "الرقم الإشاري", "accessor": "reference_number", "width": 180, "center": True},
            {"title": "التاريخ", "accessor": lambda c: str(c.date) if c.date else "-", "width": 100, "center": True},
            {"title": "الموضوع", "accessor": "subject", "width": 250},
            {"title": "النوع", "accessor": lambda c: c.cor_type.name_ar if c.cor_type else "-", "width": 120},
            {"title": "الحالة", "accessor": lambda c: c.status.name_ar if c.status else "-", "width": 120, "center": True},
            {"title": "الأهمية", "accessor": lambda c: {"normal": "عادي", "high": "مهم", "critical": "عاجل", "low": "منخفض"}.get(c.importance, "عادي"), "width": 80, "center": True},
            {"title": "القسم المرسل", "accessor": lambda c: c.sender_department.name_ar if c.sender_department else "-", "width": 130},
            {"title": "القسم المستلم", "accessor": lambda c: c.receiver_department.name_ar if c.receiver_department else "-", "width": 130},
            {"title": "المسؤول", "accessor": lambda c: c.responsible_employee.full_name_ar if c.responsible_employee else "-", "width": 130},
        ]

        self._table = DataTable(columns)
        self._table.row_double_clicked.connect(self._view_detail)
        self._table.row_selected.connect(lambda id: setattr(self, '_selected_id', id))

        self._tabs.addTab(self._table, "الكل")

        all_table = DataTable(columns[:7] + [columns[8]])
        self._all_table = all_table

        self._inbox_table = DataTable(columns)
        self._outbox_table = DataTable(columns)
        self._pending_table = DataTable(columns)
        self._archived_table = DataTable(columns)

        self._tabs.addTab(self._inbox_table, "📥 الوارد")
        self._tabs.addTab(self._outbox_table, "📤 الصادر")
        self._tabs.addTab(self._pending_table, "⏰ المتأخرة")
        self._tabs.addTab(self._archived_table, "📁 المؤرشفة")

        layout.addWidget(self._tabs)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        view_btn = QPushButton("عرض")
        view_btn.setObjectName("secondaryButton")
        view_btn.clicked.connect(self._view_selected)
        btn_layout.addWidget(view_btn)

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
                service = CorrespondenceService(session)
                all_cor = service.search(is_archived=False)
                self._table.set_data(all_cor)

                inbox = service.get_inbox()
                self._inbox_table.set_data(inbox)

                outbox = service.get_outbox()
                self._outbox_table.set_data(outbox)

                pending = service.get_pending()
                self._pending_table.set_data(pending)

                archived = service.search(is_archived=True)
                self._archived_table.set_data(archived)

                stats = service.get_statistics()
                self._stats_label.setText(
                    f"إجمالي: {stats['total']} | وارد: {stats['incoming']} | صادر: {stats['outgoing']} | "
                    f"متأخر: {stats['overdue']} | مؤرشف: {stats['archived']}"
                )
        except Exception as e:
            print(f"Error loading correspondence: {e}")

    def _add(self):
        form = CorrespondenceForm(self)
        form.saved.connect(lambda: self.refresh())
        form.exec()

    def _view_detail(self, cor_id: str):
        from src.ui.views.correspondence.correspondence_detail import CorrespondenceDetailView
        detail = CorrespondenceDetailView(self, correspondence_id=cor_id)
        detail.exec()

    def _view_selected(self):
        if self._selected_id:
            self._view_detail(self._selected_id)

    def _edit_selected(self):
        if not self._selected_id:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد مراسلة أولاً")
            return
        form = CorrespondenceForm(self, correspondence_id=self._selected_id)
        form.saved.connect(lambda: self.refresh())
        form.exec()

    def _delete_selected(self):
        if not self._selected_id:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد مراسلة أولاً")
            return
        reply = QMessageBox.question(
            self, "تأكيد الحذف", "هل أنت متأكد من حذف هذه المراسلة؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                with session_scope() as session:
                    service = CorrespondenceService(session)
                    service.delete(self._selected_id)
                    self.refresh()
                    self._selected_id = None
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف: {str(e)}")

    def _on_search(self, text: str):
        self._apply_filters()

    def _apply_filters(self):
        search_text = self._search.text().strip()
        dir_text = self._dir_filter.currentText()
        status_text = self._status_filter.currentText()

        direction_map = {"وارد": "IN", "صادر": "OUT", "داخلي": "INT", "خارجي": "EXT", "مذكرة": "MEMO", "قرار": "DEC", "تعميم": "CIRC", "خطاب": "LET"}
        direction = direction_map.get(dir_text) if dir_text != "الكل" else None

        status_map = {"مسودة": "DRAFT", "قيد المراجعة": "REVIEW", "معتمد": "APPROVED", "موقع": "SIGNED", "مختم": "STAMPED", "تم الإرسال": "SENT", "تم الاستلام": "RECEIVED", "محال": "FORWARDED", "تم التنفيذ": "COMPLETED", "مؤرشف": "ARCHIVED", "ملغي": "CANCELLED"}
        status = status_map.get(status_text) if status_text != "الكل" else None

        try:
            with session_scope() as session:
                service = CorrespondenceService(session)
                results = service.search(
                    query=search_text or None,
                    direction=direction,
                    status_code=status,
                    date_from=self._date_from.date().toPython(),
                    date_to=self._date_to.date().toPython(),
                    overdue_only=self._overdue_check.isChecked(),
                )
                self._table.set_data(results)
        except Exception:
            pass

    def _on_tab_changed(self, index):
        pass
