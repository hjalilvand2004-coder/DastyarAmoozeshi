# -*- coding: utf-8 -*-
"""صفحات مدیریت: اسناد، قواعد، کاربران، تنظیمات"""

from __future__ import annotations

import json

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from .. import db, services
from ..answers import DOC_STATUS_FA
from .widgets import Card, banner, error_box, info_box


class ImportDocDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("ثبت سند جدید (پیش‌نویس)")
        self.resize(520, 460)
        form = QFormLayout(self)
        self.txt_title = QLineEdit()
        self.cmb_type = QLineEdit("text")  # ساده نگه داشته شده: text / pdf_text / word / link
        self.txt_url = QLineEdit()
        self.btn_file = QPushButton("انتخاب فایل (txt / pdf / docx)")
        self.btn_file.clicked.connect(self._pick)
        self.lbl_file = QLabel("(فایلی انتخاب نشده است)")
        self.txt_text = QLineEdit()
        self.txt_text.setPlaceholderText("یا متن را مستقیم وارد کنید")
        self.txt_from = QLineEdit()
        self.txt_from.setPlaceholderText("۱۴۰۳/۰۷/۰۱")
        self.txt_to = QLineEdit()
        self.txt_to.setPlaceholderText("خالی = بدون پایان")
        self.txt_level = QLineEdit()
        self.txt_major = QLineEdit()
        self.txt_entry = QLineEdit()
        self.txt_entry.setPlaceholderText("مثلاً ۱۴۰۲ یا ۱۴۰۲-۱۴۰۴")
        self.chk_official = QLabel("اسناد ثبت‌شده در اینجا تا تأیید نهایی «غیررسمی» تلقی می‌شوند.")
        form.addRow("عنوان:", self.txt_title)
        form.addRow("نوع:", self.cmb_type)
        form.addRow("فایل:", self.btn_file)
        form.addRow("", self.lbl_file)
        form.addRow("لینک رسمی:", self.txt_url)
        form.addRow("متن:", self.txt_text)
        form.addRow("اعتبار از (جلالی):", self.txt_from)
        form.addRow("اعتبار تا (جلالی):", self.txt_to)
        form.addRow("مقطع:", self.txt_level)
        form.addRow("رشته:", self.txt_major)
        form.addRow("سال ورود:", self.txt_entry)
        form.addRow("", self.chk_official)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.file_path = None

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب سند", "", "Documents (*.txt *.pdf *.docx)")
        if path:
            self.file_path = path
            self.lbl_file.setText(path)

    def data(self) -> dict:
        title = self.txt_title.text().strip()
        if not title:
            raise ValueError("عنوان الزامی است.")
        entry = self.txt_entry.text().strip()
        e_from = e_to = None
        if entry:
            if "-" in entry:
                a, b = entry.split("-", 1)
                e_from, e_to = a.strip(), b.strip()
            else:
                e_from = entry
        from ..jalali import to_en_digits
        from ..jalali import jalali_to_gregorian_iso as j2g
        return {
            "title": title,
            "doc_type": self.cmb_type.text().strip() or "text",
            "file_path": self.file_path,
            "url": self.txt_url.text().strip() or None,
            "text": self.txt_text.text().strip(),
            "effective_from": j2g(self.txt_from.text()) if self.txt_from.text().strip() else None,
            "effective_until": j2g(self.txt_to.text()) if self.txt_to.text().strip() else None,
            "scope_level": self.txt_level.text().strip() or None,
            "scope_major": self.txt_major.text().strip() or None,
            "scope_entry_from": int(to_en_digits(e_from)) if e_from else None,
            "scope_entry_to": int(to_en_digits(e_to)) if e_to else None,
        }


class KbAdminPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.addWidget(banner("چرخه سند: پیش‌نویس ← در حال بررسی ← تأییدشده ← منتشرشده؛ و عملیات "
                           "«ملغی کردن» از وضعیت منتشرشده. نسخه جدید از سند منتشرشده ایجاد می‌شود و "
                           "متن نسخه جاری دست‌نخورده می‌ماند.", "info"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["عنوان", "نسخه", "وضعیت", "رسمی", "پرچم‌ها", "عملیات"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 340)
        v.addWidget(self.table, 1)
        h = QHBoxLayout()
        b1 = QPushButton("ثبت سند جدید")
        b1.clicked.connect(self._import)
        h.addWidget(b1)
        b2 = QPushButton("ارسال برای بررسی")
        b2.clicked.connect(lambda: self._status("in_review"))
        h.addWidget(b2)
        b3 = QPushButton("تأیید و انتشار")
        b3.clicked.connect(lambda: self._status("published"))
        h.addWidget(b3)
        b4 = QPushButton("ملغی کردن")
        b4.clicked.connect(self._retire)
        h.addWidget(b4)
        b5 = QPushButton("ایجاد نسخه جدید")
        b5.clicked.connect(self._revise)
        h.addWidget(b5)
        b6 = QPushButton("مشاهده متن")
        b6.clicked.connect(self._view)
        h.addWidget(b6)
        h.addStretch(1)
        v.addLayout(h)
        self.refresh()

    def refresh(self):
        try:
            docs = services.list_documents(self.win.conn, self.win.user)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        self._docs = docs
        self.table.setRowCount(0)
        for d in docs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(d["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(d["version_no"])))
            self.table.setItem(row, 2, QTableWidgetItem(DOC_STATUS_FA.get(d["status"], d["status"])))
            self.table.setItem(row, 3, QTableWidgetItem("بله" if d["is_official"] else "خیر"))
            try:
                flags = json.loads(d.get("flags") or "[]")
            except json.JSONDecodeError:
                flags = []
            self.table.setItem(row, 4, QTableWidgetItem("، ".join(flags)))
            self.table.setItem(row, 5, QTableWidgetItem(""))

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._docs):
            return self._docs[row]
        info_box(self, "انتخاب", "ابتدا یک سند را از جدول انتخاب کنید.")
        return None

    def _import(self):
        dlg = ImportDocDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            data = dlg.data()
            services.import_document(self.win.conn, self.win.user, **data)
            info_box(self, "ثبت سند", "سند با وضعیت «پیش‌نویس» ثبت شد و پس از تأیید منتشر می‌شود.")
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _status(self, new_status):
        d = self._selected()
        if not d:
            return
        try:
            if new_status == "published":
                # تأیید و انتشار در یک گام (approved → published) یا (in_review → approved → published)
                if d["status"] == "in_review":
                    services.update_document_status(self.win.conn, self.win.user, d["id"], "approved")
                services.update_document_status(self.win.conn, self.win.user, d["id"], "published")
            else:
                services.update_document_status(self.win.conn, self.win.user, d["id"], new_status)
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _retire(self):
        d = self._selected()
        if not d:
            return
        reason, ok = QInputDialog.getText(self, "ملغی کردن سند", "دلیل ابطال:")
        if not ok:
            return
        try:
            services.update_document_status(self.win.conn, self.win.user, d["id"], "retired", reason)
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _revise(self):
        d = self._selected()
        if not d:
            return
        try:
            new_id = services.revise_document(self.win.conn, self.win.user, d["id"])
            info_box(self, "نسخه جدید", f"نسخه پیش‌نویس جدید با شناسه {new_id} ایجاد شد.")
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _view(self):
        d = self._selected()
        if not d:
            return
        try:
            chunks = services.get_document_chunks(self.win.conn, self.win.user, d["id"])
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(d["title"])
        dlg.resize(640, 520)
        v = QVBoxLayout(dlg)
        tb = QTextBrowser()
        rows = []
        for c in chunks:
            head = c["clause_ref"] or f"بخش {c['idx'] + 1}"
            page = f" (صفحه {c['page_no']})" if c.get("page_no") else ""
            rows.append(f"<h3>{head}{page}</h3><div style='white-space:pre-wrap;'>{c['text']}</div>")
        tb.setHtml("".join(rows) or "(بدون متن)")
        v.addWidget(tb)
        dlg.exec()


class RulesAdminPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.addWidget(banner("قاعده فقط با منبعِ منتشرشده قابل تأیید است. ارزیابی قطعی با موتور قواعد "
                           "انجام می‌شود و مستقل از مدل زبانی است.", "info"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["عنوان", "منبع", "شرط", "وضعیت", "عملیات"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 280)
        v.addWidget(self.table, 1)
        c = Card("ارزیابی آزمایشی")
        h = QHBoxLayout()
        self.cmb_rule = QComboBox()
        h.addWidget(self.cmb_rule, 1)
        self.cmb_student = QComboBox()
        h.addWidget(self.cmb_student, 1)
        b = QPushButton("ارزیابی")
        b.clicked.connect(self._evaluate)
        h.addWidget(b)
        c.body.addLayout(h)
        self.txt_result = QTextBrowser()
        self.txt_result.setFixedHeight(110)
        c.body.addWidget(self.txt_result)
        v.addWidget(c)
        self.refresh()

    def refresh(self):
        try:
            rules = services.list_rules(self.win.conn, self.win.user)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        self._rules = rules
        self.table.setRowCount(0)
        self.cmb_rule.clear()
        docs = {d["id"]: d for d in db.q(self.win.conn, "SELECT id, title FROM documents")}
        for r in rules:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(docs.get(r["source_document_id"], {}).get("title", "-")))
            self.table.setItem(row, 2, QTableWidgetItem(r["cond_json"][:60]))
            self.table.setItem(row, 3, QTableWidgetItem(r["status"]))
            wrap = QWidget()
            wh = QHBoxLayout(wrap)
            wh.setContentsMargins(2, 2, 2, 2)
            if services.has_perm(self.win.user, "rules.approve") and r["status"] == "draft":
                b1 = QPushButton("تأیید")
                b1.clicked.connect(lambda _, rid=r["id"]: self._approve(rid))
                wh.addWidget(b1)
            if services.has_perm(self.win.user, "rules.approve") and r["status"] == "approved":
                b2 = QPushButton("غیرفعال")
                b2.clicked.connect(lambda _, rid=r["id"]: self._disable(rid))
                wh.addWidget(b2)
            self.table.setCellWidget(row, 4, wrap)
            self.cmb_rule.addItem(r["title"], r["id"])
        try:
            students = services.list_students(self.win.conn, self.win.user)
        except Exception:
            students = []
        self._students = students
        self.cmb_student.clear()
        for s in students:
            self.cmb_student.addItem(f"{s.get('full_name') or s['id']}", s["id"])

    def _approve(self, rid):
        try:
            services.approve_rule(self.win.conn, self.win.user, rid)
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _disable(self, rid):
        try:
            services.set_rule_status(self.win.conn, self.win.user, rid, "disabled")
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _evaluate(self):
        rid = self.cmb_rule.currentData()
        sid = self.cmb_student.currentData()
        if rid is None or sid is None:
            return
        try:
            res = services.evaluate_rule_for_student(self.win.conn, self.win.user, rid, sid)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        color = {"satisfied": "#1b5e20", "not_satisfied": "#b71c1c",
                 "insufficient_info": "#7a5c00", "needs_review": "#8a4b00"}.get(res["status"], "#333")
        html = (f"<p><b>{res['rule_title']}</b>: "
                f"<span style='color:{color};font-weight:bold;'>{res['status_fa']}</span></p>"
                f"<p>{res['detail']}</p>")
        if res.get("missing"):
            html += "<p>اطلاعات ناقص: " + "، ".join(res["missing"]) + "</p>"
        self.txt_result.setHtml(html)


class UsersAdminPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["نام کاربری", "نام", "نقش", "فعال", "عملیات"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 160)
        v.addWidget(self.table, 1)
        h = QHBoxLayout()
        b1 = QPushButton("افزودن کاربر")
        b1.clicked.connect(self._add)
        h.addWidget(b1)
        b2 = QPushButton("بازنشانی رمز")
        b2.clicked.connect(self._reset)
        h.addWidget(b2)
        b3 = QPushButton("فعال/غیرفعال")
        b3.clicked.connect(self._toggle)
        h.addWidget(b3)
        h.addStretch(1)
        v.addLayout(h)
        self.refresh()

    def refresh(self):
        try:
            users = services.list_users(self.win.conn, self.win.user)
        except Exception as e:
            error_box(self, "خطا", str(e))
            return
        self._users = users
        self.table.setRowCount(0)
        for u in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(u["username"]))
            self.table.setItem(row, 1, QTableWidgetItem(u["full_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(services.ROLE_FA.get(u["role"], u["role"])))
            self.table.setItem(row, 3, QTableWidgetItem("فعال" if u["active"] else "غیرفعال"))
            self.table.setItem(row, 4, QTableWidgetItem(""))

    def _add(self):
        form = QDialog(self)
        form.setWindowTitle("کاربر جدید")
        f = QFormLayout(form)
        txt_u = QLineEdit()
        txt_p = QLineEdit()
        txt_p.setEchoMode(QLineEdit.EchoMode.Password)
        txt_n = QLineEdit()
        cmb = QComboBox()
        for k, v in services.ROLE_FA.items():
            cmb.addItem(v, k)
        f.addRow("نام کاربری:", txt_u)
        f.addRow("رمز عبور:", txt_p)
        f.addRow("نام کامل:", txt_n)
        f.addRow("نقش:", cmb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(form.accept)
        bb.rejected.connect(form.reject)
        f.addRow(bb)
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            services.create_user(self.win.conn, self.win.user, txt_u.text(), txt_p.text(),
                                 txt_n.text(), cmb.currentData())
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()

    def _selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._users):
            return self._users[row]
        info_box(self, "انتخاب", "یک کاربر را انتخاب کنید.")
        return None

    def _reset(self):
        u = self._selected()
        if not u:
            return
        pw, ok = QInputDialog.getText(self, "بازنشانی رمز", "رمز جدید:")
        if not ok:
            return
        try:
            services.reset_password(self.win.conn, self.win.user, u["id"], pw)
        except Exception as e:
            error_box(self, "خطا", str(e))

    def _toggle(self):
        u = self._selected()
        if not u:
            return
        try:
            services.set_user_active(self.win.conn, self.win.user, u["id"], not u["active"])
        except Exception as e:
            error_box(self, "خطا", str(e))
        self.refresh()


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        c = Card("مدل زبانی (اختیاری)")
        form = QFormLayout()
        self.cmb_provider = QComboBox()
        self.cmb_provider.addItem("خودکار (اگر پیکربندی بود مدل، وگرنه قالبی)", "auto")
        self.cmb_provider.addItem("فقط موتور قالبی آفلاین", "template")
        self.txt_base = QLineEdit()
        self.txt_base.setPlaceholderText("https://api.openai.com/v1")
        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_model = QLineEdit()
        form.addRow("حالت:", self.cmb_provider)
        form.addRow("آدرس پایه:", self.txt_base)
        form.addRow("کلید API:", self.txt_key)
        form.addRow("نام مدل:", self.txt_model)
        c.body.addLayout(form)
        h = QHBoxLayout()
        b1 = QPushButton("ذخیره")
        b1.clicked.connect(self._save)
        h.addWidget(b1)
        b2 = QPushButton("تست ارتباط")
        b2.clicked.connect(self._test)
        h.addWidget(b2)
        h.addStretch(1)
        c.body.addLayout(h)
        v.addWidget(c)
        c2 = Card("سایر تنظیمات")
        f2 = QFormLayout()
        self.txt_rate = QLineEdit()
        f2.addRow("حداکثر پرسش در ساعت:", self.txt_rate)
        self.txt_grad = QLineEdit()
        f2.addRow("واحدهای لازم فارغ‌التحصیلی:", self.txt_grad)
        c2.body.addLayout(f2)
        b3 = QPushButton("ذخیره")
        b3.clicked.connect(self._save)
        c2.body.addWidget(b3)
        v.addWidget(c2)
        v.addStretch(1)
        v.addWidget(banner("کلید API فقط روی همین دستگاه ذخیره می‌شود. در حالت minimal فقط "
                           "مقطع/رشته/سال ورود دانشجو برای مدل ارسال می‌شود.", "info"))
        self.refresh()

    def refresh(self):
        s = db.get_settings(self.win.conn)
        idx = self.cmb_provider.findData(s.get("llm_provider", "auto"))
        self.cmb_provider.setCurrentIndex(idx if idx >= 0 else 0)
        self.txt_base.setText(s.get("llm_base_url", ""))
        self.txt_key.setText(s.get("llm_api_key", ""))
        self.txt_model.setText(s.get("llm_model", ""))
        self.txt_rate.setText(s.get("rate_limit_chat_per_hour", "20"))
        self.txt_grad.setText(s.get("grad_required_credits", "140"))

    def _save(self):
        db.set_setting(self.win.conn, "llm_provider", self.cmb_provider.currentData())
        db.set_setting(self.win.conn, "llm_base_url", self.txt_base.text().strip())
        db.set_setting(self.win.conn, "llm_api_key", self.txt_key.text().strip())
        db.set_setting(self.win.conn, "llm_model", self.txt_model.text().strip())
        db.set_setting(self.win.conn, "rate_limit_chat_per_hour", self.txt_rate.text().strip() or "20")
        db.set_setting(self.win.conn, "grad_required_credits", self.txt_grad.text().strip() or "140")
        db.audit(self.win.conn, self.win.user, "settings_update", "تنظیمات ذخیره شد")
        info_box(self, "تنظیمات", "ذخیره شد.")

    def _test(self):
        from ..llm import OpenAICompatibleProvider
        p = OpenAICompatibleProvider(self.txt_base.text().strip(), self.txt_key.text().strip(),
                                     self.txt_model.text().strip())
        if not p.capable():
            error_box(self, "تست", "آدرس/کلید/مدل کامل نیست.")
            return
        out = p.complete("سلام", [{"ref": "C1", "doc_title": "تست", "version_no": 1,
                                   "clause_ref": "", "text": "این یک سند آزمایشی است."}])
        if out:
            info_box(self, "تست", "ارتباط برقرار است. نمونه پاسخ: " + (out.short or "")[:120])
        else:
            error_box(self, "تست", "ارتباط ناموفق بود؛ تنظیمات را بررسی کنید.")
