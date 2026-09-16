from __future__ import annotations

from typing import List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QLabel, QPushButton, QComboBox,
    QAbstractItemView, QFrame, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class DataTable(QWidget):
    row_selected = Signal(str)
    row_double_clicked = Signal(str)
    search_changed = Signal(str)

    def __init__(self, columns: List[dict], parent=None):
        super().__init__(parent)
        self._columns = columns
        self._data: List[Any] = []
        self._id_column = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("\u2315  \u0628\u062D\u062B...")
        self._search.setMinimumWidth(250)
        self._search.textChanged.connect(self._on_search)
        toolbar.addWidget(self._search)

        self._filter_combo = QComboBox()
        self._filter_combo.setMinimumWidth(150)
        self._filter_combo.setPlaceholderText("\u062A\u0635\u0646\u064A\u0641...")
        self._filter_combo.currentIndexChanged.connect(self._on_filter)
        toolbar.addWidget(self._filter_combo)

        toolbar.addStretch()

        self._count_label = QLabel("0 \u0633\u062C\u0644")
        self._count_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._table.setColumnCount(len(self._columns))
        headers = [col.get("title", "") for col in self._columns]
        self._table.setHorizontalHeaderLabels(headers)

        for i, col in enumerate(self._columns):
            width = col.get("width", 150)
            self._table.setColumnWidth(i, width)

        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        self._table.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

    def set_data(self, data: List[Any]):
        self._data = data
        self._populate_table()

    def _populate_table(self):
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._data))

        for row_idx, item in enumerate(self._data):
            for col_idx, col_def in enumerate(self._columns):
                accessor = col_def.get("accessor", "")
                value = ""
                if callable(accessor):
                    value = accessor(item)
                elif hasattr(item, accessor):
                    value = getattr(item, accessor, "")
                elif isinstance(item, dict) and accessor in item:
                    value = item[accessor]

                display_value = str(value) if value is not None else ""
                widget_item = QTableWidgetItem(display_value)
                widget_item.setTextAlignment(Qt.AlignCenter if col_def.get("center") else Qt.AlignRight | Qt.AlignVCenter)

                if col_def.get("id_column"):
                    widget_item.setData(Qt.UserRole, getattr(item, "id", "") if hasattr(item, "id") else item.get("id", ""))

                self._table.setItem(row_idx, col_idx, widget_item)

        self._count_label.setText(f"{len(self._data)} \u0633\u062C\u0644")

    def _on_search(self, text: str):
        text_lower = text.lower()
        for row in range(self._table.rowCount()):
            show = False
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item and text_lower in item.text().lower():
                    show = True
                    break
            self._table.setRowHidden(row, not show)
        self.search_changed.emit(text)

    def _on_filter(self, index: int):
        pass

    def _on_selection(self):
        rows = self._table.selectionModel().selectedRows()
        if rows:
            item = self._table.item(rows[0].row(), 0)
            if item:
                self.row_selected.emit(item.data(Qt.UserRole) or item.text())

    def _on_double_click(self, index):
        item = self._table.item(index.row(), 0)
        if item:
            self.row_double_clicked.emit(item.data(Qt.UserRole) or item.text())

    def get_selected_id(self) -> Optional[str]:
        rows = self._table.selectionModel().selectedRows()
        if rows:
            item = self._table.item(rows[0].row(), 0)
            if item:
                return item.data(Qt.UserRole) or item.text()
        return None

    def set_filters(self, filters: List[str]):
        self._filter_combo.clear()
        self._filter_combo.addItem("\u062C\u0645\u064A\u0639")
        for f in filters:
            self._filter_combo.addItem(f)
