from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QStackedWidget, QFrame, QPushButton, QStatusBar,
    QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from src.ui.widgets.navigation import Sidebar
from src.ui.widgets.stat_card import StatCard
from src.core.models.base_models import User


class MainWindow(QMainWindow):
    def __init__(self, user: Optional[User] = None):
        super().__init__()
        self._user = user
        self.setWindowTitle(
            "\u0645\u0646\u0638\u0648\u0645\u0629 \u0625\u0639\u0645\u0627\u0631 \u0644\u064A\u0628\u064A\u0627 \u0644\u0646\u0642\u0644 \u0627\u0644\u0631\u0643\u0627\u0628"
            " - Emaar Libya ERP"
        )
        self.setMinimumSize(1200, 800)
        self._setup_ui()
        self._setup_status_bar()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.navigation_changed.connect(self._on_navigate)
        main_layout.addWidget(self._sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._top_bar = QFrame()
        self._top_bar.setObjectName("topBar")
        self._top_bar.setFixedHeight(56)
        top_layout = QHBoxLayout(self._top_bar)
        top_layout.setContentsMargins(24, 0, 24, 0)

        self._top_title = QLabel("\u0644\u0648\u062D\u0629 \u0627\u0644\u0645\u0639\u0644\u0648\u0645\u0627\u062A")
        self._top_title.setObjectName("topBarTitle")
        top_layout.addWidget(self._top_title)

        top_layout.addStretch()

        search_input = QLineEdit()
        search_input.setPlaceholderText("\u0628\u062D\u062B \u0639\u0627\u0645...")
        search_input.setMinimumWidth(300)
        search_input.setStyleSheet(
            "QLineEdit { background-color: #1f2937; border: 1px solid #2a2d35; "
            "border-radius: 8px; padding: 6px 12px; color: #e4e6eb; }"
        )
        top_layout.addWidget(search_input)

        content_layout.addWidget(self._top_bar)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background-color: #1a1d23;")
        content_layout.addWidget(self._stack)

        main_layout.addWidget(content)

        if self._user:
            self._sidebar.set_user_name(self._user.full_name_ar)

    def _setup_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("\u062C\u0627\u0647\u0632 \u0644\u0644\u0639\u0645\u0644")

    def add_page(self, key: str, widget: QWidget):
        self._stack.addWidget(widget)

    def _on_navigate(self, key: str):
        page_map = {self._stack.itemText(i): i for i in range(self._stack.count())}
        if key in page_map:
            self._stack.setCurrentIndex(page_map[key])
            titles = {
                "dashboard": "\u0644\u0648\u062D\u0629 \u0627\u0644\u0645\u0639\u0644\u0648\u0645\u0627\u062A",
                "employees": "\u0634\u0626\u0648\u0646 \u0627\u0644\u0645\u0648\u0638\u0641\u064A\u0646",
                "drivers": "\u0634\u0626\u0648\u0646 \u0627\u0644\u0633\u0627\u0626\u0642\u064A\u0646",
                "customers": "\u0632\u0628\u0627\u0626\u0646 \u0627\u0644\u0646\u0642\u0644",
                "departments": "\u0627\u0644\u0623\u0642\u0633\u0627\u0645",
                "correspondence": "\u0627\u0644\u0645\u0631\u0627\u0633\u0644\u0627\u062A",
                "administration": "\u0627\u0644\u0634\u0626\u0648\u0646 \u0627\u0644\u0625\u062F\u0627\u0631\u064A\u0629",
                "warehouses": "\u0627\u0644\u0645\u062E\u0627\u0632\u0646",
                "documents": "\u0627\u0644\u0645\u0633\u062A\u0646\u062F\u0627\u062A \u0648\u0627\u0644\u0623\u0631\u0634\u064A\u0641",
                "templates": "\u0627\u0644\u0642\u0648\u0627\u0644\u0628",
                "signatures": "\u0627\u0644\u062A\u0648\u0642\u064A\u0639\u0627\u062A \u0648\u0627\u0644\u0623\u062E\u062A\u0627\u0645",
                "reports": "\u0627\u0644\u062A\u0642\u0627\u0631\u064A\u0631",
                "notifications": "\u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062A",
                "users": "\u0627\u0644\u0645\u0633\u062A\u062E\u062F\u0645\u0648\u0646 \u0648\u0627\u0644\u0635\u0644\u0627\u062D\u064A\u0627\u062A",
                "backup": "\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A",
                "settings": "\u0627\u0644\u0625\u0639\u062F\u0627\u062F\u0627\u062A",
            }
            self._top_title.setText(titles.get(key, key))

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "\u062A\u0623\u0643\u064A\u062F \u0627\u0644\u0625\u063A\u0644\u0627\u0642",
            "\u0647\u0644 \u0623\u0646\u062A \u0645\u062A\u0623\u0643\u062F \u0645\u0646 \u0625\u063A\u0644\u0627\u0642 \u0627\u0644\u0646\u0638\u0627\u0645\u061F",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
