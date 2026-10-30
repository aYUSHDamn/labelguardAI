from rules.scoring import grade_for, health_score, processing_level


def test_score_is_deterministic():
    n = {"energy_kcal": 480, "sugar_g": 34, "sodium_mg": 330, "sat_fat_g": 9.5, "protein_g": 5.5, "fiber_g": 2}
    adds = [{"concern": "medium", "class": "colour"}, {"concern": "low", "class": "emulsifier"}]
    scores = {health_score(n, "biscuits_cookies", adds, ["a", "b", "c"])["score"] for _ in range(20)}
    assert len(scores) == 1


def test_known_values():
    # Plain rolled oats: tiny penalties, max bonuses -> clamps at 100.
    oats = health_score({"energy_kcal": 390, "sugar_g": 1, "sodium_mg": 5, "sat_fat_g": 1.5,
                         "protein_g": 12, "fiber_g": 10}, "breakfast_cereals", [], ["rolled oats"])
    assert oats["score"] == 100 and oats["color"] == "green" and oats["processing_level"] == 1

    # Hand-computed (each component rounded to 1 decimal):
    # 100 - 29.7(sugar) - 8.2(sodium) - 19(sat) - 7.7(energy) - 0(additives) - 5(processed)
    #     + 3.2(fibre) + 3.9(protein) = 37.5 -> 38
    r = health_score({"energy_kcal": 480, "sugar_g": 34, "sodium_mg": 330, "sat_fat_g": 9.5,
                      "protein_g": 5.5, "fiber_g": 2}, "biscuits_cookies", [], ["flour", "sugar", "oil"])
    assert r["score"] == 38 and r["color"] == "red"


def test_drinks_use_stricter_sugar_scale():
    solid = health_score({"sugar_g": 10}, "biscuits_cookies", [], ["x"])
    drink = health_score({"sugar_g": 10}, "soft_drinks", [], ["x"])
    sugar = lambda r: next(c["points"] for c in r["components"] if c["key"] == "sugar")  # noqa: E731
    assert sugar(drink) < sugar(solid)
    assert drink["basis"] == "per 100ml"


def test_penalties_are_capped():
    r = health_score({"sugar_g": 100, "sodium_mg": 10000, "sat_fat_g": 80, "energy_kcal": 900}, "other",
                     [{"concern": "high", "class": "colour"}] * 10, ["a"] * 10)
    pts = {c["key"]: c["points"] for c in r["components"]}
    assert pts == {"sugar": -35, "sodium": -25, "sat_fat": -20, "energy": -10, "additives": -15, "processing": -10}
    assert r["score"] == 0


def test_missing_values_are_reported():
    r = health_score({}, "other", [], ["x"])
    assert set(r["missing"]) == {"sugar_g", "sodium_mg", "sat_fat_g", "energy_kcal"}
    assert r["data_complete"] is False


def test_processing_levels():
    assert processing_level(["peanuts"], []) == 1
    assert processing_level(["flour", "sugar", "salt"], []) == 3
    assert processing_level(["flour", "emulsifier (322)"], []) == 4


def test_grades():
    assert grade_for(70)["color"] == "green"
    assert grade_for(69)["color"] == "amber"
    assert grade_for(50)["color"] == "amber"
    assert grade_for(49)["color"] == "red"
