# -*- coding: utf-8 -*-
"""تست‌های نسخه ۰.۴.۰: نوع اسناد (آیین‌نامه/دستورالعمل/بخشنامه)، ورود یکپارچه پرتال SSO، مهاجرت DB"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time

import pytest
from fastapi.testclient import TestClient

from app import db
from app.answers import DOC_CATEGORIES, ask
from app.security import parse_token, verify_jwt_rs256


# ---------- دسته‌بندی اسناد ----------

def test_seed_categories(conn):
    rows = db.q(conn, "SELECT DISTINCT doc_category FROM documents")
    cats = {r["doc_category"] for r in rows}
    assert {"ayinnameh", "dastoorolamal", "bakhshnameh", "other"} <= cats


def test_chat_filter_bakhshnameh(conn, student_user):
    ans = ask(conn, student_user, "مهلت پرداخت شهریه چیست؟", doc_category="bakhshnameh")
    assert not ans.no_result
    assert ans.sources, "باید استناد داشته باشد"
    assert all(s["doc_category_fa"] == "بخشنامه" for s in ans.sources)


def test_chat_filter_dastoorolamal(conn, student_user):
    ans = ask(conn, student_user, "حداقل معدل کارورزی چند است؟", doc_category="dastoorolamal")
    assert not ans.no_result
    assert all(s["doc_category_fa"] == "دستورالعمل" for s in ans.sources)
    # در دستورالعمل کارورزی معدل ۱۴ است (نه ماده ۱۸ آیین‌نامه با ۱۲)
    assert any("۱۴" in s["excerpt"] or "14" in s["excerpt"] for s in ans.sources)


def test_chat_filter_ayinnameh(conn, student_user):
    ans = ask(conn, student_user, "حداکثر واحدهای مجاز در نیمسال چیست؟", doc_category="ayinnameh")
    assert not ans.no_result
    assert all(s["doc_category_fa"] == "آیین‌نامه" for s in ans.sources)


def test_chat_filter_other_excludes_doc(conn, student_user):
    ans = ask(conn, student_user, "پذیرش در خوابگاه چه شرایطی دارد؟", doc_category="bakhshnameh")
    assert ans.no_result, "خوابگاه «سایر» است و نباید در بخشنامه‌ها پیدا شود"


# ---------- API: اعتبارسنجی doc_category ----------

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import app.config as cfg
    tmp = tmp_path_factory.mktemp("v040")
    db_file = tmp / "v040.db"
    old = cfg.db_path
    cfg.db_path = lambda: db_file
    import app.api.deps as deps
    deps.db_path = cfg.db_path
    from app import seed
    conn = db.connect(db_file)
    seed.seed_if_empty(conn)
    conn.close()
    from app.api.server import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c
    cfg.db_path = old


def test_chat_invalid_category_is_400(client):
    r = client.post("/api/v1/auth/login", json={"username": "student", "password": "Student@123"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    resp = client.post("/api/v1/chat/ask", json={"question": "سقف واحد چند است؟",
                                                 "doc_category": "invalid-cat"}, headers=h)
    assert resp.status_code == 400


def test_chat_with_category_ok(client):
    r = client.post("/api/v1/auth/login", json={"username": "student", "password": "Student@123"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    resp = client.post("/api/v1/chat/ask", json={"question": "مهلت پرداخت شهریه چیست؟",
                                                 "doc_category": "bakhshnameh"}, headers=h)
    assert resp.status_code == 200
    ans = resp.json()["answer"]
    assert not ans["no_result"]
    assert all(s["doc_category_fa"] == "بخشنامه" for s in ans["sources"])


# ---------- مهاجرت پایگاه‌داده ----------

def test_migration_adds_doc_category(tmp_path):
    import sqlite3
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("CREATE TABLE documents(id INTEGER PRIMARY KEY, title TEXT, doc_type TEXT DEFAULT 'text');")
    c.execute("INSERT INTO documents(title) VALUES('سند قدیمی')")
    c.commit()
    c.close()
    c2 = db.connect(p)
    cols = {r["name"] for r in c2.execute("PRAGMA table_info(documents)")}
    assert "doc_category" in cols
    row = db.q1(c2, "SELECT doc_category FROM documents WHERE title='سند قدیمی'")
    assert row is not None and row["doc_category"] == ""
    c2.close()


# ---------- SSO: نقطه ورود یکپارچه ----------

@pytest.fixture()
def sso_conn(tmp_path, monkeypatch):
    """اتصال ایزوله + بستن فراخوانی شبکه‌ای discovery با ایست‌بار (hermetic)"""
    c = db.connect(tmp_path / "sso.db")
    from app import seed
    seed.seed_if_empty(c)
    import app.api.routers.auth as auth_mod
    calls = {}

    def fake_discovery(issuer):
        calls["issuer"] = issuer
        return {"issuer": issuer,
                "authorization_endpoint": "http://hub.test/protocol/openid-connect/auth",
                "token_endpoint": "http://hub.test/protocol/openid-connect/token",
                "userinfo_endpoint": "http://hub.test/protocol/openid-connect/userinfo"}

    monkeypatch.setattr(auth_mod, "_oidc_discovery", fake_discovery)
    yield c, calls
    c.close()


def test_sso_entry_starts_oidc_with_pkce(sso_conn):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    c, calls = sso_conn
    app = create_app()

    # بستن وابستگی get_conn به اتصال ایزوله
    from app.api.deps import get_conn
    app.dependency_overrides[get_conn] = lambda: c
    try:
        with TestClient(app) as cl:
            r = cl.get("/api/v1/auth/sso/university/entry", follow_redirects=False)
        assert r.status_code == 302, r.text
        loc = r.headers["location"]
        assert loc.startswith("http://hub.test/protocol/openid-connect/auth?")
        assert "client_id=amoozeshyar360" in loc
        assert "code_challenge_method=S256" in loc
        assert "code_challenge=" in loc and "state=" in loc
        assert "redirect_uri=" in loc and "188.212.96.235%3A8091" in loc.replace("%3A", "%3A")
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_sso_entry_rejects_bad_token(sso_conn):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.api.deps import get_conn
    c, _ = sso_conn
    db.set_setting(c, "sso_hub_secret", "sec-test-123")
    app = create_app()
    app.dependency_overrides[get_conn] = lambda: c
    try:
        with TestClient(app) as cl:
            r = cl.get("/api/v1/auth/sso/university/entry", params={"token": "not-a-jwt"},
                       follow_redirects=False)
        assert r.status_code == 302
        assert "sso_error=" in r.headers["location"]
    finally:
        app.dependency_overrides.pop(get_conn, None)


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _make_hs256(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64u(json.dumps(header, separators=(",", ":")).encode())
    p = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    import hmac as _hmac
    s = _b64u(_hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{s}"


def test_sso_entry_hub_token_hs256_autologin(sso_conn):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.api.deps import get_conn
    c, _ = sso_conn
    db.set_setting(c, "sso_hub_secret", "sec-test-123")
    app = create_app()
    app.dependency_overrides[get_conn] = lambda: c
    now = int(time.time())
    tok = _make_hs256({"sub": "hub-user-1", "preferred_username": "haccount",
                       "name": "کاربر پرتال", "roles": ["amoozeshyar.access"], "exp": now + 300},
                      "sec-test-123")
    try:
        with TestClient(app) as cl:
            r = cl.get("/api/v1/auth/sso/university/entry", params={"token": tok},
                       follow_redirects=False)
        assert r.status_code == 302, r.text
        loc = r.headers["location"]
        assert "/sso/callback?token=" in loc and "sso=1" in loc
        app_token = loc.split("token=")[1].split("&")[0]
        body = parse_token(app_token)
        assert body and body["username"] == "haccount" and body["role"] == "student"
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_sso_role_mapping_app_key():
    from app.api.routers.auth import _map_role
    assert _map_role({"roles": ["amoozeshyar.admin"]}, "student") == "system_admin"
    assert _map_role({"roles": ["amoozeshyar.expert"]}, "student") == "expert"
    assert _map_role({"roles": ["amoozeshyar.approver"]}, "student") == "approver"
    assert _map_role({"roles": ["amoozeshyar.content"]}, "student") == "content_admin"
    assert _map_role({"roles": ["amoozeshyar.access"]}, "student") == "student"
    assert _map_role({"roles": ["barnamehyar.admin"]}, "student") == "student"
    assert _map_role({"realm_access": {"roles": ["expert"]}}, "student") == "expert"


# ---------- RS256 (jwks) ----------

def _is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    for sp in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % sp == 0:
            return n == sp
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _gen_prime(bits: int) -> int:
    while True:
        p = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(p):
            return p


def _gen_rsa_key(bits: int = 1024):
    e = 65537
    while True:
        p, q = _gen_prime(bits // 2), _gen_prime(bits // 2)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        try:
            d = pow(e, -1, phi)
        except ValueError:
            continue
        return p, q, e, d, p * q


_SHA256_DI = bytes.fromhex("3031300d060960864801650304020105000420")


def test_verify_jwt_rs256_with_jwks():
    p, q, e, d, n = _gen_rsa_key(1024)
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": "k1"}
    payload = {"sub": "hub-user-2", "preferred_username": "rs-user", "exp": now + 300}
    h = _b64u(json.dumps(header, separators=(",", ":")).encode())
    pl = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    digest = hashlib.sha256(f"{h}.{pl}".encode("ascii")).digest()
    klen = (n.bit_length() + 7) // 8
    padded = b"\x00\x01" + b"\xff" * (klen - len(digest) - len(_SHA256_DI) - 3) + b"\x00" + _SHA256_DI + digest
    m = int.from_bytes(padded, "big")
    sig = pow(m, d, n).to_bytes(klen, "big")
    token = f"{h}.{pl}.{_b64u(sig)}"

    jwk = {"kty": "RSA", "kid": "k1", "alg": "RS256", "n": _b64u(n.to_bytes(klen, "big")), "e": _b64u(e.to_bytes(3, "big"))}
    body = verify_jwt_rs256(token, {"keys": [jwk]})
    assert body and body["preferred_username"] == "rs-user"

    # امضای دستکاری‌شده باید رد شود
    bad = f"{h}.{pl}.{_b64u(bytes(klen))}"
    assert verify_jwt_rs256(bad, {"keys": [jwk]}) is None

    # توکن منقضی باید رد شود
    expired = dict(payload, exp=now - 10)
    pl2 = _b64u(json.dumps(expired, separators=(",", ":")).encode())
    digest2 = hashlib.sha256(f"{h}.{pl2}".encode("ascii")).digest()
    padded2 = b"\x00\x01" + b"\xff" * (klen - len(digest2) - len(_SHA256_DI) - 3) + b"\x00" + _SHA256_DI + digest2
    sig2 = pow(int.from_bytes(padded2, "big"), d, n).to_bytes(klen, "big")
    assert verify_jwt_rs256(f"{h}.{pl2}.{_b64u(sig2)}", {"keys": [jwk]}) is None


def test_doc_categories_constant():
    assert DOC_CATEGORIES == {"ayinnameh": "آیین‌نامه", "dastoorolamal": "دستورالعمل",
                              "bakhshnameh": "بخشنامه", "other": "سایر"}


# ---------- نسخه ۰.۵.۰: ویجت داشیار «دانشگاه هوشمند من» ----------

def test_msu_agent_js_served(client):
    r = client.get("/api/v1/integration/msu-agent.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert "MSUAgent" in r.text
    assert "MSUHostContext" in r.text  # پل وضعیت دانشجو


def test_msu_config_requires_auth(client):
    assert client.get("/api/v1/integrations/msu/config").status_code == 401


def test_msu_config_defaults(client):
    r = client.post("/api/v1/auth/login", json={"username": "student", "password": "Student@123"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    d = client.get("/api/v1/integrations/msu/config", headers=h).json()
    assert d["enabled"] is True
    assert d["url"] == "http://188.212.96.235:8096"
    assert d["origin"] == "amoozeshyar360"


def test_msu_disabled_via_setting(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    client.post("/api/v1/admin/settings", json={"key": "msu_agent_enabled", "value": "0"}, headers=h)
    d = client.get("/api/v1/integrations/msu/config", headers=h).json()
    assert d["enabled"] is False
    client.post("/api/v1/admin/settings", json={"key": "msu_agent_enabled", "value": "1"}, headers=h)
