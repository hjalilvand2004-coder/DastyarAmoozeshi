# -*- coding: utf-8 -*-
"""سرویس تقویم و مهلت‌ها: رویدادها، یادآور شخصی، تأیید دریافت (ضد تکرار)"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_conn, get_current_user
from app.services import (ack_deadline, create_deadline, list_deadlines,
                          pending_reminders, require, update_deadline)

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("", summary="فهرست مهلت‌ها/رویدادها")
def deadlines(active_only: bool = True, user: dict = Depends(get_current_user),
              conn=Depends(get_conn)):
    return {"deadlines": list_deadlines(conn, user, active_only=active_only)}


@router.get("/reminders", summary="یادآورهای اعلام‌نشده من")
def reminders(window_days: int = 30, user: dict = Depends(get_current_user),
              conn=Depends(get_conn)):
    return {"reminders": pending_reminders(conn, user, window_days=window_days)}


class DeadlineIn(BaseModel):
    title: str
    date_iso: str  # YYYY-MM-DD میلادی
    scope: dict | None = None
    source_document_id: int | None = None
    notes: str = ""


@router.post("", summary="ثبت مهلت جدید (کارشناس)")
def add_deadline(body: DeadlineIn, user: dict = Depends(get_current_user),
                 conn=Depends(get_conn)):
    did = create_deadline(conn, user, body.title, body.date_iso, body.scope,
                          body.source_document_id, body.notes or "ثبت‌شده از رابط وب")
    return {"id": did}


class DeadlinePatch(BaseModel):
    title: str | None = None
    date_iso: str | None = None
    notes: str | None = None
    active: bool | None = None


@router.patch("/{deadline_id}", summary="ویرایش مهلت (کارشناس)")
def patch_deadline(deadline_id: int, body: DeadlinePatch,
                   user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "deadlines.manage")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="فیلدی برای ویرایش ارسال نشده است")
    update_deadline(conn, user, deadline_id, fields)
    return {"ok": True}


@router.post("/{deadline_id}/ack", summary="تأیید دریافت یادآور (ضد تکرار)")
def ack(deadline_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    ack_deadline(conn, user, deadline_id)
    return {"ok": True}
