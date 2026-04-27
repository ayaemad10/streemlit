"""
pages/alerts_log.py
-------------------
Alerts Log — searchable, filterable table of all system alerts.
"""

import streamlit as st
import pandas as pd
from utils.api import get_alerts, clear_caches
from utils.style_loader import section_header, badge


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">🚨 ALERTS LOG</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--critical-red),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    col_r, _ = st.columns([1, 8])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    with st.spinner("Loading alerts…"):
        alerts = get_alerts()

    if not alerts:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:var(--text-tertiary);
                    font-family:var(--font-mono);">
            🟢 No alerts found — system is nominal.
        </div>
        """, unsafe_allow_html=True)
        return

    df = pd.DataFrame(alerts)

    # ── Normalise columns ──────────────────────────────────────────
    for col in ["id", "signal_id", "alert_type", "status", "location", "timestamp"]:
        if col not in df.columns:
            df[col] = "—"

    # ── KPI strip ─────────────────────────────────────────────────
    section_header("SUMMARY", "STATS")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("🚨 Total Alerts", len(df))
    with k2:
        sent = len(df[df["status"].str.lower() == "sent"]) if "status" in df.columns else 0
        st.metric("📬 Sent", sent)
    with k3:
        unique_locs = df["location"].nunique() if "location" in df.columns else 0
        st.metric("📍 Unique Locations", unique_locs)
    with k4:
        if "alert_type" in df.columns:
            top_type = df["alert_type"].value_counts().idxmax()
            st.metric("📣 Top Channel", top_type.upper())
        else:
            st.metric("📣 Top Channel", "—")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────
    section_header("FILTERS", "SEARCH & FILTER")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        type_options = ["All"] + sorted(df["alert_type"].dropna().unique().tolist())
        type_filter  = st.selectbox("Alert Type", type_options)
    with fc2:
        stat_options = ["All"] + sorted(df["status"].dropna().unique().tolist())
        stat_filter  = st.selectbox("Status", stat_options)
    with fc3:
        search = st.text_input("🔍 Search location", placeholder="Cairo, Sector 7…")

    # ── Apply filters ─────────────────────────────────────────────
    filtered = df.copy()
    if type_filter != "All":
        filtered = filtered[filtered["alert_type"] == type_filter]
    if stat_filter != "All":
        filtered = filtered[filtered["status"] == stat_filter]
    if search:
        filtered = filtered[filtered["location"].str.contains(search, case=False, na=False)]

    st.markdown("<br>", unsafe_allow_html=True)
    section_header(f"ALERT RECORDS ({len(filtered)} results)", "TABLE")

    # ── Styled alert cards (first 5) ──────────────────────────────
    for _, row in filtered.head(5).iterrows():
        status = str(row.get("status", "—")).lower()
        atype  = str(row.get("alert_type", "—")).upper()
        loc    = str(row.get("location", "—"))
        ts     = str(row.get("timestamp", "—"))[:19]
        aid    = row.get("id", "—")
        sid    = row.get("signal_id", "—")

        status_color = (
            "var(--safe-green)"    if status == "sent"    else
            "var(--warning-yellow)" if status == "pending" else
            "var(--critical-red)"
        )
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:12px 16px;margin-bottom:8px;
                    background:var(--bg-secondary);
                    border:1px solid var(--border-subtle);
                    border-left:3px solid {status_color};
                    border-radius:var(--radius-md);">
            <div style="display:flex;gap:24px;align-items:center;">
                <div>
                    <div style="font-size:10px;color:var(--text-tertiary);
                                letter-spacing:0.1em;text-transform:uppercase;
                                font-family:var(--font-mono);">Alert ID</div>
                    <div style="font-family:var(--font-mono);color:var(--accent-cyan);
                                font-weight:700;font-size:16px;">#{aid}</div>
                </div>
                <div>
                    <div style="font-size:10px;color:var(--text-tertiary);
                                letter-spacing:0.1em;text-transform:uppercase;
                                font-family:var(--font-mono);">Signal</div>
                    <div style="font-family:var(--font-mono);color:var(--text-secondary);">
                        #{sid}
                    </div>
                </div>
                <div>
                    <div style="font-size:10px;color:var(--text-tertiary);
                                letter-spacing:0.1em;text-transform:uppercase;
                                font-family:var(--font-mono);">Location</div>
                    <div style="color:var(--text-primary);font-size:13px;">📍 {loc}</div>
                </div>
                <div>
                    <div style="font-size:10px;color:var(--text-tertiary);
                                letter-spacing:0.1em;text-transform:uppercase;
                                font-family:var(--font-mono);">Channel</div>
                    <div style="color:var(--text-primary);">📬 {atype}</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="color:{status_color};font-weight:700;font-size:12px;
                            text-transform:uppercase;letter-spacing:0.08em;">
                    ● {status.upper()}
                </div>
                <div style="font-family:var(--font-mono);font-size:11px;
                            color:var(--text-tertiary);margin-top:4px;">
                    🕐 {ts}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if len(filtered) > 5:
        st.caption(f"Showing top 5 of {len(filtered)} alerts — see full table below.")

    # ── Full table ────────────────────────────────────────────────
    with st.expander("📋 Full Alert Table", expanded=len(filtered) <= 20):
        display_cols = [c for c in ["id", "signal_id", "location", "alert_type", "status", "timestamp"]
                        if c in filtered.columns]
        st.dataframe(
            filtered[display_cols].sort_values("id", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # ── Download ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Alerts CSV",
        data=csv,
        file_name="spectrum_alerts.csv",
        mime="text/csv",
        use_container_width=True,
    )
