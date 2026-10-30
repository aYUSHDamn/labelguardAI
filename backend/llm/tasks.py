"""
The three LLM tasks, each with caching and a deterministic fallback.

  parse_profile(text)        -> Household        fallback: keyword parser
  extract_label(jpeg)        -> Extraction       fallback: none (raises; API returns friendly error)
  explain(...)               -> short text       fallback: template sentences
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading

import config
import db
from llm import prompts
from llm.gemini_client import LLMError, gemini
from rules.profile_keywords import parse_profile_keywords
from schemas import Extraction, Household

log = logging.getLogger("labelguard.tasks")

# One lock per cache key: identical requests arriving together make ONE LLM call,
# the rest wait and read the cached answer (protects the free-tier per-minute quota).
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _h(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


# --------------------------------------------------------------- 1. profile
def parse_profile(text: str) -> tuple[Household, str, str | None]:
    key = "profile:" + _h(text.strip().lower(), config.GEMINI_MODEL)
    cached = db.kv_get("llm_cache", key)
    if cached:
        return Household.model_validate(cached), "cache", None
    try:
        data = gemini.generate_json("profile_parse", prompts.profile_parse_prompt(text),
                                    temperature=config.TEMP_PROFILE, max_tokens=config.MAX_TOKENS_PROFILE,
                                    timeout_s=config.EXTRACT_TIMEOUT_S)
        household = Household.model_validate(data)
        db.kv_put("llm_cache", key, household.model_dump())
        return household, "llm", None
    except (LLMError, ValueError) as exc:
        log.warning("profile parse fell back to keywords: %s", exc)
        reason = "AI parser unavailable" if getattr(exc, "kind", "") == "not_configured" else "AI parser failed"
        return parse_profile_keywords(text), "keyword_fallback", f"{reason}; used the keyword parser. Please review."


# ------------------------------------------------------------ 2. extraction
def extract_label(image_jpeg: bytes | list[bytes]) -> Extraction:
    data = gemini.generate_json("extraction", prompts.extraction_prompt(), image_jpeg=image_jpeg,
                                temperature=config.TEMP_EXTRACTION, max_tokens=config.MAX_TOKENS_EXTRACTION,
                                timeout_s=config.EXTRACT_TIMEOUT_S)
    try:
        return Extraction.model_validate(data)
    except ValueError as exc:
        raise LLMError(f"extraction JSON failed validation: {exc}", "bad_response") from exc


# ----------------------------------------------------------- 3. explanation
def explanation_facts(ex: dict, analysis: dict, members: list[dict]) -> dict:
    """Compact summary sent to the LLM (keeps input tokens low)."""
    return {
        "product": " ".join(x for x in [ex.get("brand"), ex.get("product_name")] if x) or "this product",
        "score": analysis["score"]["score"], "grade": analysis["score"]["label"],
        "hidden_sugars": [h["alias"] for h in analysis["hidden_sugars"]][:5],
        "misleading_claims": [f"{c['claim']}: {c['reason']}" for c in analysis["claims"]
                              if c["verdict"] == "misleading"][:2],
        "members": [{"name": m["member"], "status": m["status"],
                     "reasons": [f"{f['status']} {f['reason']} [evidence: {f['evidence']}]" for f in m["flags"][:4]]}
                    for m in members],
    }


def explain(ex: dict, analysis: dict, members: list[dict], language: str, eli12: bool) -> tuple[str, str]:
    facts = explanation_facts(ex, analysis, members)
    audience = members[0]["member"] if len(members) == 1 else "the family"
    key = "explain:" + _h(facts, language, eli12, config.GEMINI_MODEL)
    with _lock_for(key):
        return _explain_locked(key, facts, language, eli12, audience)


def _explain_locked(key: str, facts: dict, language: str, eli12: bool, audience: str) -> tuple[str, str]:
    cached = db.kv_get("llm_cache", key)
    if cached:
        return cached["text"], "cache"
    try:
        data = gemini.generate_json("explanation", prompts.explain_prompt(facts, language, eli12, audience),
                                    temperature=config.TEMP_EXPLAIN, max_tokens=config.MAX_TOKENS_EXPLAIN,
                                    timeout_s=config.EXPLAIN_TIMEOUT_S)
        text = str(data.get("explanation") or "").strip()
        if not text:
            raise LLMError("empty explanation", "bad_response")
        text = text[: config.EXPLAIN_MAX_CHARS]
        db.kv_put("llm_cache", key, {"text": text})
        return text, "llm"
    except LLMError as exc:
        log.warning("explanation fell back to template: %s", exc)
        return template_explanation(facts, language, eli12), "template_fallback"


# ------------------------------------------------- 4. ask (optional extra)
def ask(ex: dict, analysis: dict, question: str, language: str) -> tuple[str, str]:
    facts = explanation_facts(ex, analysis, analysis["members"])
    n = ex.get("nutrition_per_100g") or {}
    facts["nutrition_per_100g"] = {k: v for k, v in n.items() if v is not None}
    facts["serving_size"] = ex.get("serving_size")
    facts["ingredients"] = (ex.get("ingredients") or [])[:25]
    facts["additives"] = [f"{a['name']} (INS {a['code']}, {a['concern']} concern)" for a in analysis["additives"]][:10]
    facts["allergens_present"] = [f"{a['display']} ({a['source'].replace('_', ' ')})" for a in analysis["allergens"]]
    key = "ask:" + _h(facts, question.strip().lower(), language, config.GEMINI_MODEL)
    with _lock_for(key):
        cached = db.kv_get("llm_cache", key)
        if cached:
            return cached["text"], "cache"
        try:
            data = gemini.generate_json("ask", prompts.ask_prompt(facts, question, language),
                                        temperature=0.1, max_tokens=config.MAX_TOKENS_EXPLAIN,
                                        timeout_s=config.EXPLAIN_TIMEOUT_S)
            text = str(data.get("answer") or "").strip()[: config.EXPLAIN_MAX_CHARS]
            if not text:
                raise LLMError("empty answer", "bad_response")
            db.kv_put("llm_cache", key, {"text": text})
            return text, "llm"
        except LLMError as exc:
            log.warning("ask fell back to rules: %s", exc)
            return rule_answer(question, analysis), "rules_fallback"


def rule_answer(question: str, analysis: dict) -> str:
    """Deterministic fallback: answer 'can X eat this?' style questions from the verdicts."""
    q = question.lower()
    members = analysis["members"]
    named = [m for m in members if m["member"].lower() in q or (m["relation"] or "").lower() in q]
    lines =[f"{m['summary']}." for m in (named or members)]
    if "sugar" in q and analysis["hidden_sugars"]:
        lines.append("Sugar sources: " + ", ".join(h["alias"] for h in analysis["hidden_sugars"]) + ".")
    if "additive" in q or "ins" in q or "e-number" in q:
        lines.append("Additives: " + (", ".join(f"{a['name']} (INS {a['code']})" for a in analysis["additives"]) or "none found") + ".")
    return " ".join(lines)[:600]


TEMPLATES = {
    "en": {
        "score": "{product} scores {score}/100 ({grade}).",
        "AVOID": "Not suitable for {name}: {reason}.",
        "WARN": "Be careful for {name}: {reason}.",
        "SAFE": "No conflicts found for {name}.",
        "sugars": "Sugar is listed under {n} names: {names}.",
        "eli12": "Think of it as a sometimes-food, not an everyday food.",
    },
    "hi": {
        "score": "{product} को {score}/100 अंक मिले ({grade}).",
        "AVOID": "{name} के लिए उपयुक्त नहीं: {reason}.",
        "WARN": "{name} के लिए सावधानी: {reason}.",
        "SAFE": "{name} के प्रोफ़ाइल से कोई टकराव नहीं मिला.",
        "sugars": "चीनी {n} अलग-अलग नामों से लिखी है: {names}.",
        "eli12": "इसे रोज़ नहीं, कभी-कभी खाने वाली चीज़ समझें.",
    },
    "ta": {
        "score": "{product} {score}/100 மதிப்பெண் பெறுகிறது ({grade}).",
        "AVOID": "{name}-க்கு ஏற்றதல்ல: {reason}.",
        "WARN": "{name}-க்கு கவனம் தேவை: {reason}.",
        "SAFE": "{name}-இன் சுயவிவரத்துடன் முரண்பாடு இல்லை.",
        "sugars": "சர்க்கரை {n} பெயர்களில் உள்ளது: {names}.",
        "eli12": "இதை தினமும் அல்ல, எப்போதாவது சாப்பிடும் உணவாக நினையுங்கள்.",
    },
}


def template_explanation(facts: dict, language: str, eli12: bool) -> str:
    t = TEMPLATES.get(language, TEMPLATES["en"])
    parts = [t["score"].format(**facts)]
    for m in facts["members"][:3]:
        reason = m["reasons"][0].split(" [evidence")[0].split(" ", 1)[1] if m["reasons"] else ""
        parts.append(t[m["status"]].format(name=m["name"], reason=reason))
    if len(facts["hidden_sugars"]) >= 2:
        parts.append(t["sugars"].format(n=len(facts["hidden_sugars"]), names=", ".join(facts["hidden_sugars"])))
    if eli12 and facts["score"] < 50:
        parts.append(t["eli12"])
    return " ".join(parts)


# ----------------------------------------- generic cached JSON call (extras)
def cached_llm_json(purpose: str, prompt: str, key_parts: tuple, refresh: bool = False,
                    max_tokens: int = 1024) -> tuple[dict | None, str]:
    """One cached LLM call returning a JSON object, or (None, 'error') if the AI is unavailable."""
    key = f"{purpose}:" + _h(key_parts, config.GEMINI_MODEL)
    with _lock_for(key):
        if not refresh:
            cached = db.kv_get("llm_cache", key)
            if cached:
                return cached, "cache"
        try:
            data = gemini.generate_json(purpose, prompt, temperature=0.3, max_tokens=max_tokens,
                                        timeout_s=config.EXTRACT_TIMEOUT_S)
            db.kv_put("llm_cache", key, data)
            return data, "llm"
        except LLMError as exc:
            log.warning("%s fell back: %s", purpose, exc)
            return None, "error"
