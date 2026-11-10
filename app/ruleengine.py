# -*- coding: utf-8 -*-
"""موتور قواعد قطعی (Deterministic Rule Engine)

- کاملاً از مدل زبانی جداست.
- هر قاعده: شرط JSON + پیام هر وضعیت + فیلدهای نیازمند تأیید رسمی.
- خروجی چهار حالته: satisfied / not_satisfied / insufficient_info / needs_review
- هیچ قاعده‌ای بدون تأیید انسانی فعال نمی‌شود (سرویس‌ها بررسی می‌کنند).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SATISFIED = "satisfied"
NOT_SATISFIED = "not_satisfied"
INSUFFICIENT_INFO = "insufficient_info"
NEEDS_REVIEW = "needs_review"

STATE_FA = {
    SATISFIED: "برقرار است",
    NOT_SATISFIED: "برقرار نیست",
    INSUFFICIENT_INFO: "اطلاعات ناکافی",
    NEEDS_REVIEW: "نیازمند بررسی کارشناس آموزش",
}

OPERATORS = {">=", "<=", ">", "<", "==", "!=", "in", "not_in", "contains"}


@dataclass
class RuleResult:
    rule_id: int | None
    title: str
    status: str
    missing: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    source_document_id: int | None = None
    source_clause: str = ""

    @property
    def status_fa(self) -> str:
        return STATE_FA.get(self.status, self.status)


def _to_number(v):
    if isinstance(v, (int, float)):
        return v
    try:
        s = str(v).strip().replace(",", "")
        f = float(s)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return v


def _compare(actual, op: str, expected) -> bool | None:
    """None یعنی مقدار واقعی نامشخص/نبود"""
    if actual is None:
        return None
    if op == "==":
        a, e = _to_number(actual), _to_number(expected)
        if not isinstance(a, (int, float)) or not isinstance(e, (int, float)):
            return str(actual).strip() == str(expected).strip()
        return a == e
    if op == "!=":
        r = _compare(actual, "==", expected)
        return (not r) if r is not None else None
    if op in (">=", ">", "<=", "<"):
        a, e = _to_number(actual), _to_number(expected)
        if not isinstance(a, (int, float)) or not isinstance(e, (int, float)):
            return None
        if op == ">=":
            return a >= e
        if op == ">":
            return a > e
        if op == "<=":
            return a <= e
        return a < e
    if op == "in":
        return str(actual).strip() in [str(x).strip() for x in (expected or [])]
    if op == "not_in":
        r = _compare(actual, "in", expected)
        return (not r) if r is not None else None
    if op == "contains":
        return str(expected).strip() in str(actual)
    raise ValueError(f"عملگر ناشناخته: {op}")


def _eval_node(node, profile: dict, missing: list[str]) -> bool | None:
    """ارزیابی سه‌حالته: True / False / None (نامشخص)"""
    if node is None:
        raise ValueError("شرط قاعده خالی است")
    if "all" in node:
        vals = [_eval_node(ch, profile, missing) for ch in node["all"]]
        if any(v is False for v in vals):
            return False
        if any(v is None for v in vals):
            return None
        return True
    if "any" in node:
        vals = [_eval_node(ch, profile, missing) for ch in node["any"]]
        if any(v is True for v in vals):
            return True
        if any(v is None for v in vals):
            return None
        return False
    if "attr" in node:
        attr = node["attr"]
        op = node.get("op", "==")
        if op not in OPERATORS:
            raise ValueError(f"عملگر ناشناخته: {op}")
        actual = profile.get(attr)
        if actual is None:
            if attr not in missing:
                missing.append(attr)
            return None
        return _compare(actual, op, node.get("value"))
    raise ValueError("ساختار شرط نامعتبر است")


def extract_inputs(cond: dict) -> list[str]:
    """فهرست ویژگی‌های موردنیاز قاعده"""
    out: list[str] = []
    def walk(n):
        if not isinstance(n, dict):
            return
        if "attr" in n:
            if n["attr"] not in out:
                out.append(n["attr"])
        for key in ("all", "any"):
            for ch in n.get(key, []) or []:
                walk(ch)
    walk(cond)
    return out


def evaluate(rule: dict, profile: dict) -> RuleResult:
    """قاعده را با پروفایل دانشجو ارزیابی می‌کند (خروجی چهار حالته)"""
    cond = rule.get("cond_json") or rule.get("cond")
    if isinstance(cond, str):
        import json
        cond = json.loads(cond)
    missing: list[str] = []
    outcome = _eval_node(cond, profile or {}, missing)

    status: str
    if outcome is True:
        status = SATISFIED
    elif outcome is False:
        status = NOT_SATISFIED
    else:
        status = INSUFFICIENT_INFO

    # اگر قاعده فیلدی را «نیازمند تأیید رسمی» می‌داند و در پروفایل تأیید نشده،
    # حتی در صورت برقراری شرط هم نباید تصمیم قطعی داده شود.
    review_fields = rule.get("review_fields") or []
    if isinstance(review_fields, str):
        import json
        review_fields = json.loads(review_fields)
    flags = (profile or {}).get("flags") or {}
    unverified = [f for f in review_fields if not flags.get(f)]
    if status == SATISFIED and unverified:
        status = NEEDS_REVIEW

    return RuleResult(
        rule_id=rule.get("id"),
        title=rule.get("title", ""),
        status=status,
        missing=missing,
        details=[],
        source_document_id=rule.get("source_document_id"),
        source_clause=rule.get("source_clause", ""),
    )
