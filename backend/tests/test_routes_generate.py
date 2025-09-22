from __future__ import annotations

from pathlib import Path

from app.domain.models import PricingInputs
from app.routes import pricing


def _inputs_payload() -> dict[str, object]:
    return {"inputs": PricingInputs().model_dump()}


def test_generate_creates_outputs(client, recorder):
    resp = client.post("/api/generate", json=_inputs_payload())
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    outputs = payload["outputs"]
    assert "quote_docx" in outputs and "costing_xlsx" in outputs

    # Files written by stub generators
    settings = pricing.settings_mgr.load()
    out_root = Path(settings.OUTPUT_DIR)
    for rel in outputs.values():
        rel_path = Path(rel.lstrip("/"))
        file_path = out_root / rel_path.relative_to("outputs")
        assert file_path.exists()

    assert recorder.costing_calls
    assert recorder.word_calls


def test_generate_handles_pricing_error(client):
    pricing.ExcelPricingEngine.error = RuntimeError("excel boom")
    resp = client.post("/api/generate", json=_inputs_payload())
    assert resp.status_code == 500
    payload = resp.get_json()
    assert payload["errors"]["pricing"].startswith("excel boom")
    pricing.ExcelPricingEngine.error = None
