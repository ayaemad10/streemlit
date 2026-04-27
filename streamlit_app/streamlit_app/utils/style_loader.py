"""
utils/style_loader.py
---------------------
Loads all SpectrumGuard CSS files into Streamlit via st.markdown.
Call load_styles() at the top of every page.
"""

import os
import streamlit as st

# Path to the assets/css directory relative to this file
_CSS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "css")

# Load order matters — theme vars must come first
_CSS_FILES = [
    "theme.css",
    "typography.css",
    "animations.css",
    "components.css",
    "responsive.css",
    "style.css",
]

# Extra inline CSS to patch Streamlit's injected elements
_PATCH_CSS = """
<style>
/* ── Streamlit iframe / root patches ── */
#root > div:first-child { background: transparent !important; }
.stApp { background-color: var(--bg-deepest) !important; }
[data-testid="stSidebar"] { background-color: var(--bg-secondary) !important; border-right: 1px solid var(--border-subtle) !important; }
[data-testid="stHeader"] { background: var(--bg-secondary) !important; border-bottom: 1px solid var(--border-subtle) !important; }
.stMarkdown p { color: var(--text-primary); }
div[data-testid="metric-container"] { background: var(--bg-secondary) !important; border: 1px solid var(--border-subtle) !important; border-radius: var(--radius-lg) !important; padding: 16px !important; }
[data-testid="stMetricValue"] { color: var(--accent-cyan) !important; font-family: var(--font-mono) !important; }
[data-testid="stMetricLabel"] { color: var(--text-tertiary) !important; font-size: 11px !important; letter-spacing: 0.10em !important; text-transform: uppercase !important; }
.stDataFrame { background: var(--bg-secondary) !important; border: 1px solid var(--border-subtle) !important; border-radius: var(--radius-lg) !important; }
.stSelectbox > div > div { background: var(--bg-tertiary) !important; border: 1px solid var(--border-default) !important; color: var(--text-primary) !important; }
.stTextInput > div > div > input { background: var(--bg-tertiary) !important; border: 1px solid var(--border-default) !important; color: var(--text-primary) !important; }
.stTextArea > div > div > textarea { background: var(--bg-tertiary) !important; border: 1px solid var(--border-default) !important; color: var(--text-primary) !important; font-family: var(--font-mono) !important; }
.stButton > button { background: var(--accent-cyan) !important; color: var(--bg-deepest) !important; font-weight: 700 !important; border: none !important; border-radius: var(--radius-md) !important; letter-spacing: 0.06em !important; }
.stButton > button:hover { background: transparent !important; color: var(--accent-cyan) !important; border: 1px solid var(--accent-cyan) !important; box-shadow: var(--glow-live) !important; }
hr { border-top: 1px solid var(--border-subtle) !important; }
.stAlert { border-radius: var(--radius-md) !important; }
[data-testid="stSidebarNav"] { display: none; }
</style>
"""


@st.cache_data(show_spinner=False)
def _read_css(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_styles():
    """Inject all SpectrumGuard CSS into the Streamlit page."""
    combined = ""
    for filename in _CSS_FILES:
        filepath = os.path.join(_CSS_DIR, filename)
        if os.path.exists(filepath):
            combined += _read_css(filepath) + "\n"

    st.markdown(f"<style>{combined}</style>", unsafe_allow_html=True)
    st.markdown(_PATCH_CSS, unsafe_allow_html=True)


def card(content_html: str, extra_class: str = "") -> str:
    """Return an HTML card string for use with st.markdown."""
    return f'<div class="status-card {extra_class}">{content_html}</div>'


def badge(label: str, kind: str = "info") -> str:
    """Return a threat badge HTML string. kind: critical | warning | safe | info"""
    cls_map = {
        "critical": "threat-badge-critical",
        "warning":  "threat-badge-warning",
        "safe":     "threat-badge-safe",
        "info":     "threat-badge-info",
        "drone":    "threat-badge-warning",
        "jamming":  "threat-badge-critical",
        "normal":   "threat-badge-safe",
    }
    cls = cls_map.get(kind.lower(), "threat-badge-info")
    return f'<span class="threat-badge {cls}">{label}</span>'


def section_header(title: str, tag: str = "") -> None:
    """Render a styled section header with optional tag."""
    tag_html = f'<span class="section-header__tag">{tag}</span>' if tag else ""
    st.markdown(f"""
    <div class="section-header">
        <h2 class="h2" style="margin:0;font-size:18px;">{title}</h2>
        {tag_html}
        <div class="section-header__line"></div>
    </div>
    """, unsafe_allow_html=True)
