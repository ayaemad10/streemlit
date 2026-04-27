"""
pages/home.py
-------------
Dashboard Home — KPI overview, live status, recent alerts preview.
"""

import streamlit as st
from utils.api import get_statistics, get_alerts, get_predictions, clear_caches
from utils.style_loader import section_header, badge


def render():
    # ── Header ────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <div>
            <h1 class="h1" style="margin:0;font-size:26px;">
                <span class="live-dot"></span>&nbsp; SPECTRUM MONITOR
            </h1>
            <p style="color:var(--text-tertiary);margin:4px 0 0;font-size:12px;
                       font-family:var(--font-mono);letter-spacing:0.08em;">
                AI-Powered RF Anomaly Detection · ITC-Egypt 2026
            </p>
        </div>
    </div>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    # ── Refresh ───────────────────────────────────────────────────
    col_r, _ = st.columns([1, 8])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    # ── Load data ─────────────────────────────────────────────────
    with st.spinner("Loading dashboard data…"):
        stats    = get_statistics()
        alerts   = get_alerts()
        signals  = get_predictions(limit=50)

    label_counts   = stats.get("label_counts", {})
    total_signals  = stats.get("total_signals", 0)
    alert_count    = stats.get("alert_count", 0)
    threshold      = stats.get("alert_threshold", 0.75)
    jamming_count  = label_counts.get("Jamming", 0)
    drone_count    = label_counts.get("Drone", 0)
    normal_count   = label_counts.get("Normal", 0)

    # ── KPI row ───────────────────────────────────────────────────
    section_header("LIVE STATISTICS", "KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("📶 Total Signals", f"{total_signals:,}", help="All signals processed")
    with k2:
        st.metric("🚨 Total Alerts", f"{alert_count:,}", delta=f"+{len(alerts[:5])} recent",
                  delta_color="inverse")
    with k3:
        st.metric("📡 Normal", f"{normal_count:,}",
                  delta=f"{(normal_count/total_signals*100):.1f}%" if total_signals else "0%")
    with k4:
        st.metric("⚡ Jamming", f"{jamming_count:,}", delta_color="inverse",
                  delta=f"{'🔴 THREAT' if jamming_count > 0 else '✅ Clear'}")
    with k5:
        st.metric("🚁 Drone", f"{drone_count:,}", delta_color="inverse",
                  delta=f"{'🔴 THREAT' if drone_count > 0 else '✅ Clear'}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Threat distribution card ──────────────────────────────────
    section_header("THREAT DISTRIBUTION", "ANALYTICS")
    left, right = st.columns([3, 2])

    with left:
        if total_signals > 0:
            chart_data = {
                "Label": ["Normal", "Jamming", "Drone"],
                "Count": [normal_count, jamming_count, drone_count],
            }
            import pandas as pd
            df = pd.DataFrame(chart_data).set_index("Label")
            st.bar_chart(df, use_container_width=True, height=220,
                         color=["#00e5ff"])
        else:
            st.info("No signal data yet. Run a prediction to populate charts.")

    with right:
        st.markdown("""
        <div class="status-card" style="height:100%;">
            <div style="font-family:var(--font-mono);font-size:11px;
                        color:var(--text-tertiary);letter-spacing:0.12em;
                        text-transform:uppercase;margin-bottom:16px;">
                System Status
            </div>
        """, unsafe_allow_html=True)

        status_items = [
            ("🟢 API Server",      "Online",    "safe"),
            ("🟢 ML Model",        "Loaded",    "safe"),
            ("🟢 WebSocket",       "Active",    "safe"),
            ("🔵 Alert Threshold", f"{threshold:.0%}", "info"),
        ]
        for icon_label, value, kind in status_items:
            b = badge(value, kind)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;
                        align-items:center;padding:8px 0;
                        border-bottom:1px solid var(--border-subtle);">
                <span style="font-size:13px;color:var(--text-secondary);">
                    {icon_label}
                </span>
                {b}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent alerts table ───────────────────────────────────────
    section_header("RECENT ALERTS", "LIVE")

    if alerts:
        import pandas as pd
        recent = alerts[-10:][::-1]
        rows = []
        for a in recent:
            sig_id = a.get("signal_id", "—")
            rows.append({
                "🆔 Alert ID":   a.get("id", "—"),
                "Signal ID":     sig_id,
                "📍 Location":   a.get("location", "Unknown"),
                "📬 Type":       a.get("alert_type", "—").upper(),
                "📊 Status":     a.get("status", "—").upper(),
                "🕐 Timestamp":  str(a.get("timestamp", "—"))[:19],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:32px;color:var(--text-tertiary);
                    font-family:var(--font-mono);font-size:13px;">
            🟢 No alerts on record — system nominal.
        </div>
        """, unsafe_allow_html=True)

    # ── Recent predictions preview ────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("RECENT PREDICTIONS", "LIVE FEED")

    if signals:
        import pandas as pd
        rows = []
        for s in signals[:8]:
            lbl = s.get("label", "Unknown")
            rows.append({
                "ID":           s.get("id", "—"),
                "Label":        lbl,
                "Confidence":   f"{s.get('confidence', 0):.1%}",
                "Frequency":    f"{s.get('frequency', '—')} MHz" if s.get("frequency") else "—",
                "SNR":          f"{s.get('snr', '—')} dB" if s.get("snr") else "—",
                "Source":       s.get("source", "—"),
                "Timestamp":    str(s.get("timestamp", "—"))[:19],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No predictions yet. Use **Real-Time Predict** to run inference.")
