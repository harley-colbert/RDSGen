# RDS Refactor (Flask backend + ESM frontend)

This is a **clean separation** of the original app into:
- **/backend** → Python + Flask API (`app/` package, blueprints in `app/routes`)
- **/frontend** → static HTML/CSS/JS (ES Modules: `.mjs`), served by Flask at `/static`

## Run (dev)
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate  # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5050/ in your browser.

## API Endpoints
- `GET /api/health`
- `GET /api/settings` / `POST /api/settings`
- `GET /api/options/<name>` — values for dropdowns (e.g., guarding/feeding/etc.)
- `POST /api/validate` — validate inputs only
- `POST /api/price` — preview pricing via external Excel (if enabled in settings)
- `POST /api/generate` — creates **costing.xlsx** + **quote.docx** and returns download URLs
- `GET /api/outputs/<path>` — download generated files

## Notes
- Flask serves **/frontend** as `/static`. The SPA entry (`/`) returns `frontend/index.html`.
- Frontend JS is ESM (`.mjs`) with clean imports. No bundler required.
- Backwards-compatible with the original endpoints expected by the UI.
- The Excel COM integration is isolated in `app/services/pricing_engine.py`.
- Paths & persistence are managed by `app/config.py` using a JSON settings file.


## Quick start (root-level launcher)
From the project root:
```bash
# Windows
run.bat

# macOS/Linux (for dev only; Excel COM features require Windows)
chmod +x run.sh && ./run.sh
```
This starts Flask at http://127.0.0.1:5050/ and serves the ESM frontend from `/frontend`.
