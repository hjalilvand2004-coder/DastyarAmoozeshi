# ۱۰) معماری وب و راهنمای یکپارچه‌سازی سرویس‌ها

## نقشه سرویس‌ها (FastAPI)

هر بخش زیرسیستم یک سرویس مستقل با پیشوند `/api/v1` است؛ سایر نرم‌افزارهای دانشجو۳۶۰
(پورتال، سامانه آموزش اصلی، اپلیکیشن موبایل، چت‌بات‌ها) می‌توانند مستقیماً از آن‌ها مصرف کنند.

| سرویس | متد و مسیر | شرح |
|---|---|---|
| **auth** | `POST /auth/login` | ورود با نام کاربری/رمز (PBKDF2) → JWT |
| | `GET /auth/me` | کاربر جاری + پروفایل دانشجویی + مجوزها |
| | `GET /auth/sso/providers` | ارائه‌دهنده‌های SSO (دمو + OIDC پیکربندی‌شده) |
| | `GET /auth/sso/{p}/start` | شروع جریان (تیکت یک‌بار مصرف یا URL Authorize) |
| | `POST /auth/sso/demo/exchange` | تبادل تیکت دمو با JWT (یک‌بار مصرف، ۱۸۰ثانیه) |
| | `GET /auth/sso/university/callback` | بازگشت OIDC: تبادل کد → JWT → هدایت به فرانت |
| **chat** | `POST /chat/ask` | پاسخ سه‌لایه با `sources` (استناد واقعی)، `warnings`، `status_rows` |
| | `GET /chat/sessions` · `GET /chat/sessions/{id}/messages` | تاریخچه |
| **regulations** | `GET /regulations` · `GET /regulations/{id}` | فهرست/جزئیات + تکه‌های ماده‌به‌ماده |
| | `POST /regulations/import` · `POST /regulations/import-file` | ثبت متن یا فایل (پیش‌نویس) |
| | `POST /regulations/{id}/status` | گذار وضعیت با کنترل مجوز (`in_review/approved/published/retired`) |
| | `POST /regulations/{id}/revise` | نسخه جدید (متن نسخه جاری دست‌نخورده) |
| **rules** | `GET /rules` · `POST /rules` | فهرست/تعریف قاعده (پیش‌نویس) |
| | `POST /rules/{id}/approve` · `/status` | گردش‌کار تأیید انسانی |
| | `GET /rules/my` · `POST /rules/{id}/evaluate/{student_id}` | ارزیابی چهارحالته |
| **advisor** | `GET /advisor/courses` · `/analyze/{course_id}` · `/next-courses` · `/graduation` | مشاور تحصیلی |
| | `GET /advisor/students` · `POST /advisor/students/{id}/profile` | مدیریت پروفایل |
| **processes** | `GET /processes` · `GET /processes/{id}` · `POST /processes` | راهنمای اداری |
| **deadlines** | `GET /deadlines` · `POST /deadlines` · `PATCH /deadlines/{id}` | رویدادها |
| | `GET /deadlines/reminders` · `POST /deadlines/{id}/ack` | یادآور شخصی + ضدتکرار |
| **tickets** | `GET /tickets` · `POST /tickets` · `GET /tickets/{id}` · `POST /tickets/{id}/messages` · `POST /tickets/{id}/status` | چرخه کامل تیکت |
| **admin** | `GET/POST /admin/users` · `/users/{id}/active` · `/users/{id}/password` | کاربران |
| | `GET/POST /admin/settings` | تنظیمات (LLM و SSO؛ مقادیر حساس پوشانده می‌شوند) |
| | `GET /admin/audit` | گزارش حسابرسی |

مستندات تعاملی: **`/api/docs`** (Swagger UI) و **`/api/redoc`** — همه اجزا با OpenAPI 3.

## احراز هویت

- توکن JWT با HS256 (بدون وابستگی خارجی)؛ امضای کلید از `D360_SECRET_KEY` یا فایل پایدار در پوشه داده.
- همه درخواست‌های مگر `login`/`sso`/`health` نیازمند هدر `Authorization: Bearer <token>`.
- کنترل مجوز در **بک‌اند** انجام می‌شود (لایه `services`)؛ نقش‌ها: `student`، `expert`، `content_admin`، `approver`، `system_admin`.
- جداسازی داده بین دانشگاه‌ها با `university_id` در همه کوئری‌ها.
- محدودسازی نرخ: چت ۲۰ پرسش در ساعت (هر کاربر) + ۳۰۰ درخواست در دقیقه (هر IP روی `/api/*`).

## جریان SSO/OIDC

```
مرورگر → GET /api/v1/auth/sso/university/start
       ← { redirect: "https://idp/.../authorize?..." }
مرورگر → IdP (ورود دانشگاهی)
IdP → GET /api/v1/auth/sso/university/callback?code=..&state=..
سرور: تبادل کد در token_endpoint + userinfo
     → ایجاد/یافتن کاربر (نگاشت نقش از claim)
     → JWT برنامه → 302 به /sso/callback?token=..
فرانت‌اند: ذخیره توکن → میزکار
```

پیکربندی از «مدیریت سیستم ← تنظیمات» یا متغیرهای محیطی `D360_OIDC_ISSUER/CLIENT_ID/CLIENT_SECRET/SCOPE`.
ارائه‌دهنده دمو (`demo`) برای ارزیابی بدون IdP است و با برچسب «نمونه» مشخص می‌شود.

## لایه‌بندی پاسخ دستیار (POST /chat/ask)

```json
{
  "short": "...",                      // لایه ۲: توضیح ساده
  "conditions": ["..."],
  "status_rows": [                     // لایه ۳: موتور قواعد قطعی
    {"title": "...", "state": "satisfied|not_satisfied|insufficient_info|needs_review"}
  ],
  "next_steps": ["..."],
  "sources": [{                        // لایه ۱: متن رسمی + استناد واقعی
    "ref": "C1", "doc_title": "...", "version_no": 2, "clause_ref": "ماده ۱۸",
    "page_no": 1, "status": "published", "official": false, "excerpt": "..."
  }],
  "warnings": ["هشدار: اسناد فعلی «نمونه و غیررسمی» هستند..."],
  "confirmations": ["مغایرت احتمالی ... تعیین سند حاکم با کارشناس آموزش است."]
}
```

قواعد سخت پیاده‌سازی‌شده: ارجاع فقط به تکه‌های واقعی بازیابی‌شده (ارجاع مدل زبانی اعتبارسنجی می‌شود)؛
سند ملغی فقط با برچسب و صرفاً برای مقایسه؛ داده ناقص → «اطلاعات ناکافی» (بدون حدس)؛
متن اسناد «داده» است و الگوهای تزریق دستور پرچم می‌خورد.

## یکپارچه‌سازی با زیرساخت مشترک دانشجو۳۶۰ (نقشه راه)

- پروفایل دانشجو/احراز هویت: جایگزینی `get_student_for_user` و ارائه‌دهنده SSO با سرویس مرکزی.
- مدل زبانی/جست‌وجوی معنایی مشترک: `app/llm.py` (سازگار با OpenAI) و افزودن ایندکس برداری در `app/search.py`.
- اعلان‌ها: افزودن web push/ایمیل به `pending_reminders`.
