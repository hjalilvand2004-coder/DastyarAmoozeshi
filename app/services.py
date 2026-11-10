# -*- coding: utf-8 -*-
"""لایه سرویس‌ها - همه اعتبارسنجی مجوزها در بک‌اند (اینجا) انجام می‌شود، نه فقط در رابط کاربری

نقش‌ها: student / expert / content_admin / approver / system_admin
جداسازی داده بین دانشگاه‌ها: هر رکورد دارای university_id است و هر سرویس آن را فیلتر/بررسی می‌کند.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from . import db
from .db import audit, ex, q, q1
from .jalali import format_jalali
from .security import hash_password, sanitize_document_text, verify_password

# ---------- نقش‌ها و مجوزها ----------

ROLE_FA = {
    "student": "دانشجو",
    "expert": "کارشناس آموزش",
    "content_admin": "مدیر محتوای آیین‌نامه",
    "approver": "تأییدکننده",
    "system_admin": "مدیر سیستم",
}

EXPERT_PERMS = {
    "chat", "regs.read", "regs.read_draft", "deadlines.read", "deadlines.manage",
    "tickets.own", "tickets.handle", "advisor.self", "advisor.student", "rules.evaluate",
}
ROLE_PERMS = {
    "student": {"chat", "regs.read", "deadlines.read", "tickets.own", "advisor.self"},
    "expert": set(EXPERT_PERMS),
    "content_admin": set(EXPERT_PERMS) | {"regs.create", "regs.submit"},
    "approver": set(EXPERT_PERMS) | {"regs.approve_publish", "regs.retire", "rules.approve"},
    "system_admin": "*",
}


def has_perm(user: dict, perm: str) -> bool:
    perms = ROLE_PERMS.get(user.get("role"), set())
    return perms == "*" or perm in perms


def require(user: dict, perm: str) -> None:
    if not user or not has_perm(user, perm):
        raise PermissionError(f"دسترسی مجاز نیست: {perm} برای نقش {ROLE_FA.get(user.get('role'), '?')}")


def _uni_check(row: dict, user: dict) -> None:
    if row.get("university_id") != user["university_id"]:
        raise PermissionError("دسترسی بین دانشگاهی مجاز نیست.")


# ---------- احراز هویت و کاربران ----------

def login(conn, username: str, password: str) -> dict | None:
    row = q1(conn, "SELECT * FROM users WHERE username=? AND active=1", (username.strip(),))
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def create_user(conn, actor, username, password, full_name, role, student_id=None):
    require(actor, "users.manage")
    if role not in ROLE_FA:
        raise ValueError("نقش نامعتبر است.")
    if len(password) < 6:
        raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد.")
    return ex(conn, "INSERT INTO users(university_id, username, password_hash, full_name, role, student_id) "
                    "VALUES(?,?,?,?,?,?)",
              (actor["university_id"], username.strip(), hash_password(password), full_name, role, student_id))


def list_users(conn, actor):
    require(actor, "users.manage")
    return q(conn, "SELECT id, username, full_name, role, active, student_id FROM users WHERE university_id=?",
             (actor["university_id"],))


def set_user_active(conn, actor, user_id, active: bool):
    require(actor, "users.manage")
    row = q1(conn, "SELECT * FROM users WHERE id=?", (user_id,))
    _uni_check(row, actor)
    ex(conn, "UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
    audit(conn, actor, "user_active", f"user={user_id} active={active}")


def reset_password(conn, actor, user_id, new_password: str):
    require(actor, "users.manage")
    row = q1(conn, "SELECT * FROM users WHERE id=?", (user_id,))
    _uni_check(row, actor)
    if len(new_password) < 6:
        raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد.")
    ex(conn, "UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), user_id))
    audit(conn, actor, "user_reset_password", f"user={user_id}")


def get_student_for_user(conn, user) -> dict | None:
    if not user.get("student_id"):
        return q1(conn, "SELECT * FROM students WHERE user_id=? LIMIT 1", (user["id"],))
    return q1(conn, "SELECT * FROM students WHERE id=? AND user_id=?", (user["student_id"], user["id"]))


def update_student_profile(conn, user, student_id: int, fields: dict):
    """دانشجو پروفایل خودش را ویرایش می‌کند؛ کارشناس می‌تواند برای دانشجویان دانشگاه ویرایش کند"""
    row = q1(conn, "SELECT * FROM students WHERE id=?", (student_id,))
    if not row:
        raise ValueError("دانشجو یافت نشد.")
    _uni_check(row, user)
    if not (user.get("student_id") == student_id or has_perm(user, "advisor.student")
            or has_perm(user, "users.manage")):
        raise PermissionError("ویرایش پروفایل دیگران مجاز نیست.")
    allowed = {"full_name", "level", "major", "entry_year", "gpa", "passed_credits",
               "passed_courses", "profile_extra"}
    sets, params = [], []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k in ("passed_courses", "profile_extra") and not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k}=?")
        params.append(v)
    if not sets:
        return
    sets.append("updated_at=datetime('now')")
    params.append(student_id)
    ex(conn, f"UPDATE students SET {', '.join(sets)} WHERE id=?", tuple(params))
    audit(conn, user, "student_profile_update", f"student={student_id} fields={list(fields)}")


def list_students(conn, actor):
    require(actor, "advisor.student")
    return q(conn, "SELECT id, full_name, level, major, entry_year, gpa, passed_credits "
                   "FROM students WHERE university_id=?", (actor["university_id"],))


# ---------- پایگاه دانش آیین‌نامه‌ها ----------

DOC_TRANSITIONS = {
    "draft": {"in_review"},
    "in_review": {"draft", "approved"},
    "approved": {"published", "retired"},
    "published": {"retired"},
    "retired": set(),
}
_TRANSITION_PERM = {
    ("draft", "in_review"): "regs.submit",
    ("in_review", "draft"): "regs.create",
    ("in_review", "approved"): "regs.approve_publish",
    ("approved", "published"): "regs.approve_publish",
    ("approved", "retired"): "regs.retire",
    ("published", "retired"): "regs.retire",
}


def _extract_text(file_path: str | None, doc_type: str) -> tuple[str, list[int] | None]:
    """متن فایل را استخراج می‌کند؛ برای PDF فهرست شماره صفحه هر بخش هم برمی‌گردد"""
    p = Path(file_path) if file_path else None
    if doc_type == "link":
        return "", None
    if not p or not p.exists():
        raise ValueError("فایل یافت نشد.")
    suffix = p.suffix.lower()
    if suffix in (".txt", ".md") or doc_type == "text":
        return p.read_text(encoding="utf-8", errors="replace"), None
    if suffix == ".pdf" or doc_type == "pdf_text" or doc_type == "pdf_scan":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError("کتابخانه pypdf نصب نیست؛ برای PDF آن را نصب کنید.") from e
        reader = PdfReader(str(p))
        pages = []
        texts = []
        for i, page in enumerate(reader.pages, start=1):
            t = (page.extract_text() or "").strip()
            texts.append(t)
            pages.append(i)
        text = "\n\n".join(texts)
        return text, pages
    if suffix == ".docx" or doc_type == "word":
        try:
            import docx  # python-docx
        except ImportError as e:
            raise ValueError("کتابخانه python-docx نصب نیست.") from e
        d = docx.Document(str(p))
        return "\n".join(par.text for par in d.paragraphs), None
    raise ValueError("نوع فایل پشتیبانی نمی‌شود (txt / pdf / docx).")


_RE_CLAUSE = re.compile(r"^\s*(ماده|تبصره|فصل|بند)\s+")

def _split_chunks(text: str, pages: list[int] | None = None) -> list[dict]:
    """تکه‌بندی بر اساس ماده/تبصره/فصل؛ در نبود سرصفحه، بر اساس پاراگراف"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n|\n", text) if b.strip()]
    chunks: list[dict] = []
    cur: list[str] = []
    cur_ref = ""
    cur_page = (pages[0] if pages else None)
    page_map: list[int] = []

    def flush():
        if cur:
            chunks.append({"clause_ref": cur_ref, "page_no": cur_page,
                           "text": "\n".join(cur).strip()})

    for i, b in enumerate(blocks):
        if _RE_CLAUSE.match(b):
            flush()
            cur, cur_ref = [], ""
            m = re.match(r"^\s*((ماده|تبصره|فصل|بند)\s+[^:\-–—(]{0,25})", b)
            cur_ref = m.group(1).strip() if m else b[:20]
            if pages and i < len(pages):
                cur_page = pages[i]
        cur.append(b)
    flush()
    if not chunks and text.strip():
        chunks.append({"clause_ref": "", "page_no": 1, "text": text.strip()[:2000]})
    # تکه‌های خیلی بلند را نصف می‌کنیم
    out = []
    for c in chunks:
        t = c["text"]
        while len(t) > 1500:
            cut = t.rfind("،", 0, 1500) or 1500
            out.append({**c, "text": t[:cut].strip()})
            t = t[cut:].strip()
        out.append({**c, "text": t})
    return [c for c in out if c["text"]]


