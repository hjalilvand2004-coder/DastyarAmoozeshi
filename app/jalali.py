# -*- coding: utf-8 -*-
"""تبدیل تاریخ میلادی/جلالی - پیاده‌سازی مستقل بدون وابستگی خارجی

الگوریتم بر پایه پیاده‌سازی شناخته‌شده jalaali (MIT) است و از تقسیم «برش‌دهنده»
(مشابه جاوااسکریپت) استفاده می‌کند تا نتایج با مرجع یکسان باشد.
"""

from __future__ import annotations

import datetime

FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
FA_WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN = "0123456789"
_FA = "۰۱۲۳۴۵۶۷۸۹"


def _div(a: int, b: int) -> int:
    """تقسیم صحیح با برش به سمت صفر (هم‌ارز ~~ در جاوااسکریپت)"""
    q = a // b
    if q < 0 and q * b != a:
        q += 1
    return q


def _jal_cal(jy: int):
    breaks = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
              1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]
    gy = jy + 621
    leap_j = -14
    jp = breaks[0]
    jump = 0
    for i in range(1, len(breaks)):
        jm = breaks[i]
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(jump % 33, 4)
        jp = jm
    n = jy - jp
    leap_j += _div(n, 33) * 8 + _div(n % 33 + 3, 4)
    if jump % 33 == 4 and jump - n == 4:
        leap_j += 1
    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33
    leap = (((n + 1) % 33) - 1) % 4
    if leap == -1:
        leap = 4
    return leap, gy, march


def _g2d(gy: int, gm: int, gd: int) -> int:
    d = _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4) \
        + _div(153 * ((gm + 9) % 12) + 2, 5) + gd - 34840408
    d = d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752
    return d


def _d2g(jdn: int):
    j = 4 * jdn + 139361631
    j = j + _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(j % 1461, 4) * 5 + 308
    gd = _div(i % 153, 5) + 1
    gm = _div(i, 153) % 12 + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _j2d(jy: int, jm: int, jd: int) -> int:
    leap, gy, march = _jal_cal(jy)
    return _g2d(gy, 3, march) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1


def _d2j(jdn: int):
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _gy, march = _jal_cal(jy)
    jdn1f = _g2d(gy, 3, march)
    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            return jy, 1 + _div(k, 31), (k % 31) + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    return jy, 7 + _div(k, 30), (k % 30) + 1


# ---------- API عمومی ----------

def g_to_j(d: datetime.date) -> tuple[int, int, int]:
    return _d2j(_g2d(d.year, d.month, d.day))


def j_to_g(jy: int, jm: int, jd: int) -> datetime.date:
    gy, gm, gd = _d2g(_j2d(jy, jm, jd))
    return datetime.date(gy, gm, gd)


def month_length(jy: int, jm: int) -> int:
    if jm < 12:
        return _j2d(jy, jm + 1, 1) - _j2d(jy, jm, 1)
    return _j2d(jy + 1, 1, 1) - _j2d(jy, jm, 1)


def is_leap(jy: int) -> bool:
    return month_length(jy, 12) == 30


def weekday_fa(d: datetime.date) -> str:
    return FA_WEEKDAYS[(d.isoweekday() + 1) % 7]


def to_en_digits(s: str) -> str:
    table = str.maketrans(FA_DIGITS + AR_DIGITS, _EN + _EN)
    return str(s).translate(table)


def to_fa_digits(s: str) -> str:
    table = str.maketrans(_EN, _FA)
    return str(s).translate(table)


def format_jalali(d: datetime.date, style: str = "slash") -> str:
    jy, jm, jd = g_to_j(d)
    if style == "slash":
        return to_fa_digits(f"{jy}/{jm:02d}/{jd:02d}")
    if style == "long":
        return f"{to_fa_digits(jd)} {FA_MONTHS[jm-1]} {to_fa_digits(jy)}"
    if style == "iso":
        return f"{jy}-{jm:02d}-{jd:02d}"
    raise ValueError("style نامعتبر")


def parse_jalali(text: str) -> tuple[int, int, int] | None:
    """«۱۴۰۵/۰۹/۰۱» یا «1405-9-1» را می‌گیرد و (jy, jm, jd) برمی‌گرداند"""
    if not text:
        return None
    s = to_en_digits(str(text)).strip().replace("-", "/").replace(".", "/")
    s = s.replace(" ", "")
    parts = [p for p in s.split("/") if p != ""]
    if len(parts) != 3:
        return None
    try:
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not (1 <= jm <= 12):
        return None
    if not (1 <= jd <= month_length(jy, jm)):
        return None
    if jy < 1000:  # فرض: سال دو رقمی یعنی 14xx
        jy += 1400
    return jy, jm, jd


def jalali_to_gregorian_iso(text: str) -> str | None:
    """تاریخ جلالی متنی را به ISO میلادی برای ذخیره‌سازی تبدیل می‌کند"""
    p = parse_jalali(text)
    if not p:
        return None
    return j_to_g(*p).isoformat()
