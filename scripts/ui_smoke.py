# -*- coding: utf-8 -*-
"""تست دود رابط کاربری + تولید اسکرین‌شات (حالت offscreen)"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["DASTYAR_HOME"] = str(ROOT)
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from app import db, seed  # noqa: E402
from app.config import db_path  # noqa: E402
from app.services import login  # noqa: E402
from app.ui.theme import apply_app_style  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

# در حالت offscreen پنجره‌های مودال بلاک می‌شوند؛ خنثی می‌کنیم
QMessageBox.information = staticmethod(lambda *a, **k: print("[msgbox-info]", a[2] if len(a) > 2 else a))
QMessageBox.warning = staticmethod(lambda *a, **k: print("[msgbox-warn]", a[2] if len(a) > 2 else a))
QMessageBox.critical = staticmethod(lambda *a, **k: print("[msgbox-crit]", a[2] if len(a) > 2 else a))

IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

app = QApplication([])
app.setLayoutDirection(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)
apply_app_style(app)

conn = db.connect(db_path())
seed.seed_if_empty(conn)

SHOTS = {
    "student": [("مرور", "regs.png"), ("مشاوره", "advisor.png"),
                ("یادآور", "deadlines.png"), (None, "dashboard.png")],
    "expert": [("درخواست", "tickets.png"), ("مدیریت اسناد", "kb-admin.png"), (None, "dashboard-expert.png")],
    "admin": [("مدیریت قواعد", "rules-admin.png"), (None, "admin-pages.png")],
}

# نمونه پاسخ واقعی برای اسکرین‌شات صفحه گفتگو
from app import answers  # noqa: E402
student_login = login(conn, "student", "Student@123")
chat_win = MainWindow(conn, student_login)
chat_idx = next(i for i, (t, _p) in enumerate(chat_win.pages) if "گفتگو" in t)
chat_win.nav.setCurrentRow(chat_idx)
chat_page = chat_win.pages[chat_idx][1]
_ans = answers.ask(conn, student_login, "معدل لازم برای کارورزی چند است و چه مراحلی دارد؟")
chat_page.browser.append(_ans.to_html())
app.processEvents()
chat_win.grab().save(str(IMG / "chat.png"))
chat_win.close()

for username, pages in SHOTS.items():
    user = login(conn, username, {"student": "Student@123", "expert": "Expert@123", "admin": "Admin@123"}[username])
    assert user, username
    win = MainWindow(conn, user)
    win.show()
    app.processEvents()
    for nav_title, fname in pages:
        if nav_title:
            found = False
            for i, (t, _p) in enumerate(win.pages):
                if nav_title in t:
                    win.nav.setCurrentRow(i)
                    found = True
                    break
            if not found:
                continue
        else:
            win.nav.setCurrentRow(0)
        app.processEvents()
        win.grab().save(str(IMG / fname))
    win.close()

print("UI smoke OK, screenshots:", sorted(p.name for p in IMG.glob("*.png")))
