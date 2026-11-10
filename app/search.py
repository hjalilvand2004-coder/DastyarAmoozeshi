# -*- coding: utf-8 -*-
"""جست‌وجوی متنی BM25 روی تکه‌های اسناد (بدون وابستگی خارجی)"""

from __future__ import annotations

import math
import re
from collections import Counter

from .security import normalize_persian

STOPWORDS = {
    "و", "در", "به", "از", "که", "این", "آن", "با", "برای", "است", "هست", "می",
    "شود", "میشود", "بر", "تا", "هم", "نیز", "یا", "اگر", "هر", "یک", "های",
    "ها", "را", "کند", "کنید", "باشد", "شد", "باید", "نباید", "مورد", "طبق",
    "برابر", "طبقه", "طور", "چنانچه", "ولی", "اما", "همچنین", "ممکن", "تمام",
    "the", "a", "an", "of", "to", "and", "is", "are", "for", "in", "on", "or",
}

_RE_CLEAN = re.compile(r"[^\w\u0600-\u06FF\s]")


def tokenize(text: str) -> list[str]:
    t = normalize_persian(text).lower()
    t = _RE_CLEAN.sub(" ", t)
    return [w for w in t.split() if len(w) > 1 and w not in STOPWORDS]


class BM25:
    """(id, متن) می‌گیرد و بر اساس امتیاز BM25 مرتب‌شده برمی‌گرداند"""

    def __init__(self, docs: list[tuple[int, str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.ids: list[int] = []
        self.tfs: list[Counter] = []
        self.dls: list[int] = []
        self.df: Counter = Counter()
        for doc_id, text in docs:
            toks = tokenize(text)
            tf = Counter(toks)
            self.ids.append(doc_id)
            self.tfs.append(tf)
            self.dls.append(len(toks))
            for term in tf:
                self.df[term] += 1
        self.n = len(docs)
        self.avgdl = (sum(self.dls) / self.n) if self.n else 1.0

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 8, min_score: float = 0.4) -> list[tuple[int, float]]:
        q_tokens = tokenize(query)
        if not q_tokens or self.n == 0:
            return []
        out: list[tuple[int, float]] = []
        for i in range(self.n):
            tf = self.tfs[i]
            dl = self.dls[i]
            score = 0.0
            for term in set(q_tokens):
                f = tf.get(term, 0)
                if f == 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                score += self._idf(term) * f * (self.k1 + 1) / denom
            if score > 0:
                out.append((self.ids[i], score))
        out.sort(key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in out[:k] if s >= min_score]
