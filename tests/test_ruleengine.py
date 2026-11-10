# -*- coding: utf-8 -*-
"""تست موتور قواعد قطعی"""

from app import ruleengine as re_mod


RULE = {
    "id": 1,
    "title": "حداقل معدل کارورزی",
    "cond_json": {"attr": "gpa", "op": ">=", "value": 12},
    "review_fields": [],
    "messages": {},
}


def test_satisfied():
    res = re_mod.evaluate(RULE, {"gpa": 14.5, "flags": {}})
    assert res.status == re_mod.SATISFIED


def test_not_satisfied():
    res = re_mod.evaluate(RULE, {"gpa": 11.0, "flags": {}})
    assert res.status == re_mod.NOT_SATISFIED


def test_insufficient():
    res = re_mod.evaluate(RULE, {"gpa": None, "flags": {}})
    assert res.status == re_mod.INSUFFICIENT_INFO
    assert "gpa" in res.missing


def test_needs_review_when_unverified():
    rule = {**RULE, "review_fields": ["transcript_verified"]}
    res = re_mod.evaluate(rule, {"gpa": 15, "flags": {"transcript_verified": False}})
    assert res.status == re_mod.NEEDS_REVIEW
    res2 = re_mod.evaluate(rule, {"gpa": 15, "flags": {"transcript_verified": True}})
    assert res2.status == re_mod.SATISFIED


def test_all_any_missing_semantics():
    # any: یکی برقرار، یکی ناقص → برقرار
    cond = {"any": [{"attr": "gpa", "op": ">=", "value": 12},
                    {"attr": "rank", "op": "<=", "value": 5}]}
    res = re_mod.evaluate({"cond_json": cond, "review_fields": []}, {"gpa": 16})
    assert res.status == re_mod.SATISFIED
    # all: یکی برقرار، یکی ناقص → ناقص
    cond = {"all": [{"attr": "gpa", "op": ">=", "value": 12},
                    {"attr": "rank", "op": "<=", "value": 5}]}
    res = re_mod.evaluate({"cond_json": cond, "review_fields": []}, {"gpa": 16})
    assert res.status == re_mod.INSUFFICIENT_INFO
    assert "rank" in res.missing
    # all: یکی نابرابر → نابرابر
    res = re_mod.evaluate({"cond_json": cond, "review_fields": []}, {"gpa": 10, "rank": 1})
    assert res.status == re_mod.NOT_SATISFIED


def test_entry_year_equality():
    cond = {"attr": "entry_year", "op": "==", "value": 1403}
    res = re_mod.evaluate({"cond_json": cond, "review_fields": []}, {"entry_year": 1402})
    assert res.status == re_mod.NOT_SATISFIED
    res = re_mod.evaluate({"cond_json": cond, "review_fields": []}, {"entry_year": None})
    assert res.status == re_mod.INSUFFICIENT_INFO


def test_extract_inputs():
    cond = {"all": [{"attr": "gpa", "op": ">=", "value": 12},
                    {"any": [{"attr": "rank", "op": "<=", "value": 5},
                             {"attr": "major", "op": "==", "value": "x"}]}]}
    assert set(re_mod.extract_inputs(cond)) == {"gpa", "rank", "major"}
