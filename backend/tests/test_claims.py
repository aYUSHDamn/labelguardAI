from rules import engine
from schemas import Extraction


def verdicts(ex):
    return {c["claim"]: c["verdict"] for c in engine.analyze_product(ex)["claims"]}


def test_biscuit_claims(biscuit):
    assert verdicts(biscuit) == {"healthy": "misleading", "no added sugar": "misleading",
                                 "made with whole wheat": "misleading"}


def test_oats_claims(oats):
    assert verdicts(oats) == {"high fibre": "ok", "no added sugar": "ok"}


def test_sugar_free_threshold():
    ex = Extraction(claims=["Sugar Free"], nutrition_per_100g={"sugar_g": 3.2}, ingredients=["maltitol"])
    assert verdicts(ex)["sugar free"] == "misleading"
    ex = Extraction(claims=["sugar free"], nutrition_per_100g={"sugar_g": 0.3}, ingredients=["maltitol"])
    assert verdicts(ex)["sugar free"] == "ok"


def test_high_protein_uses_energy_share():
    ex = Extraction(claims=["high protein"], nutrition_per_100g={"protein_g": 8, "energy_kcal": 450})
    assert verdicts(ex)["high protein"] == "misleading"   # 7% of calories
    ex = Extraction(claims=["high protein"], nutrition_per_100g={"protein_g": 30, "energy_kcal": 400})
    assert verdicts(ex)["high protein"] == "ok"           # 30% of calories


def test_no_msg_but_other_enhancers():
    ex = Extraction(claims=["No added MSG"], ingredients=["Salt", "Yeast extract", "Flavour enhancer (INS 627)"])
    assert verdicts(ex)["no added msg"] == "marketing"


def test_no_preservatives():
    ex = Extraction(claims=["no preservatives"], ingredients=["Water", "Preservative (INS 211)"])
    assert verdicts(ex)["no preservatives"] == "misleading"


def test_trans_fat_free_with_hydrogenated_fat():
    ex = Extraction(claims=["0g trans fat"], ingredients=["Flour", "Partially hydrogenated vegetable oil"])
    assert verdicts(ex)["0g trans fat"] == "misleading"


def test_cholesterol_free_plant_product_is_marketing():
    ex = Extraction(claims=["cholesterol free"], ingredients=["Groundnut oil"])
    assert verdicts(ex)["cholesterol free"] == "marketing"


def test_unreadable_values_give_unknown():
    ex = Extraction(claims=["low sugar"], nutrition_per_100g={})
    assert verdicts(ex)["low sugar"] == "unknown"
