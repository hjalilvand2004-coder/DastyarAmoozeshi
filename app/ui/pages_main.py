# -*- coding: utf-8 -*-
"""صفحات اصلی: داشبورد، گفتگو، مرور اسناد، راهنمای فرایندها"""

from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter, QTextBrowser,
                             QVBoxLayout, QWidget)

from .. import answers, db, services
from ..answers import Answer
from ..jalali import format_jalali
from ..services import TICKET_STATUS_FA
from .widgets import Card, banner, error_box, info_box


class DashboardPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        settings = db.get_settings(win.conn)
        v.addWidget(banner(answers.SAMPLE_BANNER, "warn"))

        hello = Card()
        hello.body.addWidget(QLabel(
            f"خوش آمدید، {self.win.user.get('full_name') or self.win.user['username']}"))
        self.lbl_summary = QLabel()
        hello.body.addWidget(self.lbl_summary)
        v.addWidget(hello)

        c2 = Card("رویدادهای پیش‌رو (۳۰ روز آینده)")
        self.lst_deadlines = QListWidget()
        c2.body.addWidget(self.lst_deadlines)
        v.addWidget(c2, 1)

        c3 = Card("دسترسی سریع")
        h = QHBoxLayout()
        for text, key in [("پرسش از دستیار", 1), ("مرور آیین‌نامه‌ها", 2),
                          ("راهنمای فرایندها", 3), ("درخواست از کارشناس", 6)]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, k=key: self._go(k))
            h.addWidget(b)
        c3.body.addLayout(h)
        v.addWidget(c3)
        self.refresh()

    def _go(self, idx):
        if idx < self.win.stack.count():
            self.win.nav.setCurrentRow(idx)

    def refresh(self):
        rows = services.list_deadlines(self.win.conn, self.win.user)
        upcoming = [r for r in rows if 0 <= r["days_left"] <= 30]
        self.lst_deadlines.clear()
        for r in upcoming[:8]:
            state = "تأییدشده" if r["acked"] else "نیازمند تأیید"
            QListWidgetItem(f"{r['title']} - {r['date_fa']} - {state}", self.lst_deadlines)
        if not upcoming:
            QListWidgetItem("رویدادی در ۳۰ روز آینده ثبت نشده است.", self.lst_deadlines)
        tickets = services.list_tickets(self.win.conn, self.win.user)
        open_tk = [t for t in tickets if t["status"] not in ("closed",)]
        self.lbl_summary.setText(
            f"درخواست‌های باز شما: {len(open_tk)} | یادآورهای نزدیک: {len(upcoming)}")


class ChatPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.session_id = None
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)

        self.banner_sample = banner(answers.SAMPLE_BANNER, "warn")
        v.addWidget(self.banner_sample)

        top = QHBoxLayout()
        self.chk_retired = QCheckBox("نمایش نسخه‌های ملغی (برای مقایسه)")
        top.addWidget(self.chk_retired)
        top.addStretch(1)
        v.addLayout(top)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        v.addWidget(self.browser, 1)

        form = Card()
        fb = form.body
        self.txt_q = QPlainTextEdit()
        self.txt_q.setPlaceholderText("پرسش خود را بنویسید... (مثلاً: معدل لازم برای کارورزی چقدر است؟)")
        self.txt_q.setFixedHeight(70)
        fb.addWidget(self.txt_q)
        h = QHBoxLayout()
        self.btn_ask = QPushButton("پرسش از دستیار")
        self.btn_ask.clicked.connect(self._ask)
        h.addWidget(self.btn_ask)
        h.addStretch(1)
        self.lbl_provider = QLabel()
        h.addWidget(self.lbl_provider)
        fb.addLayout(h)
        v.addWidget(form)
        self.refresh()

    def refresh(self):
        settings = db.get_settings(self.win.conn)
        from ..llm import make_provider
        p = make_provider(settings)
        self.lbl_provider.setText(f"موتور پاسخ: {p.name}")

    def _ask(self):
        q = self.txt_q.toPlainText().strip()
        if not q:
            return
        self.btn_ask.setEnabled(False)
        try:
            ans = answers.ask(self.win.conn, self.win.user, q,
                              session_id=self.session_id,
                              include_retired=self.chk_retired.isChecked())
            self.session_id = ans.session_id
            html = (f'<div style="color:#283593;font-weight:bold;margin:10px 0 4px;">'
                    f'پرسش: {q}</div>' + ans.to_html() + '<hr>')
            cur = self.browser.toHtml()
            self.browser.append(html)
            self.txt_q.clear()
        except Exception as e:
            error_box(self, "خطا", str(e))
        finally:
            self.btn_ask.setEnabled(True)


class RegulationsBrowserPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)

        search_card = Card("جست‌وجو در آیین‌نامه‌ها")
        h = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("عبارت مورد نظر...")
        self.txt_search.returnPressed.connect(self._search)
        h.addWidget(self.txt_search, 1)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["همه", "منتشرشده", "ملغی‌شده"])
        h.addWidget(self.cmb_status)
        btn = QPushButton("جست‌وجو")
        btn.clicked.connect(self._search)
        h.addWidget(btn)
        search_card.body.addLayout(h)
        v.addWidget(search_card)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._show_doc)
        split.addWidget(self.lst)
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        split.addWidget(self.detail)
        split.setSizes([380, 720])
        v.addWidget(split, 1)
        self._docs: list[dict] = []

    def refresh(self):
        self._search()

    def _search(self):
        try:
            docs = services.list_documents(self.win.conn, self.win.user)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        status_filter = {"همه": None, "منتشرشده": "published", "ملغی‌شده": "retired"}[
            self.cmb_status.currentText()]
        q = (self.txt_search.text() or "").strip()
        from ..security import normalize_persian
        nq = normalize_persian(q).lower() if q else ""
        self._docs = []
        self.lst.clear()
        for d in docs:
            if status_filter and d["status"] != status_filter:
                continue
            if nq:
                from ..search import tokenize
                hay = normalize_persian(d["title"])
                chunk_texts = " ".join(c["text"] for c in db.q(
                    self.win.conn, "SELECT text FROM chunks WHERE document_id=?", (d["id"],)))
                hay = normalize_persian(hay + " " + chunk_texts).lower()
                if not all(w in hay for w in nq.split()):
                    continue
            self._docs.append(d)
            st = answers.DOC_STATUS_FA.get(d["status"], d["status"])
            QListWidgetItem(f"{d['title']} - نسخه {d['version_no']} ({st})", self.lst)
        if not self._docs:
            QListWidgetItem("موردی یافت نشد.", self.lst)

    def _show_doc(self, idx):
        if not (0 <= idx < len(self._docs)):
            self.detail.setHtml("")
            return
        d = self._docs[idx]
        rows = []
        rows.append(f"<h2>{d['title']}</h2>")
        meta = (f"وضعیت: <b>{answers.DOC_STATUS_FA.get(d['status'], d['status'])}</b> | "
                f"نسخه: {d['version_no']} | رسمی: {'بله' if d['is_official'] else 'خیر (غیررسمی)'}")
        if d.get("effective_from"):
            try:
                ef = datetime.date.fromisoformat(d["effective_from"])
                meta += f" | از تاریخ {format_jalali(ef)}"
            except ValueError:
                pass
        if d.get("effective_until"):
            eu = datetime.date.fromisoformat(d["effective_until"])
            meta += f" | تا {format_jalali(eu)}"
        for k, label in [("scope_level", "مقطع"), ("scope_major", "رشته")]:
            if d.get(k):
                meta += f" | {label}: {d[k]}"
        if d.get("scope_entry_from") or d.get("scope_entry_to"):
            meta += f" | ورودی: {d.get('scope_entry_from') or '?'} تا {d.get('scope_entry_to') or '?'}"
        rows.append(f"<p>{meta}</p>")
        if d.get("url"):
            rows.append(f'<p><a href="{d["url"]}">{d["url"]}</a></p>')
        if d.get("source_note"):
            rows.append(f'<p style="color:#a33;">{d["source_note"]}</p>')
        if d["status"] == "retired":
            reason = d.get("retired_reason") or ""
            rows.append(f"<p style='color:#b71c1c;'>این نسخه ملغی شده است. {reason}</p>")
        try:
            chunks = services.get_document_chunks(self.win.conn, self.win.user, d["id"])
        except Exception as e:
            rows.append(f"<p style='color:#b71c1c;'>{e}</p>")
            chunks = []
        for c in chunks:
            head = c["clause_ref"] or f"بخش {c['idx'] + 1}"
            page = f" (صفحه {c['page_no']})" if c.get("page_no") else ""
            rows.append(f"<h3>{head}{page}</h3><div style='white-space:pre-wrap;'>{c['text']}</div>")
        self.detail.setHtml("".join(rows))


class ProcessGuidesPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.addWidget(banner("این راهنما فقط مراحل را توضیح می‌دهد؛ ثبت نهایی همیشه در سامانه رسمی "
                           "دانشگاه انجام می‌شود و این دستیار هرگز «ثبت موفق» اعلام نمی‌کند.", "info"))
        split = QSplitter(Qt.Orientation.Horizontal)
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._show)
        split.addWidget(self.lst)
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        split.addWidget(self.detail)
        split.setSizes([340, 760])
        v.addWidget(split, 1)
        h = QHBoxLayout()
        self.btn_open = QPushButton("رفتن به سامانه مقصد")
        self.btn_open.clicked.connect(self._open_target)
        h.addWidget(self.btn_open)
        self.btn_follow = QPushButton("ایجاد درخواست پیگیری برای کارشناس")
        self.btn_follow.clicked.connect(self._follow)
        h.addWidget(self.btn_follow)
        h.addStretch(1)
        v.addLayout(h)
        self._procs: list[dict] = []

    def refresh(self):
        self._procs = services.list_processes(self.win.conn, self.win.user)
        self.lst.clear()
        for p in self._procs:
            QListWidgetItem(p["title"], self.lst)
        if not self._procs:
            QListWidgetItem("فرایندی ثبت نشده است.", self.lst)

    def _show(self, idx):
        import json
        if not (0 <= idx < len(self._procs)):
            self.detail.setHtml("")
            return
        p = self._procs[idx]
        rows = [f"<h2>{p['title']}</h2>"]
        if p.get("notes"):
            rows.append(f"<p style='color:#a33;'>{p['notes']}</p>")
        try:
            steps = json.loads(p["steps"])
        except json.JSONDecodeError:
            steps = []
        rows.append("<h3>مراحل</h3><ol>")
        for s in steps:
            rows.append(f"<li>{s}</li>")
        rows.append("</ol>")
        try:
            docs = json.loads(p.get("required_docs") or "[]")
        except json.JSONDecodeError:
            docs = []
        if docs:
            rows.append("<h3>مدارک لازم</h3><ul>")
            for d in docs:
                rows.append(f"<li>{d}</li>")
            rows.append("</ul>")
        if p.get("target_system"):
            rows.append(f"<p>سامانه مقصد: <b>{p['target_system']}</b>"
                        + (f' - <a href="{p["target_url"]}">{p["target_url"]}</a>' if p.get("target_url") else "")
                        + "</p>")
        rows.append("<p style='color:#777;'>توجه: موفقیت ثبت فقط پس از تأیید در خود سامانه مقصد معتبر است.</p>")
        self.detail.setHtml("".join(rows))
        self._current = p

    def _open_target(self):
        p = getattr(self, "_current", None)
        if p and p.get("target_url"):
            QDesktopServices.openUrl(QUrl(p["target_url"]))

    def _follow(self):
        p = getattr(self, "_current", None)
        if not p:
            return
        try:
            services.create_ticket(self.win.conn, self.win.user,
                                   f"پیگیری فرایند: {p['title']}",
                                   "لطفاً وضعیت درخواست من برای این فرایند را بررسی کنید.")
            info_box(self, "درخواست", "درخواست پیگیری برای کارشناس ثبت شد.")
        except Exception as e:
            error_box(self, "خطا", str(e))
