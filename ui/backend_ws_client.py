from __future__ import annotations

"""
WebSocket client for the new FastAPI backend.

Connects to /ws/matches/{match_id} and receives real-time updates:
- clock: Clock state changes (display_minute, period, status, etc.)
- state: Full match state updates
- event: New match events (goals, cards, etc.)
"""

import json
import os
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, QUrl, Signal, QTimer
from PySide6.QtWebSockets import QWebSocket


BACKEND_WS_BASE = os.environ.get("PITCH_BACKEND_WS_URL", "ws://127.0.0.1:8000")


class BackendWSClient(QObject):
    """Qt WebSocket client for backend real-time updates."""

    # Signals for different message types
    clockUpdated = Signal(dict)          # Full clock state dict
    stateUpdated = Signal(dict)          # Full match state dict
    eventReceived = Signal(dict)         # New event dict
    connectionStatusChanged = Signal(bool)  # Connected/disconnected

    # Legacy signal for backwards compatibility
    timeUpdated = Signal(float, bool)    # display_seconds, is_running

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._socket = QWebSocket()
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.textMessageReceived.connect(self._on_message)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._try_reconnect)
        
        self._match_id: Optional[str] = None
        self._is_connected = False

    def connect_to_match(self, match_id: str) -> None:
        """Open WebSocket connection for a specific match."""
        self._match_id = match_id
        url = QUrl(f"{BACKEND_WS_BASE}/ws/matches/{match_id}")
        print(f"[BackendWS] Connecting to {url.toString()}")
        self._socket.open(url)

    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._reconnect_timer.isActive():
            self._reconnect_timer.stop()
        self._socket.close()
        self._match_id = None

    def _try_reconnect(self) -> None:
        """Try to reconnect to the last match."""
        if self._match_id:
            self.connect_to_match(self._match_id)

    def _on_connected(self) -> None:
        self._is_connected = True
        print(f"[BackendWS] Connected to match {self._match_id}")
        if self._reconnect_timer.isActive():
            self._reconnect_timer.stop()
        self.connectionStatusChanged.emit(True)

    def _on_disconnected(self) -> None:
        self._is_connected = False
        print(f"[BackendWS] Disconnected from match {self._match_id}")
        self.connectionStatusChanged.emit(False)
        # Auto-reconnect
        if self._match_id and not self._reconnect_timer.isActive():
            self._reconnect_timer.start(2000)

    def _on_error(self, error) -> None:
        print(f"[BackendWS] WebSocket error: {error}")
        if not self._reconnect_timer.isActive() and self._match_id:
            self._reconnect_timer.start(2000)

    def _on_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except Exception as exc:
            print(f"[BackendWS] Failed to parse message: {exc}")
            return

        msg_type = data.get("type")
        payload = data.get("data") or data.get("payload") or {}

        try:
            if msg_type == "clock":
                self._handle_clock(payload)
            elif msg_type == "state":
                self._handle_state(payload)
            elif msg_type == "event":
                self._handle_event(payload)
            else:
                print(f"[BackendWS] Unknown message type: {msg_type}")
        except Exception as exc:
            print(f"[BackendWS] Failed to handle {msg_type} message: {exc}")

    def _handle_clock(self, clock_data: Dict[str, Any]) -> None:
        """Handle clock update from backend."""
        self.clockUpdated.emit(clock_data)
        
        # Also emit legacy timeUpdated signal
        display_minute = clock_data.get("display_minute", 0)
        display_second = clock_data.get("display_second", 0)
        status = clock_data.get("status", "stopped")
        
        total_seconds = (display_minute * 60) + display_second
        is_running = status == "running"
        
        self.timeUpdated.emit(float(total_seconds), is_running)

    def _handle_state(self, state_data: Dict[str, Any]) -> None:
        """Handle full match state update."""
        self.stateUpdated.emit(state_data)
        
        # Extract clock from state for legacy signal
        clock_data = state_data.get("clock", {})
        if clock_data:
            self._handle_clock(clock_data)

    def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """Handle new event notification."""
        self.eventReceived.emit(event_data)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def current_match_id(self) -> Optional[str]:
        return self._match_id


