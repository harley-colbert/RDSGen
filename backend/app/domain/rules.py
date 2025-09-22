from __future__ import annotations
from typing import Dict
from .models import Inputs, Computation

def validate(inp: Inputs) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for k in ['spare_blades_qty', 'spare_pads_qty']:
        q = getattr(inp, k)
        if q % 10 != 0:
            errors[k] = 'Quantity must be a multiple of 10 (0,10,20,30,40,50).'
    if inp.spare_parts_qty not in (0,1):
        errors['spare_parts_qty'] = 'Quantity must be 0 or 1.'
    return errors

def compute_from_price_list(inp: Inputs, base_price: float, price_list: Dict[str, float]) -> Computation:
    breakdown: Dict[str, float] = {}
    qtys: Dict[str, int] = {}

    breakdown['Base'] = float(base_price)
    qtys['Base'] = 1

    if inp.spare_parts_qty:
        unit = price_list.get('Spare Parts Package', 0.0)
        breakdown['Spare Parts Package'] = unit * inp.spare_parts_qty
        qtys['Spare Parts Package'] = inp.spare_parts_qty
    if inp.spare_blades_qty:
        unit = price_list.get('Spare Saw Blades', 0.0)
        breakdown['Spare Saw Blades'] = unit * inp.spare_blades_qty
        qtys['Spare Saw Blades'] = inp.spare_blades_qty
    if inp.spare_pads_qty:
        unit = price_list.get('Spare Foam Pads', 0.0)
        breakdown['Spare Foam Pads'] = unit * inp.spare_pads_qty
        qtys['Spare Foam Pads'] = inp.spare_pads_qty

    if inp.guarding == 'Tall':
        breakdown['Taller Guarding'] = price_list.get('Taller Guarding', 0.0)
        qtys['Taller Guarding'] = 1
    elif inp.guarding == 'Tall w/ Netting':
        breakdown['Taller Guarding and Netting'] = price_list.get('Taller Guarding and Netting', 0.0)
        qtys['Taller Guarding and Netting'] = 1

    if inp.feeding in ('Front USL','Front Badger'):
        breakdown['Front USL'] = price_list.get('Front USL', 0.0)
        qtys['Front USL'] = 1
    elif inp.feeding == 'Side USL':
        breakdown['Side USL'] = price_list.get('Side USL', 0.0)
        qtys['Side USL'] = 1
    elif inp.feeding == 'Side Badger':
        breakdown['Side Badger'] = price_list.get('Side Badger', 0.0)
        qtys['Side Badger'] = 1

    if inp.transformer == 'Canada':
        breakdown['Canada Transformer'] = price_list.get('Canada Transformer', 0.0)
        qtys['Canada Transformer'] = 1
    elif inp.transformer == 'Step Up':
        breakdown['Step Up Transformer'] = price_list.get('Step Up Transformer', 0.0)
        qtys['Step Up Transformer'] = 1

    if inp.training == 'English & Spanish':
        breakdown['Spanish Training'] = price_list.get('Spanish Training', 0.0)
        qtys['Spanish Training'] = 1

    options_total = sum(v for k,v in breakdown.items() if k != 'Base')
    total = float(base_price) + float(options_total)

    return Computation(
        options_breakdown={k:v for k,v in breakdown.items() if k != 'Base'},
        options_qty={k:v for k,v in qtys.items() if k != 'Base'},
        options_price_total=round(options_total,2),
        margin=inp.margin,
        base_price=round(float(base_price),2),
        total_price=round(float(total),2),
    )
