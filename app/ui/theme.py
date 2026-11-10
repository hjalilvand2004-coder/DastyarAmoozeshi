# -*- coding: utf-8 -*-
"""قالب ظاهری: راست‌به‌چپ، فونت فارسی، رنگ‌ها"""

from __future__ import annotations

from pathlib import Path

from ..config import resources_dir

QSS = """
* { font-family: 'Vazirmatn', 'Tahoma', 'Segoe UI', sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: #f5f6fa; }
#sidebar { background: #283593; }
#sidebar QListWidget {
    background: transparent; color: #e8eaf6; border: none; padding: 8px 4px; font-size: 14px;
}
#sidebar QListWidget::item { padding: 10px 14px; margin: 2px 6px; border-radius: 8px; }
#sidebar QListWidget::item:selected { background: #3949ab; color: #ffffff; }
#sidebar QLabel { color: #c5cae9; padding: 10px 12px 4px; font-size: 15px; font-weight: bold; }
#header { background: #ffffff; border-bottom: 1px solid #e0e0e0; }
#header QLabel { color: #333; }
#card { background: #ffffff; border: 1px solid #e3e6ef; border-radius: 10px; }
#card QLabel { color: #2b2b2b; }
QPushButton {
    background: #3949ab; color: white; border: none; border-radius: 8px;
    padding: 8px 16px; font-weight: bold;
}
QPushButton:hover { background: #303f9f; }
QPushButton:disabled { background: #b9bfe8; }
QPushButton[flat="true"] { background: #eceff1; color: #283593; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {
    background: #ffffff; border: 1px solid #cfd4e4; border-radius: 8px; padding: 6px 10px;
}
QTextEdit[readonly="true"], QTextBrowser { background: #ffffff; border: 1px solid #e3e6ef; border-radius: 10px; padding: 8px; }
QTableWidget { background: #ffffff; border: 1px solid #e3e6ef; border-radius: 10px; gridline-color: #edf0f7; }
QHeaderView::section { background: #eef1f9; color: #283593; padding: 6px; border: none; font-weight: bold; }
QLabel#hint { color: #888; font-size: 12px; }
QLabel#sectionTitle { color: #283593; font-size: 16px; font-weight: bold; }
QCheckBox { spacing: 8px; }
QTabWidget::pane { border: 1px solid #e3e6ef; border-radius: 8px; background: #fff; }
QTabBar::tab { padding: 8px 18px; color: #555; }
QTabBar::tab:selected { color: #283593; border-bottom: 2px solid #3949ab; }
"""


def apply_app_style(app) -> None:
    # فونت وزیرمتن اگر همراه برنامه باشد
    fonts_dir = Path(resources_dir()) / "fonts"
    try:
        from PyQt6.QtGui import QFontDatabase
        for f in fonts_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(f))
    except Exception:
        pass
    try:
        from PyQt6.QtGui import QFont
        app.setFont(QFont("Vazirmatn", 10))
    except Exception:
        pass
    app.setStyleSheet(QSS)
