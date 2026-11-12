# -*- coding: utf-8 -*-
"""سرویس مصرفی برای سایر نرم‌افزارهای دانشجو۳۶۰ و هر سامانه متصل دیگر

احراز: هدر «X-API-Key» (کلید سامانه متصل، مدیریت از /api/v1/integrations)
هر مسیر فقط با اسکوپ مربوطه باز است؛ نرخ هر سامانه مستقل کنترل و همه فراخوانی‌ها
ثبت می‌شوند. این سرویس «بی‌حالت» است: سامانه میزبان می‌تواند پرسش‌ها را نوبت‌بندی کند.

نقشه مسیرها:
  POST /api/v1/integration/v1/ask                    ← پرسش مستند (اسکوپ ask)
  POST /api/v1/integration/v1/regulations/search     ← جست‌وجوی آیین‌نامه (regulations.read)
  GET  /api/v1/integration/v1/regulations/{id}       ← سند + مواد (regulations.read)
  POST /api/v1/integration/v1/rules/evaluate         ← ارزیابی قاعده قطعی (rules.evaluate)
  GET  /api/v1/integration/v1/deadlines              ← مهلت‌ها (deadlines.read)
  GET  /api/v1/integration/v1/processes              ← راهنمای فرایندها (processes.read)
  POST /api/v1/integration/v1/tickets                ← ثبت درخواست کارشناس (tickets.create)
  GET  /api/v1/integration/v1/whoami                 ← بررسی کلید و اسکوپ‌ها (بدون اسکوپ)
"""

from __future__ import annotations

import dataclasses
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app import db, integration, ruleengine
from app.answers import (STRONG_SCORE, _candidate_docs, _chunks_for,
                         _make_citation, _student_profile)
from app.search import BM25, tokenize
from app.api.deps import get_conn
from app.services import create_ticket, list_deadlines

router = APIRouter(prefix="/integration/v1", tags=["integration - سرویس سایر سامانه‌ها"])


# ---------- وابستگی احراز کلید ----------

def get_system(request: Request, conn=Depends(get_conn)) -> dict:
    """احراز کلید سامانه متصل + کنترل نرخ؛ سامانه روی request.state ثبت می‌شود تا میان‌افزار لاگ بنویسد"""
    api_key = request.headers.get("X-API-Key") or ""
    system = integration.verify_key(conn, api_key)
    if not system:
        raise HTTPException(status_code=401,
                            detail="کلید API نامعتبر است یا سامانه متصل غیرفعال شده است.")
    if not integration.rate_allow(system, request.url.path):
        raise HTTPException(status_code=429,
                            detail=f"سقف فراخوانی سامانه «{system['name']}» پر شده است؛ بعداً تلاش کنید.")
    request.state.int_system = system
    return system


def _need_scope(system: dict, scope: str) -> None:
    if not integration.check_scope(system, scope):
        raise HTTPException(status_code=403,
                            detail=f"کلید سامانه «{system['name']}» اسکوپ «{scope}» را ندارد.")


def _student(conn, system: dict, ctx: "StudentCtx | None"):
    return integration.resolve_student(conn, system["university_id"],
                                       ctx.model_dump(exclude_none=True) if ctx else None)


def _meta(system: dict) -> dict:
    return {"system_code": system["code"], "system_name": system["name"],
            "sample_data": True, "disclaimer": "پاسخ‌ها بر اساس اسناد ثبت‌شده سامانه است و "
                                               "جایگزین حکم رسمی دانشگاه نیست."}


# ---------- مدل‌های ورودی ----------

class StudentCtx(BaseModel):
    """پروفایل دانشجو از سامانه میزبان؛ یا شناسه داخلی (student_id) یا داده صریح"""
    student_id: int | None = None
    full_name: str | None = None
    level: str | None = None
    major: str | None = None
    entry_year: int | None = None
    gpa: float | None = None
    passed_credits: int | None = None
    passed_courses: list[str] | None = None
    flags: dict = Field(default_factory=dict)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    topic: str | None = Field(default=None, max_length=200,
                              description="موضوع موردنیاز سامانه میزبان (مثل «کارورزی») برای تمرکز جست‌وجو")
    student: StudentCtx | None = None
    include_retired: bool = False


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    topic: str | None = Field(default=None, max_length=200)
    student: StudentCtx | None = None
    limit: int = Field(default=5, ge=1, le=20)


