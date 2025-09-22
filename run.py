# Root launcher for both backend API and ESM frontend.
# The Flask app is configured to serve /frontend as static assets.
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "backend"))  # allow 'from app import create_app'

from app import create_app  # type: ignore

if __name__ == "__main__":
    app = create_app()
    # You can change host/port here if needed
    app.run(host="127.0.0.1", port=5050, debug=True)
