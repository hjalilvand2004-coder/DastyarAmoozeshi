# -*- coding: utf-8 -*-
"""سرویس گفت‌وگوی مستند (پرسش و پاسخ سه‌لایه با استناد واقعی)"""

from __future__ import annotations

import dataclasses
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.api.deps import get_conn, get_current_user
from app.answers import ask

router = APIRouter(prefix="/chat", tags=["chat"])


class AskIn(BaseModel):
    question: str
    session_id: int | None = None
    include_retired: bool = False


@router.post("/ask", summary="پرسش از دستیار مستند")
def ask_question(body: AskIn, user: dict = Depends(get_current_user),
                 conn=Depends(get_conn)):
    ans = ask(conn, user, body.question, session_id=body.session_id,
              include_retired=body.include_retired)
    return {"answer": dataclasses.asdict(ans)}


@router.get("/sessions", summary="فهرست گفت‌وگوهای من")
def my_sessions(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    rows = db.q(conn, "SELECT * FROM chat_sessions WHERE user_id=? ORDER BY id DESC LIMIT 50",
                (user["id"],))
    return {"sessions": rows}


@router.get("/sessions/{session_id}/messages", summary="پیام‌های یک گفت‌وگو")
def session_messages(session_id: int, user: dict = Depends(get_current_user),
                     conn=Depends(get_conn)):
    s = db.q1(conn, "SELECT * FROM chat_sessions WHERE id=?", (session_id,))
    if not s or s["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="گفت‌وگو یافت نشد")
    rows = db.q(conn, "SELECT * FROM chat_messages WHERE session_id=? ORDER BY id", (session_id,))
    out = []
    for r in rows:
        try:
            meta = json.loads(r["meta"]) if r.get("meta") else {}
        except json.JSONDecodeError:
            meta = {}
        out.append({"id": r["id"], "role": r["role"], "content": r["content"],
                    "meta": meta, "created_at": r["created_at"]})
    return {"messages": out}
