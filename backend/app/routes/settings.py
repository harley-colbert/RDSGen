from flask import request, jsonify
from .blueprint import api_bp
from ..domain.models import Settings
from .deps import settings_mgr

@api_bp.get("/settings")
def get_settings():
    return jsonify(settings_mgr.load().model_dump())

@api_bp.post("/settings")
def set_settings():
    data = request.get_json(force=True) or {}
    try:
        s = Settings(**data)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Invalid settings: {e}"}), 400
    ok, errors = settings_mgr.validate_paths(s)
    if not ok:
        return jsonify({"ok": False, "errors": errors}), 400
    settings_mgr.save(s)
    return jsonify({"ok": True, "settings": s.model_dump()})
