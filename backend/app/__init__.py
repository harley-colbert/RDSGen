from __future__ import annotations
from pathlib import Path
from flask import Flask, send_from_directory
from .routes import api_bp  # <— from package, not from .routes.api

def create_app() -> Flask:
    # Serve static assets from the dedicated /frontend folder
    root = Path(__file__).resolve().parents[1]  # backend/
    frontend_dir = root.parent / "frontend"
    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="/static"  # we'll serve /static via /static, and index separately
    )

    # API
    app.register_blueprint(api_bp)

    # Index route
    @app.get("/")
    def index():
        # Serve the SPA entry
        return send_from_directory(frontend_dir, "index.html")

    return app


