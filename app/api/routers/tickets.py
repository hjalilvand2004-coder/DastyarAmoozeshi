# -*- coding: utf-8 -*-
"""سرویس تیکت به کارشناس آموزش: ثبت، گفت‌وگو، گذار وضعیت"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_conn, get_current_user
from app.services import (TICKET_STATUS_FA, TICKET_TRANSITIONS, add_ticket_message,
                          create_ticket, has_perm, list_tickets, ticket_thread,
                          transition_ticket)

router = APIRouter(prefix="/tickets", tags=["tickets"])

STATUS_FA = TICKET_STATUS_FA


@router.get("", summary="فهرست تیکت‌ها (دانشجو: خودش / کارشناس: همه)")
def tickets(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    rows = list_tickets(conn, user)
    staff = has_perm(user, "tickets.handle")
    for t in rows:
        t["allowed_transitions"] = sorted(TICKET_TRANSITIONS.get(t["status"], set())) if staff else []
    return {"tickets": rows, "is_staff": staff}


class TicketIn(BaseModel):
    subject: str
    body: str = ""


@router.post("", summary="ثبت تیکت جدید")
def new_ticket(body: TicketIn, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    tid = create_ticket(conn, user, body.subject, body.body)
    return {"id": tid, "status": "submitted"}


@router.get("/{ticket_id}", summary="جزئیات تیکت + پیام‌ها")
def get_ticket(ticket_id: int, user: dict = Depends(get_current_user),
               conn=Depends(get_conn)):
    data = ticket_thread(conn, user, ticket_id)
    staff = has_perm(user, "tickets.handle")
    data["ticket"]["allowed_transitions"] = \
        sorted(TICKET_TRANSITIONS.get(data["ticket"]["status"], set())) if staff else []
    data["is_staff"] = staff
    return data


class MessageIn(BaseModel):
    body: str


@router.post("/{ticket_id}/messages", summary="افزودن پیام")
def add_message(ticket_id: int, body: MessageIn,
                user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    add_ticket_message(conn, user, ticket_id, body.body)
    return {"ok": True}


class TransitionIn(BaseModel):
    status: str


@router.post("/{ticket_id}/status", summary="گذار وضعیت (کارشناس)")
def change_status(ticket_id: int, body: TransitionIn,
                  user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    transition_ticket(conn, user, ticket_id, body.status)
    return {"ok": True, "status": body.status,
            "status_fa": STATUS_FA.get(body.status, body.status)}
