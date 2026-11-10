# -*- coding: utf-8 -*-
"""نقطه اجرای برنامه: python run.py [گزینه‌ها]

- پیش‌فرض (وب):  FastAPI + رابط React  →  http://127.0.0.1:8600
- --open         باز شدن خودکار مرورگر
- --desktop      رابط دسکتاپ قدیمی (نیازمند PyQt6 - میراث نسخه اول)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import db, seed  # noqa: E402
from app.config import APP_NAME, VERSION, db_path  # noqa: E402


def main() -> int:
    argv = sys.argv[1:]
    print(f"{APP_NAME} - نسخه {VERSION}")

    if "--desktop" in argv:
        conn = db.connect(db_path())
        if seed.seed_if_empty(conn):
            print("[DastyarAmoozeshi] داده نمونه (غیررسمی) ایجاد شد.")
        try:
            from PyQt6.QtWidgets import QApplication  # noqa: F401
        except ImportError:
            print("PyQt6 نصب نیست. برای رابط دسکتاپ:  pip install -r requirements-desktop.txt")
            print("نسخه وب نیازی به PyQt ندارد:  python run.py")
            return 1
        from app.main import run_app
        return run_app(conn)

    from app.webapp import run_web
    return run_web(open_browser="--open" in argv)


if __name__ == "__main__":
    sys.exit(main())
