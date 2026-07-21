from __future__ import annotations

import re
import unicodedata


def strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in nk if not unicodedata.combining(c))


def norm_name(s: str) -> str:
    s = strip_accents(s or "").lower()
    # Nordic / common folds already handled by accents; keep explicit fallbacks
    s = s.replace("ø", "o").replace("æ", "ae").replace("å", "a")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_match(match: str) -> tuple[str, str]:
    m = match or ""
    for sep in (" vs ", " v ", " - ", " – ", " — ", " / "):
        if sep in m:
            a, b = m.split(sep, 1)
            return a.strip(), b.strip()
    # "Last, First vs Last, First" already covered; single name → home only
    return m.strip(), ""


def token_overlap(a: str, b: str) -> float:
    ta = set(norm_name(a).split()) - {"fc", "fk", "if", "bk", "sc", "ac", "cf", "the"}
    tb = set(norm_name(b).split()) - {"fc", "fk", "if", "bk", "sc", "ac", "cf", "the"}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def name_match_score(query_side: str, candidate: str) -> float:
    """0–1 similarity for team/player names (order-insensitive tokens)."""
    if not query_side or not candidate:
        return 0.0
    qn, cn = norm_name(query_side), norm_name(candidate)
    if not qn or not cn:
        return 0.0
    if qn == cn:
        return 1.0
    if qn in cn or cn in qn:
        return 0.85
    # Reordered "Last, First" vs "First Last"
    q_tokens = qn.replace(",", " ").split()
    c_tokens = cn.replace(",", " ").split()
    if len(q_tokens) >= 2 and set(q_tokens) == set(c_tokens):
        return 0.95
    return token_overlap(qn, cn)


def pair_match_score(
    home_q: str, away_q: str, home_c: str, away_c: str
) -> float:
    """Average of both sides; also try swapped sides once."""
    direct = (name_match_score(home_q, home_c) + name_match_score(away_q, away_c)) / 2
    swapped = (name_match_score(home_q, away_c) + name_match_score(away_q, home_c)) / 2
    return max(direct, swapped * 0.95)


def parse_score_str(score: str) -> tuple[int, int] | None:
    m = re.search(r"(\d+)\s*[-:]\s*(\d+)", score or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def date_yyyymmdd(date: str | None) -> str | None:
    """Normalize date to YYYYMMDD for ESPN-style APIs."""
    if not date:
        return None
    d = date.strip()[:10]
    if len(d) >= 10 and d[4] == "-":
        return d.replace("-", "")[:8]
    if len(d) == 8 and d.isdigit():
        return d
    return None
