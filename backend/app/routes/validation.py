from flask import request, jsonify
from .blueprint import api_bp
from ..domain.models import Inputs
from ..domain import rules

@api_bp.post("/validate")
def validate_inputs():
    data = request.get_json(force=True) or {}
    payload = data.get("inputs", data)
    try:
        inp = Inputs(**payload)
    except Exception as e:
        return jsonify({"ok": False, "errors": {"schema": str(e)}}), 400
    errors = rules.validate(inp)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    return jsonify({"ok": True})
