"""
src/api/__init__.py
-------------------
Initializes the API module and exposes its core components.

Importing this package makes routes, middleware, and websocket
handlers available for registration in main.py.
"""

from .routes import router
from .websocket import ws_router
from .middleware import LoggingMiddleware

__all__ = ["router", "ws_router", "LoggingMiddleware"]
