# backend/app/domain/models.py
from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------
class Settings(BaseModel):
    """
    Persisted application settings used across the app.
    - WORD_TEMPLATE_PATH / COSTING_TEMPLATE_PATH: local files (optional)
    - EXTERNAL_WORKBOOK_PATH: local file OR http/https URL (validated in config)
    - OUTPUT_DIR: created if missing (validated in config)
    - EXCEL_COMPAT_MODE: engine strategy (auto/com/openpyxl)
    """
    OUTPUT_DIR: str = "outputs"
    WORD_TEMPLATE_PATH: Optional[str] = ""
    COSTING_TEMPLATE_PATH: Optional[str] = ""
    EXTERNAL_WORKBOOK_PATH: Optional[str] = ""
    EXCEL_COMPAT_MODE: Literal["auto", "com", "openpyxl", "off"] = "auto"

    @model_validator(mode="after")
    def _trim_strings(self) -> "Settings":
        def _t(s: Optional[str]) -> Optional[str]:
            return s.strip() if isinstance(s, str) else s

        self.OUTPUT_DIR = _t(self.OUTPUT_DIR) or "outputs"
        self.WORD_TEMPLATE_PATH = _t(self.WORD_TEMPLATE_PATH)
        self.COSTING_TEMPLATE_PATH = _t(self.COSTING_TEMPLATE_PATH)
        self.EXTERNAL_WORKBOOK_PATH = _t(self.EXTERNAL_WORKBOOK_PATH)
        self.EXCEL_COMPAT_MODE = (self.EXCEL_COMPAT_MODE or "auto").strip()  # type: ignore
        return self


# ---------------------------------------------------------------------
# Pricing Inputs
# ---------------------------------------------------------------------
class PricingInputs(BaseModel):
    """
    Canonical inputs for pricing.
    Backward-compatible with older payloads that used:
      - margin (0–1) instead of margin_pct (0–95)
    Both fields are accepted; they stay synchronized.
    """
    # Commercial
    margin: float = Field(0.24, ge=0.0, le=1.0, description="Legacy: 0..1 fraction")
    margin_pct: float = Field(24.0, ge=0.0, le=95.0, description="Preferred: percent (0..95)")
    base_price: float = Field(414320.82, ge=0.0)

    # Spare parts
    spare_parts_qty: int = Field(1, ge=0)
    spare_blades_qty: int = Field(20, ge=0)
    spare_pads_qty: int = Field(30, ge=0)

    # Enumerated option selections (MUST align with rules/options)
    guarding: Literal["Standard", "Tall", "Tall w/ Netting"] = "Standard"
    feeding: Literal["No", "Front USL", "Side USL", "Side Badger"] = "No"
    transformer: Literal["None", "Canada", "Step Up"] = "None"
    training: Literal["English", "English & Spanish"] = "English"

    # --- Validators ---
    @field_validator("spare_blades_qty", "spare_pads_qty")
    @classmethod
    def _val_spare_step(cls, v: int) -> int:
        # Enforce multiples of 10 (or 0)
        if v == 0:
            return v
        if v % 10 != 0:
            raise ValueError("Spare quantities must be 0 or a multiple of 10.")
        return v

    @model_validator(mode="after")
    def _sync_margin_fields(self) -> "PricingInputs":
        """
        Keep margin (0..1) and margin_pct (0..95) synchronized.
        - If either looks user-specified (different from the default pairing), prefer that source.
        - Otherwise, ensure internal consistency.
        """
        # If margin_pct provided independently, use it as source of truth
        # Detect "provided" loosely by checking mismatch vs computed
        computed_pct = round(self.margin * 100.0, 6)
        if round(self.margin_pct, 6) != computed_pct:
            # Someone set margin_pct directly → derive margin
            self.margin = round(self.margin_pct / 100.0, 6)

        # Clamp safety (should already be enforced by Field ranges)
        self.margin = min(max(self.margin, 0.0), 0.95)
        self.margin_pct = min(max(self.margin_pct, 0.0), 95.0)
        # Re-sync to ensure exact consistency
        self.margin_pct = round(self.margin * 100.0, 6)
        return self


# ---------------------------------------------------------------------
# Pricing / Generation Results
# ---------------------------------------------------------------------
class Computation(BaseModel):
    options_breakdown: Dict[str, float]
    options_qty: Dict[str, int]
    options_price_total: float
    margin: float
    base_price: float
    total_price: float


class GenerateResponse(BaseModel):
    ok: bool
    outputs: Dict[str, str]


# ---------------------------------------------------------------------
# Backward-compatibility alias
#   Older code imports/uses `Inputs`; keep it working by aliasing it to
#   the new canonical model.
# ---------------------------------------------------------------------
Inputs = PricingInputs
