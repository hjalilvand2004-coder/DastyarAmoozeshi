# -*- coding: utf-8 -*-
"""راه‌اندازی رابط گرافیکی"""

from __future__ import annotations


def run_app(conn) -> int:
    from PyQt6.QtWidgets import QApplication

    from .ui.theme import apply_app_style
    from .ui.main_window import LoginDialog, MainWindow

    app = QApplication([])
    app.setApplicationName("DastyarAmoozeshi")
    app.setLayoutDirection(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)
    apply_app_style(app)

    login = LoginDialog(conn)
    if login.exec() != LoginDialog.DialogCode.Accepted or login.user is None:
        return 0
    win = MainWindow(conn, login.user)
    win.show()
    return app.exec()
