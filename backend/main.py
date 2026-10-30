"""
LabelGuard API.

Design principle: the LLM handles perception and interpretation. Deterministic
Python rules and real databases handle anything that must be consistent,
verifiable or cheap.

Run:  uvicorn main:app --reload --port 8000      (docs at http://localhost:8000/docs)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
import db
import errors
from routers import alternatives, compare, extras, meta, profile, scan, tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    if not config.GEMINI_API_KEY:
        logging.getLogger("labelguard").warning(
            "GEMINI_API_KEY not set: photo scans are disabled; demo labels, rules and alternatives still work.")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="LabelGuard API",
    version="0.1.0",
    description="Personalised food-label scanner for Indian households. " + config.DISCLAIMER,
)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
errors.install(app)

for r in (meta.router, profile.router, scan.router, alternatives.router, compare.router, tracker.router, extras.router):
    app.include_router(r)

