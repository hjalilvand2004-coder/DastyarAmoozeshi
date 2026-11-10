# -*- coding: utf-8 -*-
"""راه‌انداز نسخه وب (FastAPI + React)

- python -m app.webapp            → اجرای سرور روی 127.0.0.1:8600
- python -m app.webapp --open     → باز شدن خودکار مرورگر
- متغیر D360_PORT برای تغییر پورت
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser


def run_web(open_browser: bool = False) -> int:
    from app import db, seed
    from app.config import APP_NAME, VERSION, db_path, web_port

    conn = db.connect(db_path())
    if seed.seed_if_empty(conn):
        print("[DastyarAmoozeshi] داده نمونه (غیررسمی) ایجاد شد.")
    conn.close()

    import uvicorn
    from app.api.server import app

    port = web_port()
    print(f"{APP_NAME} - نسخه {VERSION}")
    print(f"  وب‌اپ:   http://127.0.0.1:{port}/")
    print(f"  API docs: http://127.0.0.1:{port}/api/docs")
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}/")).start()
    uvicorn.run(app, host=os.environ.get("D360_HOST", "127.0.0.1"), port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(run_web(open_browser="--open" in sys.argv))
