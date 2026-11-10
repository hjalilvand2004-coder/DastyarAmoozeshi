# -*- coding: utf-8 -*-
"""سرویس راهنمای فرایندهای اداری: گام‌به‌گام، مدارک لازم، سیستم مقصد"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_conn, get_current_user
from app.services import create_process, get_process, list_processes, require

router = APIRouter(prefix="/processes", tags=["processes"])


def _decorate(p: dict) -> dict:
    for key in ("steps", "required_docs", "keywords"):
        try:
            p[key] = json.loads(p.get(key) or ("[]"))
        except (json.JSONDecodeError, TypeError):
            p[key] = []
    return p


@router.get("", summary="فهرست فرایندها")
def processes(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    return {"processes": [_decorate(p) for p in list_processes(conn, user)]}


@router.get("/{proc_id}", summary="جزئیات فرایند")
def process(proc_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    return _decorate(get_process(conn, user, proc_id))


class ProcessIn(BaseModel):
    key: str
    title: str
    steps: list[str]
    required_docs: list[str] | None = None
    target_system: str = ""
    target_url: str = ""
    keywords: list[str] | None = None
    notes: str = ""


@router.post("", summary="ثبت فرایند جدید (کارشناس)")
def add_process(body: ProcessIn, user: dict = Depends(get_current_user),
                conn=Depends(get_conn)):
    require(user, "deadlines.manage")
    pid = create_process(conn, user, body.key, body.title, body.steps,
                         body.required_docs, body.target_system, body.target_url,
                         body.keywords, body.notes)
    return {"id": pid}
