"""
utils/api.py
------------
All HTTP calls to the SpectrumGuard FastAPI backend.
Every function is cache-aware and handles errors gracefully.
"""
import json
import logging
from typing import Any, Optional

import requests
import streamlit as st

logger = logging.getLogger("spectrum.api")

API_BASE: str = st.session_state.get(
    "api_base_url",
    "http://localhost:8000",
)

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})

TIMEOUT = 15


def _get(endpoint: str, params: Optional[dict] = None) -> Optional[Any]:
    """HTTP GET with graceful error handling."""
    try:
        resp = _session.get(f"{API_BASE}{endpoint}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"⚠️ Cannot reach API at {API_BASE}. Is the backend running?")
        return None
    except requests.exceptions.Timeout:
        st.error("⚠️ API request timed out. Please try again.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"⚠️ API error {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.exception("Unexpected API error: %s", e)
        st.error(f"⚠️ Unexpected error: {e}")
        return None


def _post(endpoint: str, data: Optional[dict] = None, files=None, form_data=None) -> Optional[Any]:
    """HTTP POST with graceful error handling."""
    try:
        if files is not None:
            resp = requests.post(
                f"{API_BASE}{endpoint}",
                files=files,
                data=form_data or {},
                timeout=TIMEOUT,
            )
        else:
            resp = _session.post(
                f"{API_BASE}{endpoint}",
                json=data,
                timeout=TIMEOUT,
            )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"⚠️ Cannot reach API at {API_BASE}. Is the backend running?")
        return None
    except requests.exceptions.Timeout:
        st.error("⚠️ API request timed out. Please try again.")
        return None
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:300]
        st.error(f"⚠️ API error {e.response.status_code}: {body}")
        return None
    except Exception as e:
        logger.exception("Unexpected POST error: %s", e)
        st.error(f"⚠️ Unexpected error: {e}")
        return None


@st.cache_data(ttl=10, show_spinner=False)
def get_alerts() -> list[dict]:
    """GET /alerts — return all alerts."""
    result = _get("/alerts")
    if result is None:
        return []
    return result if isinstance(result, list) else []


@st.cache_data(ttl=10, show_spinner=False)
def get_predictions(
    label: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """GET /predictions — paginated signal history."""
    params: dict = {"limit": limit, "offset": offset}
    if label:
        params["label"] = label
    result = _get("/predictions", params=params)
    if result is None:
        return {"total": 0, "page": 1, "limit": limit, "signals": []}
    return result


@st.cache_data(ttl=10, show_spinner=False)
def get_statistics() -> dict:
    """GET /statistics — aggregate counts and label distribution."""
    result = _get("/statistics")
    if result is None:
        return {
            "total_signals": 0,
            "label_counts": {},
            "alert_count": 0,
            "alert_threshold": 0.75,
            "report_count": 0,
        }
    return result


def predict(
    file_bytes: Optional[bytes] = None,
    filename: str = "spectrogram.png",
    iq_samples: Optional[list[float]] = None,
    frequency: Optional[float] = None,
    snr: Optional[float] = None,
    source: str = "SDR",
    alert_type: str = "email",
    location: str = "Unknown",
) -> Optional[dict]:
    """POST /predict — run inference on a spectrogram image or IQ samples."""
    form_data: dict = {
        "source": source,
        "alert_type": alert_type,
        "location": location,
    }
    if frequency is not None:
        form_data["frequency"] = str(frequency)
    if snr is not None:
        form_data["snr"] = str(snr)

    if file_bytes is not None:
        files = {"file": (filename, file_bytes, "image/png")}
        return _post("/predict", files=files, form_data=form_data)
    elif iq_samples is not None:
        form_data["iq_samples"] = json.dumps(iq_samples)
        return _post("/predict", files={}, form_data=form_data)
    else:
        st.error("Either file_bytes or iq_samples must be provided.")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_report(signal_id: int) -> Optional[dict]:
    """GET /reports/{signal_id} — per-signal AI report."""
    return _get(f"/reports/{signal_id}")


def send_chat(
    message: str,
    session_id: str = "default",
    history: Optional[list[dict]] = None,
) -> Optional[dict]:
    """POST /chat — send message to SpectrumAgent."""
    payload = {
        "message": message,
        "session_id": session_id,
        "history": history or [],
    }
    return _post("/chat", data=payload)


@st.cache_data(ttl=5, show_spinner=False)
def health_check() -> dict:
    """GET /health — liveness probe."""
    result = _get("/health")
    if result is None:
        return {"status": "offline"}
    return result


def set_api_base(url: str) -> None:
    """Update the API base URL at runtime."""
    global API_BASE
    API_BASE = url.rstrip("/")
    st.session_state["api_base_url"] = API_BASE
    get_alerts.clear()
    get_predictions.clear()
    get_statistics.clear()
    health_check.clear()


def clear_caches():
    """Clear all cached API functions."""
    get_alerts.clear()
    get_predictions.clear()
    get_statistics.clear()
    health_check.clear()