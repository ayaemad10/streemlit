# SpectrumGuard Dashboard

AI-Powered Spectrum Anomaly Detection · ITC-Egypt 2026

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start your FastAPI backend (in a separate terminal)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Launch the dashboard
streamlit run app.py
```

## Environment Variables

| Variable            | Default                         | Description                    |
|---------------------|---------------------------------|--------------------------------|
| `SPECTRUM_API_URL`  | `http://localhost:8000/api/v1`  | Backend API base URL           |
| `SPECTRUM_WS_URL`   | `ws://localhost:8000/ws/alerts` | WebSocket endpoint             |
| `API_KEY`           | *(empty)*                       | Optional API key for auth      |
| `API_TIMEOUT`       | `10`                            | Request timeout in seconds     |

## Pages

| Page               | Route          | Description                                      |
|--------------------|----------------|--------------------------------------------------|
| 🏠 Home            | `/`            | KPI overview, recent alerts, live status         |
| 📡 Real-Time       | Real-Time      | Upload/enter features, run model inference        |
| 🗺️ Live Map        | Live Map       | Interactive alert location map                   |
| 🚨 Alerts Log      | Alerts Log     | Searchable, filterable alert table               |
| 📊 Analytics       | Analytics      | Charts: distribution, confidence, timeline       |
| 🗂️ History         | History        | Paginated prediction history with filters        |
| 📄 Reports         | Reports        | Per-signal detailed report viewer                |
| 🤖 Agent Chat      | Agent Chat     | Conversational AI interface via /chat            |
| 🖥️ System Monitor  | System Monitor | CPU, RAM, disk, API health, latency              |

## Project Structure

```
streamlit_app/
├── app.py                    # Entry point + sidebar navigation
├── requirements.txt
├── utils/
│   ├── api.py                # All API functions (cached)
│   └── style_loader.py       # CSS injection + UI helpers
├── assets/css/
│   ├── theme.css             # Design tokens & CSS variables
│   ├── typography.css        # Font system
│   ├── animations.css        # Keyframes & motion utilities
│   ├── components.css        # Cards, badges, alerts, tables
│   ├── responsive.css        # Breakpoint overrides
│   └── style.css             # Global reset & Streamlit overrides
└── pages/
    ├── home.py
    ├── realtime.py
    ├── live_map.py
    ├── alerts_log.py
    ├── analytics.py
    ├── history.py
    ├── reports.py
    ├── agent_chat.py
    └── system_monitor.py
```
