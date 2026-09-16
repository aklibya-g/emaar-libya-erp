from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.widgets.stat_card import StatCard
from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Employee, Driver, Customer, Department, Warehouse,
    Correspondence, CorrespondenceStatus, StockTransaction,
)


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        header = QLabel("\u0644\u0648\u062D\u0629 \u0627\u0644\u0645\u0639\u0644\u0648\u0645\u0627\u062A")
        header.setStyleSheet("color: #e4e6eb; font-size: 22px; font-weight: bold;")
        layout.addWidget(header)

        subtitle = QLabel(
            "\u0645\u0631\u062D\u0628\u064B\u0627 \u0628\u0643 \u0625\u0644\u0649 \u0646\u0638\u0627\u0645 \u0625\u0639\u0645\u0627\u0631 \u0644\u064A\u0628\u064A\u0627 \u0644\u0646\u0642\u0644 \u0627\u0644\u0631\u0643\u0627\u0628"
        )
        subtitle.setStyleSheet("color: #6b7280; font-size: 13px;")
        layout.addWidget(subtitle)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)

        self._emp_card = StatCard("\u0627\u0644\u0645\u0648\u0638\u0641\u064A\u0646", "0", "\u263A", "#3b82f6")
        self._driver_card = StatCard("\u0627\u0644\u0633\u0627\u0626\u0642\u064A\u0646", "0", "\u2690", "#8b5cf6")
        self._customer_card = StatCard("\u0627\u0644\u0639\u0645\u0644\u0627\u0621", "0", "\u260E", "#06b6d4")
        self._dept_card = StatCard("\u0627\u0644\u0623\u0642\u0633\u0627\u0645", "0", "\u2630", "#f59e0b")

        stats_grid.addWidget(self._emp_card, 0, 0)
        stats_grid.addWidget(self._driver_card, 0, 1)
        stats_grid.addWidget(self._customer_card, 0, 2)
        stats_grid.addWidget(self._dept_card, 0, 3)

        layout.addLayout(stats_grid)

        stats_grid2 = QGridLayout()
        stats_grid2.setSpacing(12)

        self._cor_in_card = StatCard("\u0627\u0644\u0648\u0627\u0631\u062F", "0", "\u2709", "#10b981")
        self._cor_out_card = StatCard("\u0627\u0644\u0635\u0627\u062F\u0631", "0", "\u2709", "#ef4444")
        self._cor_pending_card = StatCard("\u0642\u064A\u062F \u0627\u0644\u0645\u062A\u0627\u0628\u0639\u0629", "0", "\u23F1", "#f59e0b")
        self._warehouse_card = StatCard("\u0627\u0644\u0645\u062E\u0627\u0632\u0646", "0", "\u2612", "#0ea5e9")

        stats_grid2.addWidget(self._cor_in_card, 0, 0)
        stats_grid2.addWidget(self._cor_out_card, 0, 1)
        stats_grid2.addWidget(self._cor_pending_card, 0, 2)
        stats_grid2.addWidget(self._warehouse_card, 0, 3)

        layout.addLayout(stats_grid2)

        info_frame = QFrame()
        info_frame.setStyleSheet(
            "background-color: #1f2937; border-radius: 12px; border: 1px solid #2a2d35;"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(20, 16, 20, 16)

        info_title = QLabel("\u0645\u0639\u0644\u0648\u0645\u0627\u062A \u0639\u0627\u0645\u0629")
        info_title.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(info_title)

        info_items = [
            ("\u0627\u0644\u0628\u0631\u0646\u0627\u0645\u062C", "Python 3.10+ / PySide6 / SQLAlchemy"),
            ("\u0642\u0627\u0639\u062F\u0629 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A", "SQLite / PostgreSQL"),
            ("\u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629", "SQLAlchemy + Alembic"),
            ("\u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062A", "24 وحدة \u0646\u0638\u0627\u0645\u0629"),
        ]
        for label, value in info_items:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"\u2022 {label}:"))
            val_label = QLabel(value)
            val_label.setStyleSheet("color: #9ca3af;")
            row.addWidget(val_label)
            row.addStretch()
            info_layout.addLayout(row)

        layout.addWidget(info_frame)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        try:
            with session_scope() as session:
                emp_count = session.query(Employee).filter(Employee.is_deleted == False).count()
                driver_count = session.query(Driver).filter(Driver.is_deleted == False).count()
                customer_count = session.query(Customer).filter(Customer.is_deleted == False).count()
                dept_count = session.query(Department).filter(Department.is_deleted == False).count()
                warehouse_count = session.query(Warehouse).filter(Warehouse.is_deleted == False).count()
                cor_count = session.query(Correspondence).filter(Correspondence.is_deleted == False).count()

                self._emp_card.set_value(emp_count)
                self._driver_card.set_value(driver_count)
                self._customer_card.set_value(customer_count)
                self._dept_card.set_value(dept_count)
                self._cor_in_card.set_value(cor_count)
                self._cor_out_card.set_value(cor_count)
                self._cor_pending_card.set_value(0)
                self._warehouse_card.set_value(warehouse_count)
        except Exception:
            pass
