"""
src/api/websocket.py
--------------------
Real-time alert broadcasting via WebSocket.

Endpoint : /ws/alerts
Protocol : WebSocket (JSON messages)
Behaviour:
  - Clients connect and remain subscribed.
  - When a new alert is triggered anywhere in the app, call
    broadcast_alert(alert_data) to push it to every connected client.
  - Disconnected clients are silently removed from the pool.

Usage (in routes.py after creating an alert):
    from .websocket import broadcast_alert
    await broadcast_alert({"alert_id": 7, "label": "Jamming", ...})
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("spectrum.ws")

# ── WebSocket router — registered separately in main.py ────────────
ws_router = APIRouter()


# =====================================================================
# CONNECTION MANAGER
# =====================================================================

class ConnectionManager:
    """
    Manages the pool of active WebSocket connections.
    Thread-safe via asyncio — no extra locking needed in a single-process
    ASGI deployment.
    """

    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts the handshake and registers the client."""
        await websocket.accept()
        self._clients.append(websocket)
        logger.info("WS client connected — total: %d", len(self._clients))

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a client from the pool (called on disconnect or send error)."""
        if websocket in self._clients:
            self._clients.remove(websocket)
        logger.info("WS client disconnected — total: %d", len(self._clients))

    async def broadcast(self, payload: dict) -> None:
        """
        Sends a JSON payload to every active client.
        Clients that have disconnected are quietly removed.
        """
        if not self._clients:
            return                                     # no one listening — skip

        message = json.dumps(payload, default=str)    # default=str handles datetimes
        dead: list[WebSocket] = []

        for client in list(self._clients):            # iterate a snapshot
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)                   # mark as dead

        for client in dead:
            self.disconnect(client)

    @property
    def active_count(self) -> int:
        return len(self._clients)


# Singleton shared across the entire application
manager = ConnectionManager()


# =====================================================================
# PUBLIC HELPER — call this from routes.py
# =====================================================================

async def broadcast_alert(alert_data: dict[str, Any]) -> None:
    """
    Convenience wrapper used by routes.py after a new alert is saved.

    Args:
        alert_data: Dict with at minimum:
            {
                "alert_id":   int,
                "signal_id":  int,
                "label":      str,
                "confidence": float,
                "alert_type": str,
                "location":   str,
                "timestamp":  str,
            }

    Example:
        await broadcast_alert({
            "alert_id": 7,
            "label": "Jamming",
            "confidence": 0.94,
            "alert_type": "email",
            "location": "Sector 7",
            "timestamp": "2026-04-26T18:00:00",
        })
    """
    payload = {"event": "new_alert", **alert_data}
    await manager.broadcast(payload)
    logger.info(
        "WS broadcast — label=%s | clients=%d",
        alert_data.get("label"),
        manager.active_count,
    )


# =====================================================================
# WEBSOCKET ENDPOINT
# =====================================================================

@ws_router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint that streams real-time alert events.

    Connect via:
        ws://host:port/ws/alerts

    On connect, the server sends a welcome message:
        {"event": "connected", "message": "Subscribed to real-time alerts."}

    After that, every call to broadcast_alert() sends:
        {
            "event":      "new_alert",
            "alert_id":   7,
            "signal_id":  3,
            "label":      "Jamming",
            "confidence": 0.94,
            "alert_type": "email",
            "location":   "Sector 7",
            "timestamp":  "2026-04-26T18:00:00.123456"
        }
    """
    await manager.connect(websocket)
    try:
        # Greet the new subscriber
        await websocket.send_json({
            "event":   "connected",
            "message": "Subscribed to real-time spectrum alerts.",
            "active_clients": manager.active_count,
        })

        # Keep the connection alive — we only push, but we also read
        # so that disconnects (client closing browser, etc.) are detected.
        while True:
            try:
                # Wait for any message from the client (ping / pong / keep-alive)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                logger.debug("WS ping received: %s", data)
            except asyncio.TimeoutError:
                # No message in 30 s — send a server-side ping to keep alive
                await websocket.send_json({"event": "ping"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WS error: %s", exc)
        manager.disconnect(websocket)
