# -*- coding: utf-8 -*-
"""لایه سرویس «ادغام با سایر سامانه‌ها»

هر زیرسیستم دانشجو۳۶۰ (پژوهشیار، برنامه‌ریز، پرتال، اپ موبایل، ...) می‌تواند با
کلید API از سرویس‌های این دستیار استفاده کند؛ یا چت‌بات هوشمند این دستیار را با یک
خط <script> داخل خودش نصب کند (widget.js).

اصول امنیتی:
- احراز سرویس‌به‌سرویس با هدر X-API-Key (جست‌وجو با هش SHA-256)
- هر کلید فقط اسکوپ‌های تعیین‌شده را دارد؛ درخواست خارج از اسکوپ ← ۴۰۳
- محدودسازی نرخ مستقل برای هر سامانه و هر مسیر ← ۴۲۹
- هر فراخوانی مصرفی در integration_logs ثبت می‌شود (قابل مشاهده برای مدیر سیستم)
- کلید کامل برای «نمایش در رابط مدیریت نسخه نمونه» ذخیره می‌شود؛ در عملیات واقعی
  باید از چرخش کلید (rotate) استفاده شود و کلید فقط هش نگه‌داری شود (docs/10-integration.md)
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3

from . import db
from .security import RATE_LIMITER

# ---------- کاتالوگ اسکوپ‌ها ----------

SCOPES: dict[str, str] = {
    "ask": "پرسش مستند از دستیار (پاسخ سه‌لایه با استناد)",
    "regulations.read": "جست‌وجو و دریافت آیین‌نامه‌های منتشرشده",
    "rules.evaluate": "ارزیابی قواعد قطعی برای دانشجو",
    "deadlines.read": "دریافت مهلت‌ها و رویدادهای تقویم آموزشی",
    "processes.read": "دریافت راهنمای گام‌به‌گام فرایندهای اداری",
    "tickets.create": "ثبت درخواست کارشناس برای دانشجو",
}

DEFAULT_SCOPES = ["ask", "regulations.read", "deadlines.read", "processes.read"]


# ---------- کلید ----------

def generate_key() -> str:
    return "d360_" + secrets.token_hex(20)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def mask_key(key: str) -> str:
    return key[:11] + "…" + key[-4:] if len(key) > 18 else "…"


# ---------- مدیریت سامانه‌های متصل ----------

def list_systems(conn: sqlite3.Connection, actor: dict) -> list[dict]:
    rows = db.q(conn, "SELECT * FROM external_systems WHERE university_id=? ORDER BY id",
                (actor["university_id"],))
    out = []
    for r in rows:
        r = dict(r)
        try:
            r["scopes"] = json.loads(r.get("scopes") or "[]")
        except json.JSONDecodeError:
            r["scopes"] = []
        r["api_key_masked"] = mask_key(r["api_key"])
        r["active"] = bool(r["active"])
        r["is_widget"] = bool(r["is_widget"])
        out.append(r)
    return out


def create_system(conn: sqlite3.Connection, actor: dict, name: str, code: str,
                  scopes: list[str] | None = None, rate_limit_per_hour: int = 120,
                  is_widget: bool = False, contact: str = "") -> dict:
    """سامانه متصل جدید؛ کلید فقط یک بار در پاسخ برگردانده می‌شود"""
    code = (code or "").strip().lower().replace(" ", "-")
    if not name.strip() or not code:
        raise ValueError("نام و شناسه سامانه الزامی است.")
    if not all(s in SCOPES for s in (scopes or [])):
        raise ValueError("اسکوپ نامعتبر است.")
    key = generate_key()
    sid = db.ex(conn, "INSERT INTO external_systems(university_id, name, code, api_key, api_key_hash, "
                      "scopes, rate_limit_per_hour, is_widget, contact, created_by) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (actor["university_id"], name.strip(), code, key, hash_key(key),
                 json.dumps(sorted(set(scopes or DEFAULT_SCOPES)), ensure_ascii=False),
                 max(1, int(rate_limit_per_hour or 120)), 1 if is_widget else 0,
                 (contact or "").strip(), actor.get("id")))
    db.audit(conn, actor, "integration_create", f"system={code}")
    return {"id": sid, "api_key": key}


def rotate_key(conn: sqlite3.Connection, actor: dict, system_id: int) -> str:
    row = db.q1(conn, "SELECT * FROM external_systems WHERE id=?", (system_id,))
    if not row or row["university_id"] != actor["university_id"]:
        raise LookupError("سامانه متصل یافت نشد.")
    key = generate_key()
    db.ex(conn, "UPDATE external_systems SET api_key=?, api_key_hash=? WHERE id=?",
          (key, hash_key(key), system_id))
    db.audit(conn, actor, "integration_rotate", f"system={row['code']}")
    return key


def set_system_active(conn: sqlite3.Connection, actor: dict, system_id: int, active: bool) -> None:
    row = db.q1(conn, "SELECT * FROM external_systems WHERE id=?", (system_id,))
    if not row or row["university_id"] != actor["university_id"]:
        raise LookupError("سامانه متصل یافت نشد.")
    db.ex(conn, "UPDATE external_systems SET active=? WHERE id=?", (1 if active else 0, system_id))
    db.audit(conn, actor, "integration_active", f"system={row['code']} active={active}")


def recent_logs(conn: sqlite3.Connection, actor: dict, system_id: int, limit: int = 50) -> list[dict]:
    row = db.q1(conn, "SELECT * FROM external_systems WHERE id=?", (system_id,))
    if not row or row["university_id"] != actor["university_id"]:
        raise LookupError("سامانه متصل یافت نشد.")
    return db.q(conn, "SELECT * FROM integration_logs WHERE system_id=? ORDER BY id DESC LIMIT ?",
                (system_id, max(1, min(limit, 200))))


# ---------- احراز کلید و کنترل مصرف ----------

def verify_key(conn: sqlite3.Connection, api_key: str) -> dict | None:
    if not api_key:
        return None
    row = db.q1(conn, "SELECT * FROM external_systems WHERE api_key_hash=?", (hash_key(api_key),))
    if not row or not row["active"]:
        return None
    return dict(row)


def check_scope(system: dict, scope: str) -> bool:
    try:
        scopes = json.loads(system.get("scopes") or "[]")
    except json.JSONDecodeError:
        scopes = []
    return scope in scopes


def rate_allow(system: dict, endpoint: str) -> bool:
    limit = int(system.get("rate_limit_per_hour") or 120)
    return RATE_LIMITER.allow(f"int:{system['id']}:{endpoint}", limit, window_s=3600)


def log_call(conn: sqlite3.Connection, system: dict, endpoint: str, status: int,
             duration_ms: int, ip: str = "") -> None:
    db.ex(conn, "INSERT INTO integration_logs(university_id, system_id, endpoint, status_code, "
                "duration_ms, ip) VALUES(?,?,?,?,?,?)",
          (system.get("university_id"), system["id"], endpoint, status, duration_ms, ip or ""))
    db.ex(conn, "UPDATE external_systems SET last_used_at=datetime('now'), call_count=call_count+1 "
                "WHERE id=?", (system["id"],))


# ---------- کاربر مجازی و پروفایل دانشجو از سامانه دیگر ----------

def virtual_user(university_id: int) -> dict:
    """کاربر مجازی برای موتور پاسخ/قواعد؛ فقط برای فیلتر university_id استفاده می‌شود"""
    return {"id": None, "university_id": university_id, "role": "expert",
            "username": "integration-api", "student_id": None}


def resolve_student(conn: sqlite3.Connection, university_id: int, payload: dict | None) -> dict | None:
    """پروفایل دانشجو: یا «شناسه داخلی» (student_id) از پایگاه داده، یا داده ارسالی خود سامانه"""
    if not payload:
        return None
    if isinstance(payload, dict) and payload.get("student_id"):
        row = db.q1(conn, "SELECT * FROM students WHERE id=? AND university_id=?",
                    (payload["student_id"], university_id))
        return row
    extra = payload.get("flags") if isinstance(payload.get("flags"), dict) else {}
    return {
        "id": None,
        "university_id": university_id,
        "full_name": (payload or {}).get("full_name") or "",
        "level": (payload or {}).get("level"),
        "major": (payload or {}).get("major"),
        "entry_year": (payload or {}).get("entry_year"),
        "gpa": (payload or {}).get("gpa"),
        "passed_credits": (payload or {}).get("passed_credits"),
        "passed_courses": json.dumps((payload or {}).get("passed_courses") or [], ensure_ascii=False),
        "profile_extra": json.dumps(extra, ensure_ascii=False),
    }


def service_user(conn: sqlite3.Connection, university_id: int, system: dict) -> dict:
    """کاربر خدماتی برای ثبت تیکت از سامانه دیگر (بدون امکان ورود دستی)"""
    username = f"svc-{system['code']}"
    row = db.q1(conn, "SELECT * FROM users WHERE university_id=? AND username=?",
                (university_id, username))
    if row:
        return row
    from .security import hash_password
    uid = db.ex(conn, "INSERT INTO users(university_id, username, password_hash, full_name, role, active) "
                      "VALUES(?,?,?,?,?,1)",
                (university_id, username, hash_password(secrets.token_hex(32)),
                 f"سرویس سامانه متصل ({system['name']})", "student"))
    return db.q1(conn, "SELECT * FROM users WHERE id=?", (uid,))
