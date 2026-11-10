#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انتشار ریلیز GitHub (سورس قبلاً push شده باشد)

متغیر محیطی GH_TOKEN لازم است.
خروجی build_portable.py (dist/*.zip و dist/sha256.txt) را به ریلیز اضافه می‌کند.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import __version__ as VERSION  # noqa: E402

REPO = "hjalilvand2004-coder/DastyarAmoozeshi"
TAG = f"v{VERSION}"
TOKEN = os.environ.get("GH_TOKEN", "")

BODY = f"""## نسخه {VERSION.replace('-', '٫')} — نخستین انتشار عمومی

اپلیکیشن دسکتاپ فارسی (راست‌به‌چپ) «دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰»:

- گفتگوی مستند سه‌لایه (متن رسمی سند / توضیح ساده / وضعیت شخصی دانشجو) با ارجاع واقعی به سند، نسخه، ماده و صفحه
- پایگاه دانش آیین‌نامه‌ها با نسخه‌بندی کامل (پیش‌نویس ← در حال بررسی ← تأییدشده ← منتشرشده ← ملغی) و اسکوپ (مقطع/رشته/سال ورود)
- موتور قواعد قطعی مستقل از هوش مصنوعی با خروجی چهارحالته و تأیید انسانی
- راهنمای فرایندهای اداری (بدون ادعای «ثبت موفق» در سامانه دانشگاه)
- مشاوره انتخاب واحد (پیش‌نیاز، پیشنهاد ترم بعد، وضعیت فارغ‌التحصیلی)
- یادآور مهلت‌ها با تقویم جلالی و پشتیبانی از اصلاح تقویم
- درخواست از کارشناس (تیکت) با چرخه وضعیت استاندارد
- نقش‌ها و مجوزها در بک‌اند + جداسازی چنددانشگاهی + لاگ حسابرسی
- امنیت هوش مصنوعی: محافظت از تزریق دستور، اعتبارسنجی ارجاع، پرچم خطای OCR، محدودسازی نرخ
- ۴۱ تست خودکار شامل ۸ سناریوی پذیرش الزامی

### دانلودها

| فایل | توضیح |
|---|---|
| `DastyarAmoozeshi-Portable-Windows-v{VERSION}.zip` | **نسخه پرتابل ویندوز — بدون نیاز به نصب پایتون**؛ باز کنید و `RUN-DastyarAmoozeshi.bat` را اجرا کنید (ویندوز ۱۰/۱۱ ۶۴بیتی) |
| Source code (zip/tar.gz) | سورس کامل + مستندات + تست‌ها |

SHA256 فایل پرتابل در فایل `sha256.txt` همین ریلیز آمده است.

### هشدار مهم

تمام اسناد و قواعد همراه این نسخه **«نمونه و غیررسمی»** هستند. تا زمانی که مدیر محتوای دانشگاه اسناد رسمی را ثبت و منتشر نکند، برنامه هیچ موردی را به‌عنوان قانون واقعی دانشگاه ارائه نمی‌کند و همه پاسخ‌ها با برچسب هشدار همراه است.

### مستندات

راهنمای نصب، معماری، مدل داده، قرارداد API، جریان پاسخ‌دهی، تست‌ها و گزارش محدودیت‌ها در پوشه `docs/` مخزن آمده است.
"""


def api(url: str, method: str = "GET", data=None, content_type: str = "application/json"):
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github+json",
               "User-Agent": "dastyar-release-script"}
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
        elif isinstance(data, bytes):
            body = data
        else:
            body = bytes(data)
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def main() -> int:
    if not TOKEN:
        print("GH_TOKEN تنظیم نشده است.")
        return 1
    zip_path = ROOT / "dist" / f"DastyarAmoozeshi-Portable-Windows-v{VERSION}.zip"
    if not zip_path.exists():
        print("ابتدا build_portable.py را اجرا کنید:", zip_path)
        return 1
    sha = (ROOT / "dist" / "sha256.txt").read_text(encoding="ascii").strip().split()[0]

    # ساخت یا بازیابی ریلیز
    payload = {"tag_name": TAG, "target_commitish": "main", "name": f"نسخه {TAG} — منتشر اولیه",
               "body": BODY + f"\n\nSHA256 (Portable): `{sha}`\n",
               "draft": False, "prerelease": False}
    try:
        rel = api(f"https://api.github.com/repos/{REPO}/releases", "POST", payload)
        print("ریلیز ساخته شد:", rel["html_url"])
    except urllib.error.HTTPError as e:
        if e.code == 422:  # تگ موجود است
            rel = api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
            print("ریلیز موجود است:", rel["html_url"])
        else:
            raise

    # بارگذاری فایل پرتابل (در صورت وجود نسخه قبلی، حذف و جایگزینی)
    assets = api(f"https://api.github.com/repos/{REPO}/releases/{rel['id']}/assets")
    for a in assets:
        if a["name"] == zip_path.name:
            api(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", "DELETE")
            print("فایل قدیمی حذف شد:", a["name"])

    data = zip_path.read_bytes()
    url = (f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets"
           f"?name={zip_path.name}")
    api(url, "POST", data, content_type="application/zip")
    print("بارگذاری شد:", zip_path.name, f"({len(data) / (1024 * 1024):.1f} MB)")

    # بارگذاری sha256.txt
    sha_path = ROOT / "dist" / "sha256.txt"
    for a in api(f"https://api.github.com/repos/{REPO}/releases/{rel['id']}/assets"):
        if a["name"] == "sha256.txt":
            api(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", "DELETE")
    api(f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name=sha256.txt",
        "POST", sha_path.read_bytes(), content_type="text/plain")
    print("بارگذاری شد: sha256.txt")
    print("آدرس ریلیز:", rel["html_url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
