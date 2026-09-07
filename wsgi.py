"""Production WSGI entrypoint.

Vercel loads this module in production. Refuse to start when SECRET_KEY is
missing so the Flask application's development fallback can never be used
by the production deployment.
"""

import os


if not os.environ.get("SECRET_KEY"):
    raise RuntimeError(
        "SECRET_KEY environment variable is required for production deployment."
    )

from app import app  # noqa: E402


__all__ = ["app"]
