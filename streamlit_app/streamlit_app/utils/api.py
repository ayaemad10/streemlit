"""
utils/api.py
------------
All API calls to the Spectrum Anomaly Detection backend.
Centralises base URL, error handling, and caching.
"""

import os
import time
import logging
import requests
import streamlit as st
from typing import Optional, Any

logger = logging.getLogger("spectrum.ui.api")

# ── Base URL — override with env var for production ────────────────
API_BASE = os.getenv("SPECTRUM_API_URL", "http://localhost:8000/api/v1")
WS_BASE  = os.getenv("SPECTRUM_WS_URL",  "ws://localhost:8000/ws/alerts")
TIMEOUT  = int(os.getenv("API_TIMEOUT", "10"))

# Optional API key
_API_KEY = os.getenv("API_KEY", "")
_HEADERS = {"X-API-Key": _API_KEY} if _API_KEY else {}


# ── Low-level helpers ─────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> dict | list | None:
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("🔴 **Cannot connect to API.** Is the backend running?")
        logger.error("Connection refused: %s", url)
    except requests.exceptions.Timeout:
        st.error(f"⏱️ **API timeout** ({TIMEOUT}s) — server too slow.")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ **API error {e.response.status_code}:** {e.response.text[:200]}")
    except Exception as e:
        st.error(f"❌ **Unexpected error:** {e}")
    return None


def _post(path: str, payload: dict) -> dict | None:
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=payload, headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("🔴 **Cannot connect to API.** Is the backend running?")
    except requests.exceptions.Timeout:
        st.error(f"⏱️ **API timeout** ({TIMEOUT}s).")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ **API error {e.response.status_code}:** {e.response.text[:200]}")
    except Exception as e:
        st.error(f"❌ **Unexpected error:** {e}")
    return None


# ── Public API functions ──────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def get_statistics() -> dict:
    """GET /statistics — aggregate signal counts and alert info."""
    data = _get("/statistics")
    if data is None:
        return {
            "total_signals": 0,
            "label_counts": {"Normal": 0, "Jamming": 0, "Drone": 0},
            "alert_count": 0,
            "alert_threshold": 0.75,
        }
    return data


@st.cache_data(ttl=15, show_spinner=False)
def get_predictions(
    label: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """GET /predictions — paginated signal history with optional label filter."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if label and label != "All":
        params["label"] = label
    data = _get("/predictions", params=params)
    if data is None:
        return []
    return data.get("signals", [])


@st.cache_data(ttl=15, show_spinner=False)
def get_alerts() -> list[dict]:
    """GET /alerts — all stored alerts with decrypted locations."""
    data = _get("/alerts")
    if data is None:
        return []
    return data if isinstance(data, list) else []


def predict(
    features: list[float],
    frequency: Optional[float] = None,
    snr: Optional[float] = None,
    source: str = "UI",
    alert_type: str = "email",
    location: str = "Unknown",
) -> dict | None:
    """POST /predict — run inference and return label + confidence."""
    payload = {
        "features": features,
        "source": source,
        "alert_type": alert_type,
        "location": location,
    }
    if frequency is not None:
        payload["frequency"] = frequency
    if snr is not None:
        payload["snr"] = snr
    return _post("/predict", payload)


@st.cache_data(ttl=60, show_spinner=False)
def get_report(signal_id: int) -> dict | None:
    """GET /reports/{id} — per-signal report (if endpoint exists)."""
    return _get(f"/reports/{signal_id}")


def send_chat(message: str, history: list[dict] | None = None) -> str:
    """POST /chat — AI agent chat endpoint."""
    payload = {"message": message, "history": history or []}
    result = _post("/chat", payload)
    if result is None:
        return "⚠️ Agent unavailable — could not reach /chat endpoint."
    return result.get("response", result.get("message", str(result)))


def health_check() -> dict:
    """GET /health — liveness probe, bypass cache."""
    url = f"{API_BASE}/health"
    try:
        t0 = time.perf_counter()
        r = requests.get(url, headers=_HEADERS, timeout=5)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        r.raise_for_status()
        return {"status": "online", "latency_ms": latency_ms, "data": r.json()}
    except Exception as e:
        return {"status": "offline", "latency_ms": -1, "error": str(e)}


def clear_caches():
    """Bust all st.cache_data entries (call from refresh buttons)."""
    get_statistics.clear()
    get_predictions.clear()
    get_alerts.clear()
    get_report.clear()
