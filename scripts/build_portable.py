#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ساخت نسخه پرتابل ویندوز (بدون نیاز به نصب پایتون)

- پایتون امبدد رسمی ۳.۱۲ برای ویندوز ۶۴بیتی
- نصب وابستگی‌ها از ویل‌های win_amd64
- کد برنامه به‌صورت بسته app داخل site-packages
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
PACKAGES = ["PyQt6", "pypdf", "python-docx"]

PTH_CONTENT = """python312.zip
Lib/site-packages
import site
"""

RUN_BAT = """@echo off
rem DastyarAmoozeshi - Portable launcher (no Python installation required)
cd /d "%~dp0"
set "DASTYAR_DATA_DIR=%~dp0data"
set "QT_ENABLE_HIGHDPI_SCALING=1"
runtime\\python\\python.exe -m app.main
if errorlevel 1 (
  echo.
  echo An error occurred. See the message above.
  pause
)
"""

README_TXT = """دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰ - نسخه پرتابل ویندوز
================================================================

اجرا:
  1) فایل ZIP را در یک پوشه باز کنید (Extract).
  2) RUN-DastyarAmoozeshi.bat را اجرا کنید (دابل‌کلیک).

نیازی به نصب پایتون یا PyQt نیست. ویندوز 10/11 64بیتی کافی است.
دسترسی Administrator لازم نیست.

نکته‌ها:
- داده‌ها در پوشه data کنار همین فایل‌ها ذخیره می‌شود؛
  برای انتقال کامل برنامه، کل پوشه را کپی کنید و برای حذف کامل، کل پوشه را پاک کنید.
- در اولین اجرا دیتابیس با داده «نمونه و غیررسمی» ساخته می‌شود؛
  اسناد رسمی دانشگاه را از صفحه «مدیریت اسناد» با چرخه تأیید/انتشار ثبت کنید.
- حساب‌های نمایشی: admin / expert / content / approver / student
  رمز هر حساب به‌صورت Name@123 است (مثلاً Student@123).
- برای استفاده از مدل زبانی اختیاری: تنظیمات ← «مدل زبانی».

هشدار مهم: تا زمانی که اسناد رسمی دانشگاه ثبت نشود، هیچ محتوایی
به‌عنوان قانون واقعی دانشگاه ارائه نمی‌شود؛ همه داده‌ها نمونه و غیررسمی‌اند.
"""


def download(url: str, dest: Path) -> None:
    print(f"دانلود: {url}")
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)


def main() -> int:
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

    # ۳) وابستگی‌ها برای win_amd64
    sp = pydir / "Lib" / "site-packages"
    cmd = [sys.executable, "-m", "pip", "install", "--target", str(sp),
           "--platform", "win_amd64", "--implementation", "cp",
           "--python-version", PY_VER_NODOTS, "--only-binary=:all:",
           "--no-compile", *PACKAGES]
    print("نصب ویل‌ها:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # ۴) کد برنامه
    shutil.copytree(ROOT / "app", sp / "app")

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
