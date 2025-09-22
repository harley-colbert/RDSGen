# Import the shared blueprint and *register* routes by importing each module.
from .blueprint import api_bp

# Route modules (import order does not matter as long as it happens)
from . import health       # noqa: F401
from . import settings     # noqa: F401
from . import options      # noqa: F401
from . import validation   # noqa: F401
from . import pricing      # noqa: F401
from . import generate     # noqa: F401
from . import outputs      # noqa: F401
from . import browse       # noqa: F401
from . import bootstrap    # noqa: F401

__all__ = ["api_bp"]
