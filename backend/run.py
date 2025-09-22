from app import create_app

if __name__ == "__main__":
    app = create_app()
    # For local dev; in production, use gunicorn/waitress, etc.
    app.run(host="127.0.0.1", port=5050, debug=True)
