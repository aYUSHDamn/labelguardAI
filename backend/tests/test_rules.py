from rules import engine
from rules.data import resolve_allergen
from rules.text import extract_codes, split_ingredients
from schemas import Extraction, Household, Member


def test_split_ingredients_respects_brackets():
    text = "Ingredients: Wheat flour, Sugar, Emulsifiers (INS 322, 471), Salt."
    assert split_ingredients(text) == ["Wheat flour", "Sugar", "Emulsifiers (INS 322, 471)", "Salt"]


def test_extract_codes_variants():
    assert extract_codes("Emulsifiers (INS 322, 471)") == ["322", "471"]
    assert extract_codes("Raising agents [INS 503(ii), 500(ii)]") == ["503", "500"]
    assert extract_codes("Colour E150d") == ["150d"]
    assert extract_codes("Acidity regulator (330)") == ["330"]
    assert extract_codes("Wheat flour (atta 52%)") == []


def test_hidden_sugars(biscuit):
    aliases = [h["alias"] for h in engine.find_hidden_sugars(biscuit.ingredients)]
    assert aliases == ["sugar", "invert sugar syrup", "liquid glucose", "maltodextrin"]


def test_caramel_colour_is_not_a_sugar():
    assert engine.find_hidden_sugars(["Colour (caramel colour)"]) == []


def test_maltodextrin_does_not_match_dextrin_or_dextrose():
    aliases = [h["alias"] for h in engine.find_hidden_sugars(["Maltodextrin"])]
    assert aliases == ["maltodextrin"]


def test_additives_found_with_concern(biscuit):
    codes = {a["code"]: a["concern"] for a in engine.find_additives(biscuit.ingredients)}
    assert codes == {"150d": "medium", "322": "low", "471": "low", "503": "low", "500": "low"}


def test_additive_by_name():
    found = engine.find_additives(["Sweetener (aspartame)", "monosodium glutamate"])
    assert {a["code"] for a in found} == {"951", "621"}


def test_coconut_milk_is_not_dairy():
    keys = {a["key"] for a in engine.find_allergens(["Coconut milk", "Cocoa butter"], [])}
    assert "milk" not in keys
    assert "coconut" in keys


def test_buckwheat_is_not_wheat():
    keys = {a["key"] for a in engine.find_allergens(["Buckwheat flour"], [])}
    assert "buckwheat" in keys and "gluten" not in keys


def test_allergen_resolution():
    assert resolve_allergen("cashews") == "cashew"
    assert resolve_allergen("Kaju") == "cashew"
    assert resolve_allergen("groundnut") == "peanut"
    assert resolve_allergen("dairy") == "milk"
    assert resolve_allergen("unobtainium") is None


def test_member_verdicts(biscuit, household):
    result = engine.analyze(biscuit, household)
    asha, rohan = result["members"]
    assert asha["status"] == "AVOID"
    reasons = " | ".join(f["reason"] for f in asha["flags"])
    assert "Cashew" in reasons and "Not jain" in reasons and "High sugar" in reasons
    # every flag carries evidence
    assert all(f["evidence"] for f in asha["flags"])
    assert rohan["status"] == "WARN"
    assert any("lactose" in f["reason"].lower() for f in rohan["flags"])
    assert any("traces of Peanut" in f["reason"] for f in rohan["flags"])


def test_e471_needs_check_for_vegetarian():
    ex = Extraction(ingredients=["Wheat flour", "Emulsifier (E471)"], nutrition_per_100g={"sugar_g": 1})
    hh = Household(members=[Member(name="V", diet_rules=["vegetarian"])])
    m = engine.analyze(ex, hh)["members"][0]
    assert m["status"] == "WARN"
    assert "source unclear" in m["flags"][0]["reason"]


def test_eggetarian_allows_egg_but_not_gelatin():
    ex = Extraction(ingredients=["Egg", "Gelatin"])
    m = engine.analyze(ex, Household(members=[Member(name="E", diet_rules=["eggetarian"])]))["members"][0]
    evidence = [f["evidence"] for f in m["flags"] if f["status"] == "AVOID"]
    assert evidence == ["Gelatin"]


def test_parent_allergen_warns_specific_allergy():
    ex = Extraction(ingredients=["Mixed nuts (10%)"])
    m = engine.analyze(ex, Household(members=[Member(name="A", allergens=["cashew"])]))["members"][0]
    assert m["status"] == "WARN"


def test_unknown_allergen_falls_back_to_text_match():
    ex = Extraction(ingredients=["Wheat flour", "Quinoa"])
    m = engine.analyze(ex, Household(members=[Member(name="A", allergens=["quinoa"])]))["members"][0]
    assert m["status"] == "AVOID"


def test_avoid_list_synonyms():
    ex = Extraction(ingredients=["Edible vegetable oil (palmolein)", "Salt"])
    m = engine.analyze(ex, Household(members=[Member(name="A", avoid_ingredients=["palm oil"])]))["members"][0]
    assert m["status"] == "AVOID"


def test_child_colour_warning():
    ex = Extraction(ingredients=["Sugar", "Colour (INS 102, 110)"])
    m = engine.analyze(ex, Household(members=[Member(name="Kid", relation="son", age=7)]))["members"][0]
    assert any(f["category"] == "child" for f in m["flags"])


def test_small_serving_hides_high_sugar(biscuit):
    serving = engine.analyze_product(biscuit)["serving"]
    sugar = next(r for r in serving["rows"] if r["nutrient"] == "sugar_g")
    assert sugar["per_serving"] == 6.8 and sugar["hidden_by_small_serving"]


def test_safe_when_no_conflicts(oats):
    m = engine.analyze(oats, Household(members=[Member(name="A")]))["members"][0]
    assert m["status"] == "SAFE"


def test_analysis_is_deterministic(biscuit, household):
    runs = [engine.analyze(biscuit, household) for _ in range(5)]
    assert all(r == runs[0] for r in runs)


def test_fox_nuts_are_not_tree_nuts():
    keys = {a["key"] for a in engine.find_allergens(["Fox nuts (makhana 88%)", "Ground nuts"], [])}
    assert "tree_nuts" not in keys
