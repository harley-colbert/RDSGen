from __future__ import annotations

import pytest

from app.domain.models import PricingInputs, Settings


def test_settings_trims_and_defaults(tmp_path):
    settings = Settings(
        OUTPUT_DIR=f"  {tmp_path}  ",
        WORD_TEMPLATE_PATH="  ",
        COSTING_TEMPLATE_PATH=None,
        EXTERNAL_WORKBOOK_PATH=" \t",
        EXCEL_COMPAT_MODE=" auto ",
    )
    assert settings.OUTPUT_DIR.endswith(str(tmp_path.name))
    assert settings.WORD_TEMPLATE_PATH == ""
    assert settings.COSTING_TEMPLATE_PATH is None
    assert settings.EXTERNAL_WORKBOOK_PATH == ""
    assert settings.EXCEL_COMPAT_MODE == "auto"


def test_pricing_inputs_margin_sync_round_trip():
    inputs = PricingInputs(margin=0.3, margin_pct=35)
    assert pytest.approx(inputs.margin, rel=1e-6) == 0.35
    assert pytest.approx(inputs.margin_pct, rel=1e-6) == 35.0

    inputs2 = PricingInputs(margin=0.4)
    assert inputs2.margin_pct == pytest.approx(40.0)


def test_pricing_inputs_spare_quantities_validation():
    with pytest.raises(ValueError):
        PricingInputs(spare_blades_qty=25)
    with pytest.raises(ValueError):
        PricingInputs(spare_pads_qty=5)

    ok = PricingInputs(spare_blades_qty=30, spare_pads_qty=0)
    assert ok.spare_blades_qty == 30
    assert ok.spare_pads_qty == 0
