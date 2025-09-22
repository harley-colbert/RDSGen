from pathlib import Path
from flask import send_from_directory
from .blueprint import api_bp
from .deps import settings_mgr

@api_bp.get("/outputs/<path:subpath>")
def outputs(subpath: str):
    out_root = Path(settings_mgr.load().OUTPUT_DIR)
    return send_from_directory(out_root, subpath, as_attachment=True)
