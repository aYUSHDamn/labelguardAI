"""Pydantic v2 models: the contract between the LLM, the rules engine and the API."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from config import CATEGORIES

# ------------------------------------------------------------------ vocabularies
DIET_RULES = ["vegetarian", "eggetarian", "vegan", "jain", "halal"]
DIET_SYNONYMS = {
    "veg": "vegetarian", "vegetarian": "vegetarian", "pure veg": "vegetarian",
    "eggetarian": "eggetarian", "ovo-vegetarian": "eggetarian", "ovo vegetarian": "eggetarian",
    "vegan": "vegan", "plant based": "vegan", "plant-based": "vegan",
    "jain": "jain", "no onion garlic": "jain", "satvik": "jain",
    "halal": "halal", "muslim": "halal",
}

CONDITIONS = ["diabetes", "prediabetes", "hypertension", "high_cholesterol", "heart_disease",
              "lactose_intolerance", "celiac", "kidney_disease", "pregnancy", "obesity", "pcos"]
CONDITION_SYNONYMS = {
    "diabetes": "diabetes", "diabetic": "diabetes", "type 2 diabetes": "diabetes", "sugar": "diabetes",
    "prediabetes": "prediabetes", "pre-diabetes": "prediabetes", "pre diabetic": "prediabetes",
    "pre-diabetic": "prediabetes", "prediabetic": "prediabetes", "borderline diabetes": "prediabetes",
    "hypertension": "hypertension", "high bp": "hypertension", "high blood pressure": "hypertension", "bp": "hypertension",
    "high cholesterol": "high_cholesterol", "high_cholesterol": "high_cholesterol", "cholesterol": "high_cholesterol",
    "heart disease": "heart_disease", "heart_disease": "heart_disease", "cardiac": "heart_disease",
    "lactose intolerance": "lactose_intolerance", "lactose intolerant": "lactose_intolerance",
    "lactose_intolerance": "lactose_intolerance",
    "celiac": "celiac", "coeliac": "celiac", "celiac disease": "celiac", "gluten intolerance": "celiac",
    "kidney disease": "kidney_disease", "kidney_disease": "kidney_disease", "ckd": "kidney_disease",
    "pregnancy": "pregnancy", "pregnant": "pregnancy",
    "obesity": "obesity", "overweight": "obesity", "weight loss": "obesity",
    "pcos": "pcos", "pcod": "pcos",
}

DEFAULT_SUGAR_G = 25.0      # WHO/ICMR guidance on free sugars for adults
DEFAULT_SODIUM_MG = 2000.0  # WHO: < 2 g sodium (= 5 g salt) per day
DEFAULT_SAT_FAT_G = 20.0


def _clean_list(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = re.split(r"[,;]", values)
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip().lower()
        if s and s not in out:
            out.append(s)
    return out


# ------------------------------------------------------------------- profile
class Limits(BaseModel):
    sugar_g_per_day: Optional[float] = DEFAULT_SUGAR_G
    sodium_mg_per_day: Optional[float] = DEFAULT_SODIUM_MG
    sat_fat_g_per_day: Optional[float] = DEFAULT_SAT_FAT_G

    @model_validator(mode="after")
    def _defaults(self):
        # Safe defaults for anything missing / nonsensical.
        if not self.sugar_g_per_day or self.sugar_g_per_day <= 0:
            self.sugar_g_per_day = DEFAULT_SUGAR_G
        if not self.sodium_mg_per_day or self.sodium_mg_per_day <= 0:
            self.sodium_mg_per_day = DEFAULT_SODIUM_MG
        if not self.sat_fat_g_per_day or self.sat_fat_g_per_day <= 0:
            self.sat_fat_g_per_day = DEFAULT_SAT_FAT_G
        return self


class Member(BaseModel):
    name: str = "Me"
    relation: str = "self"
    age: Optional[int] = None
    allergens: list[str] = Field(default_factory=list)
    diet_rules: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    limits: Limits = Field(default_factory=Limits)
    avoid_ingredients: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("name", "relation", mode="before")
    @classmethod
    def _str(cls, v):
        return str(v).strip() if v else ""

    @field_validator("age", mode="before")
    @classmethod
    def _age(cls, v):
        if v is None or v == "":
            return None
        m = re.search(r"\d+", str(v))
        return int(m.group()) if m and 0 < int(m.group()) < 120 else None

    @field_validator("allergens", "avoid_ingredients", mode="before")
    @classmethod
    def _lists(cls, v):
        return _clean_list(v)

    @field_validator("diet_rules", mode="before")
    @classmethod
    def _diets(cls, v):
        out = []
        for d in _clean_list(v):
            d = DIET_SYNONYMS.get(d, d)
            if d in DIET_RULES and d not in out:
                out.append(d)
        return out

    @field_validator("conditions", mode="before")
    @classmethod
    def _conds(cls, v):
        out = []
        for c in _clean_list(v):
            c = CONDITION_SYNONYMS.get(c, c.replace(" ", "_"))
            if c not in out:
                out.append(c)
        return out

    @field_validator("limits", mode="before")
    @classmethod
    def _limits(cls, v):
        return v or {}

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, v):
        return v or ""

    @model_validator(mode="after")
    def _fill(self):
        self.name = self.name or "Me"
        self.relation = self.relation or "self"
        return self


class Household(BaseModel):
    members: list[Member] = Field(default_factory=lambda: [Member()])

    @model_validator(mode="after")
    def _non_empty_unique(self):
        if not self.members:
            self.members = [Member()]
        seen: dict[str, int] = {}
        for m in self.members:  # names are used as keys, so make them unique
            if m.name in seen:
                seen[m.name] += 1
                m.name = f"{m.name} {seen[m.name]}"
            else:
                seen[m.name] = 1
        return self


class ProfileParseRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


class ProfileParseResponse(BaseModel):
    household: Household
    source: Literal["llm", "keyword_fallback", "cache"]
    warning: Optional[str] = None


# ---------------------------------------------------------------- extraction
class Nutrition(BaseModel):
    energy_kcal: Optional[float] = None
    sugar_g: Optional[float] = None
    added_sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    fat_g: Optional[float] = None
    sat_fat_g: Optional[float] = None
    trans_fat_g: Optional[float] = None
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data):
        if not isinstance(data, dict):
            return {}
        clean = {}
        for k, v in data.items():
            if isinstance(v, str):
                m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", "."))
                v = float(m.group()) if m else None
            if isinstance(v, (int, float)) and v < 0:
                v = None
            clean[k] = v
        # Rule: sodium_mg = salt_g * 400, if only salt is present.
        if clean.get("sodium_mg") is None and clean.get("salt_g") is not None:
            clean["sodium_mg"] = round(float(clean["salt_g"]) * 400, 1)
        return clean


class Extraction(BaseModel):
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: str = "other"
    ingredients: list[str] = Field(default_factory=list)
    nutrition_per_100g: Nutrition = Field(default_factory=Nutrition)
    serving_size: Optional[str] = None
    serving_size_g: Optional[float] = None
    nutrition_per_serving: Nutrition = Field(default_factory=Nutrition)
    claims: list[str] = Field(default_factory=list)
    may_contain: list[str] = Field(default_factory=list)
    front_highlights: list[str] = Field(default_factory=list)  # foods pictured / named big on the front
    front_messages: list[str] = Field(default_factory=list)    # impressions the front gives ("for kids")
    barcode: Optional[str] = None
    confidence: float = 0.5
    unreadable_fields: list[str] = Field(default_factory=list)

    @field_validator("category", mode="before")
    @classmethod
    def _cat(cls, v):
        v = (str(v).strip().lower() if v else "other").replace(" ", "_")
        return v if v in CATEGORIES else "other"

    @field_validator("ingredients", mode="before")
    @classmethod
    def _ingredients(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            from rules.text import split_ingredients
            return split_ingredients(v)
        return [str(x).strip() for x in v if x and str(x).strip()]

    @field_validator("claims", "may_contain", "unreadable_fields", "front_highlights", "front_messages", mode="before")
    @classmethod
    def _lists(cls, v):
        return _clean_list(v)

    @field_validator("nutrition_per_100g", "nutrition_per_serving", mode="before")
    @classmethod
    def _nut(cls, v):
        return v or {}

    @field_validator("confidence", mode="before")
    @classmethod
    def _conf(cls, v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.5

    @field_validator("barcode", mode="before")
    @classmethod
    def _barcode(cls, v):
        if not v:
            return None
        digits = re.sub(r"\D", "", str(v))
        return digits if 8 <= len(digits) <= 14 else None

    per_100g_computed: bool = False  # True when per-100g values were derived from per-serving

    @model_validator(mode="after")
    def _serving(self):
        if self.serving_size_g is None and self.serving_size:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(g|gm|grams?|ml)\b", self.serving_size.lower())
            if m:
                self.serving_size_g = float(m.group(1))
        # Many labels (e.g. US "Nutrition Facts") print per-serving values only.
        # Derive per-100g so the score and rules still work: per100 = per_serving * 100 / serving_g.
        g = self.serving_size_g
        if g and g > 0:
            p100, ps = self.nutrition_per_100g, self.nutrition_per_serving
            for k in Nutrition.model_fields:
                if getattr(p100, k) is None and getattr(ps, k) is not None:
                    setattr(p100, k, round(getattr(ps, k) * 100 / g, 1))
                    self.per_100g_computed = True
        return self


# ------------------------------------------------------------- API requests
class ScanJsonRequest(BaseModel):
    extraction: Extraction


class ExplainRequest(BaseModel):
    scan_id: int
    language: Literal["en", "hi", "ta"] = "en"
    eli12: bool = False
    member: Optional[str] = None


class FeedbackRequest(BaseModel):
    scan_id: int
    product_code: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    vote: Literal[1, -1]
    reason: Optional[Literal["too_sweet", "too_expensive", "dont_like_brand",
                             "not_available", "tastes_good", "good_value", "other"]] = None


class CompareRequest(BaseModel):
    scan_ids: list[int] = Field(default_factory=list)   # 2-4 scans
    scan_id_a: Optional[int] = None                      # older 2-product form still works
    scan_id_b: Optional[int] = None
    member: Optional[str] = None


class LogRequest(BaseModel):
    scan_id: int
    member: str
    servings: float = Field(default=1.0, gt=0, le=20)
    grams: Optional[float] = Field(default=None, gt=0, le=5000)