def import_document(conn, actor, title, doc_type="text", text="", file_path=None, url=None,
                    effective_from=None, effective_until=None, scope_level=None, scope_major=None,
                    scope_entry_from=None, scope_entry_to=None, source_note="", is_official=False,
                    status="draft") -> int:
    """ثبت سند در پایگاه دانش (نسخه جدید همیشه از این مسیر با وضعیت پیش‌نویس شروع می‌شود)"""
    require(actor, "regs.create")
    if not title or not title.strip():
        raise ValueError("عنوان سند الزامی است.")
    if file_path and not text:
        text, _pages = _extract_text(file_path, doc_type)
    if doc_type in ("text", "pdf_text", "pdf_scan", "word") and not (text or "").strip():
        raise ValueError("متن سند خالی است.")
    clean, flags = sanitize_document_text(text or "")
    doc_id = ex(conn, "INSERT INTO documents(university_id, title, doc_type, status, effective_from, "
                      "effective_until, scope_level, scope_major, scope_entry_from, scope_entry_to, "
                      "file_path, url, source_note, is_official, flags, created_by) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (actor["university_id"], title.strip(), doc_type, status if status in ("draft",) else "draft",
                 effective_from, effective_until, scope_level, scope_major, scope_entry_from,
                 scope_entry_to, str(file_path or ""), url, source_note, 1 if is_official else 0,
                 json.dumps(flags, ensure_ascii=False), actor["id"]))
    for i, c in enumerate(_split_chunks(clean)):
        ctext, cflags = sanitize_document_text(c["text"])
        ex(conn, "INSERT INTO chunks(document_id, clause_ref, page_no, text, normalized, idx, flags) "
                 "VALUES(?,?,?,?,?,?,?)",
           (doc_id, c["clause_ref"], c["page_no"], ctext, "", i,
            json.dumps(cflags, ensure_ascii=False)))
    # متن نرمال‌شده برای جست‌وجو
    for row in q(conn, "SELECT id, text FROM chunks WHERE document_id=?", (doc_id,)):
        from .security import normalize_persian
        ex(conn, "UPDATE chunks SET normalized=? WHERE id=?", (normalize_persian(row["text"]), row["id"]))
    audit(conn, actor, "document_import", f"doc={doc_id} title={title}")
    return doc_id


