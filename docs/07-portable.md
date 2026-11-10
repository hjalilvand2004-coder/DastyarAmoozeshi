# ۷) نسخه پرتابل ویندوز (بدون نیاز به نصب پایتون/PyQt)

## ۷.۱ دانلود و اجرا

1. از [Releases](https://github.com/hjalilvand2004-coder/DastyarAmoozeshi/releases) فایل `DastyarAmoozeshi-Portable-Windows-v*.zip` را دانلود کنید.
2. مجموع SHA256 فایل را با مقدار درخواست‌شده در یادداشت ریلیز مقایسه کنید.
3. ZIP را در پوشه‌ای باز کنید (مسیر بدون حروف خاص پیشنهاد می‌شود).
4. `RUN-DastyarAmoozeshi.bat` را اجرا کنید.

نیازمندی: ویندوز ۱۰/۱۱ ۶۴بیتی. **نیازی به نصب پایتون، PyQt یا هر پیش‌نیاز دیگر نیست** و برای اجرا دسترسی مدیر (Administrator) لازم نیست.

## ۷.۲ محتویات بسته

```
DastyarAmoozeshi-Portable/
├── runtime/python/          پایتون امبدد رسمی ۳.۱۲ (بدون نصب)
│   └── Lib/site-packages/   PyQt6 + pypdf + python-docx + کد برنامه
├── RUN-DastyarAmoozeshi.bat راه‌انداز
├── README-PORTABLE.txt      راهنمای کوتاه فارسی
└── data/                    داده برنامه (در اولین اجرا ساخته می‌شود)
```

- داده‌ها داخل همان پوشه (`data/`) ذخیره می‌شوند؛ حذف پوشه = حذف کامل برنامه.
- در اولین اجرا، دیتابیس با داده نمونه «غیررسمی» ساخته می‌شود.

## ۷.۳ ساخت دوباره بسته (برای توسعه‌دهندگان)

```bash
pip install -r requirements.txt        # روی دستگاه سازنده (هر سیستم‌عاملی)
python scripts/build_portable.py       # دانلود پایتون امبدد + ویل‌های win_amd64 و ساخت zip
```

خروجی: `dist/DastyarAmoozeshi-Portable-Windows-v*.zip` همراه `dist/sha256.txt`.
اسکریپت انتشار (`scripts/make_release.py`) همین فایل را به ریلیز GitHub اضافه می‌کند.

## ۷.۴ نکات فنی

- پایتون امبدد با فایل `python312._pth` تنظیم شده تا `Lib/site-packages` را ببیند؛ کد برنامه به‌صورت بسته `app` داخل همان site-packages کپی می‌شود و با `python -m app.main` اجرا می‌شود.
- ویل‌ها با `pip install --platform win_amd64 --only-binary=:all:` برای ویندوز ۶۴بیتی حل می‌شوند؛ نیازی به ویندوز برای ساخت نیست.
- `RUN-DastyarAmoozeshi.bat` مسیر داده را با `DASTYAR_DATA_DIR` به پوشه بسته قفل می‌کند تا نسخه واقعاً پرتابل بماند.
- در صورت بروز خطا، پنجره کنسول باز می‌ماند و متن خطا نمایش داده می‌شود.
