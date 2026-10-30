"""
Thin wrapper around the google-genai SDK.

- JSON-only output (response_mime_type="application/json"), low temperature.
- One retry on bad/empty JSON; one short back-off retry on rate limits / 5xx.
- Every call is logged to the llm_calls table (tokens + latency) for the viva.
- Raises LLMError on failure so callers can fall back to deterministic code.
"""
from __future__ import annotations

import io
import json
import logging
import re
import time
from typing import Any, Optional

from PIL import Image, ImageOps

import config
import db

log = logging.getLogger("labelguard.llm")


class LLMError(Exception):
    def __init__(self, message: str, kind: str = "llm_error"):
        super().__init__(message)
        self.kind = kind  # not_configured | rate_limited | bad_response | llm_error


def prepare_image(raw: bytes) -> bytes:
    """Validate, auto-rotate (EXIF), convert to RGB, resize to <= MAX_IMAGE_PX, return JPEG bytes."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:  # noqa: BLE001 - Pillow raises many types
        raise ValueError(f"Not a readable image: {exc}") from exc
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((config.MAX_IMAGE_PX, config.MAX_IMAGE_PX))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def parse_json(text: str) -> Any:
    """Parse model output, tolerating ```json fences or stray text around the object."""
    if not text or not text.strip():
        raise ValueError("empty response")
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end > start:
            return json.loads(t[start:end + 1])
        raise


class GeminiClient:
    def __init__(self) -> None:
        self._client = None
        self._use_thinking = bool(config.GEMINI_THINKING_LEVEL)
        self._down_until: dict[str, float] = {}

    @property
    def available(self) -> bool:
        return bool(config.GEMINI_API_KEY)

    def _get(self):
        if not self.available:
            raise LLMError("GEMINI_API_KEY is not set in backend/.env", "not_configured")
        if self._client is None:
            from google import genai
            from google.genai import types
            self._client = genai.Client(api_key=config.GEMINI_API_KEY,
                                        http_options=types.HttpOptions(timeout=config.GEMINI_TIMEOUT_S * 1000))
        return self._client

    def _config(self, temperature: float, max_tokens: int, timeout_s: Optional[int] = None):
        from google.genai import types
        kwargs = dict(temperature=temperature, max_output_tokens=max_tokens,
                      response_mime_type="application/json")
        if timeout_s:
            kwargs["http_options"] = types.HttpOptions(timeout=timeout_s * 1000)
        if self._use_thinking:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=config.GEMINI_THINKING_LEVEL.upper())
        return types.GenerateContentConfig(**kwargs)

    def generate_json(self, purpose: str, prompt: str, image_jpeg: Optional[bytes | list[bytes]] = None,
                      temperature: float = 0.0, max_tokens: int = 2048, timeout_s: Optional[int] = None) -> dict:
        """Try the main model; if Google returns a server error / rate limit / timeout, fall back
        to the next model in config.GEMINI_FALLBACK_MODELS. A model that just failed is skipped
        for a few minutes so the next request doesn't wait for it again."""
        from google.genai import types

        client = self._get()
        contents: list = [prompt]
        if image_jpeg is not None:  # one image or a list (front + back of the same pack)
            images = image_jpeg if isinstance(image_jpeg, list) else [image_jpeg]
            contents = [types.Part.from_bytes(data=img, mime_type="image/jpeg") for img in images] + [prompt]

        models = [config.GEMINI_MODEL] + [m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL]
        now = time.monotonic()
        healthy = [m for m in models if self._down_until.get(m, 0) <= now] or models
        last: Optional[LLMError] = None
        for model in healthy:
            try:
                return self._call(client, model, purpose, contents, temperature, max_tokens, timeout_s)
            except _ModelUnavailable as exc:
                log.warning("Gemini model %s unavailable (%s); trying fallback", model, exc)
                self._down_until[model] = time.monotonic() + config.GEMINI_MODEL_COOLDOWN_S
                last = LLMError(str(exc), exc.kind)
        raise last or LLMError("all Gemini models failed")

    def _call(self, client, model: str, purpose: str, contents: list, temperature: float, max_tokens: int,
              timeout_s: Optional[int]) -> dict:
        from google.genai import errors

        last_error = "unknown"
        for attempt in range(3):  # 1 call + retries for bad JSON / thinking-config rejection
            t0 = time.perf_counter()
            try:
                resp = client.models.generate_content(model=model, contents=contents,
                                                      config=self._config(temperature, max_tokens, timeout_s))
                ms = int((time.perf_counter() - t0) * 1000)
                usage = getattr(resp, "usage_metadata", None)
                in_tok = getattr(usage, "prompt_token_count", None)
                out_tok = (getattr(usage, "candidates_token_count", 0) or 0) + (getattr(usage, "thoughts_token_count", 0) or 0)
                try:
                    data = parse_json(resp.text or "")
                    if not isinstance(data, dict):
                        raise ValueError("JSON is not an object")
                except (ValueError, json.JSONDecodeError) as exc:
                    last_error = f"bad JSON: {exc}"
                    db.log_llm_call(purpose, model, False, in_tok, out_tok, ms, last_error)
                    if attempt >= 1:
                        raise LLMError(last_error, "bad_response") from exc
                    continue  # one retry
                db.log_llm_call(purpose, model, True, in_tok, out_tok, ms)
                return data
            except errors.APIError as exc:
                ms = int((time.perf_counter() - t0) * 1000)
                last_error = f"{exc.code}: {str(exc)[:200]}"
                db.log_llm_call(purpose, model, False, None, None, ms, last_error)
                if exc.code == 400 and self._use_thinking and "think" in str(exc).lower():
                    log.warning("Model rejected thinking_config; retrying without it")
                    self._use_thinking = False
                    continue
                if exc.code in (404, 429, 500, 502, 503, 504):  # model missing / overloaded / quota -> fallback
                    raise _ModelUnavailable(last_error, "rate_limited" if exc.code == 429 else "llm_error") from exc
                raise LLMError(last_error, "llm_error") from exc
            except LLMError:
                raise
            except Exception as exc:  # network errors and client-side timeouts -> fallback
                last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                db.log_llm_call(purpose, model, False, None, None, int((time.perf_counter() - t0) * 1000), last_error)
                raise _ModelUnavailable(last_error, "llm_error") from exc
        raise LLMError(last_error, "bad_response")


class _ModelUnavailable(Exception):
    def __init__(self, message: str, kind: str):
        super().__init__(message)
        self.kind = kind


gemini = GeminiClient()
