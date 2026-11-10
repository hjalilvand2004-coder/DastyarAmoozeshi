# -*- coding: utf-8 -*-
"""تست سرویس‌های یادآور، تیکت و مشاوره"""

import datetime
import json

import pytest

from app import services


def test_deadline_ack_flow(conn, student_user):
    rows = services.list_deadlines(conn, student_user)
    assert rows
    upcoming = [r for r in rows if r["days_left"] > 0]
    target = upcoming[0]
    services.ack_deadline(conn, student_user, target["id"])
    rows = services.list_deadlines(conn, student_user)
    t = next(r for r in rows if r["id"] == target["id"])
    assert t["acked"]


def test_deadline_requires_manage_perm(conn, student_user):
    with pytest.raises(PermissionError):
        services.create_deadline(conn, student_user, "رویداد تقلبی",
                                 (datetime.date.today() + datetime.timedelta(days=3)).isoformat())


def test_ticket_flow_and_transitions(conn, student_user, expert_user):
    tid = services.create_ticket(conn, student_user, "سؤال آزمایشی", "متن سؤال")
    thread = services.ticket_thread(conn, student_user, tid)
    assert thread["ticket"]["status"] == "submitted"
    # دانشجو اجازه گذار ندارد
    with pytest.raises(PermissionError):
        services.transition_ticket(conn, student_user, tid, "under_review")
    services.transition_ticket(conn, expert_user, tid, "under_review")
    services.transition_ticket(conn, expert_user, tid, "needs_info")
    # پیام دانشجو در وضعیت needs_info → برمی‌گردد به در حال بررسی
    services.add_ticket_message(conn, student_user, tid, "این هم اطلاعات تکمیلی است.")
    t = services.ticket_thread(conn, expert_user, tid)["ticket"]
    assert t["status"] == "under_review"
    services.transition_ticket(conn, expert_user, tid, "answered")
    # گذار غیرمجاز
    with pytest.raises(ValueError):
        services.transition_ticket(conn, expert_user, tid, "needs_info")
    services.transition_ticket(conn, expert_user, tid, "closed")
    with pytest.raises(ValueError):
        services.add_ticket_message(conn, student_user, tid, "پیام بعد از بستن")


def test_ticket_ownership(conn, student_user, expert_user):
    tid = services.create_ticket(conn, student_user, "تیکت شخصی", "بدنه")
    # کاربر دوم دانشجو نمی‌تواند تیکت دیگری را ببیند
    other = services.login(conn, "student2", "Student@123")
    with pytest.raises(PermissionError):
        services.ticket_thread(conn, other, tid)


def test_advisor_analysis(conn, student_user):
    student = services.get_student_for_user(conn, student_user)
    courses = services._load_courses(conn, student_user)
    cs301 = next(c for c in courses if c["code"] == "CS301")   # پیش‌نیاز CS201 دارد
    res = services.analyze_course(conn, student_user, student, cs301["id"])
    assert res["status"] == "not_satisfied"
    cs202 = next(c for c in courses if c["code"] == "CS202")   # پیش‌نیاز CS101 گذرانده شده
    res = services.analyze_course(conn, student_user, student, cs202["id"])
    assert res["status"] == "satisfied"
    sug = services.suggest_next_courses(conn, student_user, student)
    assert sug["items"] and sug["items"][0]["ok"]
    audit = services.graduation_audit(conn, student_user, student)
    assert audit["passed"] == 64 and audit["required"] == 140


def test_advisor_insufficient_info(conn):
    user = services.login(conn, "student2", "Student@123")
    # سارا فقط CS101 گذرانده اما passed_courses دارد؛ کاربر بدون پروفایل:
    u2 = dict(services.login(conn, "admin", "Admin@123"))
    res = services.suggest_next_courses(conn, u2, None)
    assert res["status"] == "insufficient_info"


def test_process_guides(conn, student_user):
    procs = services.list_processes(conn, student_user)
    assert procs
    kar = next(p for p in procs if p["key"] == "karvarizi")
    steps = json.loads(kar["steps"])
    assert len(steps) == 5
    # هیچ فرایندی «ثبت موفق» ادعا نمی‌کند
    assert not any("موفق" in s for s in steps)
