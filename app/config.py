# -*- coding: utf-8 -*-
"""پیکربندی برنامه"""

import os
from pathlib import Path

APP_NAME = "دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰"
APP_NAME_SHORT = "دستیار آموزشی"
VERSION = "0.1.0"
ORG = "Student360"


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
    # ورود یکپارچه (SSO) - هر ارائه‌دهنده سازگار با OIDC (مثل Keycloak)
    "sso_oidc_issuer": "",           # نمونه: https://sso.university.ac.ir/realms/student360
    "sso_oidc_client_id": "",
    "sso_oidc_client_secret": "",
    "sso_oidc_scope": "openid profile",
}


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
    return int(os.environ.get("D360_PORT", "8600"))


def frontend_dist_candidates():
    """محل‌های احتمالی بیلد فرانت‌اند (مخزن و بسته پرتابل)"""
    here = Path(__file__).resolve()
    return [
        here.parents[1] / "frontend" / "dist",   # مخزن: <root>/frontend/dist
        here.parent / "web_static",              # نسخه پرتابل: app/web_static
    ]
