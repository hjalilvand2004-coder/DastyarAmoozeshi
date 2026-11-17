# -*- coding: utf-8 -*-
"""پیکربندی برنامه"""

import os
from pathlib import Path

APP_NAME = "آموزش‌یار۳۶۰"
APP_NAME_SHORT = "آموزش‌یار۳۶۰"
VERSION = "0.4.0"
ORG = "Student360"

# پرتال ورود یکپارچه سازمانی (هاب SSO) و آدرس استقرار این سامانه
# این مقادیر «پیش‌فرض» هستند و با متغیر محیطی یا تنظیمات مدیر قابل بازنویسی‌اند.
DEFAULT_PUBLIC_BASE_URL = "http://188.212.96.235:8091"
DEFAULT_SSO_ISSUER = "http://188.212.96.235:8086"
DEFAULT_SSO_CLIENT_ID = "amoozeshyar360"
DEFAULT_SSO_APP_KEY = "amoozeshyar"


def base_dir() -> Path:
    """ریشه محل ذخیره داده‌ها (قابل تغییر با متغیر محیطی DASTYAR_HOME)"""
    env = os.environ.get("DASTYAR_HOME")
    if env:
        p = Path(env)
    else:
        p = Path.cwd()
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    d = base_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "dastyar.db"


def resources_dir() -> Path:
    return Path(__file__).resolve().parent / "resources"


DEFAULT_SETTINGS = {
    "llm_provider": "auto",          # auto = اگر مدل پیکربندی شده بود استفاده کن، وگرنه موتور قالبی
    "llm_base_url": "",              # نمونه: https://api.openai.com/v1
    "llm_api_key": "",
    "llm_model": "",
    "llm_timeout": "30",
    "send_profile_to_llm": "minimal",  # minimal = فقط مقطع/رشته/سال ورود
    "rate_limit_chat_per_hour": "20",
    "grad_required_credits": "140",
    "search_max_chunks": "6",
    # آدرس عمومی سامانه (مبنای ساخت redirect_uri و نقطه ورود SSO)
    "public_base_url": DEFAULT_PUBLIC_BASE_URL,   # نمونه: http://188.212.96.235:8091
    # ورود یکپارچه (SSO) - پرتال دانشجویار۳۶۰ یا هر IdP سازگار با OIDC (مثل Keycloak)
    "sso_oidc_issuer": DEFAULT_SSO_ISSUER,           # پرتال SSO سازمان: http://188.212.96.235:8086
    "sso_oidc_client_id": DEFAULT_SSO_CLIENT_ID,     # طبق ثبت سامانه در پرتال SSO
    "sso_oidc_client_secret": "",                    # کلاینت عمومی: خالی + PKCE(S256)
    "sso_oidc_scope": "openid profile",
    "sso_app_key": DEFAULT_SSO_APP_KEY,              # کلید سامانه در پرتال (مبنای نگاشت نقش‌ها)
    "sso_hub_secret": "",                            # اختیاری: رمز مشترک HS256 برای توکن امضاشدهٔ پرتال
}


def public_base_url() -> str:
    """آدرس عمومی سامانه برای ساخت redirect_uri و نقطه ورود SSO"""
    env = os.environ.get("D360_PUBLIC_BASE_URL")
    if env:
        return env.rstrip("/")
    return DEFAULT_PUBLIC_BASE_URL


def secret_key() -> str:
    """کلید امضای توکن: از متغیر محیطی، وگرنه کلید تصادفی پایدار در پوشه داده"""
    env = os.environ.get("D360_SECRET_KEY")
    if env:
        return env
    p = data_dir() / "secret.key"
    if p.exists():
        return p.read_text(encoding="ascii").strip()
    import secrets as _secrets
    key = _secrets.token_hex(32)
    p.write_text(key, encoding="ascii")
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return key


def web_port() -> int:
    """پورت سرویس وب؛ پیش‌فرض طبق استقرار سازمانی: ۸۰۹۱"""
    return int(os.environ.get("D360_PORT", "8091"))


def frontend_dist_candidates():
    """محل‌های احتمالی بیلد فرانت‌اند (مخزن و بسته پرتابل)"""
    here = Path(__file__).resolve()
    return [
        here.parents[1] / "frontend" / "dist",   # مخزن: <root>/frontend/dist
        here.parent / "web_static",              # نسخه پرتابل: app/web_static
    ]
