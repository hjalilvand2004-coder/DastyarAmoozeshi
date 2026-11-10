# -*- coding: utf-8 -*-
"""دیتابیس SQLite - طرح اولیه (v1)"""

import sqlite3
from pathlib import Path

from .config import DEFAULT_SETTINGS, db_path

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS universities(
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL REFERENCES universities(id),
  username TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT DEFAULT '',
  role TEXT NOT NULL,
  student_id INTEGER,
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(university_id, username)
);

CREATE TABLE IF NOT EXISTS students(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  user_id INTEGER,
  full_name TEXT DEFAULT '',
  level TEXT DEFAULT '',
  major TEXT DEFAULT '',
  entry_year INTEGER,
  gpa REAL,
  passed_credits INTEGER DEFAULT 0,
  passed_courses TEXT DEFAULT '[]',
  profile_extra TEXT DEFAULT '{}',
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  doc_type TEXT DEFAULT 'text',
  status TEXT DEFAULT 'draft',
  version_no INTEGER DEFAULT 1,
  parent_id INTEGER,
  effective_from TEXT,
  effective_until TEXT,
  scope_level TEXT,
  scope_major TEXT,
  scope_entry_from INTEGER,
  scope_entry_to INTEGER,
  file_path TEXT,
  url TEXT,
  source_note TEXT DEFAULT '',
  is_official INTEGER DEFAULT 0,
  flags TEXT DEFAULT '[]',
  created_by INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  retired_at TEXT,
  retired_reason TEXT
);

CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  clause_ref TEXT DEFAULT '',
  page_no INTEGER,
  text TEXT NOT NULL,
  normalized TEXT DEFAULT '',
  idx INTEGER DEFAULT 0,
  flags TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);

CREATE TABLE IF NOT EXISTS rules(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  source_document_id INTEGER,
  source_clause TEXT DEFAULT '',
  version_no INTEGER DEFAULT 1,
  scope TEXT DEFAULT '{}',
  cond_json TEXT NOT NULL,
  messages TEXT DEFAULT '{}',
  review_fields TEXT DEFAULT '[]',
  status TEXT DEFAULT 'draft',
  approved_by INTEGER,
  approved_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_sessions(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  title TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages(
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  meta TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS processes(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  key TEXT UNIQUE,
  title TEXT NOT NULL,
  steps TEXT NOT NULL,
  required_docs TEXT DEFAULT '[]',
  target_system TEXT DEFAULT '',
  target_url TEXT DEFAULT '',
  keywords TEXT DEFAULT '[]',
  source_document_id INTEGER,
  notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS deadlines(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  date_iso TEXT NOT NULL,
  scope TEXT DEFAULT '{}',
  source_document_id INTEGER,
  notes TEXT DEFAULT '',
  version_no INTEGER DEFAULT 1,
  active INTEGER DEFAULT 1,
  created_by INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deadline_acks(
  id INTEGER PRIMARY KEY,
  deadline_id INTEGER NOT NULL REFERENCES deadlines(id) ON DELETE CASCADE,
  version_no INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  ack_at TEXT DEFAULT (datetime('now')),
  UNIQUE(deadline_id, version_no, user_id)
);

CREATE TABLE IF NOT EXISTS tickets(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  subject TEXT NOT NULL,
  status TEXT DEFAULT 'submitted',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ticket_messages(
  id INTEGER PRIMARY KEY,
  ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  is_staff INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS courses(
  id INTEGER PRIMARY KEY,
  university_id INTEGER NOT NULL,
  code TEXT UNIQUE,
  name TEXT NOT NULL,
  credits INTEGER DEFAULT 2,
  prereqs TEXT DEFAULT '[]',
  keywords TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY,
  university_id INTEGER,
  user_id INTEGER,
  action TEXT NOT NULL,
  detail TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: در FastAPI هر درخواست اتصال اختصاصی خودش را می‌گیرد
    # و در همین تابع بسته می‌شود؛ خود SQLite نوشتن‌ها را سریال می‌کند.
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def q(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def q1(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    rows = q(conn, sql, params)
    return rows[0] if rows else None


def ex(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid


def get_settings(conn: sqlite3.Connection) -> dict:
    out = dict(DEFAULT_SETTINGS)
    for r in q(conn, "SELECT key, value FROM settings"):
        out[r["key"]] = r["value"]
    return out


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    ex(conn, "INSERT INTO settings(key, value) VALUES(?, ?) "
             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def audit(conn: sqlite3.Connection, user: dict | None, action: str, detail: str = "") -> None:
    uid = user["id"] if user else None
    uid_uni = user["university_id"] if user else None
    ex(conn, "INSERT INTO audit_log(university_id, user_id, action, detail) VALUES(?,?,?,?)",
       (uid_uni, uid, action, detail))
