"""
pages/reports.py
----------------
Per-signal report viewer — lookup a signal ID and show full details,
or browse recent signals and their auto-generated summaries.
"""

import streamlit as st
import pandas as pd
from utils.api import get_report, get_predictions, clear_caches
from utils.style_loader import section_header, badge


def _render_report_card(report: dict) -> None:
    """Render a detailed signal report card."""
    label       = str(report.get("label", "Unknown"))
    confidence  = float(report.get("confidence") or 0)
    signal_id   = report.get("signal_id", report.get("id", "—"))
    frequency   = report.get("frequency")
    snr         = report.get("snr")
    source      = report.get("source", "—")
    inf_ms      = report.get("inference_time_ms", "—")
    model_ver   = report.get("model_version", "—")
    timestamp   = str(report.get("timestamp", ""))[:19]
    alert_id    = report.get("alert_id")
    alert_trig  = report.get("alert_triggered", alert_id is not None)
    location    = report.get("location", report.get("alert_location", "—"))

    kind = "critical" if label == "Jamming" else ("warning" if label == "Drone" else "safe")
    border_color = {
        "critical": "var(--critical-red)",
        "warning":  "var(--warning-yellow)",
        "safe":     "var(--safe-green)",
    }[kind]
    icon = "🚨" if label == "Jamming" else ("🚁" if label == "Drone" else "✅")

    badge_html = badge(label, kind)
    alert_html = (
        f'<span style="color:var(--critical-red);font-weight:600;">⚡ Alert #{alert_id} generated</span>'
        if alert_trig else
        '<span style="color:var(--safe-green);">✅ No alert triggered</span>'
    )

    freq_str = f"{frequency:.2f} MHz" if frequency is not None else "Not recorded"
    snr_str  = f"{snr:.2f} dB"        if snr is not None else "Not recorded"

    st.markdown(f"""
    <div style="border:1px solid {border_color}60;border-radius:var(--radius-lg);
                background:var(--bg-secondary);padding:28px;margin-bottom:20px;">

        <!-- Header -->
        <div style="display:flex;align-items:flex-start;justify-content:space-between;
                    margin-bottom:24px;padding-bottom:16px;
                    border-bottom:1px solid var(--border-subtle);">
            <div style="display:flex;align-items:center;gap:16px;">
                <span style="font-size:40px;">{icon}</span>
                <div>
                    <div style="font-family:var(--font-display);font-size:26px;
                                font-weight:800;letter-spacing:0.14em;
                                text-transform:uppercase;color:{border_color};">
                        {label}
                    </div>
                    <div style="margin-top:4px;">{badge_html}</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:var(--font-mono);font-size:11px;
                            color:var(--text-tertiary);letter-spacing:0.1em;">
                    SIGNAL REPORT
                </div>
                <div style="font-family:var(--font-mono);font-size:20px;
                            color:var(--accent-cyan);font-weight:700;">
                    #{signal_id}
                </div>
            </div>
        </div>

        <!-- Confidence bar -->
        <div style="margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-size:12px;color:var(--text-tertiary);
                             font-family:var(--font-mono);text-transform:uppercase;
                             letter-spacing:0.10em;">Confidence Score</span>
                <span style="font-family:var(--font-mono);font-size:16px;
                             font-weight:700;color:{border_color};">{confidence:.1%}</span>
            </div>
            <div style="background:var(--bg-tertiary);border-radius:var(--radius-pill);
                        height:10px;overflow:hidden;">
                <div style="width:{confidence*100:.1f}%;height:100%;background:{border_color};
                            border-radius:var(--radius-pill);box-shadow:0 0 10px {border_color};"></div>
            </div>
        </div>

        <!-- Metadata grid -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
            {"".join([
                f'''<div style="background:var(--bg-tertiary);border-radius:var(--radius-md);
                            padding:14px;text-align:center;">
                    <div style="font-size:10px;color:var(--text-tertiary);
                                letter-spacing:0.12em;text-transform:uppercase;
                                font-family:var(--font-mono);margin-bottom:6px;">{lbl}</div>
                    <div style="font-family:var(--font-mono);font-size:15px;
                                color:var(--accent-cyan);font-weight:600;">{val}</div>
                </div>'''
                for lbl, val in [
                    ("Frequency",  freq_str),
                    ("SNR",        snr_str),
                    ("Source",     source),
                    ("Inference",  f"{inf_ms} ms"),
                ]
            ])}
        </div>

        <!-- Alert + model info -->
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding-top:16px;border-top:1px solid var(--border-subtle);">
            <div>{alert_html}</div>
            <div style="text-align:right;">
                <div style="font-size:11px;color:var(--text-tertiary);
                            font-family:var(--font-mono);">
                    📍 {location} &nbsp;|&nbsp; 🤖 Model {model_ver}
                </div>
                <div style="font-size:11px;color:var(--text-disabled);
                            font-family:var(--font-mono);margin-top:4px;">
                    🕐 {timestamp}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">📄 SIGNAL REPORTS</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    col_r, _ = st.columns([1, 8])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    # ── Signal ID lookup ──────────────────────────────────────────
    section_header("REPORT LOOKUP", "BY ID")
    lcol, rcol = st.columns([2, 1])
    with lcol:
        signal_id_input = st.number_input(
            "Enter Signal ID to view report",
            min_value=1, step=1, value=1,
        )
    with rcol:
        st.markdown("<br>", unsafe_allow_html=True)
        lookup_btn = st.button("🔍 Load Report", use_container_width=True)

    if lookup_btn:
        with st.spinner(f"Fetching report for signal #{signal_id_input}…"):
            report = get_report(int(signal_id_input))

        if report:
            st.success(f"✅ Report loaded for signal #{signal_id_input}")
            _render_report_card(report)
            with st.expander("🔍 Raw JSON"):
                st.json(report)
        else:
            st.warning(
                f"⚠️ No report endpoint found for signal #{signal_id_input}. "
                "Showing from predictions history instead."
            )
            # Fallback: search predictions
            signals = get_predictions(limit=500)
            match = next((s for s in signals if s.get("id") == int(signal_id_input)), None)
            if match:
                _render_report_card(match)
            else:
                st.error(f"Signal #{signal_id_input} not found in history.")

    # ── Recent signals overview ───────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("RECENT SIGNAL REPORTS", "BROWSE")

    with st.spinner("Loading recent signals…"):
        signals = get_predictions(limit=20)

    if not signals:
        st.info("No signals available.")
        return

    # Tabs by label
    labels_present = list({s.get("label", "Unknown") for s in signals})
    tabs = st.tabs(["📋 All"] + [f"{'🚨' if l=='Jamming' else '🚁' if l=='Drone' else '✅'} {l}"
                                  for l in sorted(labels_present)])

    def show_signals(subset: list[dict]) -> None:
        for sig in subset[:6]:
            _render_report_card(sig)

    with tabs[0]:
        show_signals(signals)

    for i, label in enumerate(sorted(labels_present)):
        with tabs[i + 1]:
            filtered = [s for s in signals if s.get("label") == label]
            if filtered:
                show_signals(filtered)
            else:
                st.info(f"No {label} signals.")

    # ── Batch download ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    df = pd.DataFrame(signals)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Recent Reports CSV",
        data=csv,
        file_name="signal_reports.csv",
        mime="text/csv",
        use_container_width=True,
    )
