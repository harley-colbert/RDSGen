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
    payload = PricingInputs(spare_blades_qty=15).model_dump()
    resp = client.post("/api/validate", json=payload)
    assert resp.status_code == 400
    payload = resp.get_json()
    assert "spare_blades_qty" in payload["errors"]
