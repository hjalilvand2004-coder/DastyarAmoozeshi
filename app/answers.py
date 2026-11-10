# -*- coding: utf-8 -*-
"""دستیار پاسخ‌ده مستند (Evidence-based)

اصل محصول: «اول منبع معتبر، بعد ارزیابی شرایط، در پایان پاسخ ساده و اقدام پیشنهادی»
پاسخ سه لایه دارد و لایه‌ها از هم تفکیک می‌شوند:
  لایه ۱) متن رسمی سند (عیناً، با ارجاع)
  لایه ۲) توضیح ساده (مدل زبانی اختیاری یا موتور قالبی)
  لایه ۳) وضعیت شخصی دانشجو (موتور قواعد قطعی) و اقدام بعدی

قواعد سخت:
- ارجاع فقط به تکه‌های واقعی بازیابی‌شده؛ ارجاع ساختگی حذف و گزارش می‌شود.
- سند ملغی هرگز به‌عنوان قانون جاری ارائه نمی‌شود (فقط با برچسب «ملغی» و درخواست صریح کاربر).
- داده نمونه/غیررسمی همیشه برچسب می‌خورد.
- اگر اطلاعات دانشجو ناکافی باشد، پاسخ «اطلاعات ناکافی» است؛ حدس زده نمی‌شود.
- تزریق دستور داخل اسناد فقط «داده» است و پرچم می‌خورد.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from html import escape

from . import db, ruleengine
from .llm import TemplateProvider, make_provider
from .search import BM25, tokenize
from .security import RATE_LIMITER

DISCLAIMER = "این پاسخ صرفاً راهنمای خودکار بر اساس اسناد بارگذاری‌شده در سامانه است و جایگزین حکم رسمی دانشگاه نیست."
SAMPLE_BANNER = ("هشدار: اسناد فعلی «نمونه و غیررسمی» هستند. تا زمانی که مدیر محتوای دانشگاه اسناد رسمی را "
                 "ثبت نکند، هیچ موردی به‌عنوان قانون واقعی دانشگاه ارائه نمی‌شود.")

DOC_STATUS_FA = {
    "draft": "پیش‌نویس",
    "in_review": "در حال بررسی",
    "approved": "تأییدشده",
    "published": "منتشرشده (معتبر)",
    "retired": "ملغی‌شده",
}

STRONG_SCORE = 1.2


@dataclass
class Answer:
    question: str = ""
    short: str = ""
    conditions: list[str] = field(default_factory=list)
    status_rows: list[dict] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    confirmations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider_name: str = TemplateProvider.name
    no_result: bool = False
    note: str = ""
    session_id: int | None = None
    message_id: int | None = None

    # ---------- HTML ----------
    def to_html(self) -> str:
        h = ['<div dir="rtl" style="font-family:inherit;">']
        for w in self.warnings:
            h.append(f'<div style="background:#fff3cd;border:1px solid #e0c36a;color:#7a5c00;'
                     f'border-radius:8px;padding:8px 12px;margin:6px 0;">{escape(w)}</div>')
        if self.no_result:
            h.append(f'<p>{escape(self.note or "موردی یافت نشد.")}</p>')
            h.append(f'<p style="color:#666;">{escape(DISCLAIMER)}</p>')
            h.append("</div>")
            return "".join(h)
        if self.short:
            h.append(f'<h3 style="color:#283593;margin:8px 0 4px;">پاسخ کوتاه</h3>'
                     f'<p>{escape(self.short)}</p>')
        if self.conditions:
            h.append('<h3 style="color:#283593;margin:10px 0 4px;">شرایط و استثناهای مهم</h3><ul>')
            for c in self.conditions:
                h.append(f"<li>{escape(c)}</li>")
            h.append("</ul>")
        if self.status_rows:
            h.append('<h3 style="color:#283593;margin:10px 0 4px;">وضعیت شما (ارزیابی خودکار)</h3>')
            color = {"satisfied": "#1b5e20", "not_satisfied": "#b71c1c",
                     "insufficient_info": "#7a5c00", "needs_review": "#8a4b00"}
            for r in self.status_rows:
                c = color.get(r.get("state", ""), "#333")
                line = f'<div style="margin:4px 0;">&#9679; <b>{escape(r["title"])}</b>: ' \
                       f'<span style="color:{c};font-weight:700;">{escape(r["state_fa"])}</span>'
                if r.get("missing"):
                    line += ' - اطلاعات ناقص: ' + escape("، ".join(r["missing"]))
                if r.get("detail"):
                    line += f'<br><span style="color:#555;">{escape(r["detail"])}</span>'
                line += "</div>"
                h.append(line)
        if self.next_steps:
            h.append('<h3 style="color:#283593;margin:10px 0 4px;">اقدام بعدی پیشنهادی</h3><ol>')
            for s in self.next_steps:
                h.append(f"<li>{escape(s)}</li>")
            h.append("</ol>")
        if self.sources:
            h.append('<h3 style="color:#283593;margin:10px 0 4px;">منبع رسمی (متن عینی سند)</h3>')
            for s in self.sources:
                label = f"[{s['ref']}] «{s['doc_title']}» - نسخه {s['version_no']} - {s['status_fa']}"
                if s.get("clause_ref"):
                    label += f" - {s['clause_ref']}"
                if s.get("page_no"):
                    label += f" - صفحه {s['page_no']}"
                url_line = ''
                if s.get("url"):
                    url_line = f'<div style="color:#888;">{escape(s["url"])}</div>'
                h.append(f'<div style="background:#f4f6fb;border:1px solid #d9e0f0;border-radius:8px;'
                         f'padding:8px 10px;margin:6px 0;">'
                         f'<div style="font-weight:700;color:#283593;">{escape(label)}</div>'
                         f'<div style="white-space:pre-wrap;margin-top:4px;">{escape(s["excerpt"])}</div>'
                         f'{url_line}'
                         f'</div>')
        if self.confirmations:
            h.append('<div style="background:#fff8e1;border:1px solid #e6c453;border-radius:8px;'
                     'padding:8px 12px;margin:8px 0;"><b>موارد نیازمند تأیید کارشناس آموزش:</b><ul>')
            for c in self.confirmations:
                h.append(f"<li>{escape(c)}</li>")
            h.append("</ul></div>")
        h.append(f'<p style="color:#777;font-size:0.9em;">{escape(DISCLAIMER)}</p>')
        h.append(f'<p style="color:#999;font-size:0.85em;">موتور تولید پاسخ: {escape(self.provider_name)}</p>')
        h.append("</div>")
        return "".join(h)


# ---------- اسکوپ و اعتبار اسناد ----------

def doc_effective(doc: dict, today: datetime.date) -> bool:
    ef = doc.get("effective_from")
    eu = doc.get("effective_until")
    if ef and str(ef) > today.isoformat():
        return False
    if eu and str(eu) < today.isoformat():
        return False
    return True


def scope_state(doc: dict, student: dict | None) -> tuple[bool, bool, list[str]]:
    """برمی‌گرداند: (تطبیق قطعی، نامشخص، فیلدهای ناقص)"""
    unknown: list[str] = []
    checks: list[bool] = []
    def _add(field_name, doc_val, stu_val):
        if not doc_val:
            return
        if stu_val in (None, ""):
            unknown.append(field_name)
            checks.append(True)  # هنوز قطعی نیست ولی رد هم نمی‌شود
        else:
            checks.append(str(doc_val).strip() == str(stu_val).strip())
    _add("مقطع تحصیلی", doc.get("scope_level"), (student or {}).get("level"))
    _add("رشته تحصیلی", doc.get("scope_major"), (student or {}).get("major"))
    ef, et = doc.get("scope_entry_from"), doc.get("scope_entry_to")
    if ef or et:
        ey = (student or {}).get("entry_year")
        if ey in (None, ""):
            unknown.append("سال ورود")
            checks.append(True)
        else:
            try:
                ey = int(ey)
            except (TypeError, ValueError):
                unknown.append("سال ورود")
                checks.append(True)
            else:
                if ef and ey < int(ef):
                    checks.append(False)
                if et and ey > int(et):
                    checks.append(False)
    if not checks:
        return True, False, []
    if False in checks:
        return False, False, []
    return True, bool(unknown), unknown


def _student_profile(student: dict | None) -> dict:
    if not student:
        return {"flags": {}}
    try:
        passed = json.loads(student.get("passed_courses") or "[]")
    except json.JSONDecodeError:
        passed = []
    try:
        extra = json.loads(student.get("profile_extra") or "{}")
    except json.JSONDecodeError:
        extra = {}
    return {
        "gpa": student.get("gpa"),
        "entry_year": student.get("entry_year"),
        "level": student.get("level"),
        "major": student.get("major"),
        "passed_credits": student.get("passed_credits"),
        "passed_courses": passed,
        "flags": extra if isinstance(extra, dict) else {},
        **{k: v for k, v in extra.items() if isinstance(v, (int, float, bool, str)) and k != "flags"},
    }


def _candidate_docs(conn, user, student, include_retired=False):
    today = datetime.date.today()
    rows = db.q(conn, "SELECT * FROM documents WHERE university_id=? AND status IN ('published','retired')",
                (user["university_id"],))
    current, retired = [], []
    for d in rows:
        match, _unk, _u = scope_state(d, student)
        if not match:
            continue
        if d["status"] == "retired":
            retired.append(d)
        elif doc_effective(d, today):
            current.append(d)
        else:
            retired.append(d)  # منقضی‌شده هم مثل نسخه غیرجاری رفتار می‌شود
    return current, (retired if include_retired else [])


def _chunks_for(conn, doc_ids: list[int]) -> dict[int, dict]:
    if not doc_ids:
        return {}
    marks = ",".join("?" * len(doc_ids))
    rows = db.q(conn, f"SELECT * FROM chunks WHERE document_id IN ({marks})", tuple(doc_ids))
    out = {}
    for r in rows:
        try:
            flags = json.loads(r.get("flags") or "[]")
        except json.JSONDecodeError:
            flags = []
        r = dict(r)
        r["flags"] = flags
        out[r["id"]] = r
    return out


def _make_citation(chunk: dict, doc: dict, idx: int) -> dict:
    try:
        flags = json.loads(doc.get("flags") or "[]")
    except json.JSONDecodeError:
        flags = []
    return {
        "ref": f"C{idx}",
        "chunk_id": chunk["id"],
        "document_id": doc["id"],
        "doc_title": doc["title"],
        "version_no": doc["version_no"],
        "status": doc["status"],
        "status_fa": DOC_STATUS_FA.get(doc["status"], doc["status"]),
        "clause_ref": chunk.get("clause_ref") or "",
        "page_no": chunk.get("page_no"),
        "url": doc.get("url") or "",
        "official": bool(doc.get("is_official")),
        "excerpt": (chunk.get("text") or "").strip()[:600],
        "flags": flags + list(chunk.get("flags") or []),
    }


def _eval_rules(conn, user, student, question: str, cited_doc_ids: set[int]) -> list[ruleengine.RuleResult]:
    rules = db.q(conn, "SELECT * FROM rules WHERE university_id=? AND status='approved'",
                 (user["university_id"],))
    if not rules:
        return []
    q_tokens = set(tokenize(question))
    profile = _student_profile(student)
    out: list[tuple[ruleengine.RuleResult, dict]] = []
    for r in rules:
        try:
            cond = json.loads(r["cond_json"])
            review_fields = json.loads(r.get("review_fields") or "[]")
        except json.JSONDecodeError:
            continue
        # قاعده مرتبط است اگر منبعش در اسناد بازیابی‌شده باشد یا کلیدواژه‌ای از پرسش در عنوان/شرطش باشد
        related = (r["source_document_id"] in cited_doc_ids) or \
                  bool(q_tokens & set(tokenize(r["title"] + " " + json.dumps(cond, ensure_ascii=False))))
        if not related:
            continue
        rec = dict(r)
        rec["cond_json"] = cond
        rec["review_fields"] = review_fields
        res = ruleengine.evaluate(rec, profile)
        if res.status == ruleengine.INSUFFICIENT_INFO:
            res.details.append("برای ارزیابی دقیق، این اطلاعات در پروفایل شما ثبت نشده است.")
        out.append((res, r))
    return out


def _match_process(conn, user, question: str) -> dict | None:
    procs = db.q(conn, "SELECT * FROM processes WHERE university_id=?", (user["university_id"],))
    q_tokens = set(tokenize(question))
    best, best_hits = None, 0
    for p in procs:
        try:
            kws = json.loads(p.get("keywords") or "[]")
        except json.JSONDecodeError:
            kws = []
        hits = sum(1 for kw in kws if set(tokenize(kw)) & q_tokens)
        if hits > best_hits:
            best, best_hits = p, hits
    return best


def _warn_flags(flat_flags: list[str]) -> list[str]:
    msgs = []
    if "injection_suspect" in flat_flags:
        msgs.append("در یکی از اسناد، محتوای مشکوک به «تزریق دستور» شناسایی شد؛ آن متن صرفاً به‌عنوان داده "
                    "نمایش داده می‌شود و به‌عنوان دستور اجرا نمی‌شود.")
    if "ocr_suspect" in flat_flags:
        msgs.append("متن یکی از اسناد احتمالاً خطای OCR دارد (به‌ویژه در ارقام). قبل از اتکا به اعداد، "
                    "به اصل سند مراجعه کنید.")
    return msgs


def build_answer(conn, user, student, question: str, include_retired: bool = False,
                 provider=None) -> Answer:
    """پرسش دانشجو را به پاسخ مستند سه‌لایه تبدیل می‌کند"""
    ans = Answer(question=question)
    settings = db.get_settings(conn)
    q = (question or "").strip()[:1000]
    if not q:
        ans.no_result = True
        ans.note = "پرسش خالی است."
        return ans

    current, retired = _candidate_docs(conn, user, student, include_retired)
    all_docs = current + retired
    if not all_docs:
        ans.no_result = True
        ans.note = ("در حال حاضر هیچ سند منتشرشده‌ای که به شما اعمال شود در سامانه ثبت نشده است. "
                    "لطفاً از طریق «درخواست از کارشناس» موضوع را پیگیری کنید.")
        return ans

    docs_by_id = {d["id"]: d for d in all_docs}
    chunks = _chunks_for(conn, [d["id"] for d in all_docs])
    index = BM25([(cid, c["text"]) for cid, c in chunks.items()])
    hits = index.search(q, k=int(settings.get("search_max_chunks", "6")) * 3)

    strong = [(cid, s) for cid, s in hits if s >= STRONG_SCORE]
    current_ids = [d["id"] for d in current]
    retired_ids = [d["id"] for d in retired]
    strong_current = [(cid, s) for cid, s in strong if chunks[cid]["document_id"] in current_ids]
    strong_retired = [(cid, s) for cid, s in strong if chunks[cid]["document_id"] in retired_ids]

    if not strong_current and not strong_retired:
        ans.no_result = True
        ans.note = ("در اسناد فعلی سامانه مطلب مرتبطی با این پرسش یافت نشد؛ بنابراین هیچ پاسخی که به سند "
                    "ارجاع داشته باشد ارائه نمی‌شود. می‌توانید موضوع را از کارشناس آموزش بپرسید.")
        if not include_retired and strong:
            ans.note += (" نسخه‌های ملغی هم بررسی شدند اما قابل استناد نیستند؛ اگر پرسش شما درباره "
                         "مقررات قدیمی است، گزینه «نمایش نسخه‌های ملغی» را فعال کنید.")
        return ans

    max_chunks = int(settings.get("search_max_chunks", "6"))
    chosen = strong_current[:max_chunks]
    used_retired = strong_retired[:2]

    # ساخت ارجاع‌ها فقط از تکه‌های واقعی
    citations: list[dict] = []
    for i, (cid, _score) in enumerate(chosen + used_retired, start=1):
        ch = chunks[cid]
        doc = docs_by_id[ch["document_id"]]
        citations.append(_make_citation(ch, doc, i))
    ans.sources = citations

    # هشدار داده نمونه / پرچم‌ها
    if any(not c["official"] for c in citations):
        ans.warnings.append(SAMPLE_BANNER)
    flat_flags = [f for c in citations for f in c["flags"]]
    # پرچم‌های امنیتی در سطح همه تکه‌های سندهای استنادشده (نه فقط تکه‌های نمایش‌داده‌شده)
    cited_doc_ids = {c["document_id"] for c in citations}
    for cid, ch in chunks.items():
        if ch["document_id"] in cited_doc_ids:
            flat_flags.extend(ch.get("flags") or [])
    ans.warnings.extend(_warn_flags(flat_flags))
    if used_retired:
        ans.warnings.append("در این پاسخ به نسخه ملغی/منقضی‌شده سند هم استناد شده است؛ این نسخه دیگر قابل استناد نیست "
                            "و صرفاً برای مقایسه نمایش داده شده است.")
        ans.confirmations.append("نسخه ملغی نمایش داده شده است؛ در صورت نیاز به حکم جاری با کارشناس آموزش هماهنگ کنید.")

    # تشخیص مغایرت احتمالی بین اسناد مستقلِ منتشرشده
    doc_ids_strong = {chunks[cid]["document_id"] for cid, _s in chosen}
    if len(doc_ids_strong) >= 2:
        titles = [docs_by_id[i]["title"] for i in doc_ids_strong]
        ans.confirmations.append(
            "مغایرت احتمالی: چند سند منتشرشده به این موضوع مربوط‌اند («" + "» و «".join(titles[:2]) +
            "»). تعیین سند حاکم با کارشناس آموزش است.")

    # نامشخص بودن اسکوپ به دلیل کمبود اطلاعات پروفایل
    unknown_fields: list[str] = []
    for d in current:
        _m, unk, fields = scope_state(d, student)
        if unk:
            unknown_fields.extend(fields)
    if unknown_fields:
        uniq = list(dict.fromkeys(unknown_fields))
        ans.confirmations.append(
            "برخی اسناد بر اساس «" + "، ".join(uniq) + "» شما محدود می‌شوند و این اطلاعات در پروفایل ثبت نشده است؛ "
            "تا تکمیل آن، هیچ نتیجه‌ای قطعی تلقی نمی‌شود.")

    # لایه ۲: توضیح (مدل زبانی اختیاری یا قالبی)
    provider = provider or make_provider(settings)
    brief = ""
    if student:
        brief = f"مقطع {student.get('level') or 'نامشخص'}، رشته {student.get('major') or 'نامشخص'}"
        if student.get("entry_year"):
            brief += f"، ورودی {student.get('entry_year')}"
    llm_out = None
    try:
        llm_out = provider.complete(q, citations,
                                    student_brief=brief,
                                    send_profile=(settings.get("send_profile_to_llm", "minimal") != "none"))
    except Exception:
        llm_out = None
    if llm_out:
        ans.provider_name = llm_out.provider_name
        # اعتبارسنجی ارجاع‌های مدل: فقط ارجاع به تکه‌های واقعی مجاز است
        valid_refs = {c["ref"] for c in citations}
        bad = [r for r in llm_out.cited_refs if r not in valid_refs]
        if bad:
            ans.warnings.append("ارجاع نامعتبر مدل زبانی به اسناد («" + "، ".join(bad) +
                                "») حذف شد؛ ارجاع فقط به منابع واقعی مجاز است.")
        if not llm_out.cited_refs:
            ans.warnings.append("پاسخ مدل زبانی بدون ارجاع بود؛ منابع بازیابی‌شده به‌صورت خودکار پیوست شد.")
        ans.short = llm_out.short
        ans.conditions = llm_out.conditions
    else:
        out = TemplateProvider().complete(q, citations)
        if out:
            ans.short, ans.conditions = out.short, out.conditions

    # لایه ۳: وضعیت شخصی با موتور قواعد قطعی
    rule_results = _eval_rules(conn, user, student, q, doc_ids_strong)
    for res, rule_row in rule_results:
        row = {"title": res.title, "state": res.status, "state_fa": res.status_fa,
               "missing": res.missing, "detail": ""}
        try:
            msgs = json.loads(rule_row.get("messages") or "{}")
        except json.JSONDecodeError:
            msgs = {}
        row["detail"] = msgs.get(res.status, "")
        if res.status == ruleengine.INSUFFICIENT_INFO:
            row["detail"] = row["detail"] or "اطلاعات لازم ارزیابی کامل نیست."
        ans.status_rows.append(row)
        if res.status == ruleengine.NEEDS_REVIEW:
            ans.confirmations.append(f"نتیجه قاعده «{res.title}» نیازمند تأیید کارشناس آموزش است.")

    # اقدام بعدی: فرایند اداری منطبق
    proc = _match_process(conn, user, q)
    if proc:
        try:
            steps = json.loads(proc["steps"])
        except json.JSONDecodeError:
            steps = []
        ans.next_steps = [str(s) for s in steps[:4]]
        if proc.get("target_system"):
            ans.next_steps.append(f"ثبت نهایی فقط در «{proc['target_system']}» انجام می‌شود؛ "
                                  "این دستیار هرگز موفقیت ثبت را اعلام نمی‌کند.")
    else:
        ans.next_steps.append("در صورت ابهام، موضوع را از طریق «درخواست از کارشناس» پیگیری کنید.")

    return ans


def ask(conn, user, question: str, session_id: int | None = None,
        include_retired: bool = False, provider=None) -> Answer:
    """نقطه ورود گفتگو: کنترل مجوز، محدودسازی نرخ، ذخیره تاریخچه"""
    from .services import require, get_student_for_user  # جلوگیری از چرخه واردات
    require(user, "chat")
    settings = db.get_settings(conn)
    limit = int(settings.get("rate_limit_chat_per_hour", "20") or 20)
    if not RATE_LIMITER.allow(f"chat:{user['id']}", limit):
        ans = Answer(question=question, no_result=True)
        ans.note = f"تعداد پرسش‌های شما از حد مجاز ({limit} در ساعت) گذشته است. لطفاً کمی بعد تلاش کنید."
        ans.provider_name = "محدودساز نرخ"
        return ans

    student = get_student_for_user(conn, user)
    ans = build_answer(conn, user, student, question, include_retired, provider)

    if session_id is None:
        session_id = db.ex(conn, "INSERT INTO chat_sessions(user_id, title) VALUES(?,?)",
                           (user["id"], question[:60]))
    ans.session_id = session_id
    db.ex(conn, "INSERT INTO chat_messages(session_id, role, content) VALUES(?,?,?)",
          (session_id, "user", question))
    meta = json.dumps({
        "sources": ans.sources,
        "warnings": ans.warnings,
        "confirmations": ans.confirmations,
        "provider": ans.provider_name,
        "status_rows": ans.status_rows,
    }, ensure_ascii=False)
    ans.message_id = db.ex(conn, "INSERT INTO chat_messages(session_id, role, content, meta) VALUES(?,?,?,?)",
                           (session_id, "assistant", ans.short or ans.note, meta))
    return ans
