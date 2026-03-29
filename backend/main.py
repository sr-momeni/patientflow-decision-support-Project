"""Compatibility module.

The canonical FastAPI app now lives in backend.server.
This file is kept only so old uvicorn targets like backend.main:app continue to work.
"""

try:
    from backend.server import app
except ImportError:  # pragma: no cover
    from server import app

__all__ = ["app"]
