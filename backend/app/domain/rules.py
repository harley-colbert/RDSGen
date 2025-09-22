from __future__ import annotations
from typing import Dict

from .models import Inputs, Computation

# ---------------------------------------------------------------------------
# Canonical option labels (match Excel Summary sheet row labels)
# ---------------------------------------------------------------------------
SPARE_PARTS = "Spare Parts Package"
SPARE_BLADES = "Spare Saw Blades"
SPARE_PADS = "Spare Foam Pads"
GUARD_TALLER = "Guarding – Taller"
GUARD_NETTING = "Guarding – Netting"
INFEED_FRONT = "Infeed – Front USL"
INFEED_SIDE_USL = "Infeed – Side USL"
INFEED_SIDE_BADGER = "Infeed – Side Badger"
TRAINING_BILINGUAL = "Training (English & Spanish)"
TRANSFORMER_CANADA = "Transformer – Canada"
TRANSFORMER_STEP_UP = "Transformer – Step Up"


def validate(inp: Inputs) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for k in ["spare_blades_qty", "spare_pads_qty"]:
        q = getattr(inp, k)
        if q % 10 != 0:
            errors[k] = "Quantity must be a multiple of 10 (0,10,20,30,40,50)."
    if inp.spare_parts_qty not in (0, 1):
        errors["spare_parts_qty"] = "Quantity must be 0 or 1."
    return errors


def _add_option(
    breakdown: Dict[str, float],
    qtys: Dict[str, int],
    label: str,
    unit_price: float,
    qty: int,
) -> None:
    if qty <= 0:
        return
    breakdown[label] = unit_price * qty
    qtys[label] = qty


def compute_from_price_list(inp: Inputs, base_price: float, price_list: Dict[str, float]) -> Computation:
    breakdown: Dict[str, float] = {"Base": float(base_price)}
    qtys: Dict[str, int] = {"Base": 1}

    _add_option(breakdown, qtys, SPARE_PARTS, price_list.get(SPARE_PARTS, 0.0), inp.spare_parts_qty)
    _add_option(breakdown, qtys, SPARE_BLADES, price_list.get(SPARE_BLADES, 0.0), inp.spare_blades_qty)
    _add_option(breakdown, qtys, SPARE_PADS, price_list.get(SPARE_PADS, 0.0), inp.spare_pads_qty)

    if inp.guarding == "Tall":
        _add_option(breakdown, qtys, GUARD_TALLER, price_list.get(GUARD_TALLER, 0.0), 1)
    elif inp.guarding == "Tall w/ Netting":
        _add_option(breakdown, qtys, GUARD_NETTING, price_list.get(GUARD_NETTING, 0.0), 1)

    feeding = inp.feeding
    if feeding in {"Front USL", "Front Badger"}:
        _add_option(breakdown, qtys, INFEED_FRONT, price_list.get(INFEED_FRONT, 0.0), 1)
    elif feeding == "Side USL":
        _add_option(breakdown, qtys, INFEED_SIDE_USL, price_list.get(INFEED_SIDE_USL, 0.0), 1)
    elif feeding == "Side Badger":
        _add_option(breakdown, qtys, INFEED_SIDE_BADGER, price_list.get(INFEED_SIDE_BADGER, 0.0), 1)

    if inp.transformer == "Canada":
        _add_option(
            breakdown,
            qtys,
            TRANSFORMER_CANADA,
            price_list.get(TRANSFORMER_CANADA, 0.0),
            1,
        )
    elif inp.transformer == "Step Up":
        _add_option(
            breakdown,
            qtys,
            TRANSFORMER_STEP_UP,
            price_list.get(TRANSFORMER_STEP_UP, 0.0),
            1,
        )

    if inp.training == "English & Spanish":
        _add_option(
            breakdown,
            qtys,
            TRAINING_BILINGUAL,
            price_list.get(TRAINING_BILINGUAL, 0.0),
            1,
        )

    options_total = sum(v for k, v in breakdown.items() if k != "Base")
    total = float(base_price) + float(options_total)

    return Computation(
        options_breakdown={k: v for k, v in breakdown.items() if k != "Base"},
        options_qty={k: v for k, v in qtys.items() if k != "Base"},
        options_price_total=round(options_total, 2),
        margin=inp.margin,
        base_price=round(float(base_price), 2),
        total_price=round(float(total), 2),
    )
