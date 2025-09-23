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

    @field_validator("EXCEL_COMPAT_MODE", mode="before")
    @classmethod
    def _normalize_mode(cls, value: Optional[str]) -> str:
        if value is None:
            return "auto"
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if not cleaned:
                return "auto"
            if cleaned in {"auto", "com", "openpyxl", "off"}:
                return cleaned
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def _trim_strings(self) -> "Settings":
        def _t(s: Optional[str]) -> Optional[str]:
            return s.strip() if isinstance(s, str) else s

        self.OUTPUT_DIR = _t(self.OUTPUT_DIR) or "outputs"
        self.WORD_TEMPLATE_PATH = _t(self.WORD_TEMPLATE_PATH)
        self.COSTING_TEMPLATE_PATH = _t(self.COSTING_TEMPLATE_PATH)
        self.EXTERNAL_WORKBOOK_PATH = _t(self.EXTERNAL_WORKBOOK_PATH)
        self.EXCEL_COMPAT_MODE = self.EXCEL_COMPAT_MODE or "auto"
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

    @field_validator("spare_blades_qty", "spare_pads_qty")
    @classmethod
    def _val_spare_step(cls, v: int) -> int:
        if v == 0:
            return v
        if v % 10 != 0:
            raise ValueError("Spare quantities must be 0 or a multiple of 10.")
        return v

    # Enumerated option selections (MUST align with rules/options)
    guarding: Literal["Standard", "Tall", "Tall w/ Netting"] = "Standard"
    feeding: Literal["No", "Front USL", "Side USL", "Side Badger"] = "No"
    transformer: Literal["None", "Canada", "Step Up"] = "None"
    training: Literal["English", "English & Spanish"] = "English"

    # --- Validators ---
    @model_validator(mode="after")
    def _sync_margin_fields(self) -> "PricingInputs":
        """
        Keep margin (0..1) and margin_pct (0..95) synchronized.
        """
        fields_set = getattr(self, "model_fields_set", set())
        margin_set = "margin" in fields_set
        margin_pct_set = "margin_pct" in fields_set

        if margin_set and not margin_pct_set:
            self.margin_pct = round(self.margin * 100.0, 6)
        elif margin_pct_set and not margin_set:
            self.margin = round(self.margin_pct / 100.0, 6)
        elif margin_set and margin_pct_set:
            # When both provided, favour explicit margin_pct for round-tripping.
            self.margin = round(self.margin_pct / 100.0, 6)
        else:
            # Defaults; ensure consistency
            self.margin_pct = round(self.margin * 100.0, 6)

        # Clamp to the declared ranges and keep rounding stable
        self.margin = round(min(max(self.margin, 0.0), 1.0), 6)
        self.margin_pct = round(min(max(self.margin_pct, 0.0), 95.0), 6)
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
