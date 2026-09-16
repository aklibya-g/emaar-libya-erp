from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QButtonGroup, QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QIcon


class NavButton(QPushButton):
    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_char}  {text}" if icon_char else text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class Sidebar(QWidget):
    navigation_changed = Signal(str)

    NAV_ITEMS = [
        ("dashboard", "Dashboard", "\u2302"),
        ("__separator__", "الأقسام", ""),
        ("employees", "شؤون الموظفين", "\u263A"),
        ("drivers", "شؤون السائقين", "\u2690"),
        ("customers", "زبائن النقل", "\u260E"),
        ("departments", "الأقسام", "\u2630"),
        ("__separator__", "العمليات", ""),
        ("correspondence", "المراسلات", "\u2709"),
        ("administration", "الشؤون الإدارية", "\u2611"),
        ("warehouses", "المخازن", "\u2612"),
        ("documents", "المستندات والأرشيف", "\u2637"),
        ("__separator__", "الإدارة", ""),
        ("templates", "القوالب", "\u2637"),
        ("signatures", "التوقيعات والأختام", "\u270D"),
        ("reports", "التقارير", "\u2630"),
        ("notifications", "الإشعارات", "\u2709"),
        ("users", "المستخدمون والصلاحيات", "\u260E"),
        ("backup", "النسخ الاحتياطي", "\u2601"),
        ("settings", "الإعدادات", "\u2699"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet(self.styleSheet())
        self._setup_ui()
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[str, NavButton] = {}
        self._create_buttons()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QVBoxLayout()
        header.setContentsMargins(16, 16, 16, 8)

        title = QLabel("Emaar ERP")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignCenter)
        header.addWidget(title)

        company = QLabel("\u0634\u0631\u0643\u0629 \u0625\u0639\u0645\u0627\u0631 \u0644\u064A\u0628\u064A\u0627")
        company.setObjectName("companyLabel")
        company.setAlignment(Qt.AlignCenter)
        header.addWidget(company)

        layout.addLayout(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #2a2d35; max-height: 1px;")
        layout.addWidget(separator)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._nav_container = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_container)
        self._nav_layout.setContentsMargins(0, 8, 0, 8)
        self._nav_layout.setSpacing(2)

        scroll.setWidget(self._nav_container)
        layout.addWidget(scroll)

        layout.addStretch()

        user_frame = QFrame()
        user_frame.setStyleSheet("background-color: #111318; border-top: 1px solid #2a2d35;")
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(12, 10, 12, 10)

        self._user_label = QLabel("\u263A  \u0645\u0633\u062A\u062E\u062F\u0645")
        self._user_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        user_layout.addWidget(self._user_label)
        user_layout.addStretch()

        logout_btn = QPushButton("\u274C")
        logout_btn.setObjectName("iconButton")
        logout_btn.setFixedSize(32, 32)
        logout_btn.setToolTip("\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062E\u0631\u0648\u062C")
        user_layout.addWidget(logout_btn)

        layout.addWidget(user_frame)

    def _create_buttons(self):
        for key, label, icon in self.NAV_ITEMS:
            if key == "__separator__":
                sep_label = QLabel(label)
                sep_label.setStyleSheet(
                    "color: #4b5563; font-size: 10px; font-weight: bold; "
                    "padding: 8px 16px 4px 16px; text-transform: uppercase;"
                )
                self._nav_layout.addWidget(sep_label)
                continue

            btn = NavButton(label, icon)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_click(k))
            self._nav_layout.addWidget(btn)
            self._buttons[key] = btn

        self._nav_layout.addStretch()

    def _on_nav_click(self, key: str):
        for btn_key, btn in self._buttons.items():
            btn.setChecked(btn_key == key)
        self.navigation_changed.emit(key)

    def set_active(self, key: str):
        if key in self._buttons:
            self._buttons[key].setChecked(True)

    def set_user_name(self, name: str):
        self._user_label.setText(f"\u263A  {name}")
