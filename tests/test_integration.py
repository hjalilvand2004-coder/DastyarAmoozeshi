# -*- coding: utf-8 -*-
"""تست‌های «ادغام با سایر سامانه‌ها» — احراز کلید، اسکوپ، نرخ، سرویس‌ها و ویجت"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.server import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import app.config as cfg
    tmp = tmp_path_factory.mktemp("integ")
    db_file = tmp / "integ.db"
    old = cfg.db_path
    cfg.db_path = lambda: db_file
    import app.api.deps as deps
    deps.db_path = cfg.db_path
    from app import db as app_db, seed
    conn = app_db.connect(db_file)
    seed.seed_if_empty(conn)
    conn.close()
    app = create_app()
    with TestClient(app) as c:
        yield c
    cfg.db_path = old


def _key(client, code="pajooheshyar") -> str:
    """کلید سامانه متصل نمونه را از همان دیتابیس ایزوله می‌خواند"""
    import app.api.deps as deps
    from app import db as app_db
    conn = app_db.connect(deps.db_path())
    try:
        row = app_db.q1(conn, "SELECT api_key FROM external_systems WHERE code=?", (code,))
        assert row, f"سامانه نمونه {code} نباید غایب باشد"
        return row["api_key"]
    finally:
        conn.close()


def _admin_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


H = lambda k: {"X-API-Key": k}


# ---------- احراز کلید ----------

def test_ask_without_key_is_401(client):
    r = client.post("/api/v1/integration/v1/ask", json={"question": "شرایط کارورزی؟"})
    assert r.status_code == 401


def test_ask_with_bad_key_is_401(client):
    r = client.post("/api/v1/integration/v1/ask", json={"question": "شرایط کارورزی؟"},
                    headers=H("d360_wrong"))
    assert r.status_code == 401


def test_whoami_reports_scopes(client):
    k = _key(client, "pajooheshyar")
    r = client.get("/api/v1/integration/v1/whoami", headers=H(k))
    assert r.status_code == 200
    data = r.json()["system"]
    assert data["code"] == "pajooheshyar"
    assert "ask" in data["scopes"] and "tickets.create" not in data["scopes"]


def test_scope_enforcement_403(client):
    """پژوهشیار اسکوپ tickets.create ندارد ← باید ۴۰۳ بگیرد"""
    k = _key(client, "pajooheshyar")
    r = client.post("/api/v1/integration/v1/tickets",
                    json={"subject": "تست", "body": "تست"}, headers=H(k))
    assert r.status_code == 403


def test_deactivated_key_is_401(client):
    h = _admin_headers(client)
    sys_id = client.get("/api/v1/integrations", headers=h).json()["systems"][0]["id"]
    code = client.get("/api/v1/integrations", headers=h).json()["systems"][0]["code"]
    k = _key(client, code)
    client.post(f"/api/v1/integrations/{sys_id}/active", json={"active": False}, headers=h)
    r = client.get("/api/v1/integration/v1/whoami", headers=H(k))
    assert r.status_code == 401
    client.post(f"/api/v1/integrations/{sys_id}/active", json={"active": True}, headers=h)
    assert client.get("/api/v1/integration/v1/whoami", headers=H(k)).status_code == 200


# ---------- پرسش مستند ----------

def test_ask_returns_layered_answer_with_citations(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/ask",
                    json={"question": "شرایط ثبت‌نام کارورزی چیست؟",
                          "topic": "کارورزی",
                          "student": {"level": "کارشناسی", "major": "مهندسی کامپیوتر",
                                      "entry_year": 1402, "gpa": 14.5}},
                    headers=H(k))
    assert r.status_code == 200, r.text
    ans = r.json()["answer"]
    assert ans["no_result"] is False
    assert ans["sources"], "پاسخ باید استناد داشته باشد"
    assert any("نمونه" in w for w in ans["warnings"]), "برچسب نمونه/غیررسمی الزامی است"
    meta = r.json()["meta"]
    assert meta["system_code"] == "pajooheshyar" and meta["sample_data"] is True


def test_ask_irrelevant_question_is_honest(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/ask",
                    json={"question": "قیمت بلیط فوتبال استقلال چند است؟"}, headers=H(k))
    assert r.status_code == 200
    ans = r.json()["answer"]
    assert ans["no_result"] is True and not ans["sources"]


def test_ask_retired_doc_never_current(client):
    """سند ملغی هرگز به‌عنوان قانون جاری استناد نمی‌شود (فقط با درخواست صریح و با برچسب)"""
    k = _key(client)
    r = client.post("/api/v1/integration/v1/ask",
                    json={"question": "انتخاب واحد حضوری چگونه انجام می‌شود؟"}, headers=H(k))
    assert r.status_code == 200
    ans = r.json()["answer"]
    # در پاسخ پیش‌فرض (include_retired=False) هیچ استنادی از سند ملغی نمی‌آید
    assert not [s for s in ans["sources"] if s["status"] == "retired"]


# ---------- جست‌وجوی آیین‌نامه ----------

def test_regulations_search_finds_clause(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/regulations/search",
                    json={"query": "حداقل معدل کارورزی"}, headers=H(k))
    assert r.status_code == 200
    results = r.json()["results"]
    assert results and any("کارورزی" in s["excerpt"] for s in results)
    assert all(s["status"] == "published" for s in results), "فقط اسناد منتشرشده"


def test_regulation_get_published_only(client):
    k = _key(client)
    r = client.get("/api/v1/integration/v1/regulations/999999", headers=H(k))
    assert r.status_code == 404


# ---------- قواعد قطعی ----------

def test_rules_evaluate_satisfied(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/rules/evaluate",
                    json={"query": "معدل کارورزی",
                          "student": {"gpa": 14.5}}, headers=H(k))
    assert r.status_code == 200
    results = r.json()["results"]
    assert results
    assert any(x["status"] == "satisfied" for x in results)


def test_rules_evaluate_insufficient_info(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/rules/evaluate",
                    json={"query": "معدل کارورزی", "student": {}}, headers=H(k))
    results = r.json()["results"]
    assert results and any(x["status"] == "insufficient_info" for x in results)


def test_rules_evaluate_needs_rule_id_or_query(client):
    k = _key(client)
    r = client.post("/api/v1/integration/v1/rules/evaluate", json={"student": {}}, headers=H(k))
    assert r.status_code == 400


# ---------- مهلت‌ها و فرایندها ----------

def test_deadlines_readable(client):
    k = _key(client, "barnamehriz")
    r = client.get("/api/v1/integration/v1/deadlines?days=60", headers=H(k))
    assert r.status_code == 200
    rows = r.json()["deadlines"]
    assert rows and all(0 <= d["days_left"] <= 60 for d in rows)
    assert all("date_fa" in d for d in rows)


def test_deadlines_scope_enforced(client):
    """پژوهشیار اسکوپ deadlines.read ندارد"""
    k = _key(client, "pajooheshyar")
    assert client.get("/api/v1/integration/v1/deadlines", headers=H(k)).status_code == 403


def test_processes_readable(client):
    k = _key(client)
    r = client.get("/api/v1/integration/v1/processes?query=کارورزی", headers=H(k))
    assert r.status_code == 200
    procs = r.json()["processes"]
    assert procs and procs[0]["key"] == "karvarizi" and procs[0]["steps"]


# ---------- تیکت ----------

def test_ticket_created_from_external_system(client):
    k = _key(client, "barnamehriz")
    r = client.post("/api/v1/integration/v1/tickets",
                    json={"subject": "ابهام در مهلت حذف و اضافه",
                          "body": "دانشجو در برنامه‌ریز سؤال داشت.",
                          "student": {"full_name": "علی محمدی"}}, headers=H(k))
    assert r.status_code == 200, r.text
    assert r.json()["ticket_id"] > 0
    assert r.json()["subject"].startswith("[سامانه برنامه‌ریز")


# ---------- محدودیت نرخ ----------

def test_rate_limit_429(client):
    h = _admin_headers(client)
    r = client.post("/api/v1/integrations", headers=h, json={
        "name": "سامانه پرترافیک تست", "code": "flood-test",
        "scopes": ["ask"], "rate_limit_per_hour": 1})
    assert r.status_code == 200, r.text
    k = r.json()["api_key"]
    assert client.post("/api/v1/integration/v1/ask", json={"question": "شرایط کارورزی؟"},
                       headers=H(k)).status_code == 200
    assert client.post("/api/v1/integration/v1/ask", json={"question": "شرایط کارورزی؟"},
                       headers=H(k)).status_code == 429


# ---------- مدیریت ----------

def test_admin_create_and_rotate_key(client):
    h = _admin_headers(client)
    # دانشجو اجازه مدیریت ندارد
    r = client.post("/api/v1/auth/login", json={"username": "student", "password": "Student@123"})
    assert client.get("/api/v1/integrations",
                      headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 403

    made = client.post("/api/v1/integrations", headers=h, json={
        "name": "سامانه آزمایشی جدید", "code": "new-sys", "scopes": ["ask"],
        "rate_limit_per_hour": 30, "is_widget": False, "contact": "IT"}).json()
    k1 = made["api_key"]
    assert client.get("/api/v1/integration/v1/whoami", headers=H(k1)).status_code == 200

    k2 = client.post(f"/api/v1/integrations/{made['id']}/rotate", headers=h).json()["api_key"]
    assert k2 != k1
    assert client.get("/api/v1/integration/v1/whoami", headers=H(k1)).status_code == 401
    assert client.get("/api/v1/integration/v1/whoami", headers=H(k2)).status_code == 200

    # لاگ ثبت شده باشد
    logs = client.get(f"/api/v1/integrations/{made['id']}/logs", headers=h).json()["logs"]
    assert any(l["endpoint"].endswith("/whoami") for l in logs)


# ---------- ویجت ----------

def test_widget_js_served(client):
    for path in ("/api/v1/integration/widget.js", "/widget.js"):
        r = client.get(path)
        assert r.status_code == 200
        assert "X-API-Key" in r.text and "d360body" in r.text
        assert r.headers["content-type"].startswith("application/javascript")


def test_integration_demo_page(client):
    k = _key(client, "portal-widget")
    r = client.get("/integration-demo", params={"key": k})
    assert r.status_code == 200 and "data-key" in r.text and "پژوهشیار" in r.text
    assert client.get("/integration-demo", params={"key": "bad"}).status_code == 403
