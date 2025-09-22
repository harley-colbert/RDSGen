from __future__ import annotations

from pathlib import Path

from app.domain.models import PricingInputs
from app.routes import pricing


def test_full_generation_flow(client):
    inputs = PricingInputs().model_dump()

    # 1. Validate inputs
    resp = client.post("/api/validate", json=inputs)
    assert resp.status_code == 200

    # 2. Live pricing
    resp = client.post("/api/price", json={"inputs": inputs})
    assert resp.status_code == 200
    pricing_payload = resp.get_json()["pricing"]
    assert pricing_payload["meta"]["workbook"]

    # 3. Generate outputs
    resp = client.post("/api/generate", json={"inputs": inputs})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    outputs = data["outputs"]
    assert set(outputs) == {"quote_docx", "costing_xlsx"}

    settings = pricing.settings_mgr.load()
    out_root = Path(settings.OUTPUT_DIR)
    quote_path = out_root / Path(outputs["quote_docx"]).relative_to("outputs")
    costing_path = out_root / Path(outputs["costing_xlsx"]).relative_to("outputs")
    assert quote_path.exists()
    assert costing_path.exists()

    # 4. Download one of the outputs
    dl = client.get(f"/api/outputs/{costing_path.relative_to(out_root)}")
    assert dl.status_code == 200
    assert dl.data
