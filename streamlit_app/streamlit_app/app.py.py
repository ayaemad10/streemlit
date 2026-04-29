"""
app.py
------
SpectrumGuard — AI-Powered Spectrum Anomaly Detection Dashboard
ITC-Egypt 2026 | Entry point & navigation shell.
"""
import sys
import os

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from utils.style_loader import load_css
from utils.api import health_check, set_api_base

st.set_page_config(
    page_title="SpectrumGuard — NOC Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = "http://localhost:8000"
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "chat_session_id" not in st.session_state:
    st.session_state["chat_session_id"] = "operator-session-001"

PAGES = {
    "🏠  Home": "pages/home.py",
    "📡  Real-Time Predict": "pages/realtime.py",
    "🗺️  Live Map": "pages/live_map.py",
    "🚨  Alerts Log": "pages/alerts_log.py",
    "📊  Analytics": "pages/analytics.py",
    "🕒  History": "pages/history.py",
    "📝  Reports": "pages/reports.py",
    "🤖  AI Agent Chat": "pages/agentchat.py",
    "⚙️  System Monitor": "pages/system_monitor.py",
}

with st.sidebar:
    st.markdown("""
    <div style="padding: 12px 0 20px 0; border-bottom: 1px solid #2a2f3a; margin-bottom: 16px;">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:22px;
                    font-weight:800; letter-spacing:0.18em; color:#00e5ff;
                    text-transform:uppercase; line-height:1.2;">
            📡 SpectrumGuard
        </div>
        <div style="font-size:10px; color:#718096; letter-spacing:0.14em;
                    text-transform:uppercase; margin-top:4px;">
            ITC-Egypt 2026 · NOC Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:10px;color:#718096;letter-spacing:0.18em;'
                'text-transform:uppercase;margin-bottom:8px;">Navigation</div>',
                unsafe_allow_html=True)

    selected_page = st.radio(
        label="nav",
        options=list(PAGES.keys()),
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<div style="font-size:10px;color:#718096;letter-spacing:0.14em;'
                'text-transform:uppercase;margin-bottom:6px;">API Endpoint</div>',
                unsafe_allow_html=True)

    new_url = st.text_input(
        "api_url",
        value=st.session_state["api_base_url"],
        label_visibility="collapsed",
        placeholder="http://localhost:8000",
    )
    if new_url != st.session_state["api_base_url"]:
        set_api_base(new_url)
        st.success("URL updated")

    health = health_check()
    status = health.get("status", "offline")
    if status == "ok":
        st.markdown('<div class="system-status-online" style="font-size:11px;font-weight:600;'
                    'letter-spacing:0.08em;margin-top:8px;">✅ API ONLINE</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="system-status-offline" style="font-size:11px;font-weight:600;'
                    f'letter-spacing:0.08em;margin-top:8px;">🔴 API OFFLINE - Start backend on port 8000</div>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#4a5568;text-align:center;">'
        'Team Leader: Goda Emad<br>'
        'v1.0 · RadioML 2018.01A<br>'
        'ITC-Egypt 2026'
        '</div>',
        unsafe_allow_html=True,
    )

page_file = PAGES[selected_page]
page_path = os.path.join(ROOT, page_file)

if os.path.exists(page_path):
    with open(page_path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, page_path, "exec"), {"__name__": "__main__"})
else:
    st.error(f"Page file not found: {page_path}")