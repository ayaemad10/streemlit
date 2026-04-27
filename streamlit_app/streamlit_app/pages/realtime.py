"""
pages/realtime.py
-----------------
Real-Time Predict — upload a CSV or enter features manually,
call POST /predict, and display results with confidence gauge.
"""

import json
import io
import streamlit as st
import pandas as pd
import numpy as np
from utils.api import predict
from utils.style_loader import section_header, badge


def _confidence_bar(confidence: float, label: str) -> str:
    kind = "critical" if label == "Jamming" else ("warning" if label == "Drone" else "safe")
    color_map = {"critical": "var(--critical-red)", "warning": "var(--warning-yellow)", "safe": "var(--safe-green)"}
    color = color_map[kind]
    pct = confidence * 100
    return f"""
    <div style="margin-top:8px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-secondary);">
                Confidence
            </span>
            <span style="font-family:var(--font-mono);font-size:14px;font-weight:700;color:{color};">
                {pct:.1f}%
            </span>
        </div>
        <div style="background:var(--bg-tertiary);border-radius:var(--radius-pill);
                    height:8px;overflow:hidden;">
            <div style="width:{pct:.1f}%;height:100%;background:{color};
                        border-radius:var(--radius-pill);
                        box-shadow:0 0 8px {color};
                        transition:width 0.5s ease;"></div>
        </div>
    </div>
    """