def revise_document(conn, actor, doc_id: int) -> int:
    """نسخه جدید (پیش‌نویس) از سند منتشر/تأییدشده می‌سازد؛ متن نسخه جاری دست‌نخورده می‌ماند"""
    require(actor, "regs.create")
    doc = q1(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
    _uni_check(doc, actor)
    if doc["status"] not in ("published", "approved"):
        raise ValueError("نسخه جدید فقط از سند تأییدشده یا منتشرشده قابل ایجاد است.")
    new_id = ex(conn, "INSERT INTO documents(university_id, title, doc_type, status, version_no, parent_id, "
                      "effective_from, effective_until, scope_level, scope_major, scope_entry_from, "
                      "scope_entry_to, file_path, url, source_note, is_official, flags, created_by) "
                      "VALUES(?,?,?,'draft',?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc["university_id"], doc["title"], doc["doc_type"], doc["version_no"] + 1, doc["id"],
                 doc["effective_from"], doc["effective_until"], doc["scope_level"], doc["scope_major"],
                 doc["scope_entry_from"], doc["scope_entry_to"], doc["file_path"], doc["url"],
                 doc["source_note"], doc["is_official"], doc["flags"], actor["id"]))
    for c in q(conn, "SELECT * FROM chunks WHERE document_id=?", (doc_id,)):
        ex(conn, "INSERT INTO chunks(document_id, clause_ref, page_no, text, normalized, idx, flags) "
                 "VALUES(?,?,?,?,?,?,?)",
           (new_id, c["clause_ref"], c["page_no"], c["text"], c["normalized"], c["idx"], c["flags"]))
    audit(conn, actor, "document_revise", f"from={doc_id} to={new_id}")
    return new_id