class RuleEvalIn(BaseModel):
    rule_id: int | None = None
    query: str | None = Field(default=None, max_length=500)
    student: StudentCtx | None = None


class TicketIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(default="", max_length=4000)
    student: StudentCtx | None = None


# ---------- ۱) پرسش مستند ----------

@router.post("/ask", summary="پرسش مستند از دستیار برای سامانه دیگر")
def ask(body: AskIn, system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "ask")
    q_text = body.question.strip()
    if body.topic:
        q_text = f"{q_text} ({body.topic.strip()})"
    user = integration.virtual_user(system["university_id"])
    student = _student(conn, system, body.student)
    ans = integration_answer(conn, user, student, q_text, body.include_retired)
    return {"answer": dataclasses.asdict(ans), "meta": _meta(system)}


def integration_answer(conn, user, student, question: str, include_retired: bool):
    """همان موتور پاسخ سه‌لایه سامانه (بدون ذخیره تاریخچه گفت‌وگو - بی‌حالت)"""
    from app.answers import build_answer
    return build_answer(conn, user, student, question, include_retired=include_retired)


# ---------- ۲) جست‌وجوی آیین‌نامه ----------

@router.post("/regulations/search", summary="جست‌وجو در آیین‌نامه‌های منتشرشده")
def regulations_search(body: SearchIn, system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "regulations.read")
    user = integration.virtual_user(system["university_id"])
    student = _student(conn, system, body.student)
    q_text = body.query.strip() + (f" ({body.topic.strip()})" if body.topic else "")

    current, _retired = _candidate_docs(conn, user, student, include_retired=False)
    if not current:
        return {"results": [], "note": "هیچ سند منتشرشده‌ای برای دامنه این دانشجو ثبت نشده است.",
                "meta": _meta(system)}
    docs_by_id = {d["id"]: d for d in current}
    chunks = _chunks_for(conn, [d["id"] for d in current])
    index = BM25([(cid, c["text"]) for cid, c in chunks.items()])
    hits = index.search(q_text, k=max(body.limit * 3, 10))
    strong = [(cid, s) for cid, s in hits if s >= STRONG_SCORE][: body.limit]
    if not strong:
        return {"results": [], "note": "مورد مرتبطی در اسناد منتشرشده یافت نشد.", "meta": _meta(system)}
    results = []
    for i, (cid, _s) in enumerate(strong, start=1):
        ch = chunks[cid]
        results.append(_make_citation(ch, docs_by_id[ch["document_id"]], i))
    return {"results": results, "meta": _meta(system)}


@router.get("/regulations/{document_id}", summary="دریافت سند منتشرشده به‌همراه مواد")
def regulation_get(document_id: int, system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "regulations.read")
    doc = db.q1(conn, "SELECT * FROM documents WHERE id=? AND university_id=? AND status='published'",
                (document_id, system["university_id"]))
    if not doc:
        raise LookupError("سند یافت نشد یا منتشرشده نیست.")
    chunks = db.q(conn, "SELECT clause_ref, page_no, text, idx FROM chunks WHERE document_id=? ORDER BY idx",
                  (document_id,))
    doc = dict(doc)
    doc["status_fa"] = {"published": "منتشرشده (معتبر)"}.get(doc["status"], doc["status"])
    doc["sample_warning"] = not bool(doc.get("is_official"))
    return {"document": doc, "chunks": chunks, "meta": _meta(system)}


# ---------- ۳) ارزیابی قاعده قطعی ----------

def _rule_public(res: ruleengine.RuleResult) -> dict:
    return {"rule_id": res.rule_id, "title": res.title, "status": res.status,
            "status_fa": res.status_fa, "missing": res.missing, "details": res.details,
            "source_document_id": res.source_document_id, "source_clause": res.source_clause}


