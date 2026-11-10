# ۴) قرارداد API برای یکپارچه‌سازی آینده

این نسخه دسکتاپ است؛ توابع لایه سرویس (`app/services.py` و `app/answers.ask`) عمداً به‌صورت «یک عملیات = یک فراخوانی» نوشته شده‌اند تا پوشاندن آن‌ها با REST سرراست باشد. قرارداد زیر مبنای نسخه وب/موبایل و اتصال به زیرساخت مشترک دانشجو۳۶۰ است.

## مقدمات

- احراز هویت: توکن OIDC (Keycloak) در هدر `Authorization: Bearer ...`؛ نقش‌ها همان نقش‌های سامانه.
- همه مسیرها زیر `/api/v1` و جداگانه برای هر دانشگاه (دامنه از توoken یا هدر `X-University-Id`).
- خطاها: `403` عدم مجوز، `404` یافت نشد، `422` خطای اعتبارسنجی، `429` محدودسازی نرخ.

## نمونه نقاط پایانی

### گفتگوی مستند
```
POST /api/v1/chat/asks
{ "question": "معدل لازم برای کارورزی چیست؟", "include_retired": false }
200:
{ "answer": {
    "short": "...", "conditions": ["..."],
    "status_rows": [{"title": "...", "state": "satisfied|not_satisfied|insufficient_info|needs_review", ...}],
    "next_steps": ["..."],
    "sources": [{"ref": "C1", "document_id": 1, "doc_title": "...", "version_no": 2,
                 "status": "published", "clause_ref": "ماده ۱۸", "page_no": 3, "url": "..."}],
    "confirmations": ["..."], "warnings": ["..."], "provider": "..." } }
```

### اسناد
```
GET    /api/v1/documents?status=published|retired|all
POST   /api/v1/documents            (multipart: file / text + متادیتا و اسکوپ)   [content_admin]
POST   /api/v1/documents/{id}/status   { "status": "in_review|approved|published|retired", "reason": "..." }
POST   /api/v1/documents/{id}/revisions   نسخه جدید (پیش‌نویس)
GET    /api/v1/documents/{id}/chunks
```

### قواعد
```
GET    /api/v1/rules
POST   /api/v1/rules                [content_admin]
POST   /api/v1/rules/{id}/approval  [approver]  (فقط با منبع منتشرشده)
POST   /api/v1/rules/{id}/evaluate  { "student_id": 5 }  → چهار وضعیت + فیلدهای ناقص
```

### یادآورها
```
GET    /api/v1/deadlines?window_days=30
POST   /api/v1/deadlines            [expert]
PATCH  /api/v1/deadlines/{id}       (تغییر تاریخ = نسخه جدید + ابطال تأییدها)
POST   /api/v1/deadlines/{id}/acks
GET    /api/v1/deadlines/pending    یادآورهای اعلام‌نشده نسخه جاری
```

### تیکت
```
GET    /api/v1/tickets              (کارشناس: صف دانشگاه؛ دانشجو: تیکت‌های خودش)
POST   /api/v1/tickets              { "subject": "...", "body": "..." }
GET    /api/v1/tickets/{id}/thread
POST   /api/v1/tickets/{id}/messages
POST   /api/v1/tickets/{id}/transitions   { "status": "under_review|needs_info|answered|closed" }
```

### مشاوره و پروفایل
```
GET    /api/v1/me/student-profile
PATCH  /api/v1/me/student-profile
POST   /api/v1/advisor/course-check   { "course_id": 3 }   → پیش‌نیازها
GET    /api/v1/advisor/next-courses
GET    /api/v1/advisor/graduation-audit
```

### فرایندها و مدیریت
```
GET    /api/v1/processes
GET    /api/v1/processes/{id}
GET    /api/v1/users              [system_admin]
POST   /api/v1/users              [system_admin]
GET/PATCH /api/v1/settings        [system_admin]
```

## قواعد مشترک پاسخ

- هر خروجیِ متکی به سند باید `sources` با شناسه تکه واقعی داشته باشد؛ سرویس‌ها ارجاع خارج از زمینه را رد می‌کنند.
- هر پاسخ مرتبط با داده نمونه، `warnings` حاوی برچسب «نمونه و غیررسمی» برمی‌گرداند.
- هیچ مسیری «ثبت موفق در سامانه دانشگاه» ادعا نمی‌کند؛ حداکثر لینک سامانه مقصد را می‌دهد.
- پاسخ مدل زبانی هرگز مستقیماً به کاربر نمی‌رود؛ بعد از اعتبارسنجی ارجاع و افزودن لایه‌های قطعی (وضعیت/اقدام/منبع) ارسال می‌شود.
