from app.domain.models import Inputs
from app.domain import rules
def test_sample_totals():
    inp = Inputs(margin=0.24, base_price=414320.82, spare_parts_qty=1, spare_blades_qty=20, spare_pads_qty=30, guarding='Standard', feeding='No', transformer='None', training='English')
    comp = rules.compute(inp)
    assert round(comp.options_price_total,2) == 19889.00
    assert round(comp.total_price,2) == 434209.82
