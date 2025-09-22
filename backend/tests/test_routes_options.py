from __future__ import annotations


def test_options_all(client):
    resp = client.get("/api/options")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert set(payload) >= {"guarding", "feeding", "transformer", "training"}


def test_options_category_success(client):
    resp = client.get("/api/options/guarding")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload == {"guarding": ["Standard", "Tall", "Tall w/ Netting"]}


def test_options_category_unknown(client):
    resp = client.get("/api/options/unknown")
    assert resp.status_code == 404
    payload = resp.get_json()
    assert "error" in payload


def test_options_labels(client):
    resp = client.post("/api/options/labels", json={"categories": ["feeding", "training"]})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["feeding"][0] == {"value": "No", "label": "No"}
