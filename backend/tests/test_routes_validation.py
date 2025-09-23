from __future__ import annotations

from app.domain.models import PricingInputs


def test_validate_success(client):
    payload = PricingInputs().model_dump()
    resp = client.post("/api/validate", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_validate_schema_error(client):
    resp = client.post("/api/validate", json={"margin": "invalid"})
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["errors"]["schema"]


def test_validate_rules_error(client):
    payload = PricingInputs.model_construct(
        margin=0.24,
        margin_pct=24.0,
        base_price=414320.82,
        spare_parts_qty=1,
        spare_blades_qty=15,
        spare_pads_qty=30,
        guarding="Standard",
        feeding="No",
        transformer="None",
        training="English",
    ).model_dump()
    resp = client.post("/api/validate", json=payload)
    assert resp.status_code == 400
    payload = resp.get_json()
    schema_msg = payload["errors"].get("schema", "")
    assert "spare_blades_qty" in schema_msg
