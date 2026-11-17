# -*- coding: utf-8 -*-
"""امنیت و کنترل کیفیت هوش مصنوعی

- ضدعفونی‌سازی متن اسناد (تشخیص تلاش برای تزریق دستور به مدل)
- تشخیص احتمالی خطای OCR (به‌ویژه خطای ارقام)
- هش رمز عبور (PBKDF2)
- محدودسازی نرخ (Rate limiting) در حافظه
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json as _json
import re
import secrets
import time
import unicodedata
from collections import defaultdict, deque

# ---------- توکن JWT (HS256 - بدون وابستگی خارجی) ----------

def make_token(payload: dict, expires_minutes: int = 720) -> str:
    """ساخت توکن امضاشده HS256 برای احراز هویت API"""
    from .config import secret_key
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    body = {**payload, "iat": now, "exp": now + expires_minutes * 60}

    def b64(d: bytes) -> str:
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode("ascii")

    h = b64(_json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = b64(_json.dumps(body, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret_key().encode("utf-8"), f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
    return f"{h}.{p}.{b64(sig)}"


def parse_token(token: str) -> dict | None:
    """اعتبارسنجی توکن؛ نامعتبر/منقضی → None"""
    from .config import secret_key
    try:
        h, p, s = token.split(".")
        expected = hmac.new(secret_key().encode("utf-8"), f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
        got = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        if not hmac.compare_digest(expected, got):
            return None
        body = _json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        if int(body.get("exp", 0)) < time.time():
            return None
        return body
    except Exception:
        return None


# ---------- اعتبارسنجی توکن‌های دریافتی از پرتال SSO (بدون وابستگی خارجی) ----------

_B64 = base64.urlsafe_b64decode  # میان‌بر

# پیشوند DER ساختار DigestInfo برای SHA-256 در امضای PKCS#1 v1.5
_SHA256_DIGESTINFO = bytes.fromhex("3031300d060960864801650304020105000420")


def _jwk_b64int(v: str) -> int:
    return int.from_bytes(_B64(v + "=" * (-len(v) % 4)), "big")


def verify_jwt_rs256(token: str, jwks: dict) -> dict | None:
    """اعتبارسنجی JWT امضاشده با RS256 بر اساس کلیدهای عمومی IdP (jwks_uri)"""
    try:
        h, p, s = token.split(".")
        header = _json.loads(_B64(h + "=" * (-len(h) % 4)))
        if str(header.get("alg", "")).upper() != "RS256":
            return None
        kid = header.get("kid")
        key = None
        for k in jwks.get("keys", []):
            if k.get("kty") == "RSA" and (kid is None or k.get("kid") == kid):
                if k.get("alg") and str(k["alg"]).upper() != "RS256":
                    continue
                key = k
                break
        if not key or "n" not in key or "e" not in key:
            return None
        sig = _B64(s + "=" * (-len(s) % 4))
        n, e = _jwk_b64int(key["n"]), _jwk_b64int(key["e"])
        klen = (n.bit_length() + 7) // 8
        m = pow(int.from_bytes(sig, "big"), e, n)
        padded = m.to_bytes(klen, "big")
        digest = hashlib.sha256(f"{h}.{p}".encode("ascii")).digest()
        expected = b"\x00\x01" + b"\xff" * (klen - len(digest) - len(_SHA256_DIGESTINFO) - 3) + \
            b"\x00" + _SHA256_DIGESTINFO + digest
        if not hmac.compare_digest(padded, expected):
            return None
        body = _json.loads(_B64(p + "=" * (-len(p) % 4)))
        if int(body.get("exp", 0)) < time.time():
            return None
        return body
    except Exception:
        return None


def verify_jwt_hs256(token: str, secret: str) -> dict | None:
    """اعتبارسنجی JWT امضاشده با رمز مشترک HS256 (توکن صادرشدهٔ پرتال سازمانی)"""
    try:
        h, p, s = token.split(".")
        header = _json.loads(_B64(h + "=" * (-len(h) % 4)))
        if str(header.get("alg", "")).upper() != "HS256":
            return None
        expected = hmac.new(secret.encode("utf-8"), f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
        got = _B64(s + "=" * (-len(s) % 4))
        if not hmac.compare_digest(expected, got):
            return None
        body = _json.loads(_B64(p + "=" * (-len(p) % 4)))
        if int(body.get("exp", 0)) < time.time():
            return None
        return body
    except Exception:
        return None

# الگوهای مشکوک به تزریق دستور (انگلیسی + فارسی)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"you\s+are\s+now\s+(a|an)",
    r"system\s*prompt",
    r"new\s+instructions?\s*:",
    r"developer\s+mode",
    r"دستور(های)?\s*قبلی\s*را\s*نادیده",
    r"نادیده\s*بگیر",
    r"سیستم\s*را\s*نادیده",
    r"نقش\s*خود\s*را\s*تغییر",
    r"تو\s*اکنون\s*یک",
    r"دستورالعمل\s*جدید",
    r"جای\s*دستورالعمل",
]

_RE_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

_RE_MIXED_DIGITS = re.compile(r"[0-9][۰-۹٠-٩]|[\u06F0-\u06F9٠-٩][0-9]")


def normalize_persian(text: str) -> str:
    """نرمال‌سازی متن فارسی برای جست‌وجو (نمایش اصلی سند دست‌نخورده می‌ماند)"""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    for src, dst in [("ي", "ی"), ("ك", "ک"), ("ة", "ه"), ("أ", "ا"), ("إ", "ا"),
                     ("ٱ", "ا"), ("ى", "ی"), ("ؤ", "و"), ("\u200c", ""), ("\u200f", ""),
                     ("\u200e", ""), ("\u00a0", " ")]:
        t = t.replace(src, dst)
    t = t.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def ocr_suspect(text: str) -> bool:
    """تشخیص احتمال خطای OCR: ارقام مخلوط فارسی/لاتین یا نسبت بالای حروف لاتین در متن فارسی"""
    if not text:
        return False
    if _RE_MIXED_DIGITS.search(text):
        return True
    fa = len(re.findall(r"[\u0600-\u06FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if fa > 40 and latin > 8 and latin / (fa + latin) > 0.10:
        return True
    # کلماتی مثل «.0 12» یا «o۱۲»
    if re.search(r"\b[0-9]{1,2}[.,][A-Za-z]\b", text):
        return True
    return False


def sanitize_document_text(text: str) -> tuple[str, list[str]]:
    """متن سند را همراه فهرست پرچم‌های امنیتی برمی‌گرداند (متن اصلی حذف نمی‌شود؛ فقط پرچم می‌خورد)"""
    flags: list[str] = []
    if not text:
        return text or "", flags
    for rx in _RE_INJECTION:
        if rx.search(text):
            flags.append("injection_suspect")
            break
    if ocr_suspect(text):
        flags.append("ocr_suspect")
    return text, flags


# ---------- رمز عبور ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, salt, digest = stored.split("$")
    except (ValueError, AttributeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return hmac.compare_digest(dk.hex(), digest)


# ---------- محدودسازی نرخ ----------

class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_s: int = 3600) -> bool:
        now = time.time()
        dq = self._hits[key]
        while dq and now - dq[0] > window_s:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


RATE_LIMITER = RateLimiter()