@router.post("/rules/evaluate", summary="ارزیابی قواعد قطعی برای دانشجوی سامانه میزبان")
def rules_evaluate(body: RuleEvalIn, system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "rules.evaluate")
    if not body.rule_id and not (body.query or "").strip():
        raise ValueError("یا rule_id یا query ارسال کنید.")
    student = _student(conn, system, body.student)
    profile = _student_profile(student)
    rules = db.q(conn, "SELECT * FROM rules WHERE university_id=? AND status='approved'",
                 (system["university_id"],))
    if body.rule_id:
        rules = [r for r in rules if r["id"] == body.rule_id]
        if not rules:
            raise LookupError("قاعده یافت نشد یا تأیید انسانی ندارد.")
    else:
        q_tokens = set(tokenize(body.query))
        picked = []
        for r in rules:
            try:
                cond = json.loads(r["cond_json"])
            except json.JSONDecodeError:
                continue
            if q_tokens & set(tokenize(r["title"] + " " + json.dumps(cond, ensure_ascii=False))):
                picked.append(r)
        rules = picked
    out = []
    for r in rules:
        try:
            cond = json.loads(r["cond_json"])
            review_fields = json.loads(r.get("review_fields") or "[]")
        except json.JSONDecodeError:
            continue
        rec = dict(r)
        rec["cond_json"] = cond
        rec["review_fields"] = review_fields
        res = ruleengine.evaluate(rec, profile)
        out.append(_rule_public(res))
    return {"results": out, "meta": _meta(system)}


# ---------- ۴) مهلت‌ها ----------

@router.get("/deadlines", summary="مهلت‌های پیشِ رو برای دانشجو/دانشگاه")
def deadlines(days: int = 90, system: dict = Depends(get_system), conn=Depends(get_conn),
        student_id: int | None = None):
    _need_scope(system, "deadlines.read")
    user = integration.virtual_user(system["university_id"])
    ctx = StudentCtx(student_id=student_id) if student_id else None
    student = _student(conn, system, ctx)
    rows = list_deadlines(conn, user, student)
    rows = [r for r in rows if 0 <= r["days_left"] <= max(1, min(days, 365))]
    for r in rows:
        r.pop("acked", None)
    return {"deadlines": rows, "meta": _meta(system)}


# ---------- ۵) راهنمای فرایندها ----------

@router.get("/processes", summary="راهنمای گام‌به‌گام فرایندهای اداری")
def processes(query: str = "", system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "processes.read")
    rows = db.q(conn, "SELECT * FROM processes WHERE university_id=?", (system["university_id"],))
    q_tokens = set(tokenize(query))
    scored = []
    for p in rows:
        try:
            kws = json.loads(p.get("keywords") or "[]")
            steps = json.loads(p.get("steps") or "[]")
        except json.JSONDecodeError:
            kws, steps = [], []
        hits = sum(1 for kw in kws if set(tokenize(kw)) & q_tokens) if q_tokens else 0
        p = dict(p)
        p["steps"] = [str(s) for s in steps]
        p.pop("keywords", None)
        scored.append((hits, p))
    scored.sort(key=lambda t: -t[0])
    out = [p for h, p in scored if hits_ok(h, q_tokens)]
    return {"processes": out, "meta": _meta(system)}


def hits_ok(h: int, q_tokens: set) -> bool:
    return (not q_tokens) or h > 0


# ---------- ۶) تیکت از طرف سامانه میزبان ----------

@router.post("/tickets", summary="ثبت درخواست کارشناس برای دانشجو از سامانه دیگر")
def tickets(body: TicketIn, system: dict = Depends(get_system), conn=Depends(get_conn)):
    _need_scope(system, "tickets.create")
    svc = integration.service_user(conn, system["university_id"], system)
    subject = f"[{system['name']}] {body.subject.strip()}"
    text = body.body.strip()
    if body.student and (body.student.full_name or body.student.student_id):
        who = body.student.full_name or f"شناسه {body.student.student_id}"
        text = (f"ارسال‌شده از سامانه «{system['name']}» برای دانشجوی {who}.\n\n" + text).strip()
    tid = create_ticket(conn, svc, subject, text)
    db.audit(conn, None, "integration_ticket", f"system={system['code']} ticket={tid}")
    return {"ticket_id": tid, "subject": subject, "meta": _meta(system)}


# ---------- ۷) خودآزمایی کلید ----------

@router.get("/whoami", summary="بررسی کلید، اسکوپ‌ها و آمار مصرف")
def whoami(system: dict = Depends(get_system), conn=Depends(get_conn)):
    return {
        "system": {"id": system["id"], "name": system["name"], "code": system["code"],
                   "scopes": json.loads(system.get("scopes") or "[]"),
                   "rate_limit_per_hour": system["rate_limit_per_hour"],
                   "is_widget": bool(system["is_widget"]),
                   "call_count": system["call_count"],
                   "last_used_at": system["last_used_at"]},
        "meta": _meta(system),
    }
