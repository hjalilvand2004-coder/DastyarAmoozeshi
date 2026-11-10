# ۳) مدل داده (SQLite - طرح v1)

همه جداول در `app/db.py` تعریف شده‌اند. کلید اصلی همه `id` (AUTOINCREMENT) و داده‌های ساختاریافته به‌صورت JSON ذخیره می‌شوند.

## دانشگاه‌ها و کاربران

- `universities(id, name, code)` — برای جداسازی داده چنددانشگاهی.
- `users(id, university_id, username, password_hash, full_name, role, student_id, active, created_at)`
  نقش‌ها: `student` / `expert` / `content_admin` / `approver` / `system_admin`؛ رمزها PBKDF2-SHA256.
- `students(id, university_id, user_id, full_name, level, major, entry_year, gpa, passed_credits, passed_courses(json), profile_extra(json))`
  `profile_extra` می‌تواند پرچم‌هایی مثل `transcript_verified` و `on_probation` داشته باشد (ورودی موتور قواعد).

## پایگاه دانش آیین‌نامه‌ها

- `documents(id, university_id, title, doc_type, status, version_no, parent_id, effective_from, effective_until, scope_level, scope_major, scope_entry_from, scope_entry_to, file_path, url, source_note, is_official, flags, created_by, retired_at, retired_reason)`
  - `doc_type`: `text` / `pdf_text` / `pdf_scan` / `word` / `link`
  - `status`: `draft` → `in_review` → `approved` → `published` → `retired` (گذارها در `services.DOC_TRANSITIONS` محدود شده‌اند)
  - `flags`: پرچم‌های امنیتی سطح سند مثل `injection_suspect` / `ocr_suspect`
  - `is_official=0` یعنی غیررسمی (همه داده‌های نمونه) — مبنای هشدار دائمی.
- `chunks(id, document_id, clause_ref, page_no, text, normalized, idx, flags)`
  تکه‌بندی بر اساس ماده/تبصره/فصل؛ `text` عین متن سند و `normalized` نسخه نرمال‌شده برای جست‌وجو؛ `page_no` برای PDF از pypdf می‌آید.

## قواعد

- `rules(id, university_id, title, source_document_id, source_clause, version_no, scope, cond_json, messages, review_fields, status, approved_by, approved_at)`
  - `cond_json`: درخت شرط (`all` / `any` / برگ با `attr, op, value`)
  - `messages`: متن هر چهار وضعیت برای نمایش
  - `review_fields`: فیلدهایی که در صورت نبود تأیید رسمی، خروجی «نیازمند بررسی کارشناس» می‌شود
  - `status`: `draft` / `approved` / `disabled` — تأیید فقط وقتی ممکن است که سند منبع `published` باشد.

## گفتگو

- `chat_sessions(id, user_id, title, created_at)`
- `chat_messages(id, session_id, role, content, meta, created_at)` — در `meta` ارجاع‌ها، هشدارها و موارد نیازمند تأیید همان پاسخ ذخیره می‌شود (قابلیت ممیزی).

## فرایندها، یادآورها و تیکت

- `processes(id, university_id, key, title, steps(json), required_docs(json), target_system, target_url, keywords(json), source_document_id, notes)`
- `deadlines(id, university_id, title, date_iso, scope, source_document_id, notes, version_no, active, created_by, created_at)`
- `deadline_acks(id, deadline_id, version_no, user_id, ack_at, UNIQUE(deadline_id, version_no, user_id))`
  نسخه‌بندی رویداد مبنای «اصلاح تقویم»: ویرایش تاریخ، `version_no` را بالا می‌برد و تأییدهای قبلی بی‌اثر می‌شود.
- `tickets(id, university_id, user_id, subject, status, created_at, updated_at)`
- `ticket_messages(id, ticket_id, author_id, body, is_staff, created_at)`

## دروس و پیکربندی

- `courses(id, university_id, code, name, credits, prereqs(json), keywords(json))`
- `settings(key, value)` — پیکربندی مدل زبانی، سقف نرخ، واحدهای فارغ‌التحصیلی، ...
- `audit_log(id, university_id, user_id, action, detail, created_at)` — تمام عملیات حساس (تأیید/انتشار/ابطال سند، تأیید قاعده، تغییر وضعیت تیکت، اصلاح تقویم، تغییرات کاربر و تنظیمات) ثبت می‌شود.

## نکات سازگاری با استقرار دانشگاهی

- تاریخ‌ها ISO میلادی ذخیره و در UI جلالی نمایش داده می‌شوند.
- `is_official` و `source_note` برای تشخیص «سند رسمی» از «نمونه» در هر گزارش/پاسخ استفاده می‌شوند.
- برای اتصال به SSO کافی است `users` شناسه بیرونی بگیرد؛ بقیه طرح بدون تغییر می‌ماند.
