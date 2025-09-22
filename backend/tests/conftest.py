from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict

import pytest

from app.config import SettingsManager
from app.domain.models import Settings


# ---------------------------------------------------------------------------
# Third-party library shims
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _stub_external_modules() -> None:
    """Provide light-weight stand-ins for heavy Windows/Office dependencies."""

    if "docxtpl" not in sys.modules:
        docxtpl = types.ModuleType("docxtpl")

        class DocxTemplate:  # type: ignore[too-many-ancestors]
            def __init__(self, template_path: str) -> None:
                self.template_path = template_path
                self.rendered: Dict[str, Any] | None = None

            def render(self, context: Dict[str, Any], environment=None) -> None:  # noqa: ANN001
                self.rendered = dict(context)

            def save(self, path: str | Path) -> None:
                Path(path).write_text(json.dumps(self.rendered or {}), encoding="utf-8")

        docxtpl.DocxTemplate = DocxTemplate  # type: ignore[attr-defined]
        sys.modules["docxtpl"] = docxtpl

    if "docx" not in sys.modules:
        docx = types.ModuleType("docx")

        class _ParagraphDocument:
            def __init__(self) -> None:
                self.lines: list[str] = []

            def add_heading(self, text: str, level: int = 1) -> None:  # noqa: ARG002
                self.lines.append(f"# {text}")

            def add_paragraph(self, text: str) -> None:
                self.lines.append(text)

            def save(self, path: str | Path) -> None:
                Path(path).write_text("\n".join(self.lines), encoding="utf-8")

        docx.Document = _ParagraphDocument  # type: ignore[attr-defined]
        sys.modules["docx"] = docx

    if "openpyxl" not in sys.modules:
        openpyxl = types.ModuleType("openpyxl")

        class _Cell:
            def __init__(self) -> None:
                self.value: Any = None

        class _Worksheet:
            def __init__(self) -> None:
                self.title = "Sheet"
                self._cells: Dict[tuple[int, int], _Cell] = {}
                self.max_row = 1

            def cell(self, row: int, column: int) -> _Cell:
                key = (row, column)
                cell = self._cells.get(key)
                if cell is None:
                    cell = _Cell()
                    self._cells[key] = cell
                if row > self.max_row:
                    self.max_row = row
                return cell

            def append(self, values: list[Any]) -> None:
                row = self.max_row + 1
                for idx, value in enumerate(values, start=1):
                    self.cell(row, idx).value = value
                self.max_row = row

        class Workbook:  # noqa: D401 - stub
            def __init__(self) -> None:
                self.active = _Worksheet()

            def save(self, path: str | Path) -> None:
                payload = {
                    "title": self.active.title,
                    "max_row": self.active.max_row,
                    "data": {f"{r},{c}": cell.value for (r, c), cell in self.active._cells.items()},
                }
                Path(path).write_text(json.dumps(payload), encoding="utf-8")

        def load_workbook(path: str | Path) -> Workbook:  # noqa: D401 - stub
            wb = Workbook()
            wb.active.title = Path(path).stem
            return wb

        openpyxl.Workbook = Workbook  # type: ignore[attr-defined]
        openpyxl.load_workbook = load_workbook  # type: ignore[attr-defined]
        sys.modules["openpyxl"] = openpyxl

    # Minimal COM shims to satisfy pricing engine imports
    if "pythoncom" not in sys.modules:
        pythoncom = types.ModuleType("pythoncom")
        pythoncom.CoInitialize = lambda *a, **k: None  # type: ignore[attr-defined]
        pythoncom.CoUninitialize = lambda *a, **k: None  # type: ignore[attr-defined]
        sys.modules["pythoncom"] = pythoncom

    if "pywintypes" not in sys.modules:
        pywintypes = types.ModuleType("pywintypes")

        class com_error(Exception):
            ...

        pywintypes.com_error = com_error  # type: ignore[attr-defined]
        sys.modules["pywintypes"] = pywintypes

    if "win32com" not in sys.modules:
        win32com = types.ModuleType("win32com")
        client = types.ModuleType("win32com.client")

        class _FakeWorkbook:
            def __init__(self) -> None:
                self.Worksheets = lambda name: types.SimpleNamespace(Range=lambda cell: types.SimpleNamespace(Value=0))

            def Close(self, *a, **k) -> None:  # noqa: ANN001
                return None

        class _FakeExcel:
            Version = "0"
            Visible = False

            def __init__(self) -> None:
                self.DisplayAlerts = False

            def Workbooks(self):  # pragma: no cover - not used in tests
                return types.SimpleNamespace(Open=lambda *a, **k: _FakeWorkbook())

            def Quit(self) -> None:
                return None

        client.DispatchEx = lambda name: _FakeExcel()  # type: ignore[attr-defined]
        win32com.client = client  # type: ignore[attr-defined]
        sys.modules["win32com"] = win32com
        sys.modules["win32com.client"] = client


