"""
src/api/middleware.py
---------------------
Custom middleware for the Spectrum API.

Included:
  - LoggingMiddleware  → logs HTTP method, path, status code, and elapsed time
  - API key auth       → optional; activated when API_KEY env var is set

Usage in main.py:
    app.add_middleware(LoggingMiddleware)
"""

import os
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ------------------------------------------------------------------
# Logger — writes to stdout; can be redirected to a file via config
# ------------------------------------------------------------------
logger = logging.getLogger("spectrum.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ------------------------------------------------------------------
# Optional API key (set API_KEY env var to enable auth enforcement)
# ------------------------------------------------------------------
_API_KEY: str | None = os.getenv("API_KEY")          # None → auth disabled
_SKIP_AUTH_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/health"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that:
      1. Logs every incoming request (method + path).
      2. Measures and logs response time in milliseconds.
      3. Enforces API key authentication when API_KEY env var is set.

    API key must be sent in the 'X-API-Key' request header.
    Auth is skipped for documentation and health-check paths.
    """

    async def dispatch(self, request: Request, call_next):
        # ── 1. Optional API key check ──────────────────────────────
        if _API_KEY and request.url.path not in _SKIP_AUTH_PATHS:
            client_key = request.headers.get("X-API-Key", "")
            if client_key != _API_KEY:
                logger.warning(
                    "AUTH FAIL — %s %s | IP: %s",
                    request.method,
                    request.url.path,
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key."},
                )

        # ── 2. Log incoming request ────────────────────────────────
        start = time.perf_counter()
        logger.info("→ %s %s", request.method, request.url.path)

        # ── 3. Forward to next handler ─────────────────────────────
        try:
            response = await call_next(request)
        except Exception as exc:                       # safety net
            logger.exception("Unhandled exception during request: %s", exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )

        # ── 4. Log response ────────────────────────────────────────
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "← %s %s | %d | %.1f ms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        # Attach timing header so clients (and load balancers) can see it
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response
