"""
app.py
------
SpectrumGuard — AI-Powered Spectrum Anomaly Detection Dashboard
Entry point: sets page config, sidebar navigation, and routes to pages.
"""

import importlib
import sys
import os

import streamlit as st

# ── Make utils importable from any page ───────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from utils.style_loader import load_styles

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="SpectrumGuard — Anomaly Detection",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_styles()

# ── Page registry ─────────────────────────────────────────────────
PAGES = {
    "🏠  Home":             "pages.home",
    "📡  Real-Time Predict": "pages.realtime",
    "🗺️  Live Map":          "pages.live_map",
    "🚨  Alerts Log":        "pages.alerts_log",
    "📊  Analytics":         "pages.analytics",
    "🗂️  History":           "pages.history",
    "📄  Reports":           "pages.reports",
    "🤖  Agent Chat":        "pages.agent_chat",
    "🖥️  System Monitor":    "pages.system_monitor",
}

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 24px;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
            <span style="font-size:28px;">📡</span>
            <div>
                <div style="font-family:var(--font-display);font-size:18px;font-weight:800;
                            letter-spacing:0.14em;color:var(--accent-cyan);text-transform:uppercase;">
                    SpectrumGuard
                </div>
                <div style="font-size:10px;color:var(--text-tertiary);letter-spacing:0.12em;
                            text-transform:uppercase;font-family:var(--font-mono);">
                    AI Anomaly Detection
                </div>
            </div>
        </div>
        <div style="height:1px;background:var(--border-subtle);margin-top:16px;"></div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation buttons
    if "current_page" not in st.session_state:
        st.session_state.current_page = list(PAGES.keys())[0]

    for label in PAGES:
        is_active = st.session_state.current_page == label
        btn_style = (
            "background:var(--accent-cyan-glow);border-left:3px solid var(--accent-cyan);"
            if is_active
            else "border-left:3px solid transparent;"
        )
        if st.button(
            label,
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_page = label
            st.rerun()

    st.markdown("""
    <div style="position:absolute;bottom:20px;left:16px;right:16px;">
        <div style="height:1px;background:var(--border-subtle);margin-bottom:12px;"></div>
        <div style="font-size:10px;color:var(--text-disabled);letter-spacing:0.08em;
                    font-family:var(--font-mono);text-align:center;">
            ITC-EGYPT 2026 · v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Route to selected page ────────────────────────────────────────
module_path = PAGES[st.session_state.current_page]
module = importlib.import_module(module_path)
module.render()
