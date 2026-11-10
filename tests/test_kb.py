# -*- coding: utf-8 -*-
"""تست پایگاه دانش، نسخه‌بندی اسناد، مجوزها و جست‌وجو"""

import pytest

from app import db, services


def test_login_roles(conn):
    u = services.login(conn, "student", "Student@123")
    assert u and u["role"] == "student"
    assert services.login(conn, "student", "wrong") is None


def test_import_and_chunks(conn, content_user):
    doc_id = services.import_document(
        conn, content_user, "آیین‌نامه تستی",
        text="ماده ۱: سقف واحد بیست است.\n\nماده ۲: درس افکار عمومی اجباری است.\n\nتبصره ۱: استثنا با مجوز.")
    chunks = services.get_document_chunks(conn, content_user, doc_id)
    refs = [c["clause_ref"] for c in chunks]
    assert any("ماده ۱" in r for r in refs)
    assert any("تبصره" in r for r in refs)
    # متن نرمال‌شده برای جست‌وجو ذخیره شده است
    assert all(c["normalized"] for c in chunks)


def test_status_transitions_and_permissions(conn, content_user, approver_user, student_user):
    doc_id = services.import_document(conn, content_user, "سند چرخه", text="ماده ۱: متن آزمایشی است.")
    # دانشجو اجازه تغییر وضعیت ندارد
    with pytest.raises(PermissionError):
        services.update_document_status(conn, student_user, doc_id, "in_review")
    services.update_document_status(conn, content_user, doc_id, "in_review")
    services.update_document_status(conn, approver_user, doc_id, "approved")
    services.update_document_status(conn, approver_user, doc_id, "published")
    # گذار غیرمجاز
    with pytest.raises(ValueError):
        services.update_document_status(conn, approver_user, doc_id, "in_review")
    services.update_document_status(conn, approver_user, doc_id, "retired", "تست")
    row = db.q1(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
    assert row["status"] == "retired"


def test_revise_creates_draft_version(conn, content_user, approver_user):
    doc_id = services.import_document(conn, content_user, "سند نسخه‌بندی", text="ماده ۱: متن اول.")
    services.update_document_status(conn, content_user, doc_id, "in_review")
    services.update_document_status(conn, approver_user, doc_id, "approved")
    services.update_document_status(conn, approver_user, doc_id, "published")
    new_id = services.revise_document(conn, content_user, doc_id)
    new_doc = db.q1(conn, "SELECT * FROM documents WHERE id=?", (new_id,))
    assert new_doc["version_no"] == 2 and new_doc["status"] == "draft"
    # متن نسخه جاری دست‌نخورده مانده است
    old = db.q1(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
    assert old["status"] == "published"


def test_rule_approve_requires_published_source(conn, content_user, approver_user):
    doc_id = services.import_document(conn, content_user, "سند قاعده", text="ماده ۱: حداقل معدل ۱۲ است.")
    rule_id = services.create_rule(conn, content_user, "قاعده تستی", {"attr": "gpa", "op": ">=", "value": 12},
                                  source_document_id=doc_id)
    with pytest.raises(ValueError):
        services.approve_rule(conn, approver_user, rule_id)  # منبع هنوز منتشر نشده
    services.update_document_status(conn, content_user, doc_id, "in_review")
    services.update_document_status(conn, approver_user, doc_id, "approved")
    services.update_document_status(conn, approver_user, doc_id, "published")
    services.approve_rule(conn, approver_user, rule_id)  # اکنون مجاز
    row = db.q1(conn, "SELECT status FROM rules WHERE id=?", (rule_id,))
    assert row["status"] == "approved"


def test_bm25_relevance(conn):
    from app.search import BM25
    docs = [
        (1, "حداقل معدل لازم برای ثبت‌نام کارورزی دوازده است."),
        (2, "پذیرش در خوابگاه منوط به ارائه گواهی سکونت است."),
        (3, "سقف انتخاب واحد در نیمسال بیست واحد است."),
    ]
    idx = BM25(docs)
    hits = idx.search("معدل کارورزی", k=3)
    assert hits and hits[0][0] == 1
    hits = idx.search("خوابگاه سکونت", k=3)
    assert hits and hits[0][0] == 2


def test_irrelevant_query_no_result(conn, student_user):
    from app.answers import build_answer
    student = services.get_student_for_user(conn, student_user)
    ans = build_answer(conn, student_user, student, "شرایط رزرو زمین تنیس دانشگاه چیست؟")
    assert ans.no_result
    assert ans.sources == []
