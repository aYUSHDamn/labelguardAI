"""End-to-end API tests with NO LLM and NO network (GEMINI_API_KEY empty, OFF disabled)."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["llm_configured"] is False


def test_profile_parse_falls_back_to_keywords(client):
    r = client.post("/api/profile/parse", json={
        "text": "Pre-diabetic, allergic to cashews, Jain, cutting sodium. My son is lactose intolerant."})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "keyword_fallback" and body["warning"]
    me, son = body["household"]["members"]
    assert me["allergens"] == ["cashew"] and me["diet_rules"] == ["jain"]
    assert me["conditions"] == ["prediabetes"] and me["limits"]["sodium_mg_per_day"] == 1500
    assert son["relation"] == "son" and son["conditions"] == ["lactose_intolerance"]


def test_full_flow(client):
    household = {"members": [
        {"name": "Asha", "allergens": ["Cashews"], "diet_rules": ["jain"], "conditions": ["prediabetes"]},
        {"name": "Rohan", "relation": "son", "age": 9, "conditions": ["lactose_intolerance"]}]}
    r = client.put("/api/profile", json={"household": household})
    assert r.status_code == 200
    assert r.json()["household"]["members"][0]["allergens"] == ["cashew"]

    r = client.post("/api/scan/demo/choco_cream_biscuit")
    assert r.status_code == 200
    scan = r.json()
    sid = scan["scan_id"]
    assert scan["analysis"]["members"][0]["status"] == "AVOID"
    assert scan["analysis"]["score"]["score"] < 50

    # explanation falls back to the template without an API key
    r = client.post("/api/scan/explain", json={"scan_id": sid, "language": "hi", "eli12": True})
    assert r.status_code == 200 and r.json()["source"] == "template_fallback"
    assert "/100" in r.json()["explanation"]

    # alternatives come from the fallback CSV, are better, and are safe for everyone
    r = client.get(f"/api/alternatives/{sid}")
    alts = r.json()["alternatives"]
    assert 1 <= len(alts) <= 3
    assert all(a["score"] > scan["analysis"]["score"]["score"] for a in alts)
    assert all("cashew" not in (a["product_name"] or "").lower() for a in alts)

    # feedback re-ranks
    first = alts[0]
    client.post("/api/alternatives/feedback", json={"scan_id": sid, "product_code": first["code"],
                                                    "product_name": first["product_name"], "brand": first["brand"],
                                                    "vote": -1, "reason": "not_available"})
    alts2 = client.get(f"/api/alternatives/{sid}").json()["alternatives"]
    moved = next((a for a in alts2 if a["code"] == first["code"]), None)
    assert moved is None or moved["feedback_adjustment"] < 0

    # log + tracker
    r = client.post("/api/log", json={"scan_id": sid, "member": "Asha", "servings": 2})
    assert r.status_code == 200 and r.json()["grams"] == 40
    t = client.get("/api/tracker").json()
    asha = next(m for m in t["members"] if m["member"] == "Asha")
    assert asha["sugar_g"] == 13.6 and asha["items_logged"] == 1

    # compare
    sid2 = client.post("/api/scan/demo/roasted_makhana").json()["scan_id"]
    c = client.post("/api/compare", json={"scan_id_a": sid, "scan_id_b": sid2, "member": "Asha"}).json()
    assert c["winner_scan_id"] == sid2


def test_scan_json_is_deterministic(client):
    ex = {"extraction": {"product_name": "X", "ingredients": ["Sugar", "Maltodextrin", "Salt"],
                         "nutrition_per_100g": {"sugar_g": 20, "sodium_mg": 400}}}
    s1 = client.post("/api/scan/json", json=ex).json()["analysis"]
    s2 = client.post("/api/scan/json", json=ex).json()["analysis"]
    assert s1 == s2


def test_bad_image_gives_error_json(client):
    r = client.post("/api/scan", files={"file": ("x.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400 and r.json() == {
        "error": "bad_image", "detail": "That file isn't a readable image. Please use a JPG or PNG photo."}


def test_scan_without_api_key_is_friendly(client):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, format="PNG")
    r = client.post("/api/scan", files={"file": ("x.png", buf.getvalue(), "image/png")})
    assert r.status_code == 503 and r.json()["error"] == "not_configured"


def test_missing_scan_404(client):
    r = client.get("/api/scan/99999")
    assert r.status_code == 404 and r.json()["error"] == "not_found"


def test_validation_error_shape(client):
    r = client.post("/api/compare", json={"scan_id_a": "abc"})
    assert r.status_code == 422 and set(r.json()) == {"error", "detail"}


def test_image_scan_is_cached_by_hash(client, monkeypatch):
    """Second upload of the same photo must cost zero LLM calls."""
    import pipeline
    from schemas import Extraction
    calls = []

    def fake_extract(jpeg):
        calls.append(len(jpeg))
        return Extraction(product_name="Fake", category="biscuits_cookies", ingredients=["Wheat flour", "Sugar"],
                          nutrition_per_100g={"sugar_g": 20, "sodium_mg": 300}, confidence=0.9)

    monkeypatch.setattr(pipeline, "extract_label", fake_extract)
    buf = io.BytesIO()
    Image.new("RGB", (3000, 2000), "white").save(buf, format="JPEG")
    raw = buf.getvalue()
    r1 = client.post("/api/scan", files={"file": ("a.jpg", raw, "image/jpeg")}).json()
    r2 = client.post("/api/scan", files={"file": ("a.jpg", raw, "image/jpeg")}).json()
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True
    assert r1["analysis"]["score"] == r2["analysis"]["score"]
    # image was resized to <= 1024 px before being sent
    from PIL import Image as _I
    assert max(_I.open(io.BytesIO(pipeline.prepare_image(raw))).size) <= 1024
