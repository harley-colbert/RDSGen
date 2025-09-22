from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse
import os
import time
import logging

import pythoncom            # COM apartment
import pywintypes           # for pywintypes.com_error


@dataclass
class ExcelPriceList:
    base_price: float
    items: Dict[str, float]


class ExcelPricingEngine:
    SUMMARY = "Summary"
    MARGIN_CELL = "M4"

    # Row -> label (matches VBA mapping)
    PRICE_ROW_LABELS: Dict[int, str] = {
        32: "Guarding – Taller",
        33: "Guarding – Netting",
        18: "Infeed – Front USL",
        19: "Infeed – Side USL",
        20: "Infeed – Side Badger",
        38: "Spare Parts Package",
        39: "Spare Saw Blades",
        40: "Spare Foam Pads",
        45: "Training (English & Spanish)",
        46: "Transformer – Canada",
        47: "Transformer – Step Up",
    }

    # Input cells we toggle
    FLAG_CELLS = ["H18", "H19", "H20", "H32", "H33", "H38", "H39", "H40", "H45", "H46", "H47"]

    # Rows summed for the base cost
    BASE_COMPONENT_ROWS = list(range(4, 11)) + [14, 17, 24, 31]

    def __init__(self, workbook_path: str, visible: bool = False, logger: logging.Logger | None = None):
        # Keep SharePoint URLs as-is; normalize local paths for COM
        if self._is_remote(workbook_path):
            self.workbook_path = workbook_path
        else:
            self.workbook_path = os.path.normpath(str(Path(workbook_path)))
        self.visible = visible
        self.log = logger or logging.getLogger("pricing.engine")

    # ------------------------- helpers (COM / Excel) -------------------------

    @staticmethod
    def _is_remote(p: str) -> bool:
        try:
            u = urlparse(p)
            return u.scheme in ("http", "https")
        except Exception:
            return False

    def _open_excel(self):
        """Create a fresh Excel COM instance, timing + logging included."""
        pythoncom.CoInitialize()
        t0 = time.perf_counter()
        try:
            import win32com.client as win32
            xl = win32.DispatchEx("Excel.Application")
            xl.Visible = self.visible
            xl.DisplayAlerts = False
            try:
                ver = xl.Version
            except Exception:
                ver = "?"
            dt = (time.perf_counter() - t0) * 1000
            self.log.debug("excel_open ok ms=%.1f version=%s visible=%s", dt, ver, self.visible)
            return xl
        except Exception as e:
            # Balance COM if we failed
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            raise
        # (Do not uninitialize here; caller must call _close)

    def _open_workbook(self, xl, *, read_only: bool):
        """Open the workbook with explicit read-only flag; logs timing."""
        t0 = time.perf_counter()
        wb = xl.Workbooks.Open(
            self.workbook_path,
            UpdateLinks=0,
            ReadOnly=bool(read_only),
            IgnoreReadOnlyRecommended=True,
            AddToMru=False,
            Local=True,
        )
        dt = (time.perf_counter() - t0) * 1000
        self.log.debug(
            "workbook_open ok ms=%.1f read_only=%s remote=%s path=%s",
            dt, read_only, self._is_remote(self.workbook_path), self.workbook_path
        )
        return wb

    def _open_rw_else_ro(self, xl):
        """Try RW; if COM blocks (locked/in-use), fall back to RO and log."""
        try:
            wb = self._open_workbook(xl, read_only=False)
            return wb, False
        except pywintypes.com_error as e:
            self.log.warning("workbook_open rw_failed com_error=%s; falling back to read_only", e)
            wb = self._open_workbook(xl, read_only=True)
            return wb, True
        except Exception as e:
            self.log.warning("workbook_open rw_failed err=%s; falling back to read_only", e)
            wb = self._open_workbook(xl, read_only=True)
            return wb, True

    @staticmethod
    def _close(xl, wb, save_changes: bool = False, logger: logging.Logger | None = None):
        t0 = time.perf_counter()
        try:
            if wb is not None:
                wb.Close(SaveChanges=bool(save_changes))
        except Exception:
            if logger:
                logger.debug("workbook_close ignored_error", exc_info=True)
        try:
            if xl is not None:
                xl.Quit()
        except Exception:
            if logger:
                logger.debug("excel_quit ignored_error", exc_info=True)
        try:
            pythoncom.CoUninitialize()
        except Exception:
            if logger:
                logger.debug("coinitialize_uninit ignored_error", exc_info=True)
        if logger:
            dt = (time.perf_counter() - t0) * 1000
            logger.debug("excel_close done ms=%.1f save=%s", dt, save_changes)

    def _force_calc(self, xl):
        t0 = time.perf_counter()
        try:
            xl.CalculateFullRebuild()
        except Exception:
            try:
                xl.CalculateFull()
            except Exception:
                xl.Calculate()
        dt = (time.perf_counter() - t0) * 1000
        self.log.debug("calc ok ms=%.1f", dt)

    # ------------------------- public: boot/read-only/edit pattern -------------------------

    def warm_cache_readonly(self) -> None:
        """Open RO to warm Excel/Office auth + links, force calc, close."""
        self.log.debug("warm_cache_ro start")
        xl, wb = None, None
        try:
            xl = self._open_excel()
            wb = self._open_workbook(xl, read_only=True)
            self._force_calc(xl)
        finally:
            self._close(xl, wb, save_changes=False, logger=self.log)
            self.log.debug("warm_cache_ro done")

    def update_margin_readwrite(self, margin_decimal: float, *, save: bool = False) -> None:
        """Open RW, update M4, calc, close (optional save)."""
        self.log.debug("update_margin_rw start margin=%.6f save=%s", float(margin_decimal), save)
        xl, wb = None, None
        try:
            xl = self._open_excel()
            wb = self._open_workbook(xl, read_only=False)
            ws = wb.Worksheets(self.SUMMARY)
            ws.Range(self.MARGIN_CELL).Value = float(margin_decimal)
            self._force_calc(xl)
        finally:
            self._close(xl, wb, save_changes=save, logger=self.log)
            self.log.debug("update_margin_rw done")

    def read_price_snapshot_readonly(self) -> ExcelPriceList:
        """Open RO and read current base + option rows (no edits)."""
        self.log.debug("read_snapshot_ro start")
        xl, wb = None, None
        try:
            xl = self._open_excel()
            wb = self._open_workbook(xl, read_only=True)
            ws = wb.Worksheets(self.SUMMARY)
            self._force_calc(xl)

            base_total = 0.0
            for r in self.BASE_COMPONENT_ROWS:
                v = ws.Range(f"J{r}").Value
                base_total += float(v or 0.0)

            items = {}
            for r, name in self.PRICE_ROW_LABELS.items():
                v = ws.Range(f"J{r}").Value
                items[name] = float(v or 0.0)

            return ExcelPriceList(base_price=round(base_total, 2),
                                  items={k: round(v, 2) for k, v in items.items()})
        finally:
            self._close(xl, wb, save_changes=False, logger=self.log)
            self.log.debug("read_snapshot_ro done")

    # ------------------------- existing APIs (kept + instrumented) -------------------------

    def get_price_list_for_margin(self, margin_decimal: float) -> ExcelPriceList:
        """
        Build a unit price list at a given margin: set M4 and set all flags/qty=1,
        read J-cells. Edits are in-memory (no save).
        """
        self.log.debug("price_list start margin=%.6f", float(margin_decimal))
        xl, wb = None, None
        try:
            t_total = time.perf_counter()
            xl = self._open_excel()
            wb, opened_ro = self._open_rw_else_ro(xl)
            ws = wb.Worksheets(self.SUMMARY)

            t_write = time.perf_counter()
            ws.Range(self.MARGIN_CELL).Value = float(margin_decimal)
            for addr in self.FLAG_CELLS:
                ws.Range(addr).Value = 1
            t_calc0 = time.perf_counter()
            self._force_calc(xl)
            t_read0 = time.perf_counter()

            base_total = 0.0
            for r in self.BASE_COMPONENT_ROWS:
                base_total += float(ws.Range(f"J{r}").Value or 0.0)

            items = {}
            for r, name in self.PRICE_ROW_LABELS.items():
                items[name] = float(ws.Range(f"J{r}").Value or 0.0)

            t_end = time.perf_counter()
            self.log.debug(
                "price_list done opened_ro=%s t_write_ms=%.1f t_calc_ms=%.1f t_read_ms=%.1f t_total_ms=%.1f",
                opened_ro,
                (t_calc0 - t_write) * 1000,
                (t_read0 - t_calc0) * 1000,
                (t_end - t_read0) * 1000,
                (t_end - t_total) * 1000,
            )

            return ExcelPriceList(
                base_price=round(base_total, 2),
                items={k: round(v, 2) for k, v in items.items()},
            )
        finally:
            self._close(xl, wb, save_changes=False, logger=self.log)

    def compute_live_prices(self, inputs: Any, return_sell: bool = True) -> Dict[str, Any]:
        """
        Write selections + margin into Summary, recalc, and return:
          - base cost (sum of J rows)
          - option costs from J18,J19,J20,J32,J33,J38,J39,J40,J45,J46,J47
        Converts to sell = cost / (1 - margin) when return_sell=True.
        Edits are in-memory (no save).
        """
        # tiny helper to read from dict or object
        def g(name: str, default=None):
            if isinstance(inputs, dict):
                return inputs.get(name, default)
            return getattr(inputs, name, default)

        self.log.debug("live_price start")
        xl, wb = None, None
        opened_ro = False
        try:
            t_total = time.perf_counter()
            xl = self._open_excel()
            wb, opened_ro = self._open_rw_else_ro(xl)
            ws = wb.Worksheets(self.SUMMARY)

            # 1) Margin
            m = float(g("margin", 0.0) or 0.0)

            t_write = time.perf_counter()
            ws.Range(self.MARGIN_CELL).Value = m

            # 2) Clear all flags/qtys first
            for addr in self.FLAG_CELLS:
                ws.Range(addr).Value = 0

            # 3) Quantities
            ws.Range("H38").Value = int(g("spare_parts_qty", 0) or 0)
            ws.Range("H39").Value = int(g("spare_blades_qty", 0) or 0)
            ws.Range("H40").Value = int(g("spare_pads_qty", 0) or 0)

            # 4) Guarding
            guarding = g("guarding", "Standard") or "Standard"
            if guarding == "Taller":
                ws.Range("H32").Value = 1
            elif guarding == "Netting":
                ws.Range("H33").Value = 1

            # 5) Feeding
            feeding = g("feeding", "No") or "No"
            if feeding == "Front USL":
                ws.Range("H18").Value = 1
            elif feeding == "Side USL":
                ws.Range("H19").Value = 1
            elif feeding == "Side Badger":
                ws.Range("H20").Value = 1

            # 6) Training
            training = g("training", "English") or "English"
            if training == "English & Spanish":
                ws.Range("H45").Value = 1

            # 7) Transformer
            transformer = g("transformer", "None") or "None"
            if transformer == "Canada":
                ws.Range("H46").Value = 1
            elif transformer == "Step Up":
                ws.Range("H47").Value = 1

            t_calc0 = time.perf_counter()
            self._force_calc(xl)

            # 9) Read base COST
            t_read0 = time.perf_counter()
            base_cost = 0.0
            for r in self.BASE_COMPONENT_ROWS:
                base_cost += float(ws.Range(f"J{r}").Value or 0.0)

            # Option COSTS
            def J(row: int) -> float:
                return float(ws.Range(f"J{row}").Value or 0.0)

            costs = {
                32: J(32), 33: J(33), 18: J(18), 19: J(19), 20: J(20),
                38: J(38), 39: J(39), 40: J(40), 45: J(45), 46: J(46), 47: J(47),
            }

            def to_sell(c: float) -> float:
                return c / (1.0 - m) if return_sell and m < 0.9999 else c

            base_sell = to_sell(base_cost)
            sell = {row: to_sell(c) for row, c in costs.items()}

            items: Dict[str, Dict[str, Any]] = {
                "Spare Parts Package": {
                    "label": "Spare Parts Package",
                    "qty": int(g("spare_parts_qty", 0) or 0),
                    "cost": costs[38], "sell": sell[38],
                },
                "Spare Saw Blades": {
                    "label": "Spare Saw Blades",
                    "qty": int(g("spare_blades_qty", 0) or 0),
                    "cost": costs[39], "sell": sell[39],
                },
                "Spare Foam Pads": {
                    "label": "Spare Foam Pads",
                    "qty": int(g("spare_pads_qty", 0) or 0),
                    "cost": costs[40], "sell": sell[40],
                },
                "Guarding – Taller": {
                    "label": "Guarding – Taller",
                    "qty": 1 if guarding == "Taller" else 0,
                    "cost": costs[32], "sell": sell[32],
                },
                "Guarding – Netting": {
                    "label": "Guarding – Netting",
                    "qty": 1 if guarding == "Netting" else 0,
                    "cost": costs[33], "sell": sell[33],
                },
                "Infeed – Front USL": {
                    "label": "Infeed – Front USL",
                    "qty": 1 if feeding == "Front USL" else 0,
                    "cost": costs[18], "sell": sell[18],
                },
                "Infeed – Side USL": {
                    "label": "Infeed – Side USL",
                    "qty": 1 if feeding == "Side USL" else 0,
                    "cost": costs[19], "sell": sell[19],
                },
                "Infeed – Side Badger": {
                    "label": "Infeed – Side Badger",
                    "qty": 1 if feeding == "Side Badger" else 0,
                    "cost": costs[20], "sell": sell[20],
                },
                "Training (English & Spanish)": {
                    "label": "Training (English & Spanish)",
                    "qty": 1 if training == "English & Spanish" else 0,
                    "cost": costs[45], "sell": sell[45],
                },
                "Transformer – Canada": {
                    "label": "Transformer – Canada",
                    "qty": 1 if transformer == "Canada" else 0,
                    "cost": costs[46], "sell": sell[46],
                },
                "Transformer – Step Up": {
                    "label": "Transformer – Step Up",
                    "qty": 1 if transformer == "Step Up" else 0,
                    "cost": costs[47], "sell": sell[47],
                },
            }

            t_end = time.perf_counter()
            self.log.debug(
                "live_price done opened_ro=%s t_write_ms=%.1f t_calc_ms=%.1f t_read_ms=%.1f t_total_ms=%.1f "
                "base_cost=%.2f base_sell=%.2f",
                opened_ro,
                (t_calc0 - t_write) * 1000,
                (t_read0 - t_calc0) * 1000,
                (t_end - t_read0) * 1000,
                (t_end - t_total) * 1000,
                base_cost, base_sell
            )

            return {
                "ok": True,
                "margin": m,
                "base": {"cost": round(base_cost, 2), "sell": round(base_sell, 2)},
                "items": {k: {"label": v["label"], "qty": v["qty"],
                              "cost": round(v["cost"], 2), "sell": round(v["sell"], 2)}
                          for k, v in items.items()},
                "meta": {  # extra debug info; UI ignores it
                    "opened_readonly": opened_ro,
                    "t_write_ms": round((t_calc0 - t_write) * 1000, 1),
                    "t_calc_ms": round((t_read0 - t_calc0) * 1000, 1),
                    "t_read_ms": round((t_end - t_read0) * 1000, 1),
                    "t_total_ms": round((t_end - t_total) * 1000, 1),
                },
            }
        finally:
            self._close(xl, wb, save_changes=False, logger=self.log)


