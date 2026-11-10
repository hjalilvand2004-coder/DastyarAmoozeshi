# -*- coding: utf-8 -*-
"""صفحات سرویس‌ها: مشاوره انتخاب واحد، یادآور و تقویم، درخواست از کارشناس"""

from __future__ import annotations

import datetime
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from .. import services
from ..jalali import format_jalali, jalali_to_gregorian_iso
from ..services import TICKET_STATUS_FA, TICKET_TRANSITIONS
from .widgets import Card, banner, error_box, info_box


class AdvisorPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)

        v.addWidget(banner("این تحلیل فقط بر اساس داده ثبت‌شده در همین سامانه است و جایگزین "
                           "نظر رسمی سامانه آموزشی دانشگاه نیست.", "info"))
        self.lbl_student = QLabel()
        v.addWidget(self.lbl_student)

        c1 = Card("تحلیل پیش‌نیاز یک درس")
        h = QHBoxLayout()
        self.cmb_course = QComboBox()
        h.addWidget(self.cmb_course, 1)
        b1 = QPushButton("بررسی شرایط")
        b1.clicked.connect(self._analyze)
        h.addWidget(b1)
        c1.body.addLayout(h)
        self.txt_result = QTextBrowser()
        self.txt_result.setFixedHeight(160)
        c1.body.addWidget(self.txt_result)
        v.addWidget(c1)

        c2 = Card("برنامه ترم بعد و فارغ‌التحصیلی")
        h2 = QHBoxLayout()
        b2 = QPushButton("پیشنهاد دروس ترم بعد")
        b2.clicked.connect(self._suggest)
        h2.addWidget(b2)
        b3 = QPushButton("بررسی وضعیت فارغ‌التحصیلی")
        b3.clicked.connect(self._audit)
        h2.addWidget(b3)
        h2.addStretch(1)
        c2.body.addLayout(h2)
        self.txt_result2 = QTextBrowser()
        c2.body.addWidget(self.txt_result2, 1)
        v.addWidget(c2, 1)
        self.refresh()

    def refresh(self):
        self._student = services.get_student_for_user(self.win.conn, self.win.user)
        if self._student:
            s = self._student
            self.lbl_student.setText(
                f"دانشجو: {s.get('full_name') or '-'} | مقطع: {s.get('level') or 'نامشخص'} | "
                f"رشته: {s.get('major') or 'نامشخص'} | ورودی: {s.get('entry_year') or 'نامشخص'} | "
                f"معدل: {s.get('gpa') if s.get('gpa') is not None else 'نامشخص'} | "
                f"واحد گذرانده: {s.get('passed_credits') if s.get('passed_credits') is not None else 'نامشخص'}")
        else:
            self.lbl_student.setText("پروفایل دانشجو برای این کاربر یافت نشد.")
        self._courses = {c["id"]: c for c in services._load_courses(self.win.conn, self.win.user)}
        self.cmb_course.clear()
        for c in self._courses.values():
            self.cmb_course.addItem(f"{c['name']} ({c['code']}) - {c['credits']} واحد", c["id"])

    def _analyze(self):
        cid = self.cmb_course.currentData()
        if cid is None or not self._student:
            return
        try:
            res = services.analyze_course(self.win.conn, self.win.user, self._student, cid)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        color = {"satisfied": "#1b5e20", "not_satisfied": "#b71c1c",
                 "insufficient_info": "#7a5c00"}.get(res["status"], "#333")
        html = f"<p><b>نتیجه:</b> <span style='color:{color};font-weight:bold;'>{res['status_fa']}</span></p>"
        html += f"<p>{res['message']}</p>"
        if res.get("missing_courses"):
            html += "<p>دروس ناقص: " + "، ".join(res["missing_courses"]) + "</p>"
        self.txt_result.setHtml(html)

    def _suggest(self):
        if not self._student:
            return
        res = services.suggest_next_courses(self.win.conn, self.win.user, self._student)
        html = f"<p>{res['message']}</p><ol>"
        for it in res["items"]:
            ok = "قابل انتخاب" if it["ok"] else "پیش‌نیاز ناقص: " + "، ".join(it["missing"])
            html += f"<li>{it['course']['name']} ({it['course']['credits']} واحد) - {ok}</li>"
        html += "</ol>"
        self.txt_result2.setHtml(html)

    def _audit(self):
        if not self._student:
            return
        res = services.graduation_audit(self.win.conn, self.win.user, self._student)
        html = f"<p>{res['message']}</p>"
        if res.get("not_passed_courses"):
            html += "<p>دروس باقی‌مانده (بر اساس فهرست همین سامانه): " + \
                    "، ".join(c["name"] for c in res["not_passed_courses"]) + "</p>"
        self.txt_result2.setHtml(html)


