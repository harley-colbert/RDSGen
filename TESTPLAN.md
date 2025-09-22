# Test Plan

## Scope & Goals
- Exercise core domain models (`app.domain.models`, `app.domain.rules`).
- Validate services that generate files (`app.services.costing_gen`, `app.services.word_gen`) via stubs to avoid Excel/Word dependencies.
- Cover REST API blueprints registered under `/api` (settings, validation, pricing, generate, outputs, options, browse, health).
- Ensure integration flow from inputs validation through pricing and document generation is testable via Flask's test client using patched dependencies.
- Frontend ESM utilities in `frontend/js` need unit coverage for state management and formatting logic.
- Target coverage: ≥85% for `app.domain` & `app.services`, ≥70% overall including routes.

## Unit Tests

### `app.domain.models`
- `Settings` normalization/validation (trim whitespace, default fallback for empty strings).
- `PricingInputs` margin synchronization (margin vs margin_pct), enumerated value enforcement, spare quantity validator edge cases.

### `app.domain.rules`
- `validate` rejecting invalid spare quantities, accepting valid inputs.
- `compute_from_price_list` totals for different option selections, coverage of each branch.
- (If legacy `compute` is expected, add regression verifying behavior or capture `AttributeError`).

### `app.services.costing_gen`
- `generate` populates workbook with correct rows when template missing (use stub `openpyxl` workbook implementation writing to in-memory structure / temporary file).
- Handling of option quantities and totals, ensuring new rows appended instead of overwritten.

### `app.services.word_gen`
- When template path blank, fallback to python-docx path is used (stub `docx.Document`).
- With template path, ensure stubbed `DocxTemplate.render` receives context with expected keys/values.

### `app.services.pricing_engine`
- Focus on helper functions not requiring COM:
  - `_is_remote` classification.
  - Possibly stub `_open_excel`/`_open_workbook` to avoid COM and test `get_price_list_for_margin` orchestrates correctly by injecting fake Excel objects.
  - Because COM not available on Linux CI, heavy COM-dependent tests replaced by verifying error handling/logging using monkeypatch.

### Frontend Modules
- `frontend/js/state.mjs`: ensure setters merge state correctly (pure functions, testable via Vitest).
- `frontend/js/api.mjs`: test error handling when fetch returns non-2xx (mock fetch via happy-dom/globalThis).
- `frontend/js/ui/inputs.mjs`: isolate formatting helpers (`fmtMoney`, `fmtMs`, `fmtSec`, `selectHTML`, `timingsHTML`, `pricingTableHTML`) by exporting them for testing (if not exported, refactor via tests using `await import()` and destructuring). Validate currency formatting, table HTML structure, debounce behavior using fake timers.

## API Tests (Flask)
For each endpoint under `/api` use Flask `test_client` with fixtures providing stub `SettingsManager`, `CostingGenerator`, `WordGenerator`, and `ExcelPricingEngine` to avoid external dependencies.

- `GET /api/health`: returns `{ok: True}` and timestamp string.
- `GET /api/settings`: returns sanitized default settings from stub manager.
- `POST /api/settings`: accepts valid payload, rejects invalid paths (simulate validation errors via stub).
- `GET /api/options`, `GET /api/options/<category>`, `POST /api/options/labels`: verify canonical option payloads and 404 path.
- `POST /api/validate`: success path, schema error path (missing fields), rules error path (invalid spare quantity).
- `POST /api/price`: happy path returns pricing stub, 400 for Excel compat off, 404 workbook missing (simulate via stub), 500 when engine raises.
- `POST /api/price/refresh`: success after refreshing cache (stub), error when path missing or not enabled.
- `POST /api/generate`: with stubbed services ensures outputs referencing `/outputs/...` and failure when Excel shim raises.
- `GET /api/outputs/<subpath>`: uses tmp output directory fixture and ensures Flask sends file (use `open` to create file and assert response data/headers).
- `GET /api/browse`: patch ProcessPoolExecutor to return canned path; error path when worker raises.

## Integration Tests
- Use Flask app fixture (with stub dependencies) to simulate full flow:
  1. `POST /api/settings` to configure output paths.
  2. `POST /api/validate` with valid payload.
  3. `POST /api/price` to fetch pricing response.
  4. `POST /api/generate` to create outputs; assert stub services captured calls and files created in tmp dir.
- Validate the interplay between domain validation, pricing, and output generation. Ensure stubs record invocation order.

## Frontend Integration
- With Vitest + happy-dom, simulate DOM for `renderInputs`/`renderSettings`/`renderOutput` using mocked fetch responses. Ensure event listeners trigger API calls and update DOM (use fake timers for debounced pricing refresh).

## End-to-End Smoke (Optional)
- Because app relies on native Excel/Word/COM on Windows, full E2E with Playwright is unstable in CI; skip E2E tests and document rationale. Provide placeholder Playwright config disabled by default.

## Tooling & Coverage
- Python: `pytest --maxfail=1 --disable-warnings -q --cov=app --cov-report=term-missing`.
- JS: `pnpm vitest run --coverage` (or `npx vitest` if pnpm unavailable).
- Aggregate coverage reports; enforce thresholds via config (pytest `--cov-fail-under=70`, Vitest coverage thresholds for functions/lines ~70%).

## Fixtures & Mocks
- Provide `tests/conftest.py` with:
  - `app` fixture building Flask app via `create_app` while monkeypatching `settings_mgr`, `CostingGenerator`, `WordGenerator`, `ExcelPricingEngine`.
  - `client` fixture returning Flask `test_client`.
  - `fake_settings` fixture returning minimal valid `Settings` with tmp directories.
  - Utility fixture to populate stub modules (`docxtpl`, `docx`, `openpyxl`, `pythoncom`, `pywintypes`, `win32com.client`).
- HTTP mocking: prefer `responses` to stub `requests` if needed (not used currently but available for future tests).

