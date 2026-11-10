# -*- coding: utf-8 -*-
import pytest

from app import db, seed


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    seed.seed_if_empty(c)
    yield c
    c.close()


@pytest.fixture()
def student_user(conn):
    from app.services import login
    return login(conn, "student", "Student@123")


@pytest.fixture()
def expert_user(conn):
    from app.services import login
    return login(conn, "expert", "Expert@123")


@pytest.fixture()
def content_user(conn):
    from app.services import login
    return login(conn, "content", "Content@123")


@pytest.fixture()
def approver_user(conn):
    from app.services import login
    return login(conn, "approver", "Approver@123")
