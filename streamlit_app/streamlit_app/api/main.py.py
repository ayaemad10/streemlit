"""
main.py
-------
Application entry point for the Spectrum Anomaly Detection API.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Fix: Add correct paths to import database modules ──────────────
# Get the project root directory (where src/ is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "database"))

# ── Internal imports ───────────────────────────────────────────────
from src.api.routes import router
from src.api.websocket import ws_router
from src.api.middleware import LoggingMiddleware

logger = logging.getLogger("spectrum.main")

# ── Configuration from environment ────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", str(PROJECT_ROOT / "src" / "ai_model" / "saved_models" / "best_model.keras"))
MODEL_VERSION = os.getenv("MODEL_VER", "v1.0")
_RAW_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _RAW_ORIGINS.split(",")]


# =====================================================================
# LIFESPAN
# =====================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads model at startup, unloads at shutdown."""
    logger.info("=" * 60)
    logger.info("Spectrum API starting up …")
    logger.info("Model path    : %s", MODEL_PATH)
    logger.info("Model version : %s", MODEL_VERSION)
    logger.info("CORS origins  : %s", ALLOWED_ORIGINS)
    logger.info("Project root  : %s", PROJECT_ROOT)
    logger.info("=" * 60)

    # Try to load model (optional - API works without it for testing)
    try:
        import tensorflow as tf
        from tensorflow.keras.models import load_model

        logger.info("TensorFlow version : %s", tf.__version__)

        if os.path.exists(MODEL_PATH):
            logger.info("Loading model …")
            model = load_model(MODEL_PATH)
            logger.info("Model loaded — input shape: %s | output shape: %s",
                       model.input_shape, model.output_shape)

            # Warm-up inference
            import numpy as np
            dummy = np.zeros((1, model.input_shape[-1]), dtype=np.float32)
            model.predict(dummy, verbose=0)
            logger.info("Warm-up inference complete.")
            app.state.model = model
        else:
            logger.warning(f"Model not found at {MODEL_PATH}. API will run in demo mode.")
            app.state.model = None

        app.state.model_version = MODEL_VERSION

    except ImportError:
        logger.warning("TensorFlow not installed. API running without ML model.")
        app.state.model = None
    except Exception as exc:
        logger.error(f"Failed to load model: {exc}")
        app.state.model = None

    logger.info("Spectrum API ready.")
    yield

    logger.info("Spectrum API shutting down …")
    app.state.model = None
    logger.info("Model unloaded. Goodbye.")


# =====================================================================
# APP INSTANCE
# =====================================================================

app = FastAPI(
    title="Spectrum Anomaly Detection API",
    description=(
        "Real-time RF signal classification using a deep learning model. "
        "Detects Normal, Jamming, and Drone signals."
    ),
    version=MODEL_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =====================================================================
# MIDDLEWARE
# =====================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)


# =====================================================================
# ROUTERS
# =====================================================================

app.include_router(router, prefix="/api/v1", tags=["API v1"])
app.include_router(ws_router)


# =====================================================================
# ROOT
# =====================================================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Spectrum Anomaly Detection API is running.",
        "docs": "/docs",
        "redoc": "/redoc",
        "ws": "ws://localhost:8000/ws/alerts",
    }


# =====================================================================
# DEVELOPMENT ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )