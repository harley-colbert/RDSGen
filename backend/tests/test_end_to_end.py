from __future__ import annotations

from app.domain.models import PricingInputs
from app.domain import rules


def test_compute_from_price_list_matches_expected_totals():
    inputs = PricingInputs(
        margin=0.24,
        base_price=414320.82,
        spare_parts_qty=1,
        spare_blades_qty=20,
        spare_pads_qty=30,
        guarding="Standard",
        feeding="No",
        transformer="None",
        training="English",
    )
    price_list = {
        "Spare Parts Package": 14500.0,
        "Spare Saw Blades": 199.89,
        "Spare Foam Pads": 149.9,
    }
    comp = rules.compute_from_price_list(inputs, inputs.base_price, price_list)
    assert round(comp.options_price_total, 2) == 19888.8
    assert round(comp.total_price, 2) == 434209.62
