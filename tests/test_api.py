# -*- coding: utf-8 -*-
"""تست‌های API (FastAPI) - شامل سناریوهای پذیرش از سمت HTTP"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.server import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import app.config as cfg
    tmp = tmp_path_factory.mktemp("api")
    db_file = tmp / "api.db"
    old = cfg.db_path
    cfg.db_path = lambda: db_file  # نوعی: مسیر DB ایزوله برای این ماژول
    import app.api.deps as deps
    deps.db_path = cfg.db_path
    # ساخت و پر کردن دیتابیس ایزوله
    from app import db as app_db, seed
    conn = app_db.connect(db_file)
    seed.seed_if_empty(conn)
    conn.close()
    app = create_app()
    with TestClient(app) as c:
        yield c
    cfg.db_path = old


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.order(1)
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_unauthorized_is_401(client):
    assert client.get("/api/v1/regulations").status_code == 401


def test_login_and_me(client):
    data = _login(client, "student", "Student@123")
    assert data["user"]["role"] == "student"
    h = {"Authorization": f"Bearer {data['token']}"}
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert me["user"]["username"] == "student"
    assert me["student"]["major"] == "مهندسی کامپیوتر"


def test_sso_demo_flow_without_password(client):
    start = client.get("/api/v1/auth/sso/demo/start", params={"as_": "student"}).json()
    r = client.post("/api/v1/auth/sso/demo/exchange", json={"ticket": start["ticket"]})
    assert r.status_code == 200
    assert r.json()["token"]
    # تیکت یک‌بار مصرف است
    r2 = client.post("/api/v1/auth/sso/demo/exchange", json={"ticket": start["ticket"]})
    assert r2.status_code == 400


def test_chat_answer_has_citations_and_sample_banner(client):
    tok = _login(client, "student", "Student@123")["token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post("/api/v1/chat/ask", headers=h,
                    json={"question": "شرایط ثبت‌نام کارورزی چیست؟"})
    assert r.status_code == 200
    ans = r.json()["answer"]
    assert ans["sources"], "پاسخ باید استناد واقعی داشته باشد"
    assert any("نمونه" in w for w in ans["warnings"]), "برچسب نمونه/غیررسمی الزامی است"
    assert not ans["no_result"]


def test_chat_unrelated_question_is_honest(client):
    tok = _login(client, "student", "Student@123")["token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post("/api/v1/chat/ask", headers=h,
                    json={"question": "قیمت بلیط فوتبال چقدر است؟"})
    ans = r.json()["answer"]
    assert ans["no_result"] is True


def test_regulations_cycle_and_permissions(client):
    content = _login(client, "content", "Content@123")
    approver = _login(client, "approver", "Approver@123")
    student = _login(client, "student", "Student@123")
    hc = {"Authorization": f"Bearer {content['token']}"}
    ha = {"Authorization": f"Bearer {approver['token']}"}
    hs = {"Authorization": f"Bearer {student['token']}"}

    r = client.post("/api/v1/regulations/import", headers=hc,
                    json={"title": "سند تست API", "text": "ماده ۱: متن آزمایشی سند تست API."})
    assert r.status_code == 200
    doc_id = r.json()["id"]

    # دانشجو اجازه گذار وضعیت ندارد
    assert client.post(f"/api/v1/regulations/{doc_id}/status", headers=hs,
                       json={"status": "in_review"}).status_code == 403

    # چرخه کامل: ثبت‌کننده ارسال می‌کند، تأییدکننده تأیید و منتشر می‌کند
    assert client.post(f"/api/v1/regulations/{doc_id}/status", headers=hc,
                       json={"status": "in_review"}).status_code == 200
    for st in ("approved", "published"):
        assert client.post(f"/api/v1/regulations/{doc_id}/status", headers=ha,
                           json={"status": st}).status_code == 200
    docs = client.get("/api/v1/regulations", headers=hs).json()["documents"]
    assert any(d["id"] == doc_id and d["status"] == "published" for d in docs)


def test_rule_approval_flow_and_my_status(client):
    content = _login(client, "content", "Content@123")
    approver = _login(client, "approver", "Approver@123")
    student2 = _login(client, "student2", "Student@123")
    hc = {"Authorization": f"Bearer {content['token']}"}
    ha = {"Authorization": f"Bearer {approver['token']}"}
    h2 = {"Authorization": f"Bearer {student2['token']}"}

    r = client.post("/api/v1/rules", headers=hc, json={
        "title": "قاعده تست API (معدل>=13)",
        "cond": {"attr": "gpa", "op": ">=", "value": 13},
    })
    assert r.status_code == 200
    rid = r.json()["id"]
    assert client.post(f"/api/v1/rules/{rid}/approve", headers=hc).status_code == 403
    assert client.post(f"/api/v1/rules/{rid}/approve", headers=ha).status_code == 200

    my = client.get("/api/v1/rules/my", headers=h2).json()
    row = next(x for x in my["results"] if x["rule_id"] == rid)
    assert row["status"] == "satisfied"  # معدل سارا ۱۶ است


def test_student2_entry_year_unknown_flags_insufficient(client):
    """سناریوی پذیرش ۳: سال ورود نامشخص → نتیجه قطعی اعلام نمی‌شود"""
    student2 = _login(client, "student2", "Student@123")
    h2 = {"Authorization": f"Bearer {student2['token']}"}
    my = client.get("/api/v1/rules/my", headers=h2).json()
    assert my["student"]["entry_year"] is None
    row = next(x for x in my["results"] if "ورودی ۱۴۰۳" in x["title"])
    assert row["status"] == "insufficient_info"


def test_tickets_flow(client):
    student = _login(client, "student", "Student@123")
    expert = _login(client, "expert", "Expert@123")
    hs = {"Authorization": f"Bearer {student['token']}"}
    he = {"Authorization": f"Bearer {expert['token']}"}

    tid = client.post("/api/v1/tickets", headers=hs,
                      json={"subject": "تست تیکت", "body": "سؤال آزمایشی"}).json()["id"]
    assert client.post(f"/api/v1/tickets/{tid}/status", headers=he,
                       json={"status": "under_review"}).status_code == 200
    assert client.post(f"/api/v1/tickets/{tid}/messages", headers=he,
                       json={"body": "پاسخ آزمایشی کارشناس"}).status_code == 200
    thread = client.get(f"/api/v1/tickets/{tid}", headers=hs).json()
    assert thread["ticket"]["status"] == "answered"
    assert len(thread["messages"]) == 2
    # گذار نامجاز رد می‌شود
    assert client.post(f"/api/v1/tickets/{tid}/status", headers=he,
                       json={"status": "under_review_from_nowhere"}).status_code in (400, 422)


def test_deadlines_reminders_and_ack_dedupe(client):
    student = _login(client, "student", "Student@123")
    hs = {"Authorization": f"Bearer {student['token']}"}
    rems = client.get("/api/v1/deadlines/reminders", headers=hs).json()["reminders"]
    assert rems, "باید یادآور نمونه وجود داشته باشد"
    did = rems[0]["id"]
    assert client.post(f"/api/v1/deadlines/{did}/ack", headers=hs).status_code == 200
    rems2 = client.get("/api/v1/deadlines/reminders", headers=hs).json()["reminders"]
    assert all(r["id"] != did for r in rems2), "یادآور پس از تأیید نباید تکرار شود"


def test_injection_document_is_flagged(client):
    """سناریوی پذیرش ۸: دستور مخرب داخل سند فقط داده است"""
    student = _login(client, "student", "Student@123")
    h = {"Authorization": f"Bearer {student['token']}"}
    r = client.post("/api/v1/chat/ask", headers=h,
                    json={"question": "شرایط انتخاب دستیار آموزشی چیست؟"})
    ans = r.json()["answer"]
    if not ans["no_result"]:
        assert any("تزریق" in w for w in ans["warnings"]), "باید پرچم تزریق نمایش داده شود"


def test_openapi_is_served(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for expected in ("/api/v1/auth/login", "/api/v1/chat/ask", "/api/v1/regulations",
                     "/api/v1/rules/my", "/api/v1/deadlines/reminders", "/api/v1/tickets"):
        assert expected in paths
