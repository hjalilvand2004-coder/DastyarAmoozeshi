# -*- coding: utf-8 -*-
"""سرویس احراز هویت: ورود با رمز، ورود یکپارچه SSO/OIDC (قابل تعویض)، پروفایل من

- ورود محلی: POST /auth/login (PBKDF2)
- SSO: ارائه‌دهنده دمو (بدون رمز، برای نمایش) + هر IdP سازگار با OIDC (Keycloak و ...)
- راه‌اندازی OIDC فقط با پیکربندی (issuer/client_id/...) فعال می‌شود؛
  تا آن زمان «هیچ ادعایی درباره هویت رسمی دانشگاه» انجام نمی‌شود.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app import db
from app.api.deps import get_conn, get_current_user, public_user
from app.security import make_token
from app.services import ROLE_FA, get_student_for_user, login as svc_login

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------- تیکت‌های یک‌بار مصرف SSO (فقط حافظه، زمان‌دار) ----------
_TICKETS: dict[str, dict] = {}
_TICKET_LOCK = threading.Lock()

DEMO_IDENTITIES = [
    {"id": "student", "label": "دانشجوی نمونه (علی محمدی)"},
    {"id": "student2", "label": "دانشجو با پروفایل ناقص (سارا)"},
    {"id": "expert", "label": "کارشناس آموزش"},
    {"id": "approver", "label": "تأییدکننده آیین‌نامه"},
    {"id": "admin", "label": "مدیر سیستم"},
]


def _new_ticket(value: str, ttl_s: int = 180) -> str:
    t = secrets.token_urlsafe(24)
    with _TICKET_LOCK:
        if len(_TICKETS) > 500:  # پاک‌سازی قدیمی‌ها
            now = time.time()
            for k in [k for k, v in _TICKETS.items() if v["exp"] < now]:
                _TICKETS.pop(k, None)
        _TICKETS[t] = {"value": value, "exp": time.time() + ttl_s}
    return t


def _consume_ticket(t: str) -> str | None:
    with _TICKET_LOCK:
        rec = _TICKETS.pop(t, None)
    if not rec or rec["exp"] < time.time():
        return None
    return rec["value"]


# ---------- ورود محلی ----------

class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login", summary="ورود با نام کاربری و رمز عبور")
def login(body: LoginIn, conn=Depends(get_conn)):
    user = svc_login(conn, body.username.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور نادرست است")
    db.audit(conn, user, "login", "ورود با رمز عبور")
    token = make_token({"uid": user["id"], "username": user["username"], "role": user["role"]})
    return {"token": token, "user": public_user(user)}


@router.get("/me", summary="پروفایل کاربر جاری")
def me(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    student = get_student_for_user(conn, user)
    return {"user": public_user(user), "student": student}


# ---------- SSO ----------

def _sso_settings(conn) -> dict:
    st = db.get_settings(conn)
    return {
        "issuer": os.environ.get("D360_OIDC_ISSUER") or st.get("sso_oidc_issuer", ""),
        "client_id": os.environ.get("D360_OIDC_CLIENT_ID") or st.get("sso_oidc_client_id", ""),
        "client_secret": os.environ.get("D360_OIDC_CLIENT_SECRET") or st.get("sso_oidc_client_secret", ""),
        "scope": os.environ.get("D360_OIDC_SCOPE") or st.get("sso_oidc_scope", "openid profile"),
        "default_role": os.environ.get("D360_SSO_DEFAULT_ROLE", "student"),
    }


@router.get("/sso/providers", summary="ارائه‌دهنده‌های ورود یکپارچه")
def sso_providers(conn=Depends(get_conn)):
    cfg = _sso_settings(conn)
    providers = [{
        "id": "demo", "kind": "demo", "configured": True,
        "name": "ورود آزمایشی بدون رمز (نمونه)",
        "identities": DEMO_IDENTITIES,
    }]
    if cfg["issuer"]:
        providers.append({
            "id": "university", "kind": "oidc", "configured": True,
            "name": "ورود یکپارچه دانشگاه (SSO)",
        })
    return {"providers": providers}


@router.get("/sso/{provider}/start", summary="شروع ورود SSO")
def sso_start(provider: str, request: Request, as_: str | None = None, conn=Depends(get_conn)):
    cfg = _sso_settings(conn)
    if provider == "demo":
        username = (as_ or "student").strip()
        allowed = {"student", "student2", "expert", "content", "approver", "admin"}
        if username not in allowed:
            raise HTTPException(status_code=400, detail="هویت آزمایشی نامعتبر است")
        t = _new_ticket(f"demo:{username}")
        return {"kind": "demo", "ticket": t,
                "redirect": f"/sso/callback?ticket={urllib.parse.quote(t)}&provider=demo"}
    if provider == "university" and cfg["issuer"]:
        disc = _oidc_discovery(cfg["issuer"])
        base = str(request.base_url).rstrip("/")
        redirect_uri = f"{base}/api/v1/auth/sso/university/callback"
        state = _new_ticket("oidc-state", ttl_s=600)
        q = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": redirect_uri,
            "scope": cfg["scope"] or "openid profile",
            "state": state,
        })
        return {"kind": "oidc", "redirect": f"{disc['authorization_endpoint']}?{q}"}
    raise HTTPException(status_code=404, detail="ارائه‌دهنده SSO یافت نشد یا پیکربندی نشده است")


class ExchangeIn(BaseModel):
    ticket: str


@router.post("/sso/{provider}/exchange", summary="تبدیل تیکت SSO به توکن (فقط ارائه‌دهنده دمو)")
def sso_exchange(provider: str, body: ExchangeIn, conn=Depends(get_conn)):
    if provider != "demo":
        raise HTTPException(status_code=400, detail="این ارائه‌دهنده از exchange پشتیبانی نمی‌کند")
    username = _consume_ticket(body.ticket)
    if not username or not username.startswith("demo:"):
        raise HTTPException(status_code=400, detail="تیکت نامعتبر، منقضی یا مصرف‌شده است")
    user = _issue_for_username(conn, username.split(":", 1)[1], role_default="student")
    db.audit(conn, user, "login", "ورود SSO آزمایشی (بدون رمز)")
    token = make_token({"uid": user["id"], "username": user["username"], "role": user["role"]})
    return {"token": token, "user": public_user(user)}


@router.get("/sso/{provider}/callback", summary="بازگشت OIDC (مرورگر)", include_in_schema=True)
def sso_callback(provider: str, code: str | None = None, state: str | None = None,
                 request: Request = None, conn=Depends(get_conn)):
    """جریان کد OIDC: تبادل کد → دریافت هویت → صدور توکن برنامه → هدایت به فرانت"""
    cfg = _sso_settings(conn)
    if provider != "university" or not cfg["issuer"]:
        raise HTTPException(status_code=404, detail="ارائه‌دهنده OIDC پیکربندی نشده است")
    if not code or not state:
        raise HTTPException(status_code=400, detail="پارامترهای callback ناقص است")
    if not _consume_ticket(state):
        raise HTTPException(status_code=400, detail="state نامعتبر یا منقضی است")
    disc = _oidc_discovery(cfg["issuer"])
    base = str(request.base_url).rstrip("/") if request else ""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{base}/api/v1/auth/sso/university/callback",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }).encode()
    req = urllib.request.Request(disc["token_endpoint"], data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tok = _json_loads(resp.read())
    except Exception:
        raise HTTPException(status_code=502, detail="تبادل توکن با سرور SSO ناموفق بود")
    access = tok.get("access_token") or ""
    if not access:
        raise HTTPException(status_code=502, detail="توکن دسترسی دریافت نشد")
    req2 = urllib.request.Request(disc.get("userinfo_endpoint") or
                                  (cfg["issuer"].rstrip("/") + "/userinfo"),
                                  headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req2, timeout=15) as resp:
            info = _json_loads(resp.read())
    except Exception:
        raise HTTPException(status_code=502, detail="دریافت اطلاعات هویت ناموفق بود")
    username = (info.get("preferred_username") or info.get("email") or "").strip()
    if not username:
        raise HTTPException(status_code=502, detail="شناسه کاربر در پاسخ SSO نبود")
    role = _map_role(info, cfg["default_role"])
    user = _issue_for_username(conn, username, role_default=role, full_name=info.get("name") or "")
    db.audit(conn, user, "login", f"ورود یکپارچه ({cfg['issuer']})")
    token = make_token({"uid": user["id"], "username": user["username"], "role": user["role"]})
    dest = f"/sso/callback?token={urllib.parse.quote(token)}&sso=1"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=dest, status_code=302)


def _map_role(info: dict, default_role: str) -> str:
    """نگاشت نقش‌های IdP به نقش‌های برنامه (قابل سفارشی‌سازی)"""
    roles = info.get("roles") or []
    realm = (info.get("realm_access") or {}).get("roles") or []
    all_roles = {str(r).lower() for r in list(roles) + list(realm)}
    if any("system_admin" in r or "sysadmin" in r for r in all_roles):
        return "system_admin"
    if any("approver" in r for r in all_roles):
        return "approver"
    if any("content" in r for r in all_roles):
        return "content_admin"
    if any("expert" in r for r in all_roles):
        return "expert"
    return default_role if default_role in ROLE_FA else "student"


def _issue_for_username(conn, username: str, role_default: str = "student",
                        full_name: str = "") -> dict:
    """ورود یا ایجاد خودکار کاربر SSO (بدون رمز - auth_type sso)"""
    from app.security import hash_password
    username = username.strip()
    user = db.q1(conn, "SELECT * FROM users WHERE username=?", (username,))
    if user:
        if not user["active"]:
            raise HTTPException(status_code=403, detail="حساب شما غیرفعال است")
        return dict(user)
    uni = db.q1(conn, "SELECT id FROM universities ORDER BY id LIMIT 1")
    if not uni:
        raise HTTPException(status_code=503, detail="هنوز دانشگاهی در سامانه ثبت نشده است")
    role = role_default if role_default in ROLE_FA else "student"
    uid = db.ex(conn, "INSERT INTO users(university_id, username, password_hash, full_name, role) "
                      "VALUES(?,?,?,?,?)",
                (uni["id"], username, hash_password(secrets.token_urlsafe(24)), full_name or username, role))
    db.audit(conn, {"id": uid, "university_id": uni["id"]}, "sso_autoprovision",
             f"ایجاد خودکار کاربر {username} با نقش {role}")
    return dict(db.q1(conn, "SELECT * FROM users WHERE id=?", (uid,)))


def _oidc_discovery(issuer: str) -> dict:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return _json_loads(resp.read())
    except Exception:
        raise HTTPException(status_code=502, detail="کشف پیکربندی OIDC ناموفق بود")


def _json_loads(raw: bytes) -> dict:
    import json
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
