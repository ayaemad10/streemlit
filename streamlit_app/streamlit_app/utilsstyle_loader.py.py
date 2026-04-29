"""
utils/style_loader.py
---------------------
Loads all SpectrumGuard CSS files into the Streamlit app.
"""
import os
import streamlit as st

CSS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "css")

CSS_FILES = [
    "theme.css",
    "typography.css",
    "style.css",
    "components.css",
    "animations.css",
    "responsive.css",
]


def load_css() -> None:
    """Concatenate and inject all CSS files via st.markdown."""
    combined = []
    for fname in CSS_FILES:
        fpath = os.path.join(CSS_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                combined.append(f"/* === {fname} === */\n{f.read()}")
        else:
            pass

    if combined:
        css_block = "\n\n".join(combined)
        st.markdown(f"<style>{css_block}</style>", unsafe_allow_html=True)


def inject_extra_css(css: str) -> None:
    """Inject additional CSS directly (for per-page overrides)."""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)