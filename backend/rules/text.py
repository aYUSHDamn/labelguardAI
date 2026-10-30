"""Text helpers for ingredient lists: splitting, normalising, matching, INS codes."""
from __future__ import annotations

import re
from functools import lru_cache

# Additive class words that are usually followed by bare INS numbers,
# e.g. "Emulsifiers (322, 471)" or "Acidity regulator [330]".
_CLASS_WORDS = (r"emulsifiers?|stabili[sz]ers?|acidity regulators?|preservatives?|colou?rs?|"
                r"flavou?r enhancers?|raising agents?|antioxidants?|thickeners?|sweeteners?|"
                r"humectants?|anti-?caking agents?|gelling agents?|glazing agents?|"
                r"firming agents?|bleaching agents?|improvers?|leavening agents?|"
                r"dough conditioners?|synthetic food colou?rs?")
_CODE_RE = re.compile(r"\b(?:ins|e)\s*[-:]?\s*(\d{3,4}[a-f]?)(?:\s*\(\s*[ivx]+\s*\))?", re.I)
_CLASS_GROUP_RE = re.compile(rf"(?:{_CLASS_WORDS})\s*[\(\[]([^\)\]]*)[\)\]]", re.I)
_BARE_NUM_RE = re.compile(r"\b(\d{3,4}[a-f]?)\b", re.I)


def split_ingredients(text: str) -> list[str]:
    """Split on commas/semicolons that are NOT inside brackets; keep printed order."""
    if not text:
        return []
    text = re.sub(r"^\s*ingredients?\s*[:\-]\s*", "", text.strip(), flags=re.I)
    out, buf, depth = [], [], 0
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            item = "".join(buf).strip(" .")
            if item:
                out.append(item)
            buf = []
        else:
            buf.append(ch)
    item = "".join(buf).strip(" .")
    if item:
        out.append(item)
    return out


def norm(text: str) -> str:
    """Lowercase, unify quotes/dashes, collapse whitespace. Keeps brackets."""
    t = (text or "").lower()
    t = t.replace("’", "'").replace("–", "-").replace("—", "-")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


@lru_cache(maxsize=4096)
def _term_regex(term: str) -> re.Pattern:
    # Word-boundary match that tolerates plural 's'/'es' (e.g. "nut" -> "nuts").
    escaped = re.escape(term.lower()).replace(r"\ ", r"[\s\-]+")
    return re.compile(rf"(?<![a-z]){escaped}(?:e?s)?(?![a-z])")


def contains_term(text: str, term: str) -> bool:
    return bool(_term_regex(term).search(text))


def find_terms(text: str, terms: list[str]) -> list[str]:
    """Return terms found in text, longest first, without double-counting overlaps."""
    found, consumed = [], text
    for term in sorted(set(terms), key=len, reverse=True):
        rx = _term_regex(term)
        if rx.search(consumed):
            found.append(term)
            consumed = rx.sub(" § ", consumed)
    return found


def strip_phrases(text: str, phrases: list[str]) -> str:
    for p in phrases:
        text = _term_regex(p).sub(" ", text)
    return text


def extract_codes(text: str) -> list[str]:
    """INS/E-numbers mentioned in an ingredient: 'E471', 'INS 330', 'Emulsifier (322, 471)'."""
    t = re.sub(r"\(\s*[ivx]+\s*\)", "", norm(text))  # drop sub-type markers like 500(ii)
    codes = [m.group(1).lower() for m in _CODE_RE.finditer(t)]
    for grp in _CLASS_GROUP_RE.finditer(t):
        codes += [m.group(1).lower() for m in _BARE_NUM_RE.finditer(grp.group(1))]
    out = []
    for c in codes:
        if c not in out:
            out.append(c)
    return out


def code_base(code: str) -> str:
    """'150d' -> '150d', '471' -> '471', '472e' -> '472e'. Also usable for loose base matching."""
    return re.sub(r"[^0-9a-f]", "", code.lower())
