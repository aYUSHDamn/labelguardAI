"""Consistent error JSON: every failure returns {"error": <code>, "detail": <friendly message>}."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from llm.gemini_client import LLMError

log = logging.getLogger("labelguard.errors")


class APIError(Exception):
    def __init__(self, status: int, error: str, detail: str):
        self.status, self.error, self.detail = status, error, detail


LLM_ERRORS = {
    "not_configured": (503, "AI is not configured. Add GEMINI_API_KEY to backend/.env, or try a demo label."),
    "rate_limited": (429, "The AI service is busy (rate limit). Please wait a minute and try again."),
    "bad_response": (502, "We couldn't read this label. Try a sharper, well-lit photo of the ingredients and nutrition panel."),
    "llm_error": (502, "The AI service had a problem. Please try again in a moment."),
}


def install(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api(_: Request, exc: APIError):
        return JSONResponse(status_code=exc.status, content={"error": exc.error, "detail": exc.detail})

    @app.exception_handler(LLMError)
    async def _llm(_: Request, exc: LLMError):
        status, detail = LLM_ERRORS.get(exc.kind, LLM_ERRORS["llm_error"])
        log.warning("LLM error (%s): %s", exc.kind, exc)
        return JSONResponse(status_code=status, content={"error": exc.kind, "detail": detail})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        return JSONResponse(status_code=422, content={"error": "invalid_request",
                                                      "detail": f"{where}: {first.get('msg', 'invalid input')}"})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": "http_error", "detail": str(exc.detail)})

    @app.exception_handler(Exception)
    async def _any(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"error": "server_error",
                                                      "detail": "Something went wrong on our side. Please try again."})
