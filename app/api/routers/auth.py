# -*- coding: utf-8 -*-
"""سرویس احراز هویت: ورود با رمز، ورود یکپارچه SSO/OIDC (پرتال سازمانی)، پروفایل من

- ورود محلی: POST /auth/login (PBKDF2)
- SSO: پرتال ورود یکپارچه سازمانی (OIDC) + ارائه‌دهنده دمو (بدون رمز، برای نمایش)
  * نقطه ورود ثابت برای ثبت در پرتال SSO:  GET /api/v1/auth/sso/university/entry
    - بدون پارامتر → شروع جریان OIDC (اگر نشست پرتال فعال باشد، بدون رمز کامل می‌شود)
    - code/state  → تکمیل جریان کد OIDC (با PKCE S256)
    - token/jwt   → توکن امضاشدهٔ پرتال (RS256 با jwks یا HS256 با رمز مشترک)
  * راه‌اندازی فقط با پیکربندی (issuer/client_id/...) فعال می‌شود؛ تا آن زمان
    «هیچ ادعایی درباره هویت رسمی دانشگاه» انجام نمی‌شود.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import config as _config
from app import db
from app.api.deps import get_conn, get_current_user, public_user
from app.security import make_token, verify_jwt_hs256, verify_jwt_rs256
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


def _new_ticket(value: str, ttl_s: int = 600) -> str:
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
        # آدرس عمومی سامانه (مبنای redirect_uri): متغیر محیطی > تنظیم مدیر > پیش‌فرض استقرار
        "base": (os.environ.get("D360_PUBLIC_BASE_URL")
                 or (st.get("public_base_url") or "").rstrip("/")
                 or _config.public_base_url()),
        # رمز مشترک اختیاری برای توکن‌های HS256 صادرشده از پرتال سازمانی
        "hub_secret": os.environ.get("D360_SSO_HUB_SECRET") or st.get("sso_hub_secret", ""),
        # کلید سامانه در پرتال (مبنای نگاشت نقش‌ها مثل amoozeshyar.admin)
        "app_key": os.environ.get("D360_SSO_APP_KEY") or st.get("sso_app_key", _config.DEFAULT_SSO_APP_KEY),
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
            "name": "ورود یکپارچه سازمانی (پرتال SSO)",
            "entry_url": f"{cfg['base']}/api/v1/auth/sso/university/entry",
        })
    return {"providers": providers}


# ---------- PKCE (S256) برای کلاینت عمومی ----------

def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _state_bundle(verifier: str) -> str:
    return json.dumps({"verifier": verifier}, separators=(",", ":"))


# ---------- کش کلیدهای عمومی IdP (jwks_uri) ----------

_JWKS_CACHE: dict[str, tuple[float, dict]] = {}
_JWKS_LOCK = threading.Lock()


def _fetch_jwks(disc: dict) -> dict:
    url = disc.get("jwks_uri") or (disc["issuer"].rstrip("/") + "/protocol/openid-connect/certs")
    with _JWKS_LOCK:
        cached = _JWKS_CACHE.get(url)
        if cached and time.time() - cached[0] < 600:
            return cached[1]
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = _json_loads(resp.read())
    with _JWKS_LOCK:
        _JWKS_CACHE[url] = (time.time(), data)
    return data


# ---------- هدایت‌های استاندارد به فرانت ----------

def _sso_done(token: str) -> RedirectResponse:
    dest = f"/sso/callback?token={urllib.parse.quote(token)}&sso=1"
    return RedirectResponse(url=dest, status_code=302)


def _sso_fail(msg: str) -> RedirectResponse:
    return RedirectResponse(url=f"/sso/callback?sso_error={urllib.parse.quote(msg)}", status_code=302)


@router.get("/sso/{provider}/start", summary="شروع ورود SSO")
def sso_start(provider: str, request: Request, as_: str | None = None, conn=Depends(get_conn)):
    cfg = _sso_settings(conn)
    if provider == "demo":
        username = (as_ or "student").strip()
        allowed = {"student", "student2", "expert", "content", "approver", "admin"}
        if username not in allowed:
            raise HTTPException(status_code=400, detail="هویت آزمایشی نامعتبر است")
        t = _new_ticket(f"demo:{username}", ttl_s=180)
        return {"kind": "demo", "ticket": t,
                "redirect": f"/sso/callback?ticket={urllib.parse.quote(t)}&provider=demo"}
    if provider == "university" and cfg["issuer"]:
        disc = _oidc_discovery(cfg["issuer"])
        redirect_uri = f"{cfg['base']}/api/v1/auth/sso/university/callback"
        verifier, challenge = _pkce_pair()
        state = _new_ticket(_state_bundle(verifier))
        q = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": redirect_uri,
            "scope": cfg["scope"] or "openid profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
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


# ---------- نقطه ورود یکپارچه (ثبت‌شده به‌عنوان «آدرس ورود» در پرتال SSO) ----------

@router.get("/sso/university/entry",
            summary="نقطه ورود یکپارچه سامانه (این آدرس در پرتال SSO ثبت می‌شود)")
def sso_entry(request: Request, conn=Depends(get_conn), code: str | None = None,
              state: str | None = None, token: str | None = None, jwt: str | None = None):
    """نقطه شروع جریان ورود یکپارچه از پرتال سازمانی:
    - بدون پارامتر: هدایت به صفحه ورود پرتال SSO (با نشست فعال پرتال، بدون رمز کامل می‌شود)
    - code (+state): تکمیل جریان کد OIDC
    - token یا jwt: توکن امضاشدهٔ پرتال (RS256 با jwks یا HS256 با رمز مشترک)
    خروجی همه حالت‌ها: هدایت مرورگر به فرانت با توکن برنامه
    """
    cfg = _sso_settings(conn)
    if not cfg["issuer"]:
        raise HTTPException(status_code=404, detail="پرتال SSO پیکربندی نشده است")

    raw = token or jwt
    if raw and not code:
        info = None
        try:
            disc = _oidc_discovery(cfg["issuer"])
            info = verify_jwt_rs256(raw, _fetch_jwks(disc))
        except HTTPException:
            info = None
        if not info and cfg["hub_secret"]:
            info = verify_jwt_hs256(raw, cfg["hub_secret"])
        if not info:
            return _sso_fail("توکن ورود یکپارچه نامعتبر یا منقضی است")
        username = (info.get("preferred_username") or info.get("username")
                    or info.get("email") or "").strip()
        if not username:
            return _sso_fail("شناسه کاربر در توکن پرتال نبود")
        role = _map_role(info, cfg["default_role"], cfg["app_key"])
        user = _issue_for_username(conn, username, role_default=role,
                                   full_name=info.get("name") or "")
        db.audit(conn, user, "login", "ورود یکپارچه با توکن پرتال SSO")
        return _sso_done(make_token({"uid": user["id"], "username": user["username"],
                                     "role": user["role"]}))

    if code:
        verifier = None
        if state:
            stored = _consume_ticket(state)
            if stored:
                try:
                    verifier = json.loads(stored).get("verifier")
                except (json.JSONDecodeError, AttributeError):
                    verifier = None
        return _complete_oidc(conn, cfg, code, verifier)

    # بدون پارامتر: شروع جریان OIDC (ورود بدون رمز اگر نشست پرتال فعال باشد)
    disc = _oidc_discovery(cfg["issuer"])
    verifier, challenge = _pkce_pair()
    redirect_uri = f"{cfg['base']}/api/v1/auth/sso/university/callback"
    state = _new_ticket(_state_bundle(verifier))
    q = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "scope": cfg["scope"] or "openid profile",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(url=f"{disc['authorization_endpoint']}?{q}", status_code=302)


def _complete_oidc(conn, cfg: dict, code: str, verifier: str | None) -> RedirectResponse:
    """تبادل کد OIDC → دریافت هویت → صدور توکن برنامه → هدایت به فرانت"""
    disc = _oidc_discovery(cfg["issuer"])
    redirect_uri = f"{cfg['base']}/api/v1/auth/sso/university/callback"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": cfg["client_id"],
    }
    if verifier:
        data["code_verifier"] = verifier
    if cfg["client_secret"]:
        data["client_secret"] = cfg["client_secret"]
    req = urllib.request.Request(disc["token_endpoint"],
                                 data=urllib.parse.urlencode(data).encode(),
                                 method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tok = _json_loads(resp.read())
    except Exception:
        return _sso_fail("تبادل توکن با پرتال SSO ناموفق بود (کد مصرف‌شده یا پیکربندی ناسازگار)")
    access = tok.get("access_token") or ""
    if not access:
        return _sso_fail("توکن دسترسی از پرتال SSO دریافت نشد")
    req2 = urllib.request.Request(disc.get("userinfo_endpoint") or
                                  (cfg["issuer"].rstrip("/") + "/userinfo"),
                                  headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req2, timeout=15) as resp:
            info = _json_loads(resp.read())
    except Exception:
        return _sso_fail("دریافت اطلاعات هویت از پرتال SSO ناموفق بود")
    username = (info.get("preferred_username") or info.get("username")
                or info.get("email") or "").strip()
    if not username:
        return _sso_fail("شناسه کاربر در پاسخ پرتال SSO نبود")
    role = _map_role(info, cfg["default_role"], cfg["app_key"])
    user = _issue_for_username(conn, username, role_default=role, full_name=info.get("name") or "")
    db.audit(conn, user, "login", f"ورود یکپارچه ({cfg['issuer']})")
    return _sso_done(make_token({"uid": user["id"], "username": user["username"],
                                 "role": user["role"]}))


@router.get("/sso/{provider}/callback", summary="بازگشت OIDC (مرورگر)", include_in_schema=True)
def sso_callback(provider: str, code: str | None = None, state: str | None = None,
                 request: Request = None, conn=Depends(get_conn)):
    cfg = _sso_settings(conn)
    if provider != "university" or not cfg["issuer"]:
        raise HTTPException(status_code=404, detail="ارائه‌دهنده OIDC پیکربندی نشده است")
    if not code or not state:
        raise HTTPException(status_code=400, detail="پارامترهای callback ناقص است")
    stored = _consume_ticket(state)
    if not stored:
        raise HTTPException(status_code=400, detail="state نامعتبر یا منقضی است")
    try:
        verifier = json.loads(stored).get("verifier")
    except (json.JSONDecodeError, AttributeError):
        verifier = None
    return _complete_oidc(conn, cfg, code, verifier)


def _map_role(info: dict, default_role: str, app_key: str = "amoozeshyar") -> str:
    """نگاشت نقش‌های پرتال SSO به نقش‌های برنامه

    قرارداد پرتال: «کلید سامانه.نقش» (مثل amoozeshyar.admin یا amoozeshyar.access)؛
    نقش‌های رایج IdP (Keycloak و ...) هم پوشش داده می‌شوند.
    """
    roles = list(info.get("roles") or [])
    realm = (info.get("realm_access") or {}).get("roles") or []
    ra = info.get("resource_access") or {}
    if isinstance(ra, dict):
        for v in ra.values():
            if isinstance(v, dict):
                roles.extend(v.get("roles") or [])
    all_roles = {str(r).lower() for r in list(roles) + list(realm)}
    app = (app_key or "amoozeshyar").lower()
    if f"{app}.admin" in all_roles or any("system_admin" in r or "sysadmin" in r for r in all_roles):
        return "system_admin"
    if f"{app}.approver" in all_roles or any("approver" in r for r in all_roles):
        return "approver"
    if f"{app}.content" in all_roles or any("content_admin" in r or r == "content" for r in all_roles):
        return "content_admin"
    if f"{app}.expert" in all_roles or any("expert" in r for r in all_roles):
        return "expert"
    # «amoozeshyar.access» یا بدون نقش خاص → نقش پیش‌فرض (دانشجو)
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
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
