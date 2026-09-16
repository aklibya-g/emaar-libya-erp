from __future__ import annotations

DARK_THEME = """
/* ============================
   Emaar Libya ERP - Dark Theme
   ============================ */

/* Global */
QMainWindow, QDialog {
    background-color: #1a1d23;
    color: #e4e6eb;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #e4e6eb;
}

/* Sidebar */
#sidebar {
    background-color: #0f1117;
    border-right: 1px solid #2a2d35;
    min-width: 240px;
    max-width: 240px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: right;
    font-size: 13px;
    margin: 2px 8px;
}

#sidebar QPushButton:hover {
    background-color: #1f2937;
    color: #e4e6eb;
}

#sidebar QPushButton:checked {
    background-color: #1e40af;
    color: #ffffff;
}

#sidebarTitle {
    color: #60a5fa;
    font-size: 14px;
    font-weight: bold;
    padding: 16px;
    border-bottom: 1px solid #2a2d35;
}

#companyLabel {
    color: #9ca3af;
    font-size: 11px;
    padding: 0px 16px 12px 16px;
}

/* Top Bar */
#topBar {
    background-color: #111318;
    border-bottom: 1px solid #2a2d35;
    min-height: 56px;
    max-height: 56px;
}

#topBarTitle {
    color: #e4e6eb;
    font-size: 18px;
    font-weight: bold;
}

#topBarSubtitle {
    color: #9ca3af;
    font-size: 12px;
}

/* Cards */
#statCard {
    background-color: #1f2937;
    border-radius: 12px;
    border: 1px solid #2a2d35;
    padding: 16px;
}

#statCard:hover {
    border-color: #3b82f6;
}

#statCardTitle {
    color: #9ca3af;
    font-size: 12px;
    font-weight: 500;
}

#statCardValue {
    color: #e4e6eb;
    font-size: 28px;
    font-weight: bold;
}

#statCardIcon {
    font-size: 24px;
}

/* Tables */
QTableWidget {
    background-color: #1a1d23;
    alternate-background-color: #1f2937;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    gridline-color: #2a2d35;
    selection-background-color: #1e40af;
    selection-color: #ffffff;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #2a2d35;
}

QTableWidget::item:selected {
    background-color: #1e40af;
}

QHeaderView::section {
    background-color: #111318;
    color: #9ca3af;
    border: none;
    border-bottom: 2px solid #2a2d35;
    padding: 10px 12px;
    font-weight: bold;
    font-size: 12px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    background-color: #1f2937;
    color: #e4e6eb;
}

/* Buttons */
QPushButton {
    background-color: #1e40af;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #374151;
    color: #6b7280;
}

#secondaryButton {
    background-color: #374151;
    color: #e4e6eb;
}

#secondaryButton:hover {
    background-color: #4b5563;
}

#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
}

#dangerButton:hover {
    background-color: #ef4444;
}

#successButton {
    background-color: #059669;
    color: #ffffff;
}

#successButton:hover {
    background-color: #10b981;
}

#iconButton {
    background-color: transparent;
    color: #9ca3af;
    padding: 6px;
    border-radius: 6px;
}

#iconButton:hover {
    background-color: #1f2937;
    color: #e4e6eb;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
    background-color: #1f2937;
    color: #e4e6eb;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #1e40af;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #3b82f6;
}

QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {
    background-color: #111318;
    color: #6b7280;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #9ca3af;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1f2937;
    color: #e4e6eb;
    border: 1px solid #2a2d35;
    selection-background-color: #1e40af;
    border-radius: 8px;
    padding: 4px;
}

/* Labels */
#formLabel {
    color: #9ca3af;
    font-size: 12px;
    font-weight: 500;
}

/* Group Box */
QGroupBox {
    border: 1px solid #2a2d35;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #e4e6eb;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 8px;
    color: #60a5fa;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #1a1d23;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #4b5563;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6b7280;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1a1d23;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #4b5563;
    border-radius: 5px;
    min-width: 30px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #2a2d35;
    border-radius: 8px;
    background-color: #1a1d23;
}

QTabBar::tab {
    background-color: #1f2937;
    color: #9ca3af;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 20px;
    font-size: 13px;
}

QTabBar::tab:selected {
    color: #60a5fa;
    border-bottom-color: #3b82f6;
}

QTabBar::tab:hover {
    background-color: #2a2d35;
    color: #e4e6eb;
}

/* Status Badges */
#statusActive {
    color: #10b981;
    background-color: rgba(16, 185, 129, 0.15);
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
}

#statusInactive {
    color: #ef4444;
    background-color: rgba(239, 68, 68, 0.15);
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
}

#statusPending {
    color: #f59e0b;
    background-color: rgba(245, 158, 11, 0.15);
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
}

/* Tooltips */
QToolTip {
    background-color: #1f2937;
    color: #e4e6eb;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* Menu */
QMenu {
    background-color: #1f2937;
    color: #e4e6eb;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #1e40af;
}

/* Splitter */
QSplitter::handle {
    background-color: #2a2d35;
    width: 2px;
}

/* Progress Bar */
QProgressBar {
    background-color: #1f2937;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 4px;
}

/* Message Box */
QMessageBox {
    background-color: #1a1d23;
}

QMessageBox QLabel {
    color: #e4e6eb;
    font-size: 13px;
}
"""
