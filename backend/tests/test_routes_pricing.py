from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.models import PricingInputs
from app.routes import pricing


def _pricing_payload() -> dict[str, object]:
    return {"inputs": PricingInputs().model_dump()}


def test_price_success(client, recorder):
    resp = client.post("/api/price", json=_pricing_payload())
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["pricing"]["meta"]["source"] == "cache_ro"
    assert recorder.pricing_calls  # engine invoked via cache warm


def test_price_requires_excel_enabled(client):
    settings = pricing.settings_mgr.load()
    updated = settings.model_copy(update={"EXCEL_COMPAT_MODE": "off"})
    pricing.settings_mgr.save(updated)

    resp = client.post("/api/price", json=_pricing_payload())
    assert resp.status_code == 400
    assert "Excel compatibility mode is OFF" in resp.get_json()["errors"]["pricing"]


def test_price_missing_workbook_path(client, tmp_path):
    settings = pricing.settings_mgr.load()
    workbook = tmp_path / "wb.xlsx"
    workbook.write_text("grid", encoding="utf-8")
    updated = settings.model_copy(update={"EXTERNAL_WORKBOOK_PATH": str(workbook)})
    pricing.settings_mgr.save(updated)
    workbook.unlink()

    resp = client.post("/api/price", json=_pricing_payload())
    assert resp.status_code == 400
    assert "Workbook not found" in resp.get_json()["errors"]["pricing"]


def test_price_engine_failure(client):
    pricing.ExcelPricingEngine.error = RuntimeError("boom")
    resp = client.post("/api/price", json=_pricing_payload())
    assert resp.status_code == 500
    assert "boom" in resp.get_json()["errors"]["pricing"]
    pricing.ExcelPricingEngine.error = None


def test_price_refresh_endpoint(client, tmp_path):
    settings = pricing.settings_mgr.load()
    workbook = tmp_path / "wb.xlsx"
    workbook.write_text("grid", encoding="utf-8")
    updated = settings.model_copy(update={"EXTERNAL_WORKBOOK_PATH": str(workbook), "EXCEL_COMPAT_MODE": "auto"})
    pricing.settings_mgr.save(updated)

    resp = client.post("/api/price/refresh")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["workbook"] == str(workbook)
