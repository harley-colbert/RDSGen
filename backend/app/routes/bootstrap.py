from __future__ import annotations

from flask import jsonify, current_app

from .blueprint import api_bp
from .pricing import preload_cost_cache


@api_bp.post("/bootstrap")
def bootstrap():
    """Load the external workbook cache before the UI is presented."""

    try:
        result = preload_cost_cache()
        payload = {
            "ok": True,
            "excel_enabled": result.get("excel_enabled", False),
            "cache_loaded": result.get("cache_loaded", False),
            "workbook": result.get("workbook", ""),
            "cache_ts": result.get("cache_ts"),
            "cache_method": result.get("cache_method"),
        }
        return jsonify(payload)
    except FileNotFoundError as exc:
        return jsonify({
            "ok": False,
            "errors": {"pricing": str(exc)},
        }), 400
    except RuntimeError as exc:
        return jsonify({
            "ok": False,
            "errors": {"pricing": str(exc)},
        }), 400
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.exception("Bootstrap failed")
        return jsonify({
            "ok": False,
            "errors": {"pricing": f"{type(exc).__name__}: {exc}"},
        }), 500
