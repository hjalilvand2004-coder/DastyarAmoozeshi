# -*- coding: utf-8 -*-
"""سرویس پایگاه دانش آیین‌نامه‌ها: ثبت، چرخه تأیید/انتشار، نسخه‌بندی، ابطال"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import get_conn, get_current_user
from app.services import (get_document_chunks, import_document, list_documents,
                          revise_document, update_document_status)

router = APIRouter(prefix="/regulations", tags=["regulations"])


@router.get("", summary="فهرست اسناد (پیش‌نویس‌ها فقط برای مجازها)")
def list_regs(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    return {"documents": list_documents(conn, user)}


@router.get("/{doc_id}", summary="جزئیات سند + تکه‌های متن")
def get_reg(doc_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    docs = list_documents(conn, user)
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="سند یافت نشد یا دسترسی ندارد")
    chunks = get_document_chunks(conn, user, doc_id)
    return {"document": doc, "chunks": chunks}


class ImportIn(BaseModel):
    title: str
    text: str = ""
    doc_type: str = "text"
    url: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    scope_level: str | None = None
    scope_major: str | None = None
    scope_entry_from: int | None = None
    scope_entry_to: int | None = None
    source_note: str = ""


@router.post("/import", summary="ثبت سند متنی (خروجی: پیش‌نویس)")
def import_text(body: ImportIn, user: dict = Depends(get_current_user),
                conn=Depends(get_conn)):
    doc_id = import_document(conn, user, title=body.title, doc_type=body.doc_type,
                             text=body.text, url=body.url,
                             effective_from=body.effective_from, effective_until=body.effective_until,
                             scope_level=body.scope_level, scope_major=body.scope_major,
                             scope_entry_from=body.scope_entry_from, scope_entry_to=body.scope_entry_to,
                             source_note=body.source_note or "ثبت‌شده از رابط وب")
    return {"id": doc_id, "status": "draft"}


@router.post("/import-file", summary="بارگذاری فایل (txt/md/pdf/docx) به‌عنوان پیش‌نویس")
async def import_file(title: str = Form(...), file: UploadFile = File(...),
                      url: str | None = Form(None),
                      scope_level: str | None = Form(None),
                      scope_major: str | None = Form(None),
                      user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    suffix = Path(file.filename or "f.txt").suffix.lower()
    if suffix not in (".txt", ".md", ".pdf", ".docx"):
        raise HTTPException(status_code=400,
                            detail="فقط txt/md/pdf/docx پشتیبانی می‌شود (اسکن/OCR در فاز بعد)")
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()
        doc_type = {"": "text", ".txt": "text", ".md": "text",
                    ".pdf": "pdf", ".docx": "docx"}[suffix]
        doc_id = import_document(conn, user, title=title, doc_type=doc_type,
                                 file_path=tmp.name, url=url,
                                 scope_level=scope_level, scope_major=scope_major,
                                 source_note=f"بارگذاری فایل: {file.filename}")
    finally:
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass
    return {"id": doc_id, "status": "draft"}


class StatusIn(BaseModel):
    status: str
    reason: str = ""


@router.post("/{doc_id}/status", summary="گذار وضعیت سند (چرخه تأیید/انتشار/ابطال)")
def set_status(doc_id: int, body: StatusIn, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    update_document_status(conn, user, doc_id, body.status, body.reason)
    return {"ok": True, "status": body.status}


@router.post("/{doc_id}/revise", summary="ایجاد نسخه جدید (پیش‌نویس) از سند")
def revise(doc_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    new_id = revise_document(conn, user, doc_id)
    return {"id": new_id, "status": "draft"}
