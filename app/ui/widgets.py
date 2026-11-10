# -*- coding: utf-8 -*-
"""ویجت‌های مشترک"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout


class Card(QFrame):
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(14, 12, 14, 12)
        self._v.setSpacing(8)
        if title:
            t = QLabel(title)
            t.setObjectName("sectionTitle")
            self._v.addWidget(t)

    @property
    def body(self) -> QVBoxLayout:
        return self._v


def banner(text: str, kind: str = "warn") -> QFrame:
    colors = {
        "warn": ("#fff8e1", "#e6c453", "#7a5c00"),
        "danger": ("#fdecea", "#f5b9ae", "#8a1c11"),
        "info": ("#e8eaf6", "#b9c0ea", "#283593"),
    }
    bg, border, fg = colors.get(kind, colors["info"])
    f = QFrame()
    f.setStyleSheet(f"background:{bg};border:1px solid {border};border-radius:8px;")
    v = QVBoxLayout(f)
    v.setContentsMargins(10, 6, 10, 6)
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setStyleSheet(f"color:{fg};border:none;")
    v.addWidget(lb)
    return f


def info_box(parent, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def error_box(parent, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def hline() -> QFrame:
    ln = QFrame()
    ln.setFrameShape(QFrame.Shape.HLine)
    ln.setStyleSheet("color:#e6e9f2;")
    return ln


def row(widgets: list, stretch_last: bool = True) -> QFrame:
    w = QFrame()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    for i, x in enumerate(widgets):
        h.addWidget(x)
    if stretch_last:
        h.addStretch(1)
    return w
