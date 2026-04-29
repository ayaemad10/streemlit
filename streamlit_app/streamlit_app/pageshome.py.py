"""
pages/home.py
-------------
Dashboard Home — live KPI cards, label distribution, recent alerts.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.api import get_statistics, get_alerts, get_predictions

st.markdown("""
<div class="page-enter">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
    <span class="live-dot"></span>
    <h1 style="margin:0;font-size:26px;letter-spacing:0.18em;color:#edf2f7;">
      SPECTRUM MONITOR
    </h1>
  </div>
  <p style="color:#718096;font-size:13px;margin:0 0 24px 22px;">
    AI-Powered RF Anomaly Detection · ITC-Egypt 2026
  </p>
</div>
""", unsafe_allow_html=True)

with st.spinner("Loading dashboard data…"):
    stats = get_statistics()
    alerts = get_alerts()
    preds = get_predictions(limit=10)

if stats.get("total_signals", 0) == 0 and not alerts and preds.get("total", 0) == 0:
    st.warning("""
    ⚠️ **No data available from API**
    
    Please ensure the FastAPI backend is running:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload