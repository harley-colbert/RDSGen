# backend/app/config.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
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
    """Filesystem-backed settings storage with validation helpers."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        """Initialise the manager.

        Parameters
        ----------
        storage_path:
            Optional override for where the JSON settings document lives.
            Defaults to ``<repo-root>/settings.json`` to match the desktop
            launcher the team currently uses.
        """

        backend_dir = Path(__file__).resolve().parents[1]
        default_path = backend_dir.parent / "settings.json"
        self._path = Path(storage_path) if storage_path is not None else default_path
        self._cache: Settings | None = None
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def load(self, *, refresh: bool = False) -> Settings:
        """Load settings from disk (or cached copy).

        ``refresh`` forces a re-read which is useful for tests that mutate
        the file directly.
        """

        if self._cache is not None and not refresh:
            return self._cache

        data: Dict[str, object]
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text("utf-8"))
            except Exception as exc:  # pragma: no cover - defensive logging
                log.warning("Failed to read settings from %s: %s", self.path, exc)
                data = {}
        else:
            data = {}

        compat = data.get("EXCEL_COMPAT_MODE")
        if isinstance(compat, bool):
            data["EXCEL_COMPAT_MODE"] = "auto" if compat else "off"

        settings = Settings(**data)
        self._cache = settings
        return settings

    def save(self, settings: Settings) -> Settings:
        """Persist *settings* to disk after validation/sanitisation."""

        settings = self.sanitize(settings)
        ok, errors = self.validate_paths(settings)
        if not ok:
            raise ValueError(f"Invalid settings: {errors}")

        serialised = settings.model_dump()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(serialised, indent=2), encoding="utf-8")
            self._cache = settings
        log.debug("Settings saved to %s", self.path)
        return settings

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
        """Apply additional normalisation/safety checks before save."""
        # The ``Settings`` model already trims strings, but we clone via
        # ``model_dump``/``model_validate`` to ensure we persist a clean copy
        # that reflects any new defaults added in the future.
        return Settings.model_validate(s.model_dump())
