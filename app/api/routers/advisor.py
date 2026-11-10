# -*- coding: utf-8 -*-
"""سرویس مشاور تحصیلی: تحلیل درس، پیشنهاد درس بعدی، ممیزی فارغ‌التحصیلی، پروفایل دانشجویان"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.api.deps import get_conn, get_current_user
from app.services import (analyze_course, get_student_for_user, graduation_audit,
                          list_students, require, suggest_next_courses,
                          update_student_profile)

router = APIRouter(prefix="/advisor", tags=["advisor"])


def _resolve_student(conn, user, student_id: int | None) -> dict:
    if student_id and student_id != (user.get("student_id") or -1):
        require(user, "advisor.student")
        stu = db.q1(conn, "SELECT * FROM students WHERE id=?", (student_id,))
        if not stu:
            raise HTTPException(status_code=404, detail="دانشجو یافت نشد")
        return dict(stu)
    require(user, "advisor.self")
    stu = get_student_for_user(conn, user)
    if not stu:
        raise HTTPException(status_code=404,
                            detail="پروفایل دانشجویی به حساب شما متصل نیست")
    return stu


@router.get("/students", summary="فهرست دانشجویان (کارشناس)")
def students(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    require(user, "advisor.student")
    return {"students": list_students(conn, user)}


@router.get("/courses", summary="فهرست دروس")
def courses(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    rows = db.q(conn, "SELECT * FROM courses WHERE university_id=? ORDER BY code",
                (user["university_id"],))
    for r in rows:
        try:
            r["prereqs"] = __import__("json").loads(r.get("prereqs") or "[]")
        except Exception:
            r["prereqs"] = []
    return {"courses": rows}


@router.get("/analyze/{course_id}", summary="تحلیل شرایط یک درس برای دانشجو")
def analyze(course_id: int, student_id: int | None = None,
            user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    stu = _resolve_student(conn, user, student_id)
    return analyze_course(conn, user, stu, course_id)


@router.get("/next-courses", summary="پیشنهاد دروس قابل اخذ در ترم بعد")
def next_courses(student_id: int | None = None, limit: int = 5,
                 user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    stu = _resolve_student(conn, user, student_id)
    return suggest_next_courses(conn, user, stu, limit)


@router.get("/graduation", summary="ممیزی فارغ‌التحصیلی")
def graduation(student_id: int | None = None,
               user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    stu = _resolve_student(conn, user, student_id)
    return graduation_audit(conn, user, stu)


class ProfileIn(BaseModel):
    fields: dict


@router.post("/students/{student_id}/profile", summary="ویرایش پروفایل دانشجو (کارشناس/خود دانشجو)")
def edit_profile(student_id: int, body: ProfileIn,
                 user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    allowed = {"level", "major", "entry_year", "gpa", "passed_credits",
               "passed_courses", "profile_extra"}
    fields = {k: v for k, v in body.fields.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="فیلد مجازی برای ویرایش ارسال نشده است")
    update_student_profile(conn, user, student_id, fields)
    return {"ok": True}
