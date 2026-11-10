#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ساخت نسخه پرتابل ویندوز وب‌اپ (بدون نیاز به نصب پایتون/Node/PyQt)

- پایتون امبدد رسمی ۳.۱۲ برای ویندوز ۶۴بیتی
- نصب وابستگی‌های وب (FastAPI/Uvicorn) از ویل‌های win_amd64
- بیلد React از قبل ساخته‌شده (frontend/dist) داخل بسته قرار می‌گیرد
- اجرا: RUN-DastyarAmoozeshi.bat → سرور محلی + باز شدن مرورگر
- خروجی: dist/DastyarAmoozeshi-Portable-Windows-v<VER>.zip + dist/sha256.txt
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import __version__ as VERSION  # noqa: E402

PY_VER = "3.12.8"
PY_VER_NODOTS = "312"
PY_URL = f"https://www.python.org/ftp/python/{PY_VER}/python-{PY_VER}-embed-amd64.zip"
PACKAGES = ["fastapi", "uvicorn", "python-multipart", "pypdf", "python-docx"]

PTH_CONTENT = """python312.zip
Lib/site-packages
import site
"""

RUN_BAT = """@echo off
rem DastyarAmoozeshi - Portable web launcher (no Python installation required)
title DastyarAmoozeshi - Student360 Assistant
cd /d "%~dp0"
set "DASTYAR_HOME=%~dp0data"
set "D360_PORT=8600"
echo.
echo   DastyarAmoozeshi (Student360) - web version
echo   URL: http://127.0.0.1:8600/
echo   API docs: http://127.0.0.1:8600/api/docs
echo   Close this window to stop the server.
echo.
runtime\\python\\python.exe -m app.webapp --open
if errorlevel 1 (
  echo.
  echo An error occurred. See the message above.
  pause
)
"""

README_TXT = f"""دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰ - نسخه پرتابل ویندوز (وب)
================================================================

اجرا:
  1) فایل ZIP را در یک پوشه باز کنید (Extract).
  2) RUN-DastyarAmoozeshi.bat را اجرا کنید (دابل‌کلیک).
  3) مرورگر به‌صورت خودکار روی http://127.0.0.1:8600 باز می‌شود.

نیازی به نصب پایتون، Node یا PyQt نیست. ویندوز 10/11 64بیتی کافی است.
دسترسی Administrator لازم نیست. برای خروج، پنجره سیاه (سرور) را ببندید.

- مستندات تعاملی API (برای سایر نرم‌افزارها): http://127.0.0.1:8600/api/docs
- داده‌ها در پوشه data کنار همین فایل‌ها ذخیره می‌شود؛ برای انتقال کامل برنامه،
  کل پوشه را کپی کنید و برای حذف کامل، کل پوشه را پاک کنید.
- در اولین اجرا دیتابیس با داده «نمونه و غیررسمی» ساخته می‌شود.
- حساب‌های نمایشی (ورود با رمز): admin / expert / content / approver / student
  رمز هر حساب به‌صورت Name@123 است (مثلاً Student@123).
- ورود بدون رمز: در صفحه ورود، «ورود آزمایشی بدون رمز (نمونه)» را انتخاب کنید.
- ورود یکپارچه دانشگاهی (SSO/Keycloak): مدیر سیستم در بخش «مدیریت سیستم ← تنظیمات»
  آدرس IdP و کلاینت را ثبت کند؛ سپس دکمه SSO در صفحه ورود فعال می‌شود.
- مدل زبانی اختیاری: مدیریت سیستم ← تنظیمات ← llm_base_url / llm_api_key / llm_model
  بدون پیکربندی، موتور قالبی آفلاین پاسخ می‌دهد.

هشدار مهم: تا زمانی که اسناد رسمی دانشگاه ثبت و منتشر نشود، هیچ محتوایی
به‌عنوان قانون واقعی دانشگاه ارائه نمی‌شود؛ همه داده‌ها نمونه و غیررسمی‌اند.
نسخه {VERSION}
"""


def download(url: str, dest: Path) -> None:
    print(f"دانلود: {url}")
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)


def main() -> int:
    frontend_dist = ROOT / "frontend" / "dist"
    if not (frontend_dist / "index.html").exists():
        print("خطا: بیلد فرانت‌اند یافت نشد. ابتدا:  cd frontend && npm install && npm run build")
        return 1

    dist = ROOT / "dist"
    bundle = dist / "portable"
    if bundle.exists():
        shutil.rmtree(bundle)
    pydir = bundle / "runtime" / "python"
    pydir.mkdir(parents=True)

    # ۱) پایتون امبدد
    tmp = dist / "_py.zip"
    download(PY_URL, tmp)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(pydir)
    tmp.unlink()

    # ۲) فعال‌سازی site-packages
    (pydir / f"python{PY_VER_NODOTS}._pth").write_text(PTH_CONTENT, encoding="ascii")

    # ۳) وابستگی‌های وب برای win_amd64
    sp = pydir / "Lib" / "site-packages"
    cmd = [sys.executable, "-m", "pip", "install", "--target", str(sp),
           "--platform", "win_amd64", "--implementation", "cp",
           "--python-version", PY_VER_NODOTS, "--only-binary=:all:",
           "--no-compile", *PACKAGES]
    print("نصب ویل‌ها:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # ۴) کد برنامه + بیلد فرانت‌اند
    shutil.copytree(ROOT / "app", sp / "app",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "resources"))
    shutil.copytree(frontend_dist, sp / "app" / "web_static")

    # ۵) راه‌انداز و راهنما
    (bundle / "RUN-DastyarAmoozeshi.bat").write_bytes(RUN_BAT.replace("\n", "\r\n").encode("ascii"))
    (bundle / "README-PORTABLE.txt").write_text(README_TXT, encoding="utf-8-sig")
    (bundle / "data").mkdir(exist_ok=True)

    # ۶) ZIP
    out = dist / f"DastyarAmoozeshi-Portable-Windows-v{VERSION}.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(bundle.rglob("*")):
            if p.is_file():
                z.write(p, "DastyarAmoozeshi-Portable/" + p.relative_to(bundle).as_posix())

    # ۷) SHA256
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    (dist / "sha256.txt").write_text(f"{h}  {out.name}\n", encoding="ascii")
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"ساخته شد: {out.name} ({size_mb:.1f} MB)")
    print(f"SHA256: {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