def _result_card(result: dict) -> None:
    label      = result.get("label", "Unknown")
    confidence = result.get("confidence", 0)
    signal_id  = result.get("signal_id", "—")
    inf_ms     = result.get("inference_time_ms", "—")
    alert_trig = result.get("alert_triggered", False)
    alert_id   = result.get("alert_id")
    model_ver  = result.get("model_version", "—")
    timestamp  = str(result.get("timestamp", "—"))[:19]

    kind = "critical" if label == "Jamming" else ("warning" if label == "Drone" else "safe")
    icon = "🚨" if label == "Jamming" else ("🚁" if label == "Drone" else "✅")
    border_color = {
        "critical": "var(--critical-red)",
        "warning":  "var(--warning-yellow)",
        "safe":     "var(--safe-green)",
    }[kind]

    bar_html = _confidence_bar(confidence, label)
    badge_html = badge(label, kind)
    alert_html = (
        f'<span style="color:var(--critical-red);font-weight:700;">⚡ Alert #{alert_id} triggered</span>'
        if alert_trig else
        '<span style="color:var(--safe-green);">✅ No alert</span>'
    )

    st.markdown(f"""
    <div style="border:1px solid {border_color};border-radius:var(--radius-lg);
                background:var(--bg-secondary);padding:24px;margin-top:16px;
                box-shadow:0 0 20px {border_color}40;">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
            <span style="font-size:48px;">{icon}</span>
            <div>
                <div style="font-family:var(--font-display);font-size:32px;
                            font-weight:800;letter-spacing:0.12em;color:{border_color};
                            text-transform:uppercase;">
                    {label}
                </div>
                {badge_html}
            </div>
        </div>
        {bar_html}
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px;">
            <div style="background:var(--bg-tertiary);border-radius:var(--radius-md);padding:12px;">
                <div style="font-size:10px;color:var(--text-tertiary);
                            letter-spacing:0.12em;text-transform:uppercase;
                            font-family:var(--font-mono);">Signal ID</div>
                <div style="font-family:var(--font-mono);font-size:18px;
                            color:var(--accent-cyan);font-weight:600;">{signal_id}</div>
            </div>
            <div style="background:var(--bg-tertiary);border-radius:var(--radius-md);padding:12px;">
                <div style="font-size:10px;color:var(--text-tertiary);
                            letter-spacing:0.12em;text-transform:uppercase;
                            font-family:var(--font-mono);">Inference</div>
                <div style="font-family:var(--font-mono);font-size:18px;
                            color:var(--accent-cyan);font-weight:600;">{inf_ms} ms</div>
            </div>
            <div style="background:var(--bg-tertiary);border-radius:var(--radius-md);padding:12px;">
                <div style="font-size:10px;color:var(--text-tertiary);
                            letter-spacing:0.12em;text-transform:uppercase;
                            font-family:var(--font-mono);">Model</div>
                <div style="font-family:var(--font-mono);font-size:18px;
                            color:var(--accent-cyan);font-weight:600;">{model_ver}</div>
            </div>
        </div>
        <div style="margin-top:16px;padding-top:16px;
                    border-top:1px solid var(--border-subtle);
                    display:flex;justify-content:space-between;align-items:center;">
            {alert_html}
            <span style="font-family:var(--font-mono);font-size:11px;
                         color:var(--text-tertiary);">🕐 {timestamp}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">📡 REAL-TIME PREDICTION</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    # ── LEFT: Input panel ─────────────────────────────────────────
    with left:
        section_header("INPUT SIGNAL DATA", "PREDICT")

        input_mode = st.radio(
            "Input Mode",
            ["✏️ Manual Entry", "📁 Upload CSV", "🎲 Generate Demo"],
            horizontal=True,
        )

        features    = None
        frequency   = None
        snr         = None
        source      = "UI-Manual"
        alert_type  = "email"
        location    = "Unknown"

        if input_mode == "✏️ Manual Entry":
            raw = st.text_area(
                "Feature Vector (comma-separated floats)",
                placeholder="0.12, 0.45, 0.78, 0.33, 0.91, ...",
                height=120,
                help="Enter the pre-processed feature vector for your signal.",
            )
            c1, c2 = st.columns(2)
            with c1:
                frequency = st.number_input("Frequency (MHz)", min_value=0.0, value=433.5, step=0.1)
                alert_type = st.selectbox("Alert Type", ["email", "whatsapp", "sound"])
            with c2:
                snr      = st.number_input("SNR (dB)", value=15.0, step=0.5)
                location = st.text_input("Location", value="Cairo, Egypt")
            source = st.text_input("Source / Sensor ID", value="SDR-01")

            if raw:
                try:
                    features = [float(x.strip()) for x in raw.split(",") if x.strip()]
                except ValueError:
                    st.error("❌ Invalid format — use comma-separated numbers only.")

        elif input_mode == "📁 Upload CSV":
            uploaded = st.file_uploader(
                "Upload signal CSV (one row = one sample)",
                type=["csv"],
                help="Each column is a feature. First row = header (optional).",
            )
            c1, c2 = st.columns(2)
            with c1:
                row_idx    = st.number_input("Row index to predict", min_value=0, value=0, step=1)
                alert_type = st.selectbox("Alert Type", ["email", "whatsapp", "sound"])
            with c2:
                location = st.text_input("Location", value="Cairo, Egypt")
                source   = st.text_input("Source", value="CSV-Upload")

            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    st.dataframe(df.head(5), use_container_width=True)
                    if row_idx < len(df):
                        features = df.iloc[int(row_idx)].tolist()
                        st.success(f"✅ Row {row_idx} loaded — {len(features)} features.")
                    else:
                        st.warning(f"Row {row_idx} out of range ({len(df)} rows).")
                except Exception as e:
                    st.error(f"❌ Could not parse CSV: {e}")

        else:  # Demo
            n_features = st.slider("Number of features", 16, 256, 64)
            demo_class = st.selectbox("Simulate class", ["Normal", "Jamming", "Drone"])
            alert_type = st.selectbox("Alert Type", ["email", "whatsapp", "sound"])
            location   = st.text_input("Location", value="Demo Station, Cairo")
            source     = "DEMO-GEN"

            rng = np.random.default_rng(42)
            if demo_class == "Jamming":
                features = (rng.normal(0.8, 0.1, n_features)).clip(0, 1).tolist()
            elif demo_class == "Drone":
                features = (rng.normal(0.5, 0.2, n_features)).clip(0, 1).tolist()
            else:
                features = (rng.normal(0.2, 0.1, n_features)).clip(0, 1).tolist()

            st.success(f"🎲 Generated {n_features} demo features for '{demo_class}' simulation.")

        # ── Submit ────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🚀 Run Prediction", type="primary", use_container_width=True,
                            disabled=features is None)

    # ── RIGHT: Results panel ──────────────────────────────────────
    with right:
        section_header("PREDICTION RESULT", "OUTPUT")

        if "last_result" not in st.session_state:
            st.session_state.last_result = None

        if run_btn and features:
            with st.spinner("🧠 Running model inference…"):
                result = predict(
                    features=features,
                    frequency=frequency,
                    snr=snr,
                    source=source,
                    alert_type=alert_type,
                    location=location,
                )
            if result:
                st.session_state.last_result = result
                st.success("✅ Prediction complete!")
            else:
                st.error("❌ Prediction failed — check API connection.")

        if st.session_state.last_result:
            _result_card(st.session_state.last_result)

            # Raw JSON expander
            with st.expander("🔍 Raw API Response"):
                st.json(st.session_state.last_result)
        else:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;
                        border:1px dashed var(--border-subtle);
                        border-radius:var(--radius-lg);
                        background:var(--bg-secondary);">
                <div style="font-size:48px;margin-bottom:16px;">📡</div>
                <div style="font-family:var(--font-mono);font-size:13px;
                            color:var(--text-tertiary);">
                    Enter signal data and click<br>
                    <strong style="color:var(--accent-cyan);">Run Prediction</strong>
                    to see results.
                </div>
            </div>
            """, unsafe_allow_html=True)
