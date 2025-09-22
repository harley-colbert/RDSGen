# backend/app/routes/options.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, TypedDict

from flask import Blueprint, jsonify, request

from .blueprint import api_bp

log = logging.getLogger("RDSGen.routes.options")
bp = Blueprint("options", __name__, url_prefix="/options")


class OptionsPayload(TypedDict):
    """
    Shape for options payloads returned to the frontend.
    All option lists include canonical values used by validators/rules.
    """
    guarding: List[str]
    feeding: List[str]
    transformer: List[str]
    training: List[str]
    spare_parts_qty: List[int]
    spare_blades_qty: List[int]
    spare_pads_qty: List[int]


@dataclass(frozen=True)
class _Available:
    """
    Canonical option vocabulary.
    IMPORTANT: These values align with domain validators and pricing rules.
    """
    spare_parts_qty: List[int]
    spare_blades_qty: List[int]
    spare_pads_qty: List[int]
    guarding: List[str]
    feeding: List[str]
    transformer: List[str]
    training: List[str]


AVAILABLE = _Available(
    spare_parts_qty=[0, 1],
    spare_blades_qty=[0, 10, 20, 30, 40, 50],
    spare_pads_qty=[0, 10, 20, 30, 40, 50],
    # Aligned with validators/rules: "Standard", "Tall", "Tall w/ Netting"
    guarding=["Standard", "Tall", "Tall w/ Netting"],
    # Aligned and de-duplicated: no "Front Badger"
    feeding=["No", "Front USL", "Side USL", "Side Badger"],
    transformer=["None", "Canada", "Step Up"],
    training=["English", "English & Spanish"],
)


def _compose_payload() -> OptionsPayload:
    """Return the complete options payload in one response."""
    payload: OptionsPayload = {
        "spare_parts_qty": AVAILABLE.spare_parts_qty,
        "spare_blades_qty": AVAILABLE.spare_blades_qty,
        "spare_pads_qty": AVAILABLE.spare_pads_qty,
        "guarding": AVAILABLE.guarding,
        "feeding": AVAILABLE.feeding,
        "transformer": AVAILABLE.transformer,
        "training": AVAILABLE.training,
    }
    return payload


@bp.get("")
def get_all_options():
    """
    GET /api/options
    Returns the entire option map so the FE can hydrate all <select>s in one call.
    """
    log.debug("Options requested (all)")
    return jsonify(_compose_payload())


@bp.get("/<category>")
def get_options(category: str):
    """
    GET /api/options/<category>
    Returns options for a single category to support lazy-loading.
    """
    log.debug("Options requested for category=%s", category)
    data: Dict[str, Any] = _compose_payload()
    if category not in data:
        log.warning("Unknown options category requested: %s", category)
        return jsonify({"error": f"Unknown category '{category}'"}), 404
    return jsonify({category: data[category]})


@bp.post("/labels")
def get_labeled_options():
    """
    OPTIONAL convenience:
    POST /api/options/labels
    Body: { "categories": ["guarding","feeding",...] }
    Returns [{ value, label }] for each requested category (label==value by default).
    This lets the FE show a friendly label while submitting the canonical value.
    """
    body = request.get_json(silent=True) or {}
    cats: List[str] = body.get("categories") or []
    full = _compose_payload()

    result: Dict[str, List[Dict[str, str]]] = {}
    for cat in cats:
        if cat not in full:
            continue
        result[cat] = [{"value": v, "label": v} for v in full[cat]]  # label==value by default

    log.debug("Labeled options response for categories=%s", cats)
    return jsonify(result)


# Register nested blueprint under the API namespace
api_bp.register_blueprint(bp)
