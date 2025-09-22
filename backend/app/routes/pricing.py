# backend/app/routes/pricing.py
from __future__ import annotations

import os
import logging
from time import time
from threading import Lock
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Tuple, Optional, Any

from flask import request, jsonify, current_app

from .blueprint import api_bp
from .deps import settings_mgr
from ..domain.models import Inputs
from ..domain import rules
from ..services.pricing_engine import ExcelPricingEngine  # ExcelPriceList type optional

log = logging.getLogger("RDSGen.routes.pricing")

# ---------------- Cache of workbook costs (base + per-option) ----------------
_cache_lock = Lock()
_price_cache: Dict[str, object] = {
    "key": None,     # workbook path (str)
    "ts": 0.0,       # when loaded (epoch seconds)
    "base": None,    # float base cost
    "items": None,   # dict[str,float] option costs
}


# ----------------------------- Helpers ---------------------------------------

def _is_url(p: str) -> bool:
    try:
        u = urlparse(p)
        return u.scheme in ("http", "https")
    except Exception:
        return False


def _excel_mode_enabled(excel_compat_mode) -> bool:
    """
    Backward + forward compatible:
    - old schema: bool (True == enabled)
    - new schema: 'auto' | 'com' | 'openpyxl' (any of these means enabled)
    """
    if isinstance(excel_compat_mode, bool):
        return bool(excel_compat_mode)
    if isinstance(excel_compat_mode, str):
        return excel_compat_mode.strip().lower() in {"auto", "com", "openpyxl"}
    return False


def _ensure_cost_cache(path: str) -> None:
    """
    Load costing grid (read-only baseline) if cache is empty or workbook changed.

    Uses ExcelPricingEngine(path, visible=False) and reads a **margin=0.0** price
    list. This returns base COST and per-option COSTS independent of runtime
    margin. Runtime margin is applied later in rules.compute_from_price_list().
    """
    with _cache_lock:
        if _price_cache["key"] == path and _price_cache["base"] is not None:
            return

        eng = ExcelPricingEngine(path, visible=False)
        # IMPORTANT: call with positional margin only (no invalid kwargs).
        pl = eng.get_price_list_for_margin(0.0)

        _price_cache["key"] = path
        _price_cache["ts"] = time()
        _price_cache["base"] = getattr(pl, "base_price", None)
        _price_cache["items"] = getattr(pl, "items", None)

        if _price_cache["base"] is None or _price_cache["items"] is None:
            raise RuntimeError("ExcelPricingEngine returned an unexpected structure (missing base_price/items).")

        current_app.logger.info(
            "cost_cache refreshed path=%s base=%.2f items=%d",
            path, float(_price_cache["base"]), len(_price_cache["items"] or {})
        )


def _get_cached_costs(path: str) -> Tuple[float, Dict[str, float]]:
    _ensure_cost_cache(path)
    with _cache_lock:
        base = float(_price_cache["base"])  # type: ignore[arg-type]
        items = dict(_price_cache["items"] or {})  # type: ignore[assignment]
        return base, items


# --------- Compatibility helper expected by generate.py (re-added) -----------

def _excel_pricing_if_enabled(margin: float) -> Optional[Any]:
    """
    Compatibility shim for generate.py.

    Return a price list object from the external Excel workbook when Excel mode
    is enabled; else None.

    - Allows SharePoint/HTTPS paths (no local exists() check for URLs).
    - For local paths, verifies the file exists.
    - Uses engine.get_price_list_for_margin(margin), returning the workbook-derived
      structure (typically with .base_price and .items).
    """
    s = settings_mgr.load()
    excel_enabled = _excel_mode_enabled(getattr(s, "EXCEL_COMPAT_MODE", False))
    if not excel_enabled:
        return None

    path = (getattr(s, "EXTERNAL_WORKBOOK_PATH", "") or "").strip()
    if not path:
        raise RuntimeError("EXCEL_COMPAT_MODE is ON but EXTERNAL_WORKBOOK_PATH is empty.")

    if not _is_url(path) and not Path(path).exists():
        raise RuntimeError(f"External workbook not found: {path}")

    eng = ExcelPricingEngine(path, visible=False)
    # IMPORTANT: call with positional margin only.
    return eng.get_price_list_for_margin(float(margin))


