# -*- coding: utf-8 -*-
"""نقطه اجرای برنامه (کنسول): python run.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import db, seed  # noqa: E402
from app.config import APP_NAME, VERSION, db_path  # noqa: E402


def main() -> int:
    conn = db.connect(db_path())
    if seed.seed_if_empty(conn):
        print("[DastyarAmoozeshi] داده نمونه (غیررسمی) ایجاد شد.")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print("PyQt6 نصب نیست. برای اجرای رابط گرافیکی:  pip install -r requirements.txt")
        print("راهنما: docs/06-install.md")
        return 1
    from app.main import run_app
    return run_app(conn)


if __name__ == "__main__":
    print(f"{APP_NAME} - نسخه {VERSION}")
    sys.exit(main())
