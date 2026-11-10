# -*- coding: utf-8 -*-
"""سرویس قواعد قطعی: تعریف، گردش‌کار تأیید، ارزیابی (کارشناس برای دانشجو / دانشجو برای خودش)"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.api.deps import get_conn, get_current_user
from app.ruleengine import evaluate
from app.services import (approve_rule, create_rule, evaluate_rule_for_student,
                          get_student_for_user, list_rules, require, set_rule_status)
from app.answers import _student_profile

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", summary="فهرست قواعد")
def get_rules(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    return {"rules": list_rules(conn, user)}


class RuleIn(BaseModel):
    title: str
    cond: dict
    source_document_id: int | None = None
    source_clause: str = ""
    messages: dict | None = None
    review_fields: list[str] | None = None


@router.post("", summary="تعریف قاعده جدید (پیش‌فرض: draft)")
def add_rule(body: RuleIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    rid = create_rule(conn, user, body.title, body.cond, body.source_document_id,
                      body.source_clause, messages=body.messages,
                      review_fields=body.review_fields)
    return {"id": rid, "status": "draft"}


@router.post("/{rule_id}/approve", summary="تأیید قاعده (فقط تأییدکننده)")
def approve(rule_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    approve_rule(conn, user, rule_id)
    return {"ok": True, "status": "approved"}


class RuleStatusIn(BaseModel):
    status: str  # approved | disabled


@router.post("/{rule_id}/status", summary="فعال/غیرفعال‌سازی قاعده تأییدشده")
def set_status(rule_id: int, body: RuleStatusIn, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    set_rule_status(conn, user, rule_id, body.status)
    return {"ok": True, "status": body.status}


@router.get("/my", summary="ارزیابی قواعد تأییدشده برای خودم (دانشجو)")
def my_rule_status(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "advisor.self")
    student = get_student_for_user(conn, user)
    if not student:
        return {"student": None, "results": []}
    profile = _student_profile(student)
    results = []
    for r in db.q(conn, "SELECT * FROM rules WHERE university_id=? AND status='approved'",
                  (user["university_id"],)):
        try:
            import json as _json
            rec = dict(r)
            rec["cond"] = _json.loads(r["cond_json"])
            rec["review_fields"] = _json.loads(r.get("review_fields") or "[]")
            rec["messages"] = _json.loads(r.get("messages") or "{}")
        except Exception:
            continue
        res = evaluate(rec, profile)
        if res.status == "insufficient_info":
            res.details.append("برای ارزیابی دقیق، این اطلاعات در پروفایل شما ثبت نشده است.")
        results.append({"rule_id": r["id"], "title": r["title"], "source_clause": r["source_clause"],
                        "status": res.status, "status_fa": res.status_fa,
                        "missing": res.missing, "detail": rec["messages"].get(res.status, "")})
    return {"student": student, "results": results}


@router.post("/{rule_id}/evaluate/{student_id}", summary="ارزیابی قاعده برای دانشجو (کارشناس)")
def eval_for_student(rule_id: int, student_id: int, user: dict = Depends(get_current_user),
                     conn=Depends(get_conn)):
    return evaluate_rule_for_student(conn, user, rule_id, student_id)
