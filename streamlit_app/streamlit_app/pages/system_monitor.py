"""
pages/system_monitor.py
------------------------
System Monitor — CPU, RAM, disk, API health, model status.
Auto-refreshes every 5 seconds if enabled.
"""

import time
import streamlit as st
from utils.api import health_check, API_BASE
from utils.style_loader import section_header


def _gauge_html(label: str, value: float, unit: str = "%",
                warn: float = 70, crit: float = 90) -> str:
    """Return an HTML gauge bar."""
    color = (
        "var(--critical-red)"    if value >= crit else
        "var(--warning-yellow)"  if value >= warn else
        "var(--safe-green)"
    )
    return f"""
    <div style="margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-family:var(--font-mono);font-size:12px;
                         color:var(--text-secondary);">{label}</span>
            <span style="font-family:var(--font-mono);font-size:14px;
                         font-weight:700;color:{color};">{value:.1f}{unit}</span>
        </div>
        <div style="background:var(--bg-tertiary);border-radius:var(--radius-pill);
                    height:8px;overflow:hidden;">
            <div style="width:{min(value,100):.1f}%;height:100%;background:{color};
                        border-radius:var(--radius-pill);
                        box-shadow:0 0 8px {color};"></div>
        </div>
    </div>
    """


def _status_row(label: str, value: str, status: str = "ok") -> str:
    dot_color = {
        "ok":      "var(--safe-green)",
        "warn":    "var(--warning-yellow)",
        "error":   "var(--critical-red)",
        "info":    "var(--accent-cyan)",
    }.get(status, "var(--text-tertiary)")
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                padding:10px 0;border-bottom:1px solid var(--border-subtle);">
        <span style="color:var(--text-secondary);font-size:13px;">{label}</span>
        <span style="font-family:var(--font-mono);font-size:13px;color:{dot_color};
                     font-weight:600;">● {value}</span>
    </div>
    """


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">🖥️ SYSTEM MONITOR</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-cyan),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    # ── Auto-refresh toggle ───────────────────────────────────────
    hdr1, hdr2 = st.columns([4, 2])
    with hdr2:
        auto_refresh = st.toggle("🔄 Auto-refresh (5s)", value=False)

    if auto_refresh:
        time.sleep(5)
        st.rerun()

    # ── Collect metrics ───────────────────────────────────────────
    with st.spinner("Collecting system metrics…"):
        api_health = health_check()

        # psutil metrics
        try:
            import psutil
            cpu_pct    = psutil.cpu_percent(interval=0.5)
            mem        = psutil.virtual_memory()
            ram_pct    = mem.percent
            ram_used   = mem.used  / (1024 ** 3)
            ram_total  = mem.total / (1024 ** 3)
            disk       = psutil.disk_usage("/")
            disk_pct   = disk.percent
            disk_used  = disk.used  / (1024 ** 3)
            disk_total = disk.total / (1024 ** 3)
            cpu_count  = psutil.cpu_count(logical=True)
            boot_time  = psutil.boot_time()
            uptime_s   = time.time() - boot_time
            uptime_h   = uptime_s / 3600
            net        = psutil.net_io_counters()
            bytes_sent = net.bytes_sent / (1024 ** 2)
            bytes_recv = net.bytes_recv / (1024 ** 2)
            psutil_ok  = True
        except ImportError:
            cpu_pct = ram_pct = disk_pct = 0.0
            ram_used = ram_total = disk_used = disk_total = 0.0
            cpu_count = bytes_sent = bytes_recv = uptime_h = 0.0
            psutil_ok = False

    api_online  = api_health["status"] == "online"
    api_latency = api_health.get("latency_ms", -1)
    api_data    = api_health.get("data", {})

    # ── KPI strip ─────────────────────────────────────────────────
    section_header("SYSTEM HEALTH", "LIVE")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        label = "🟢 Online" if api_online else "🔴 Offline"
        st.metric("🌐 API Status", label)
    with k2:
        st.metric("⚡ API Latency", f"{api_latency} ms" if api_online else "—",
                  delta="Fast" if api_online and api_latency < 200 else
                         ("Slow" if api_online else "Unreachable"),
                  delta_color="normal" if api_online and api_latency < 200 else "inverse")
    with k3:
        st.metric("🧠 CPU Usage", f"{cpu_pct:.1f}%" if psutil_ok else "N/A")
    with k4:
        st.metric("💾 RAM Usage", f"{ram_pct:.1f}%" if psutil_ok else "N/A")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────
    left_col, right_col = st.columns(2, gap="large")

    # ── LEFT: Resource gauges ──────────────────────────────────────
    with left_col:
        section_header("RESOURCE USAGE", "GAUGES")
        st.markdown('<div class="status-card">', unsafe_allow_html=True)

        if psutil_ok:
            st.markdown(
                _gauge_html("🧠 CPU Usage",  cpu_pct) +
                _gauge_html("💾 RAM Usage",  ram_pct) +
                _gauge_html("💿 Disk Usage", disk_pct, warn=80, crit=95),
                unsafe_allow_html=True,
            )
            # Detail rows
            st.markdown(
                _status_row("CPU Cores",           str(cpu_count),                     "info") +
                _status_row("RAM Used",            f"{ram_used:.1f} / {ram_total:.1f} GB", "info") +
                _status_row("Disk Used",           f"{disk_used:.1f} / {disk_total:.1f} GB", "info") +
                _status_row("System Uptime",       f"{uptime_h:.1f} hours",            "ok") +
                _status_row("Net Sent",            f"{bytes_sent:.1f} MB",             "info") +
                _status_row("Net Received",        f"{bytes_recv:.1f} MB",             "info"),
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ `psutil` not installed. Run `pip install psutil` for live metrics.")
            st.markdown("""
            <div style="text-align:center;padding:24px;color:var(--text-tertiary);
                        font-family:var(--font-mono);">
                System metrics unavailable
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── RIGHT: API status ──────────────────────────────────────────
    with right_col:
        section_header("API STATUS", "HEALTH")
        st.markdown('<div class="status-card">', unsafe_allow_html=True)

        api_status_str = "ONLINE" if api_online else "OFFLINE"
        api_dot = "ok" if api_online else "error"

        st.markdown(
            _status_row("API Server",      api_status_str,             api_dot) +
            _status_row("Endpoint",        API_BASE,                   "info") +
            _status_row("Response Time",   f"{api_latency} ms" if api_online else "—",
                        "ok" if api_online and api_latency < 300 else "warn") +
            _status_row("Model",           api_data.get("model_version", "—"), "info") +
            _status_row("API Version",     api_data.get("version", "v1"),       "info"),
            unsafe_allow_html=True,
        )

        if not api_online:
            err = api_health.get("error", "Connection refused")
            st.markdown(f"""
            <div style="background:var(--critical-red-bg);border:1px solid var(--critical-red-border);
                        border-radius:var(--radius-md);padding:12px;margin-top:12px;">
                <div style="color:var(--critical-red);font-weight:700;margin-bottom:4px;">
                    ⚠️ API Unreachable
                </div>
                <div style="font-family:var(--font-mono);font-size:11px;
                            color:var(--text-tertiary);">{err[:120]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Connectivity test ──────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("CONNECTIVITY TEST", "PING")
        st.markdown('<div class="status-card">', unsafe_allow_html=True)

        endpoints = [
            ("/health",      "Health Check"),
            ("/statistics",  "Statistics"),
            ("/predictions", "Predictions"),
            ("/alerts",      "Alerts"),
        ]
        import requests
        for path, name in endpoints:
            url = f"{API_BASE}{path}"
            try:
                t0  = time.perf_counter()
                r   = requests.get(url, timeout=3)
                ms  = int((time.perf_counter() - t0) * 1000)
                ok  = r.status_code == 200
                st.markdown(
                    _status_row(
                        f"{name} ({path})",
                        f"{'✅' if ok else '❌'} {r.status_code} · {ms}ms",
                        "ok" if ok else "error",
                    ),
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.markdown(
                    _status_row(f"{name} ({path})", f"❌ {str(e)[:40]}", "error"),
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── CPU history chart ──────────────────────────────────────────
    if psutil_ok:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("RESOURCE SNAPSHOT", "CURRENT")

        import pandas as pd
        snapshot_df = pd.DataFrame({
            "Resource":   ["CPU",        "RAM",      "Disk"],
            "Usage (%)":  [cpu_pct,      ram_pct,    disk_pct],
        }).set_index("Resource")
        st.bar_chart(snapshot_df, use_container_width=True, height=200)

    # ── Footer ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:24px;text-align:center;font-family:var(--font-mono);
                font-size:11px;color:var(--text-disabled);">
        Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
        &nbsp;·&nbsp; SpectrumGuard Monitor v1.0
    </div>
    """, unsafe_allow_html=True)
