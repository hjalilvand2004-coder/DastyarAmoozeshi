# -*- coding: utf-8 -*-
"""سرویس مدیریت «سامانه‌های متصل» — فقط مدیر سیستم

ثبت سامانه دیگر (پژوهشیار، برنامه‌ریز، ...) + کلید API + اسکوپ‌ها + محدودیت نرخ،
چرخش کلید، فعال/غیرفعال‌سازی، مشاهده لاگ فراخوانی‌ها و کاتالوگ اسکوپ‌ها.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import integration
from app.api.deps import get_conn, get_current_user
from app.services import require

router = APIRouter(prefix="/integrations", tags=["integrations - مدیریت سامانه‌های متصل"])


@router.get("/scopes", summary="کاتالوگ اسکوپ‌های موجود برای سامانه‌های متصل")
def scopes(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    return {"scopes": [{"scope": k, "description": v} for k, v in integration.SCOPES.items()]}


@router.get("", summary="فهرست سامانه‌های متصل")
def systems(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    return {"systems": integration.list_systems(conn, user)}


class SystemIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=60)
    scopes: list[str] = Field(default_factory=lambda: list(integration.DEFAULT_SCOPES))
    rate_limit_per_hour: int = Field(default=120, ge=1, le=10000)
    is_widget: bool = False
    contact: str = Field(default="", max_length=200)


@router.post("", summary="ثبت سامانه متصل جدید (کلید فقط یک بار نمایش داده می‌شود)")
def add_system(body: SystemIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    res = integration.create_system(conn, user, body.name, body.code, body.scopes,
                                    body.rate_limit_per_hour, body.is_widget, body.contact)
    return res


@router.post("/{system_id}/rotate", summary="چرخش کلید (کلید قبلی باطل می‌شود)")
def rotate(system_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "users.manage")
    return {"api_key": integration.rotate_key(conn, user, system_id)}


class ActiveIn(BaseModel):
    active: bool


@router.post("/{system_id}/active", summary="فعال/غیرفعال‌سازی سامانه متصل")
def set_active(system_id: int, body: ActiveIn, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    require(user, "users.manage")
    integration.set_system_active(conn, user, system_id, body.active)
    return {"ok": True}


@router.get("/{system_id}/logs", summary="لاگ فراخوانی‌های سامانه متصل")
def logs(system_id: int, limit: int = 50, user: dict = Depends(get_current_user),
         conn=Depends(get_conn)):
    require(user, "users.manage")
    return {"logs": integration.recent_logs(conn, user, system_id, limit)}
