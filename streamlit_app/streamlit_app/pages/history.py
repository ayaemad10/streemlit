"""
pages/history.py
----------------
Prediction History — paginated, searchable, filterable log of all
signals processed by the system.
"""

import streamlit as st
import pandas as pd
from utils.api import get_predictions, clear_caches
from utils.style_loader import section_header, badge


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">🗂️ PREDICTION HISTORY</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    # ── Controls row ──────────────────────────────────────────────
    section_header("FILTERS", "SEARCH")
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        label_filter = st.selectbox("Label Filter", ["All", "Normal", "Jamming", "Drone"])
    with c2:
        limit = st.selectbox("Records per page", [50, 100, 200, 500], index=1)
    with c3:
        conf_min = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.05)
    with c4:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    # ── Pagination ────────────────────────────────────────────────
    if "history_page" not in st.session_state:
        st.session_state.history_page = 0

    offset = st.session_state.history_page * limit

    with st.spinner("Loading signal history…"):
        lf = label_filter if label_filter != "All" else None
        signals = get_predictions(label=lf, limit=limit, offset=offset)

    if not signals:
        st.info("No signals found. Try adjusting filters or run predictions first.")
        return

    df = pd.DataFrame(signals)

    # Ensure columns
    for col in ["id", "label", "confidence", "frequency", "snr",
                "source", "inference_time_ms", "model_version", "timestamp"]:
        if col not in df.columns:
            df[col] = None

    # Apply confidence filter
    if "confidence" in df.columns:
        df = df[df["confidence"].fillna(0) >= conf_min]

    # ── Summary strip ─────────────────────────────────────────────
    section_header("SUMMARY", "STATS")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("📶 Showing", len(df))
    with s2:
        avg_conf = df["confidence"].mean() if "confidence" in df.columns else 0
        st.metric("🎯 Avg Confidence", f"{avg_conf:.1%}")
    with s3:
        avg_inf = df["inference_time_ms"].mean() if "inference_time_ms" in df.columns else 0
        st.metric("⚡ Avg Inference", f"{avg_inf:.0f} ms" if avg_inf else "—")
    with s4:
        top_label = df["label"].mode()[0] if "label" in df.columns and len(df) else "—"
        st.metric("🏆 Top Label", top_label)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Visual cards for first 6 ──────────────────────────────────
    section_header("RECENT SIGNALS", "LIVE FEED")

    cols = st.columns(3)
    for i, (_, row) in enumerate(df.head(6).iterrows()):
        label      = str(row.get("label", "Unknown"))
        confidence = float(row.get("confidence") or 0)
        sig_id     = row.get("id", "—")
        source     = row.get("source", "—")
        freq       = row.get("frequency")
        ts         = str(row.get("timestamp", ""))[:16]
        inf_ms     = row.get("inference_time_ms", "—")

        kind = "critical" if label == "Jamming" else ("warning" if label == "Drone" else "safe")
        icon = "🚨" if label == "Jamming" else ("🚁" if label == "Drone" else "✅")
        border_color = {
            "critical": "var(--critical-red)",
            "warning":  "var(--warning-yellow)",
            "safe":     "var(--safe-green)",
        }[kind]
        conf_pct = f"{confidence:.1%}"
        freq_str = f"{freq:.1f} MHz" if freq is not None else "—"

        with cols[i % 3]:
            st.markdown(f"""
            <div style="border:1px solid {border_color}40;border-radius:var(--radius-lg);
                        background:var(--bg-secondary);padding:16px;margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;
                            margin-bottom:10px;">
                    <span style="font-size:20px;">{icon}</span>
                    <span style="font-family:var(--font-mono);font-size:11px;
                                color:var(--text-tertiary);">#{sig_id}</span>
                </div>
                <div style="font-family:var(--font-display);font-size:18px;font-weight:700;
                            letter-spacing:0.10em;text-transform:uppercase;
                            color:{border_color};margin-bottom:8px;">{label}</div>
                <div style="background:var(--bg-tertiary);border-radius:var(--radius-pill);
                            height:4px;margin-bottom:10px;overflow:hidden;">
                    <div style="width:{confidence*100:.1f}%;height:100%;
                                background:{border_color};"></div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;
                            font-family:var(--font-mono);color:var(--text-tertiary);">
                    <span>🎯 {conf_pct}</span>
                    <span>📡 {freq_str}</span>
                    <span>🔧 {source}</span>
                    <span>⚡ {inf_ms} ms</span>
                </div>
                <div style="font-family:var(--font-mono);font-size:10px;
                            color:var(--text-disabled);margin-top:8px;">🕐 {ts}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Full table ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("FULL TABLE", "ALL RECORDS")

    display_cols = [c for c in
        ["id", "label", "confidence", "frequency", "snr",
         "source", "inference_time_ms", "model_version", "timestamp"]
        if c in df.columns]

    df_display = df[display_cols].copy()
    if "confidence" in df_display.columns:
        df_display["confidence"] = df_display["confidence"].apply(
            lambda x: f"{x:.1%}" if pd.notna(x) else "—"
        )

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ── Pagination controls ───────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    pag1, pag2, pag3 = st.columns([1, 2, 1])
    with pag1:
        if st.button("⬅️ Prev Page", disabled=st.session_state.history_page == 0,
                     use_container_width=True):
            st.session_state.history_page -= 1
            st.rerun()
    with pag2:
        st.markdown(
            f"<div style='text-align:center;font-family:var(--font-mono);font-size:12px;"
            f"color:var(--text-tertiary);padding-top:8px;'>"
            f"Page {st.session_state.history_page + 1} · offset {offset}</div>",
            unsafe_allow_html=True,
        )
    with pag3:
        if st.button("Next Page ➡️", disabled=len(signals) < limit,
                     use_container_width=True):
            st.session_state.history_page += 1
            st.rerun()

    # ── Download ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Page as CSV",
        data=csv,
        file_name=f"predictions_page_{st.session_state.history_page + 1}.csv",
        mime="text/csv",
        use_container_width=True,
    )
