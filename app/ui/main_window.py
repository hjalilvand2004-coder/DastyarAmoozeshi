# -*- coding: utf-8 -*-
"""پنجره اصلی + ورود با نقش‌ها"""

from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from .. import db
from ..answers import Answer
from ..config import APP_NAME_SHORT, VERSION
from ..jalali import format_jalali, weekday_fa
from ..services import ROLE_FA, has_perm, login, pending_reminders
from .pages_main import ChatPage, DashboardPage, ProcessGuidesPage, RegulationsBrowserPage
from .pages_services import AdvisorPage, DeadlinesPage, TicketsPage
from .pages_admin import KbAdminPage, RulesAdminPage, SettingsPage, UsersAdminPage


class LoginDialog(QDialog):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.user: dict | None = None
        self.setWindowTitle(f"ورود - {APP_NAME_SHORT} نسخه {VERSION}")
        self.setFixedWidth(420)
        v = QVBoxLayout(self)
        title = QLabel(f"ورود به {APP_NAME_SHORT}")
        title.setObjectName("sectionTitle")
        v.addWidget(title)
        form = QFormLayout()
        self.txt_user = QLineEdit()
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("نام کاربری:", self.txt_user)
        form.addRow("رمز عبور:", self.txt_pass)
        v.addLayout(form)
        self.btn_login = QPushButton("ورود")
        self.btn_login.clicked.connect(self._login)
        v.addWidget(self.btn_login)
        hint = QLabel("حساب‌های نمایشی: admin / expert / content / approver / student\n"
                      "رمز هر حساب به‌صورت Name@123 است (مثلاً Student@123).")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

    def _login(self):
        user = login(self.conn, self.txt_user.text(), self.txt_pass.text())
        if not user:
            QMessageBox.warning(self, "ورود", "نام کاربری یا رمز عبور نادرست است.")
            return
        self.user = user
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, conn, user: dict):
        super().__init__()
        self.conn = conn
        self.user = user
        self.setWindowTitle(f"{APP_NAME_SHORT} - {user.get('full_name') or user['username']}")
        self.resize(1150, 720)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # نوار کناری
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 10, 0, 10)
        brand = QLabel(APP_NAME_SHORT)
        sv.addWidget(brand)
        self.nav = QListWidget()
        sv.addWidget(self.nav, 1)
        h.addWidget(sidebar)

        # ستون اصلی
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(52)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(16, 6, 16, 6)
        self.lbl_today = QLabel()
        hh.addWidget(self.lbl_today)
        hh.addStretch(1)
        self.lbl_user = QLabel(f"{user.get('full_name') or user['username']} - "
                               f"{ROLE_FA.get(user['role'], user['role'])}")
        hh.addWidget(self.lbl_user)
        rv.addWidget(header)
        self.stack = QStackedWidget()
        rv.addWidget(self.stack, 1)
        h.addWidget(right, 1)
        self.setCentralWidget(central)

        self._build_pages()
        self.nav.currentRowChanged.connect(self._switch)
        self.nav.setCurrentRow(0)
        self._update_today()
        self._check_reminders()

    # ---------- صفحات ----------
    def _build_pages(self):
        self.pages: list[tuple[str, QWidget]] = []
        defs = [
            ("داشبورد", lambda: DashboardPage(self), None),
            ("گفتگو با دستیار", lambda: ChatPage(self), "chat"),
            ("مرور آیین‌نامه‌ها", lambda: RegulationsBrowserPage(self), "regs.read"),
            ("راهنمای فرایندها", lambda: ProcessGuidesPage(self), "regs.read"),
            ("مشاوره انتخاب واحد", lambda: AdvisorPage(self), "advisor.self"),
            ("یادآور و تقویم", lambda: DeadlinesPage(self), "deadlines.read"),
            ("درخواست از کارشناس", lambda: TicketsPage(self), "tickets.own"),
        ]
        if has_perm(self.user, "regs.create"):
            defs.append(("مدیریت اسناد", lambda: KbAdminPage(self), None))
        if has_perm(self.user, "rules.evaluate"):
            defs.append(("مدیریت قواعد", lambda: RulesAdminPage(self), None))
        if has_perm(self.user, "users.manage"):
            defs.append(("مدیریت کاربران", lambda: UsersAdminPage(self), None))
            defs.append(("تنظیمات", lambda: SettingsPage(self), None))
        for title, factory, perm in defs:
            if perm is not None and not has_perm(self.user, perm):
                continue
            page = factory()
            self.pages.append((title, page))
            self.stack.addWidget(page)
            QListWidgetItem(title, self.nav)

    def _switch(self, idx: int):
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)
            page = self.pages[idx][1]
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:
                    pass

    def _update_today(self):
        today = datetime.date.today()
        self.lbl_today.setText(f"امروز: {weekday_fa(today)} {format_jalali(today, 'long')}")

    def _check_reminders(self):
        try:
            pending = pending_reminders(self.conn, self.user)
        except Exception:
            pending = []
        if pending:
            titles = "\n".join(f"- {p['title']} ({p['date_fa']})" for p in pending[:5])
            QMessageBox.information(
                self, "یادآور رویدادها",
                "رویدادهای نزدیک که تأیید نکرده‌اید:\n" + titles +
                "\n\n(بر اساس نسخه جاری رویدادها؛ پس از هر اصلاح تقویم، یادآور دوباره اعلام می‌شود.)")

    def refresh_all(self):
        for _t, page in self.pages:
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:
                    pass
