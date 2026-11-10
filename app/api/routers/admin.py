# -*- coding: utf-8 -*-
"""سرویس مدیریت سیستم: کاربران، تنظیمات (با پوشاندن مقادیر حساس)، گزارش حسابرسی"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.api.deps import get_conn, get_current_user
from app.services import (create_user, list_students, list_users, require,
                          reset_password, set_user_active)

router = APIRouter(prefix="/admin", tags=["admin"])

SECRET_KEYS = {"llm_api_key", "sso_oidc_client_secret"}
MASK = "••••••••"


@router.get("/users", summary="فهرست کاربران")
def users(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    rows = list_users(conn, user)
    for r in rows:
        r.pop("password_hash", None)
    return {"users": rows}


class UserIn(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    student_id: int | None = None


@router.post("/users", summary="ایجاد کاربر")
def add_user(body: UserIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    uid = create_user(conn, user, body.username.strip(), body.password,
                      body.full_name.strip(), body.role, body.student_id)
    return {"id": uid}


class ActiveIn(BaseModel):
    active: bool


@router.post("/users/{user_id}/active", summary="فعال/غیرفعال‌سازی کاربر")
def set_active(user_id: int, body: ActiveIn, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    set_user_active(conn, user, user_id, body.active)
    return {"ok": True}


class PasswordIn(BaseModel):
    password: str


@router.post("/users/{user_id}/password", summary="بازنشانی رمز کاربر")
def reset_pwd(user_id: int, body: PasswordIn, user: dict = Depends(get_current_user),
              conn=Depends(get_conn)):
    reset_password(conn, user, user_id, body.password)
    return {"ok": True}


@router.get("/settings", summary="تنظیمات سامانه (مقادیر حساس پوشانده می‌شوند)")
def get_settings(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    st = db.get_settings(conn)
    for k in SECRET_KEYS:
        if st.get(k):
            st[k] = MASK
    return {"settings": st}


class SettingIn(BaseModel):
    key: str
    value: str


@router.post("/settings", summary="به‌روزرسانی تنظیم")
def set_setting(body: SettingIn, user: dict = Depends(get_current_user),
                conn=Depends(get_conn)):
    require(user, "users.manage")
    if body.key in SECRET_KEYS and body.value == MASK:
        return {"ok": True, "skipped": "مقدار بدون تغییر ماند"}
    allowed = set(db.DEFAULT_SETTINGS) | {"sample_data_mode"}
    if body.key not in allowed:
        raise HTTPException(status_code=400, detail=f"کلید «{body.key}» مجاز نیست")
    db.set_setting(conn, body.key, body.value)
    db.audit(conn, user, "settings_update", body.key)
    return {"ok": True}


@router.get("/audit", summary="گزارش حسابرسی (آخرین رخدادها)")
def audit_log(limit: int = 200, user: dict = Depends(get_current_user),
              conn=Depends(get_conn)):
    require(user, "users.manage")
    limit = max(1, min(limit, 500))
    rows = db.q(conn, "SELECT a.*, u.username FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
                      "ORDER BY a.id DESC LIMIT ?", (limit,))
    return {"events": rows}


@router.get("/students", summary="فهرست دانشجویان (کارشناس+)")
def students(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "advisor.student")
    return {"students": list_students(conn, user)}
