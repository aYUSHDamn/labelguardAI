"""
Central configuration for LabelGuard.

Everything that depends on an EXTERNAL service (Gemini model names, Open Food
Facts endpoints and rate limits) lives here so it can be verified/changed in
one place. Values can be overridden in backend/.env.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


# ---------------------------------------------------------------- Gemini (VERIFY)
# The ONE place the model name lives. Check https://ai.google.dev/gemini-api/docs/models
# before your demo; override with GEMINI_MODEL in .env if it has changed.
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-3.8-flash")
# Tried in order if the main model times out / is overloaded (504, 503, 429...).
GEMINI_FALLBACK_MODELS = [m.strip() for m in _env("GEMINI_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite").split(",") if m.strip()]
GEMINI_MODEL_COOLDOWN_S = 300  # skip a failing model for 5 minutes before trying it again
GEMINI_API_KEY = _env("GEMINI_API_KEY")  # backend only, never sent to the frontend
# Gemini 3.x models "think" before answering and thinking tokens are billed as
# output. "low" keeps cost down. Set to "" to omit the thinking config entirely.
GEMINI_THINKING_LEVEL = _env("GEMINI_THINKING_LEVEL", "low")
GEMINI_TIMEOUT_S = int(_env("GEMINI_TIMEOUT_S", "60"))
EXTRACT_TIMEOUT_S = 20  # per model attempt for label reading; then the fallback model is tried

# Generation settings for the three (and only three) kinds of LLM call.
TEMP_PROFILE = 0.0
TEMP_EXTRACTION = 0.0
TEMP_EXPLAIN = 0.2
# max_output_tokens includes thinking tokens on Gemini 3.x, so these caps are
# generous; the prompts themselves ask for short output.
MAX_TOKENS_PROFILE = 2048
MAX_TOKENS_EXTRACTION = 4096
MAX_TOKENS_EXPLAIN = 1024
EXPLAIN_MAX_CHARS = 600  # hard trim on the visible explanation (~120 tokens)
EXPLAIN_TIMEOUT_S = 20   # summary is optional: fall back to the template rather than make the user wait

MAX_IMAGE_PX = 1024
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

# ------------------------------------------------------- Open Food Facts (VERIFY)
# Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
OFF_BASE_URL = _env("OFF_BASE_URL", "https://world.openfoodfacts.org")
OFF_PRODUCT_PATH = "/api/v2/product/{barcode}.json"
OFF_SEARCH_PATH = "/api/v2/search"
OFF_CATEGORY_PARAM = "categories_tags_en"   # e.g. categories_tags_en=biscuits
# Country filter. In Oct 2026 testing, searches WITH this filter returned OFF's
# "Page temporarily unavailable" page; set OFF_COUNTRY_PARAM= (empty) in .env to drop it.
OFF_COUNTRY_PARAM = os.getenv("OFF_COUNTRY_PARAM", "countries_tags_en").strip()  # may be empty
OFF_COUNTRY_VALUE = "india"
OFF_PAGE_SIZE = 40
OFF_TIMEOUT_S = 5
# Published limits: 10 search req/min/IP, 15 product req/min/IP. We stay under.
OFF_SEARCH_MIN_INTERVAL_S = 6.5
OFF_PRODUCT_MIN_INTERVAL_S = 4.5
OFF_CACHE_TTL_HOURS = 24 * 7
OFF_USER_AGENT = _env("OFF_USER_AGENT", "LabelGuard/0.1 (student demo project)")
OFF_ENABLED = _env("OFF_ENABLED", "1") == "1"

# ------------------------------------------------------------------- App / misc
DB_PATH = Path(_env("DB_PATH", str(BASE_DIR / "labelguard.db")))
CORS_ORIGINS = [o.strip() for o in _env(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

DISCLAIMER = ("LabelGuard is informational only and is not medical advice. "
              "Always read the physical label and consult a doctor or dietitian "
              "for medical decisions.")

# Fixed category list used by the extraction prompt, the scorer and the
# alternatives engine. Each maps to Open Food Facts category tags (English).
CATEGORIES: dict[str, list[str]] = {
    "biscuits_cookies": ["biscuits", "cookies"],
    "chips_namkeen": ["crisps", "salty-snacks"],
    "instant_noodles": ["instant-noodles"],
    "breakfast_cereals": ["breakfast-cereals"],
    "chocolates_confectionery": ["chocolates", "confectioneries"],
    "soft_drinks": ["sodas", "carbonated-drinks"],
    "juices": ["fruit-juices", "juices-and-nectars"],
    "dairy_drinks": ["flavoured-milks", "milk-drinks"],
    "yogurt_curd": ["yogurts"],
    "ice_cream": ["ice-creams"],
    "bread_bakery": ["breads", "cakes"],
    "sauces_ketchup": ["ketchup", "sauces"],
    "spreads_jams": ["jams", "spreads"],
    "ready_to_eat": ["meals", "prepared-meals"],
    "health_drinks": ["malted-drinks", "cocoa-and-its-products"],
    "nutrition_bars": ["cereal-bars", "protein-bars"],
    "sweets_mithai": ["indian-sweets", "desserts"],
    "pickles_chutneys": ["pickles", "chutneys"],
    "dairy_products": ["cheeses", "butters"],
    "other": [],
}
# Categories measured per 100 ml: sugar thresholds are stricter for drinks.
LIQUID_CATEGORIES = {"soft_drinks", "juices", "dairy_drinks"}
