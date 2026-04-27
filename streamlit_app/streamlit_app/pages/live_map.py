"""
pages/live_map.py
-----------------
Live Threat Map — plots alert locations on an interactive map.
Uses pydeck if available, falls back to folium → st.components.
"""

import streamlit as st
import pandas as pd
from utils.api import get_alerts, clear_caches
from utils.style_loader import section_header, badge

# ── Cairo / Egypt coordinates as default center ───────────────────
DEFAULT_LAT = 30.0444
DEFAULT_LON = 31.2357

# Rough geocode table for common Egyptian cities / sectors
_KNOWN_LOCATIONS: dict[str, tuple[float, float]] = {
    "cairo":      (30.0444, 31.2357),
    "sector 7":   (30.0600, 31.2500),
    "alexandria": (31.2001, 29.9187),
    "giza":       (29.9870, 31.2118),
    "heliopolis": (30.0911, 31.3219),
    "maadi":      (29.9608, 31.2503),
    "nasr city":  (30.0622, 31.3422),
    "zamalek":    (30.0626, 31.2195),
    "unknown":    (30.0444, 31.2357),
}


def _geo(location: str) -> tuple[float, float]:
    """Best-effort geocoding from location string."""
    low = location.lower()
    for key, coords in _KNOWN_LOCATIONS.items():
        if key in low:
            return coords
    # Scatter near Cairo with a small jitter so points don't stack
    import hashlib, math
    h = int(hashlib.md5(location.encode()).hexdigest(), 16)
    lat = DEFAULT_LAT + (h % 200 - 100) / 5000
    lon = DEFAULT_LON + (h % 300 - 150) / 5000
    return lat, lon


def _color(label: str) -> list[int]:
    """RGBA colour per signal class."""
    return {
        "Jamming": [239, 68,  68,  220],
        "Drone":   [245, 158, 11,  220],
        "Normal":  [16,  185, 129, 180],
    }.get(label, [0, 229, 255, 180])


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">🗺️ LIVE THREAT MAP</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            clear_caches()
            st.rerun()

    with st.spinner("Loading alert locations…"):
        alerts = get_alerts()

    if not alerts:
        st.info("📍 No alerts to display on map. Run a prediction first.")
        return

    # ── Build dataframe ───────────────────────────────────────────
    rows = []
    for a in alerts:
        loc = a.get("location", "Unknown")
        lat, lon = _geo(loc)
        rows.append({
            "alert_id":   a.get("id", 0),
            "signal_id":  a.get("signal_id", 0),
            "location":   loc,
            "alert_type": a.get("alert_type", "—"),
            "status":     a.get("status", "—"),
            "timestamp":  str(a.get("timestamp", ""))[:19],
            "lat":        lat,
            "lon":        lon,
        })

    df = pd.DataFrame(rows)

    # ── Filter controls ───────────────────────────────────────────
    section_header("FILTER ALERTS", "MAP CONTROLS")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.multiselect(
            "Status", options=df["status"].unique().tolist(),
            default=df["status"].unique().tolist(),
        )
    with col_f2:
        type_filter = st.multiselect(
            "Alert Type", options=df["alert_type"].unique().tolist(),
            default=df["alert_type"].unique().tolist(),
        )

    df = df[df["status"].isin(status_filter) & df["alert_type"].isin(type_filter)]

    section_header("THREAT LOCATIONS", "LIVE MAP")

    # ── Try pydeck first ──────────────────────────────────────────
    try:
        import pydeck as pdk

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_radius=5000,
            get_fill_color=[239, 68, 68, 200],
            pickable=True,
            auto_highlight=True,
        )
        text_layer = pdk.Layer(
            "TextLayer",
            data=df,
            get_position=["lon", "lat"],
            get_text="location",
            get_size=14,
            get_color=[237, 242, 247],
            get_alignment_baseline="'bottom'",
            pickable=False,
        )
        view = pdk.ViewState(
            latitude=df["lat"].mean(),
            longitude=df["lon"].mean(),
            zoom=8,
            pitch=40,
        )
        deck = pdk.Deck(
            layers=[layer, text_layer],
            initial_view_state=view,
            map_style="mapbox://styles/mapbox/dark-v10",
            tooltip={"text": "📍 {location}\n🆔 Alert #{alert_id}\n📬 {alert_type}\n🕐 {timestamp}"},
        )
        st.pydeck_chart(deck, use_container_width=True)

    except ImportError:
        # ── Fallback: folium ──────────────────────────────────────
        try:
            import folium
            from streamlit_folium import st_folium

            m = folium.Map(
                location=[df["lat"].mean(), df["lon"].mean()],
                zoom_start=9,
                tiles="CartoDB dark_matter",
            )
            for _, row in df.iterrows():
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=10,
                    color="#ef4444",
                    fill=True,
                    fill_color="#ef4444",
                    fill_opacity=0.7,
                    popup=folium.Popup(
                        f"<b>Alert #{row['alert_id']}</b><br>"
                        f"📍 {row['location']}<br>"
                        f"📬 {row['alert_type']}<br>"
                        f"🕐 {row['timestamp']}",
                        max_width=200,
                    ),
                ).add_to(m)
            st_folium(m, use_container_width=True, height=500)

        except ImportError:
            # ── Fallback: st.map ──────────────────────────────────
            st.warning("⚠️ Install `pydeck` or `folium + streamlit-folium` for an interactive map.")
            st.map(df.rename(columns={"lat": "latitude", "lon": "longitude"}))

    # ── Alert list ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("ALERT DETAILS", "TABLE")
    st.dataframe(
        df[["alert_id", "signal_id", "location", "alert_type", "status", "timestamp"]],
        use_container_width=True,
        hide_index=True,
    )

    # ── Stats row ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("📍 Unique Locations", df["location"].nunique())
    with s2:
        st.metric("🚨 Alerts Plotted", len(df))
    with s3:
        top_loc = df["location"].value_counts().idxmax() if len(df) else "—"
        st.metric("🔥 Hotspot", top_loc)