class DeadlineDialog(QDialog):
    def __init__(self, parent, title="", date_iso="", notes=""):
        super().__init__(parent)
        self.setWindowTitle("رویداد تقویم")
        form = QFormLayout(self)
        self.txt_title = QLineEdit(title)
        self.txt_date = QLineEdit()
        if date_iso:
            try:
                self.txt_date.setText(format_jalali(datetime.date.fromisoformat(date_iso), "iso"))
            except ValueError:
                pass
        self.txt_date.setPlaceholderText("۱۴۰۵/۰۹/۰۱")
        self.txt_notes = QLineEdit(notes)
        form.addRow("عنوان:", self.txt_title)
        form.addRow("تاریخ (جلالی):", self.txt_date)
        form.addRow("توضیح:", self.txt_notes)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def data(self):
        iso = jalali_to_gregorian_iso(self.txt_date.text())
        if not iso:
            raise ValueError("تاریخ جلالی نامعتبر است (نمونه صحیح: ۱۴۰۵/۰۹/۰۱).")
        return {"title": self.txt_title.text().strip(), "date_iso": iso,
                "notes": self.txt_notes.text().strip()}


class DeadlinesPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.addWidget(banner("پس از هر اصلاح رسمی تقویم، نسخه رویداد تغییر می‌کند و یادآور دوباره "
                           "اعلام می‌شود؛ تأییدهای قبلی باطل می‌شوند.", "info"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["عنوان", "تاریخ (جلالی)", "روز باقی‌مانده",
                                              "وضعیت یادآور", "عملیات"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 320)
        v.addWidget(self.table, 1)
        if services.has_perm(self.win.user, "deadlines.manage"):
            h = QHBoxLayout()
            b1 = QPushButton("افزودن رویداد")
            b1.clicked.connect(self._add)
            h.addWidget(b1)
            b2 = QPushButton("ویرایش رویداد انتخاب‌شده")
            b2.clicked.connect(self._edit)
            h.addWidget(b2)
            h.addStretch(1)
            v.addLayout(h)
        self.refresh()

    def refresh(self):
        rows = services.list_deadlines(self.win.conn, self.win.user)
        self._rows = rows
        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(r["date_fa"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(r["days_left"])))
            self.table.setItem(row, 3, QTableWidgetItem("تأییدشده" if r["acked"] else "نیازمند تأیید"))
            btn = QPushButton("تأیید دیدم")
            btn.setEnabled(not r["acked"])
            btn.clicked.connect(lambda _, did=r["id"]: self._ack(did))
            self.table.setCellWidget(row, 4, btn)

    def _ack(self, did):
        try:
            services.ack_deadline(self.win.conn, self.win.user, did)
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _add(self):
        dlg = DeadlineDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                d = dlg.data()
                services.create_deadline(self.win.conn, self.win.user, d["title"], d["date_iso"],
                                         notes=d["notes"])
            except Exception as e:
                error_box(self, "خطا", str(e))
            self.refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            info_box(self, "ویرایش", "ابتدا یک رویداد را از جدول انتخاب کنید.")
            return
        r = self._rows[row]
        dlg = DeadlineDialog(self, r["title"], r["date_iso"], r.get("notes") or "")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                d = dlg.data()
                services.update_deadline(self.win.conn, self.win.user, r["id"], d)
                QMessageBox.information(self, "تقویم",
                                        "رویداد اصلاح شد و نسخه جدید ثبت گردید؛ یادآور دوباره اعلام می‌شود.")
            except Exception as e:
                error_box(self, "خطا", str(e))
            self.refresh()


class TicketsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.is_staff = services.has_perm(win.user, "tickets.handle")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.addWidget(banner("وضعیت‌ها: ثبت‌شده ← در حال بررسی ← نیاز به اطلاعات ← پاسخ داده شده ← بسته",
                           "info"))
        split = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._show)
        lv.addWidget(self.lst, 1)
        if not self.is_staff:
            newc = Card("درخواست جدید")
            self.txt_subject = QLineEdit()
            self.txt_subject.setPlaceholderText("موضوع")
            self.txt_body = QPlainTextEdit()
            self.txt_body.setPlaceholderText("شرح درخواست...")
            self.txt_body.setFixedHeight(70)
            nb = QPushButton("ثبت درخواست")
            nb.clicked.connect(self._create)
            newc.body.addWidget(self.txt_subject)
            newc.body.addWidget(self.txt_body)
            newc.body.addWidget(nb)
            lv.addWidget(newc)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.thread = QTextBrowser()
        rv.addWidget(self.thread, 1)
        self.txt_reply = QPlainTextEdit()
        self.txt_reply.setPlaceholderText("پیام شما...")
        self.txt_reply.setFixedHeight(60)
        rv.addWidget(self.txt_reply)
        h = QHBoxLayout()
        self.btn_send = QPushButton("ارسال پیام")
        self.btn_send.clicked.connect(self._send)
        h.addWidget(self.btn_send)
        if self.is_staff:
            self.btn_transition = QPushButton("تغییر وضعیت")
            self.btn_transition.clicked.connect(self._transition)
            h.addWidget(self.btn_transition)
        h.addStretch(1)
        rv.addLayout(h)
        split.addWidget(right)
        split.setSizes([420, 730])
        v.addWidget(split, 1)
        self._tickets: list[dict] = []
        self.refresh()

    def refresh(self):
        try:
            self._tickets = services.list_tickets(self.win.conn, self.win.user)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        self.lst.clear()
        for t in self._tickets:
            who = f" - {t.get('requester', '')}" if self.is_staff and t.get("requester") else ""
            QListWidgetItem(f"#{t['id']} {t['subject']} [{t['status_fa']}]{who}", self.lst)
        if not self._tickets:
            QListWidgetItem("درخواستی ثبت نشده است.", self.lst)

    def _show(self, idx):
        if not (0 <= idx < len(self._tickets)):
            self.thread.setHtml("")
            return
        t = self._tickets[idx]
        try:
            data = services.ticket_thread(self.win.conn, self.win.user, t["id"])
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        rows = [f"<h2>#{t['id']} - {t['subject']}</h2>"
                f"<p>وضعیت: <b>{TICKET_STATUS_FA.get(t['status'], t['status'])}</b></p>"]
        for m in data["messages"]:
            who = m["author"] or "؟"
            tag = "کارشناس" if m["is_staff"] else "دانشجو"
            rows.append(f"<div style='background:#f4f6fb;border-radius:8px;padding:8px;margin:4px 0;'>"
                        f"<b>{who} ({tag})</b><div style='white-space:pre-wrap;'>{m['body']}</div></div>")
        self.thread.setHtml("".join(rows))
        self._current = t

    def _create(self):
        try:
            services.create_ticket(self.win.conn, self.win.user,
                                   self.txt_subject.text(), self.txt_body.toPlainText())
            self.txt_subject.clear()
            self.txt_body.clear()
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _send(self):
        t = getattr(self, "_current", None)
        if not t:
            return
        body = self.txt_reply.toPlainText().strip()
        if not body:
            return
        try:
            services.add_ticket_message(self.win.conn, self.win.user, t["id"], body)
            self.txt_reply.clear()
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _transition(self):
        t = getattr(self, "_current", None)
        if not t:
            return
        allowed = sorted(TICKET_TRANSITIONS.get(t["status"], set()))
        if not allowed:
            return
        labels = [f"{s} ({TICKET_STATUS_FA[s]})" for s in allowed]
        choice, ok = QInputDialog.getItem(self, "تغییر وضعیت", "وضعیت جدید:", labels, 0, False)
        if not ok:
            return
        new_status = choice.split(" ")[0]
        try:
            services.transition_ticket(self.win.conn, self.win.user, t["id"], new_status)
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()
