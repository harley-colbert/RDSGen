from datetime import datetime
from flask import jsonify
from .blueprint import api_bp

@api_bp.get("/health")
def health():
    return jsonify({"ok": True, "ts": datetime.utcnow().isoformat() + "Z"})
