from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import SettingsManager
from app.domain.models import Settings


def test_settings_manager_loads_defaults_when_missing(tmp_path: Path):
    mgr = SettingsManager(storage_path=tmp_path / "settings.json")
    settings = mgr.load()
    assert settings.OUTPUT_DIR.endswith("outputs")


def test_settings_manager_saves_and_reads_round_trip(tmp_path: Path):
    storage = tmp_path / "settings.json"
    mgr = SettingsManager(storage_path=storage)
    outputs = tmp_path / "custom"
    outputs.mkdir()
    template = tmp_path / "tpl.docx"
    template.write_text("tpl", encoding="utf-8")
    costing = tmp_path / "tpl.xlsx"
    costing.write_text("tpl", encoding="utf-8")
    workbook = tmp_path / "grid.xlsx"
    workbook.write_text("grid", encoding="utf-8")

    saved = mgr.save(Settings(
        OUTPUT_DIR=str(outputs),
        WORD_TEMPLATE_PATH=str(template),
        COSTING_TEMPLATE_PATH=str(costing),
        EXTERNAL_WORKBOOK_PATH=str(workbook),
        EXCEL_COMPAT_MODE="auto",
    ))
    assert saved == mgr.load(refresh=True)

    data = json.loads(storage.read_text("utf-8"))
    assert data["OUTPUT_DIR"] == str(outputs)


def test_settings_manager_coerces_boolean_excel_flag(tmp_path: Path):
    storage = tmp_path / "settings.json"
    storage.write_text(json.dumps({"EXCEL_COMPAT_MODE": True}), encoding="utf-8")
    mgr = SettingsManager(storage_path=storage)
    settings = mgr.load(refresh=True)
    assert settings.EXCEL_COMPAT_MODE == "auto"

    storage.write_text(json.dumps({"EXCEL_COMPAT_MODE": False}), encoding="utf-8")
    settings = mgr.load(refresh=True)
    assert settings.EXCEL_COMPAT_MODE == "off"


def test_settings_manager_validate_paths_handles_missing(tmp_path: Path):
    outputs = tmp_path / "out"
    mgr = SettingsManager(tmp_path / "settings.json")
    settings = Settings(
        OUTPUT_DIR=str(outputs / "missing"),
        WORD_TEMPLATE_PATH=str(tmp_path / "nope.docx"),
        COSTING_TEMPLATE_PATH=str(tmp_path / "nope.xlsx"),
        EXTERNAL_WORKBOOK_PATH=str(tmp_path / "nope2.xlsx"),
        EXCEL_COMPAT_MODE="auto",
    )
    ok, errors = mgr.validate_paths(settings)
    assert not ok
    assert "WORD_TEMPLATE_PATH" in errors
    assert "EXTERNAL_WORKBOOK_PATH" in errors