# ---------------------------------------------------------------------------
# Flask app fixtures
# ---------------------------------------------------------------------------


class StubRecorder:
    def __init__(self) -> None:
        self.costing_calls: list[tuple[Path, Any, Any]] = []
        self.word_calls: list[tuple[Path, Any, Any]] = []
        self.pricing_calls: list[Any] = []


@pytest.fixture()
def fake_settings(tmp_path: Path) -> Settings:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    costing_tpl = tmp_path / "costing_template.xlsx"
    costing_tpl.write_text("template", encoding="utf-8")
    word_tpl = tmp_path / "quote_template.docx"
    word_tpl.write_text("template", encoding="utf-8")
    workbook = tmp_path / "price_grid.xlsx"
    workbook.write_text("grid", encoding="utf-8")
    return Settings(
        OUTPUT_DIR=str(outputs),
        WORD_TEMPLATE_PATH=str(word_tpl),
        COSTING_TEMPLATE_PATH=str(costing_tpl),
        EXTERNAL_WORKBOOK_PATH=str(workbook),
        EXCEL_COMPAT_MODE="auto",
    )


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch, fake_settings: Settings, tmp_path: Path) -> Any:
    from app import create_app
    from app.routes import deps, generate, outputs, pricing

    recorder = StubRecorder()

    storage = tmp_path / "settings.json"
    mgr = SettingsManager(storage_path=storage)
    mgr.save(fake_settings)

    class FakePriceList:
        def __init__(self, base_price: float = 100.0, items: Dict[str, float] | None = None) -> None:
            self.base_price = base_price
            self.items = items or {"Option A": 123.45}

    class FakeExcelEngine:
        price_list = FakePriceList()
        error: Exception | None = None

        def __init__(self, path: str, visible: bool = False) -> None:  # noqa: FBT001, FBT002
            self.path = path
            self.visible = visible

        def get_price_list_for_margin(self, margin: float) -> FakePriceList:
            recorder.pricing_calls.append((self.path, margin))
            if FakeExcelEngine.error is not None:
                raise FakeExcelEngine.error
            return FakeExcelEngine.price_list

    class FakeCostingGenerator:
        def __init__(self, template_path: str) -> None:
            self.template_path = template_path

        def generate(self, out_path: Path, inputs, comp) -> None:  # noqa: ANN001
            recorder.costing_calls.append((out_path, inputs, comp))
            out_path.write_text("COSTING", encoding="utf-8")

    class FakeWordGenerator:
        def __init__(self, template_path: str) -> None:
            self.template_path = template_path

        def generate(self, out_path: Path, inputs, comp) -> None:  # noqa: ANN001
            recorder.word_calls.append((out_path, inputs, comp))
            out_path.write_text("WORD", encoding="utf-8")

    monkeypatch.setattr(deps, "settings_mgr", mgr, raising=False)
    monkeypatch.setattr(pricing, "settings_mgr", mgr, raising=False)
    monkeypatch.setattr(generate, "settings_mgr", mgr, raising=False)
    monkeypatch.setattr(outputs, "settings_mgr", mgr, raising=False)

    monkeypatch.setattr(pricing, "ExcelPricingEngine", FakeExcelEngine)
    monkeypatch.setattr(generate, "CostingGenerator", FakeCostingGenerator)
    monkeypatch.setattr(generate, "WordGenerator", FakeWordGenerator)

    pricing._price_cache.update({  # reset cache between tests
        "key": None,
        "ts": 0.0,
        "base": None,
        "items": None,
    })

    FakeExcelEngine.error = None
    FakeExcelEngine.price_list = FakePriceList()

    flask_app = create_app()
    flask_app.config["TEST_RECORDER"] = recorder
    return flask_app


@pytest.fixture()
def client(app) -> Any:  # noqa: ANN001
    return app.test_client()


@pytest.fixture()
def recorder(app) -> StubRecorder:
    return app.config["TEST_RECORDER"]
