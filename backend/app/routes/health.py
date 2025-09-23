from datetime import UTC, datetime
from flask import jsonify
from .blueprint import api_bp

@api_bp.get("/health")
def health():
    now = datetime.now(UTC)
    return jsonify({"ok": True, "ts": now.isoformat().replace("+00:00", "Z")})
