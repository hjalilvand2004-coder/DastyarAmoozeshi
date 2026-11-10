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


def _module_main() -> None:
    """نقطه اجرا برای `python -m app.main` (نسخه پرتابل)"""
    import sys
    from . import db, seed
    from .config import APP_NAME, VERSION, db_path

    print(f"{APP_NAME} - نسخه {VERSION}")
    conn = db.connect(db_path())
    if seed.seed_if_empty(conn):
        print("[DastyarAmoozeshi] داده نمونه (غیررسمی) ایجاد شد.")
    sys.exit(run_app(conn))


if __name__ == "__main__":
    _module_main()
