from __future__ import annotations

from app.domain.models import PricingInputs
from app.domain import rules


def _price_list() -> dict[str, float]:
    return {
        "Spare Parts Package": 100.0,
        "Spare Saw Blades": 5.0,
        "Spare Foam Pads": 2.5,
        "Guarding – Taller": 300.0,
        "Guarding – Netting": 450.0,
        "Infeed – Front USL": 50.0,
        "Infeed – Side USL": 60.0,
        "Infeed – Side Badger": 70.0,
        "Transformer – Canada": 80.0,
        "Transformer – Step Up": 90.0,
        "Training (English & Spanish)": 25.0,
    }


def test_validate_flags_bad_spares():
    inp = PricingInputs(spare_blades_qty=15, spare_pads_qty=20)
    errors = rules.validate(inp)
    assert "spare_blades_qty" in errors
    assert "spare_pads_qty" not in errors


def test_compute_from_price_list_accumulates_all_options():
    inp = PricingInputs(
        spare_parts_qty=1,
        spare_blades_qty=20,
        spare_pads_qty=10,
        guarding="Tall w/ Netting",
        feeding="Side Badger",
        transformer="Canada",
        training="English & Spanish",
        base_price=1000.0,
    )
    comp = rules.compute_from_price_list(inp, 1000.0, _price_list())
    assert comp.options_qty["Spare Parts Package"] == 1
    assert comp.options_breakdown["Spare Saw Blades"] == 100.0
    assert comp.options_breakdown["Spare Foam Pads"] == 25.0
    assert comp.options_breakdown["Infeed – Side Badger"] == 70.0
    assert comp.options_breakdown["Transformer – Canada"] == 80.0
    assert comp.total_price == 1000.0 + comp.options_price_total


def test_compute_from_price_list_with_minimal_options():
    inp = PricingInputs(
        spare_parts_qty=0,
        spare_blades_qty=0,
        spare_pads_qty=0,
        guarding="Standard",
        feeding="No",
        transformer="None",
        training="English",
        base_price=500.0,
    )
    comp = rules.compute_from_price_list(inp, 500.0, _price_list())
    assert comp.options_breakdown == {}
    assert comp.options_price_total == 0.0
    assert comp.total_price == 500.0
