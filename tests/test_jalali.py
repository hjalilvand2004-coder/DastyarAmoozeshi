# -*- coding: utf-8 -*-
"""تست‌های تقویم جلالی"""

import datetime

from app.jalali import (FA_MONTHS, format_jalali, g_to_j, is_leap, j_to_g, month_length,
                        parse_jalali, to_en_digits, to_fa_digits, weekday_fa, jalali_to_gregorian_iso)

# لنگرهای معتبر: اول فروردین و اسفند ۳۰ سال کبیسه
ANCHORS = [
    (datetime.date(2024, 3, 20), (1403, 1, 1)),
    (datetime.date(2025, 3, 21), (1404, 1, 1)),
    (datetime.date(2025, 3, 20), (1403, 12, 30)),   # ۱۴۰۳ کبیسه است
    (datetime.date(2026, 11, 10), (1405, 8, 19)),
    (datetime.date(2023, 3, 21), (1402, 1, 1)),
]


def test_anchors_g_to_j():
    for g, j in ANCHORS:
        assert g_to_j(g) == j, f"{g} باید {j} باشد"


def test_anchors_j_to_g():
    for g, j in ANCHORS:
        assert j_to_g(*j) == g


def test_round_trip_range():
    d = datetime.date(2020, 1, 1)
    end = datetime.date(2030, 12, 31)
    step = datetime.timedelta(days=7)
    while d <= end:
        jy, jm, jd = g_to_j(d)
        assert j_to_g(jy, jm, jd) == d
        d += step


def test_month_lengths():
    assert month_length(1403, 12) == 30   # کبیسه
    assert month_length(1404, 12) == 29
    assert month_length(1405, 6) == 31
    assert month_length(1405, 7) == 30
    assert is_leap(1403) and not is_leap(1404)


def test_format_and_parse():
    d = datetime.date(2026, 11, 10)
    assert format_jalali(d, "slash") == "۱۴۰۵/۰۸/۱۹"
    assert "آبان" in format_jalali(d, "long")
    assert parse_jalali("۱۴۰۵/۰۸/۱۹") == (1405, 8, 19)
    assert parse_jalali("1405-9-1") == (1405, 9, 1)
    assert parse_jalali("۱۴۰۵/۱۳/۰۱") is None
    assert parse_jalali("۱۴۰۳/۱۲/۳۰") == (1403, 12, 30)   # ۱۴۰۳ کبیسه است
    assert parse_jalali("۱۴۰۵/۱۲/۳۰") is None             # ۱۴۰۵ کبیسه نیست
    assert jalali_to_gregorian_iso("۱۴۰۵/۰۸/۱۹") == "2026-11-10"


def test_digits_and_weekday():
    assert to_en_digits("۱۲۳") == "123"
    assert to_fa_digits("45") == "۴۵"
    assert weekday_fa(datetime.date(2026, 11, 10)) == "سه‌شنبه"
    assert weekday_fa(datetime.date(2026, 11, 13)) == "جمعه"
    assert len(FA_MONTHS) == 12
