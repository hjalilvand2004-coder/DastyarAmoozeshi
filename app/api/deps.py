# -*- coding: utf-8 -*-
"""وابستگی‌های مشترک روترها: اتصال DB، کاربر جاری، کنترل دسترسی"""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, Request

from app import db
from app.config import db_path
from app.security import parse_token
from app.services import ROLE_PERMS, ROLE_FA, has_perm


def get_conn() -> sqlite3.Connection:
    conn = db.connect(db_path())
    try:
        yield conn
    finally:
        conn.close()


def _unauth(detail: str = "احراز هویت لازم است") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise _unauth()
    payload = parse_token(auth[7:].strip())
    if not payload or not payload.get("uid"):
        raise _unauth("توکن نامعتبر یا منقضی شده است")
    row = db.q1(conn, "SELECT * FROM users WHERE id=?", (payload["uid"],))
    if not row or not row.get("active"):
        raise _unauth("کاربر یافت نشد یا غیرفعال است")
    return dict(row)


def user_perms(user: dict) -> list[str]:
    perms = ROLE_PERMS.get(user.get("role"), set())
    return ["*"] if perms == "*" else sorted(perms)


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user.get("full_name") or "",
        "role": user["role"],
        "role_fa": ROLE_FA.get(user.get("role"), "?"),
        "student_id": user.get("student_id"),
        "permissions": user_perms(user),
    }