def update_document_status(conn, actor, doc_id: int, new_status: str, reason: str = "") -> None:
    doc = q1(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
    if not doc:
        raise ValueError("سند یافت نشد.")
    _uni_check(doc, actor)
    allowed = DOC_TRANSITIONS.get(doc["status"], set())
    if new_status not in allowed:
        raise ValueError(f"گذار وضعیت «{doc['status']}» به «{new_status}» مجاز نیست.")
    perm = _TRANSITION_PERM.get((doc["status"], new_status))
    if perm:
        require(actor, perm)
    if new_status == "retired":
        ex(conn, "UPDATE documents SET status='retired', retired_at=date('now'), retired_reason=? WHERE id=?",
           (reason or "ملغی شد.", doc_id))
    else:
        ex(conn, "UPDATE documents SET status=? WHERE id=?", (new_status, doc_id))
    audit(conn, actor, "document_status", f"doc={doc_id} {doc['status']}->{new_status}")


def list_documents(conn, actor, include_drafts=None) -> list[dict]:
    if include_drafts is None:
        include_drafts = has_perm(actor, "regs.read_draft") or has_perm(actor, "regs.create")
    if include_drafts:
        require(actor, "regs.read_draft")
        rows = q(conn, "SELECT * FROM documents WHERE university_id=? ORDER BY status, version_no DESC, id",
                 (actor["university_id"],))
    else:
        rows = q(conn, "SELECT * FROM documents WHERE university_id=? AND status IN ('published','retired') "
                       "ORDER BY id", (actor["university_id"],))
    return rows


def get_document_chunks(conn, actor, doc_id: int) -> list[dict]:
    doc = q1(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
    if not doc:
        raise ValueError("سند یافت نشد.")
    _uni_check(doc, actor)
    if doc["status"] in ("draft", "in_review", "approved") and not (
            has_perm(actor, "regs.read_draft") or has_perm(actor, "regs.create")):
        raise PermissionError("سند غیرمنتشرشده برای دانشجو قابل مشاهده نیست.")
    return q(conn, "SELECT * FROM chunks WHERE document_id=? ORDER BY idx", (doc_id,))


# ---------- قواعد ----------

def create_rule(conn, actor, title, cond_json: dict, source_document_id=None, source_clause="",
                messages=None, review_fields=None, scope=None) -> int:
    require(actor, "regs.create")
    return ex(conn, "INSERT INTO rules(university_id, title, source_document_id, source_clause, scope, "
                    "cond_json, messages, review_fields, status) VALUES(?,?,?,?,?,?,?,?, 'draft')",
              (actor["university_id"], title, source_document_id, source_clause,
               json.dumps(scope or {}, ensure_ascii=False),
               json.dumps(cond_json, ensure_ascii=False),
               json.dumps(messages or {}, ensure_ascii=False),
               json.dumps(review_fields or [], ensure_ascii=False)))


def approve_rule(conn, actor, rule_id: int) -> None:
    require(actor, "rules.approve")
    rule = q1(conn, "SELECT * FROM rules WHERE id=?", (rule_id,))
    if not rule:
        raise ValueError("قاعده یافت نشد.")
    _uni_check(rule, actor)
    if rule["source_document_id"]:
        doc = q1(conn, "SELECT * FROM documents WHERE id=?", (rule["source_document_id"],))
        if not doc or doc["status"] != "published":
            raise ValueError("منبع قاعده منتشرشده (جاری) نیست؛ تأیید قاعده مجاز نیست.")
    ex(conn, "UPDATE rules SET status='approved', approved_by=?, approved_at=datetime('now') WHERE id=?",
       (actor["id"], rule_id))
    audit(conn, actor, "rule_approve", f"rule={rule_id}")


def set_rule_status(conn, actor, rule_id: int, status: str) -> None:
    require(actor, "rules.approve")
    if status not in ("approved", "disabled"):
        raise ValueError("وضعیت نامعتبر.")
    rule = q1(conn, "SELECT * FROM rules WHERE id=?", (rule_id,))
    _uni_check(rule, actor)
    ex(conn, "UPDATE rules SET status=? WHERE id=?", (status, rule_id))
    audit(conn, actor, "rule_status", f"rule={rule_id} status={status}")


def list_rules(conn, actor):
    require(actor, "rules.evaluate")
    return q(conn, "SELECT * FROM rules WHERE university_id=? ORDER BY id", (actor["university_id"],))


def evaluate_rule_for_student(conn, actor, rule_id: int, student_id: int) -> dict:
    require(actor, "rules.evaluate")
    rule = q1(conn, "SELECT * FROM rules WHERE id=?", (rule_id,))
    _uni_check(rule, actor)
    stu = q1(conn, "SELECT * FROM students WHERE id=?", (student_id,))
    _uni_check(stu, actor)
    from .ruleengine import evaluate
    from .answers import _student_profile
    rec = dict(rule)
    try:
        rec["cond_json"] = json.loads(rule["cond_json"])
        rec["review_fields"] = json.loads(rule.get("review_fields") or "[]")
    except json.JSONDecodeError:
        pass
    res = evaluate(rec, _student_profile(stu))
    return {"rule_title": rule["title"], "status": res.status, "status_fa": res.status_fa,
            "missing": res.missing, "detail": (json.loads(rule.get("messages") or "{}")
                                               if rule.get("messages") else {}).get(res.status, "")}


# ---------- فرایندهای اداری ----------

def list_processes(conn, user):
    return q(conn, "SELECT * FROM processes WHERE university_id=?", (user["university_id"],))


def get_process(conn, user, proc_id: int) -> dict:
    p = q1(conn, "SELECT * FROM processes WHERE id=?", (proc_id,))
    if not p:
        raise ValueError("فرایند یافت نشد.")
    _uni_check(p, user)
    return p


def create_process(conn, actor, key, title, steps, required_docs=None, target_system="",
                   target_url="", keywords=None, notes=""):
    require(actor, "deadlines.manage")
    return ex(conn, "INSERT INTO processes(university_id, key, title, steps, required_docs, target_system, "
                    "target_url, keywords, notes) VALUES(?,?,?,?,?,?,?,?,?)",
              (actor["university_id"], key, title, json.dumps(steps, ensure_ascii=False),
               json.dumps(required_docs or [], ensure_ascii=False), target_system, target_url,
               json.dumps(keywords or [], ensure_ascii=False), notes))


# ---------- یادآورها و تقویم ----------

def create_deadline(conn, actor, title, date_iso, scope=None, source_document_id=None, notes="") -> int:
    require(actor, "deadlines.manage")
    datetime.date.fromisoformat(date_iso)
    return ex(conn, "INSERT INTO deadlines(university_id, title, date_iso, scope, source_document_id, "
                    "notes, created_by) VALUES(?,?,?,?,?,?,?)",
              (actor["university_id"], title, date_iso, json.dumps(scope or {}, ensure_ascii=False),
               source_document_id, notes, actor["id"]))


def update_deadline(conn, actor, deadline_id: int, fields: dict) -> int:
    """ویرایش تاریخ/عنوان، شماره نسخه را افزایش می‌دهد تا یادآورهای قبلی باطل و دوباره اعلام شود"""
    require(actor, "deadlines.manage")
    d = q1(conn, "SELECT * FROM deadlines WHERE id=?", (deadline_id,))
    _uni_check(d, actor)
    new_version = d["version_no"]
    if "date_iso" in fields and fields["date_iso"] != d["date_iso"]:
        datetime.date.fromisoformat(fields["date_iso"])
        new_version = d["version_no"] + 1
    title = fields.get("title", d["title"])
    date_iso = fields.get("date_iso", d["date_iso"])
    notes = fields.get("notes", d["notes"])
    ex(conn, "UPDATE deadlines SET title=?, date_iso=?, notes=?, version_no=? WHERE id=?",
       (title, date_iso, notes, new_version, deadline_id))
    audit(conn, actor, "deadline_update", f"deadline={deadline_id} v{d['version_no']}->v{new_version}")
    return new_version


def list_deadlines(conn, user, student=None, active_only=True):
    rows = q(conn, "SELECT * FROM deadlines WHERE university_id=? AND active=1 ORDER BY date_iso"
             if active_only else
             "SELECT * FROM deadlines WHERE university_id=? ORDER BY date_iso",
             (user["university_id"],))
    out = []
    today = datetime.date.today()
    for d in rows:
        try:
            dd = datetime.date.fromisoformat(d["date_iso"])
        except ValueError:
            continue
        d = dict(d)
        d["date_fa"] = format_jalali(dd, "long")
        d["days_left"] = (dd - today).days
        acked = q1(conn, "SELECT id FROM deadline_acks WHERE deadline_id=? AND version_no=? AND user_id=?",
                   (d["id"], d["version_no"], user["id"]))
        d["acked"] = bool(acked)
        out.append(d)
    return out


def ack_deadline(conn, user, deadline_id: int) -> None:
    d = q1(conn, "SELECT * FROM deadlines WHERE id=?", (deadline_id,))
    _uni_check(d, user)
    ex(conn, "INSERT OR IGNORE INTO deadline_acks(deadline_id, version_no, user_id) VALUES(?,?,?)",
       (deadline_id, d["version_no"], user["id"]))


def pending_reminders(conn, user, student=None, window_days=30) -> list[dict]:
    """یادآورهای اعلام‌نشده: رویداد فعالِ در بازه، بدون تأیید کاربر برای نسخه جاری"""
    rows = list_deadlines(conn, user, student)
    today = datetime.date.today()
    out = []
    for d in rows:
        dd = datetime.date.fromisoformat(d["date_iso"])
        if -1 <= d["days_left"] <= window_days and not d["acked"]:
            d["date_obj"] = dd
            out.append(d)
    return out


# ---------- تیکت و ارجاع به کارشناس ----------

TICKET_STATUS_FA = {
    "submitted": "ثبت‌شده",
    "under_review": "در حال بررسی",
    "needs_info": "نیاز به اطلاعات",
    "answered": "پاسخ داده شده",
    "closed": "بسته",
}
TICKET_TRANSITIONS = {
    "submitted": {"under_review"},
    "under_review": {"needs_info", "answered", "closed"},
    "needs_info": {"answered", "under_review"},
    "answered": {"closed", "under_review"},
    "closed": set(),
}


def create_ticket(conn, user, subject: str, body: str) -> int:
    require(user, "tickets.own")
    if not subject.strip():
        raise ValueError("موضوع الزامی است.")
    tid = ex(conn, "INSERT INTO tickets(university_id, user_id, subject) VALUES(?,?,?)",
             (user["university_id"], user["id"], subject.strip()[:200]))
    add_ticket_message(conn, user, tid, body or "")
    return tid


def _ticket_access(conn, user, ticket_id: int) -> dict:
    t = q1(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not t:
        raise ValueError("تیکت یافت نشد.")
    _uni_check(t, user)
    is_staff = has_perm(user, "tickets.handle")
    if t["user_id"] != user["id"] and not is_staff:
        raise PermissionError("این تیکت متعلق به شما نیست.")
    return t


def add_ticket_message(conn, user, ticket_id: int, body: str) -> None:
    t = _ticket_access(conn, user, ticket_id)
    if t["status"] == "closed":
        raise ValueError("تیکت بسته است.")
    is_staff = 1 if has_perm(user, "tickets.handle") else 0
    ex(conn, "INSERT INTO ticket_messages(ticket_id, author_id, body, is_staff) VALUES(?,?,?,?)",
       (ticket_id, user["id"], body.strip()[:4000], is_staff))
    # پاسخ کارشناس، وضعیت را به «پاسخ داده شده» می‌برد
    if is_staff and t["status"] in ("under_review", "needs_info"):
        ex(conn, "UPDATE tickets SET status='answered', updated_at=datetime('now') WHERE id=?", (ticket_id,))
    elif not is_staff and t["status"] in ("needs_info", "answered"):
        ex(conn, "UPDATE tickets SET status='under_review', updated_at=datetime('now') WHERE id=?", (ticket_id,))
    else:
        ex(conn, "UPDATE tickets SET updated_at=datetime('now') WHERE id=?", (ticket_id,))


def transition_ticket(conn, user, ticket_id: int, new_status: str) -> None:
    require(user, "tickets.handle")
    t = _ticket_access(conn, user, ticket_id)
    if new_status not in TICKET_TRANSITIONS.get(t["status"], set()):
        raise ValueError(f"گذار «{t['status']}» به «{new_status}» مجاز نیست.")
    ex(conn, "UPDATE tickets SET status=?, updated_at=datetime('now') WHERE id=?", (new_status, ticket_id))
    audit(conn, user, "ticket_transition", f"ticket={ticket_id} {t['status']}->{new_status}")


def list_tickets(conn, user) -> list[dict]:
    if has_perm(user, "tickets.handle"):
        rows = q(conn, "SELECT t.*, u.full_name AS requester FROM tickets t "
                       "JOIN users u ON u.id=t.user_id WHERE t.university_id=? ORDER BY t.updated_at DESC",
                 (user["university_id"],))
    else:
        rows = q(conn, "SELECT * FROM tickets WHERE user_id=? ORDER BY updated_at DESC", (user["id"],))
    for r in rows:
        r["status_fa"] = TICKET_STATUS_FA.get(r["status"], r["status"])
    return rows


def ticket_thread(conn, user, ticket_id: int) -> dict:
    t = _ticket_access(conn, user, ticket_id)
    msgs = q(conn, "SELECT m.*, u.full_name AS author, u.role AS author_role FROM ticket_messages m "
                   "JOIN users u ON u.id=m.author_id WHERE m.ticket_id=? ORDER BY m.id", (ticket_id,))
    return {"ticket": t, "messages": msgs}


# ---------- مشاوره انتخاب واحد (پیش‌نیاز و فارغ‌التحصیلی) ----------

def _load_courses(conn, user) -> list[dict]:
    rows = q(conn, "SELECT * FROM courses WHERE university_id=?", (user["university_id"],))
    for r in rows:
        try:
            r["prereqs"] = json.loads(r.get("prereqs") or "[]")
        except json.JSONDecodeError:
            r["prereqs"] = []
    return rows


def analyze_course(conn, user, student, course_id: int) -> dict:
    """تحلیل پیش‌نیاز یک درس - نتیجه جایگزین نظر سامانه آموزشی نیست"""
    courses = {c["id"]: c for c in _load_courses(conn, user)}
    course = courses.get(course_id)
    if not course:
        raise ValueError("درس یافت نشد.")
    try:
        passed = json.loads((student or {}).get("passed_courses") or "[]")
    except json.JSONDecodeError:
        passed = []
    if student is None or student.get("passed_courses") is None:
        return {"status": "insufficient_info", "status_fa": "اطلاعات ناکافی",
                "missing": ["دروس گذرانده‌شده"], "missing_courses": [],
                "message": "در پروفایل شما فهرست دروس گذرانده‌شده ثبت نشده است؛ تحلیل قطعی ممکن نیست.",
                "course": course}
    missing = [p for p in course["prereqs"] if p not in passed]
    if missing:
        names = [courses[c]["name"] for c in courses if c in missing] or missing
        return {"status": "not_satisfied", "status_fa": "برقرار نیست",
                "missing": [], "missing_courses": names,
                "message": "پیش‌نیازهای زیر هنوز گذرانده نشده‌اند: " + "، ".join(names),
                "course": course}
    return {"status": "satisfied", "status_fa": "برقرار است", "missing": [], "missing_courses": [],
            "message": "تمام پیش‌نیازهای این درس در فهرست دروس شما موجود است (بر اساس داده ثبت‌شده در سامانه).",
            "course": course}


def suggest_next_courses(conn, user, student, limit=5) -> dict:
    if student is None or student.get("passed_courses") is None:
        return {"status": "insufficient_info", "items": [],
                "message": "فهرست دروس گذرانده‌شده شما ثبت نشده است."}
    try:
        passed = json.loads(student.get("passed_courses") or "[]")
    except json.JSONDecodeError:
        passed = []
    items = []
    for c in _load_courses(conn, user):
        if c["code"] in passed:
            continue
        missing = [p for p in c["prereqs"] if p not in passed]
        items.append({"course": c, "ok": not missing, "missing": missing})
    items.sort(key=lambda x: (0 if x["ok"] else 1, len(x["missing"]), -x["course"]["credits"]))
    return {"status": "satisfied", "items": items[:limit],
            "message": "این پیشنهاد فقط بر اساس پیش‌نیازهای ثبت‌شده در همین سامانه است و جایگزین "
                       "مشورت با کارشناس آموزش نیست."}


def graduation_audit(conn, user, student) -> dict:
    settings = db.get_settings(conn)
    required = int(settings.get("grad_required_credits", "140") or 140)
    if student is None or student.get("passed_credits") is None:
        return {"status": "insufficient_info", "message": "تعداد واحدهای گذرانده‌شده شما ثبت نشده است."}
    passed = int(student.get("passed_credits") or 0)
    remaining = max(0, required - passed)
    try:
        passed_codes = json.loads(student.get("passed_courses") or "[]")
    except json.JSONDecodeError:
        passed_codes = []
    not_passed = [c for c in _load_courses(conn, user) if c["code"] not in passed_codes]
    return {"status": "satisfied" if remaining == 0 else "not_satisfied",
            "required": required, "passed": passed, "remaining": remaining,
            "not_passed_courses": not_passed[:8],
            "message": f"بر اساس داده همین سامانه، {passed} واحد از {required} واحد گذرانده شده و "
                       f"{remaining} واحد باقی مانده است. بررسی رسمی فقط توسط کارشناس آموزش انجام می‌شود."}
