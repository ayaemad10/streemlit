"""
pages/analytics.py
------------------
Analytics — charts for signal distribution, confidence trends,
alert timelines, and per-label breakdowns.
"""

import streamlit as st
import pandas as pd
import numpy as np
from utils.api import get_statistics, get_predictions, get_alerts, clear_caches
from utils.style_loader import section_header


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">📊 ANALYTICS</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    col_r, _ = st.columns([1, 8])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    with st.spinner("Loading analytics data…"):
        stats   = get_statistics()
        signals = get_predictions(limit=500)
        alerts  = get_alerts()

    label_counts = stats.get("label_counts", {})
    total        = stats.get("total_signals", 0)

    # ── KPI ───────────────────────────────────────────────────────
    section_header("KEY METRICS", "OVERVIEW")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📶 Signals", f"{total:,}")
    with k2:
        st.metric("🚨 Alerts", f"{stats.get('alert_count', 0):,}")
    with k3:
        jamming = label_counts.get("Jamming", 0)
        jrate   = f"{jamming/total*100:.1f}%" if total else "0%"
        st.metric("⚡ Jamming Rate", jrate, delta_color="inverse",
                  delta="🔴 High" if jamming/max(total, 1) > 0.2 else "✅ Low")
    with k4:
        st.metric("🎯 Threshold", f"{stats.get('alert_threshold', 0.75):.0%}")

    st.markdown("<br>", unsafe_allow_html=True)

    if not signals:
        st.info("No signal data available. Run predictions to populate charts.")
        return

    df = pd.DataFrame(signals)

    # Ensure columns exist
    for col in ["label", "confidence", "timestamp", "frequency", "snr", "source"]:
        if col not in df.columns:
            df[col] = None

    # ── Row 1: Distribution + Confidence ─────────────────────────
    section_header("SIGNAL DISTRIBUTION & CONFIDENCE", "CHARTS")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Signal Label Distribution**")
        dist_df = pd.DataFrame(
            {"Count": label_counts},
        ).sort_values("Count", ascending=False)
        if not dist_df.empty:
            st.bar_chart(dist_df, use_container_width=True, height=280)

    with c2:
        st.markdown("**Confidence Distribution by Label**")
        conf_df = df.groupby("label")["confidence"].mean().reset_index()
        conf_df.columns = ["Label", "Avg Confidence"]
        conf_df = conf_df.set_index("Label")
        if not conf_df.empty:
            st.bar_chart(conf_df, use_container_width=True, height=280)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Time series ────────────────────────────────────────
    section_header("CONFIDENCE OVER TIME", "TREND")

    if df["timestamp"].notna().any():
        try:
            df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df_sorted = df.dropna(subset=["ts"]).sort_values("ts")

            if not df_sorted.empty:
                pivot = df_sorted.pivot_table(
                    index="ts", columns="label", values="confidence",
                    aggfunc="mean",
                ).fillna(method="ffill").fillna(0)

                st.line_chart(pivot, use_container_width=True, height=280)
            else:
                st.info("Timestamp data unavailable for trend chart.")
        except Exception:
            # Fallback: rolling confidence
            conf_series = df["confidence"].reset_index(drop=True)
            st.line_chart(conf_series, use_container_width=True, height=280)
    else:
        st.info("No timestamp data for time-series chart.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Source breakdown + SNR/Frequency ───────────────────
    col3, col4 = st.columns(2)

    with col3:
        section_header("SIGNALS BY SOURCE", "BREAKDOWN")
        if df["source"].notna().any():
            src_counts = df["source"].value_counts()
            st.bar_chart(src_counts, use_container_width=True, height=240)
        else:
            st.info("No source data.")

    with col4:
        section_header("SNR DISTRIBUTION", "SIGNAL QUALITY")
        if df["snr"].notna().any():
            snr_df = df.dropna(subset=["snr"])[["label", "snr"]]
            snr_pivot = snr_df.groupby("label")["snr"].mean()
            st.bar_chart(snr_pivot, use_container_width=True, height=240)
        else:
            st.info("No SNR data available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 4: Alerts timeline ────────────────────────────────────
    if alerts:
        section_header("ALERTS TIMELINE", "HISTORY")
        alert_df = pd.DataFrame(alerts)
        if "timestamp" in alert_df.columns:
            try:
                alert_df["ts"] = pd.to_datetime(alert_df["timestamp"], errors="coerce")
                alert_df = alert_df.dropna(subset=["ts"])
                alert_df["date"] = alert_df["ts"].dt.date
                daily = alert_df.groupby("date").size().rename("alerts")
                st.area_chart(daily, use_container_width=True, height=200)
            except Exception:
                pass

    # ── Frequency heatmap proxy ───────────────────────────────────
    if df["frequency"].notna().any():
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("FREQUENCY ANALYSIS", "SPECTRUM")
        freq_df = df.dropna(subset=["frequency"])
        freq_bins = freq_df.groupby("label")["frequency"].mean().rename("Avg MHz")
        st.bar_chart(freq_bins, use_container_width=True, height=200)

    # ── Raw stats table ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 Raw Statistics"):
        summary = df.groupby("label").agg(
            count=("label", "count"),
            avg_confidence=("confidence", "mean"),
            min_confidence=("confidence", "min"),
            max_confidence=("confidence", "max"),
        ).round(4)
        st.dataframe(summary, use_container_width=True)
