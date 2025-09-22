from __future__ import annotations

from pathlib import Path

from app.routes import pricing


def test_outputs_serves_existing_file(client):
    settings = pricing.settings_mgr.load()
    out_root = Path(settings.OUTPUT_DIR)
    subdir = out_root / "2024"
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / "quote.docx"
    target.write_text("hello", encoding="utf-8")

    resp = client.get(f"/api/outputs/{target.relative_to(out_root)}")
    assert resp.status_code == 200
    assert resp.data == b"hello"
    assert resp.headers["Content-Disposition"].startswith("attachment;")