# ----------------------------- Endpoints -------------------------------------

@api_bp.post("/price", endpoint="price_live")
def price_live():
    """
    Compute live pricing from cached read-only costs + current inputs/margin.

    Request body supports:
    - either top-level fields or { "inputs": { ... } }
    - legacy `margin` (0..1) and/or `margin_pct` (0..95); models keep them in sync
    """
    payload = request.get_json(force=True) or {}
    data = payload.get("inputs", payload)

    # Validate & normalize inputs early
    try:
        inp = Inputs(**data)
    except Exception as e:
        return jsonify({"ok": False, "errors": {"inputs": str(e)}}), 400

    # Domain-level validation (if your rules module adds constraints)
    val_errors = rules.validate(inp)
    if val_errors:
        return jsonify({"ok": False, "errors": val_errors}), 400

    # Settings and guardrails
    s = settings_mgr.load()
    path = (getattr(s, "EXTERNAL_WORKBOOK_PATH", "") or "").strip()
    excel_enabled = _excel_mode_enabled(getattr(s, "EXCEL_COMPAT_MODE", False))

    if not excel_enabled:
        return jsonify({"ok": False, "errors": {"pricing": "Excel compatibility mode is OFF"}}), 400
    if not path:
        return jsonify({"ok": False, "errors": {"pricing": "External workbook path is empty"}}), 400

    # Existence check only for local files; URLs (SharePoint/HTTPS) are allowed
    if not _is_url(path) and not Path(path).exists():
        return jsonify({"ok": False, "errors": {"pricing": f"Workbook not found: {path}"}}), 400

    # Compute using cached baseline + rules
    try:
        base_cost, item_costs = _get_cached_costs(path)
        comp = rules.compute_from_price_list(inp, base_cost, item_costs)
        payload = comp.model_dump() if hasattr(comp, "model_dump") else comp  # support pydantic/BaseModel or dict

        payload["meta"] = {
            "source": "cache_ro",
            "cache_ts": _price_cache["ts"],
            "workbook": path,
        }
        return jsonify({"ok": True, "pricing": payload})
    except Exception as e:
        current_app.logger.exception("Live pricing (cache) failed for %s", path)
        return jsonify({"ok": False, "errors": {"pricing": f"{type(e).__name__}: {e}"}}), 500


@api_bp.post("/price/refresh", endpoint="price_refresh")
def price_refresh():
    """
    Force refresh of the costing cache (read-only baseline).
    Useful after changing settings (workbook path / compat mode).
    """
    s = settings_mgr.load()
    path = (getattr(s, "EXTERNAL_WORKBOOK_PATH", "") or "").strip()
    excel_enabled = _excel_mode_enabled(getattr(s, "EXCEL_COMPAT_MODE", False))

    if not excel_enabled or not path:
        return jsonify({"ok": False, "errors": {"pricing": "Excel compat OFF or path missing"}}), 400

    if not _is_url(path) and not os.path.exists(path):
        return jsonify({"ok": False, "errors": {"pricing": f"Workbook not found: {path}"}}), 400

    try:
        _ensure_cost_cache(path)
        return jsonify({
            "ok": True,
            "base_cost": _price_cache["base"],
            "items": _price_cache["items"],
            "cache_ts": _price_cache["ts"],
            "workbook": path,
        })
    except Exception as e:
        current_app.logger.exception("Price cache refresh failed for %s", path)
        return jsonify({"ok": False, "errors": {"pricing": f"{type(e).__name__}: {e}"}}), 500
