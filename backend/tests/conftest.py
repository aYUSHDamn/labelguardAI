import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Isolated DB, no real API key and no network during tests.
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = str(Path(_tmp) / "test.db")
os.environ["GEMINI_API_KEY"] = ""
os.environ["OFF_ENABLED"] = "0"


@pytest.fixture
def biscuit():
    from schemas import Extraction
    return Extraction(
        product_name="Choco Cream Biscuits", brand="TestBrand", category="biscuits_cookies",
        ingredients=["Refined wheat flour (maida)", "Sugar", "Edible vegetable oil (palm)", "Invert sugar syrup",
                     "Cocoa solids (4%)", "Cashew (2%)", "Liquid glucose", "Maltodextrin", "Milk solids",
                     "Emulsifiers (INS 322, 471)", "Raising agents [INS 503(ii), 500(ii)]", "Iodised salt",
                     "Colour (INS 150d)", "Artificial flavouring substances (vanilla)", "Onion powder"],
        nutrition_per_100g={"energy_kcal": 480, "sugar_g": 34, "sodium_mg": 330, "fat_g": 19,
                            "sat_fat_g": 9.5, "protein_g": 5.5, "fiber_g": 2},
        serving_size="3 biscuits (20 g)", claims=["healthy", "no added sugar", "made with whole wheat"],
        may_contain=["peanut", "soy"], confidence=0.9,
    )


@pytest.fixture
def oats():
    from schemas import Extraction
    return Extraction(
        product_name="Rolled Oats", category="breakfast_cereals", ingredients=["Rolled oats (100%)"],
        nutrition_per_100g={"energy_kcal": 390, "sugar_g": 1, "sodium_mg": 5, "fat_g": 8, "sat_fat_g": 1.5,
                            "protein_g": 12, "fiber_g": 10},
        serving_size="40 g", claims=["high fibre", "no added sugar"], confidence=0.95,
    )


@pytest.fixture
def household():
    from schemas import Household
    return Household(members=[
        {"name": "Asha", "allergens": ["cashews"], "diet_rules": ["jain"], "conditions": ["pre-diabetic"],
         "limits": {"sodium_mg_per_day": 1500}},
        {"name": "Rohan", "relation": "son", "age": 9, "conditions": ["lactose intolerant"], "allergens": ["peanut"]},
    ])
