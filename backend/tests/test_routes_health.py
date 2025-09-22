from __future__ import annotations


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["ts"].endswith("Z")
