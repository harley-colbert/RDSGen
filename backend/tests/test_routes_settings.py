from __future__ import annotations

from pathlib import Path


def test_get_settings_returns_current_config(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["OUTPUT_DIR"]
    assert payload["EXCEL_COMPAT_MODE"] in {"auto", "off", "com", "openpyxl"}


def test_set_settings_success(client, tmp_path, app):
    new_outputs = tmp_path / "outputs"
    new_outputs.mkdir()
    workbook = tmp_path / "grid.xlsx"
    workbook.write_text("grid", encoding="utf-8")
    word_tpl = tmp_path / "quote.docx"
    word_tpl.write_text("tpl", encoding="utf-8")
    costing_tpl = tmp_path / "cost.xlsx"
    costing_tpl.write_text("tpl", encoding="utf-8")

    resp = client.post(
        "/api/settings",
        json={
            "OUTPUT_DIR": str(new_outputs),
            "WORD_TEMPLATE_PATH": str(word_tpl),
            "COSTING_TEMPLATE_PATH": str(costing_tpl),
            "EXTERNAL_WORKBOOK_PATH": str(workbook),
            "EXCEL_COMPAT_MODE": "auto",
        },
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["settings"]["OUTPUT_DIR"] == str(new_outputs)

    saved = client.get("/api/settings").get_json()
    assert saved["OUTPUT_DIR"] == str(new_outputs)


def test_set_settings_validation_errors(client):
    resp = client.post("/api/settings", json={"OUTPUT_DIR": 123})
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["ok"] is False
