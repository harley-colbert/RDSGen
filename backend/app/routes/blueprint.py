from flask import Blueprint

# One blueprint, shared by all route modules
api_bp = Blueprint("api", __name__, url_prefix="/api")
