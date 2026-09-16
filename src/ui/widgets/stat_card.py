from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StatCard(QWidget):
    def __init__(
        self,
        title: str,
        value: str | int,
        icon: str = "",
        color: str = "#3b82f6",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setObjectName("statCardIcon")
            icon_label.setStyleSheet(f"color: {color}; font-size: 20px;")
            top_row.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("statCardTitle")
        top_row.addWidget(title_label)
        top_row.addStretch()

        layout.addLayout(top_row)

        self._value_label = QLabel(str(value))
        self._value_label.setObjectName("statCardValue")
        layout.addWidget(self._value_label)

        self.setStyleSheet(
            f"#statCard {{ border-left: 3px solid {color}; }}"
        )

    def set_value(self, value: str | int):
        self._value_label.setText(str(value))


class DashboardCard(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        title_label = QLabel(title)
        title_label.setObjectName("statCardTitle")
        layout.addWidget(title_label)

        self._content_layout = QVBoxLayout()
        layout.addLayout(self._content_layout)
