# backend/app/config.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse

from .domain.models import Settings

log = logging.getLogger("RDSGen.config")


def _is_url(p: str) -> bool:
    try:
        scheme = urlparse(p).scheme.lower()
        return scheme in ("http", "https")
    except Exception:
        return False


class SettingsManager:
    """
    Validates and (optionally) normalizes Settings objects before persistence.
    """

    @staticmethod
    def validate_paths(s: Settings) -> Tuple[bool, Dict[str, str]]:
        """
        Validate file/dir paths and URL allowance.

        Rules:
          - WORD_TEMPLATE_PATH / COSTING_TEMPLATE_PATH:
                If provided, MUST exist locally as files.
          - EXTERNAL_WORKBOOK_PATH:
                May be a local file (must exist) OR a valid http/https URL (SharePoint, etc).
          - OUTPUT_DIR:
                Must be creatable if it does not exist.
        """
        errors: Dict[str, str] = {}

        # Local templates must exist as files if provided
        for key in ("WORD_TEMPLATE_PATH", "COSTING_TEMPLATE_PATH"):
            p = getattr(s, key)
            if p:
                path = Path(p)
                if not path.exists():
                    errors[key] = f"Path does not exist: {p}"
                elif not path.is_file():
                    errors[key] = f"Path is not a file: {p}"

        # External workbook: allow local file OR URL
        p = s.EXTERNAL_WORKBOOK_PATH
        if p:
            if _is_url(p):
                # Optionally, enforce allowed hosts here if you want to restrict
                pass
            else:
                path = Path(p)
                if not path.exists():
                    errors["EXTERNAL_WORKBOOK_PATH"] = f"Not a valid URL and file does not exist: {p}"
                elif not path.is_file():
                    errors["EXTERNAL_WORKBOOK_PATH"] = f"Not a valid URL and path is not a file: {p}"

        # OUTPUT_DIR must be creatable
        out = Path(s.OUTPUT_DIR or "outputs")
        try:
            out.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors["OUTPUT_DIR"] = f"Cannot create OUTPUT_DIR '{out}': {e}"

        ok = len(errors) == 0
        if not ok:
            log.warning("Settings validation failed: %s", errors)
        else:
            log.debug("Settings validation OK. OUTPUT_DIR=%s", out.resolve())
        return ok, errors

    @staticmethod
    def sanitize(s: Settings) -> Settings:
        """
        Optional: apply additional normalization/safety checks before save.
        Currently a no-op besides trimming handled in the model.
        """
        return s
