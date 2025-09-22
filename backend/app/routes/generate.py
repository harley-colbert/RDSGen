from datetime import datetime
from pathlib import Path
from flask import request, jsonify
from .blueprint import api_bp
from .deps import settings_mgr
from .pricing import _excel_pricing_if_enabled
from ..domain.models import Inputs, GenerateResponse
from ..domain import rules
from ..services.costing_gen import CostingGenerator
from ..services.word_gen import WordGenerator

@api_bp.post("/generate")
def generate():
    data = request.get_json(force=True) or {}
    inp = Inputs(**data.get("inputs", data))
    val_errors = rules.validate(inp)
    if val_errors:
        return jsonify({"ok": False, "errors": val_errors}), 400

    s = settings_mgr.load()
    out_root = Path(s.OUTPUT_DIR)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = out_root / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        price_list = _excel_pricing_if_enabled(inp.margin)
    except Exception as e:
        return jsonify({"ok": False, "errors": {"pricing": str(e)}}), 500

    if price_list is None:
        comp = rules.compute(inp)
    else:
        comp = rules.compute_from_price_list(inp, price_list.base_price, price_list.items)

    costing_out = out_dir / "costing.xlsx"
    CostingGenerator(s.COSTING_TEMPLATE_PATH).generate(costing_out, inp, comp)

    word_out = out_dir / "quote.docx"
    WordGenerator(s.WORD_TEMPLATE_PATH).generate(word_out, inp, comp)

    resp = GenerateResponse(
        ok=True,
        outputs={
            "quote_docx": f"/outputs/{ts}/quote.docx",
            "costing_xlsx": f"/outputs/{ts}/costing.xlsx",
        },
    )
    return jsonify(resp.model_dump())
