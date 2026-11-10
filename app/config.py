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
}
