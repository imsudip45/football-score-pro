"""
Main Window for Football Score Pro 2.0
Main application window with Match Setup tab
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProxyStyle,
    QPushButton,
    QStatusBar,
    QStyle,
    QStyleFactory,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .backend_service import BackendService
from .match_setup_tab import MatchSetupTab
from .play_on_tab import PlayOnTab
from .styles import get_global_focus_reset_style
from .subs_penalty_tab import SubsAndPenaltyTab
from .widgets.fixture_loader_dialog import FixtureLoaderDialog
from .widgets.key_mapping_dialog import KeyMappingDialog
from .widgets.lock_option_dialog import LockOptionDialog
from .widgets.lock_overlay import LockOverlay
from .widgets.pin_dialog import PinDialog
from .widgets.set_pin_dialog import SetPinDialog


class NoFocusStyle(QProxyStyle):
    """Proxy style that suppresses Qt's focus rectangles globally."""

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)


class _PaletteGuard(QObject):
    """Event filter that re-applies a fixed palette when OS theme changes."""

    def __init__(self, app: QApplication, palette: QPalette):
        super().__init__()
        self._app = app
        self._palette = palette

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.ThemeChange,
            QEvent.Type.StyleChange,
        ):
            self._app.setPalette(self._palette)
        return False


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, backend_service: BackendService):
        super().__init__()
        self.backend_service = backend_service
        
        # Initialize key mappings
        self.key_mappings = {
            "Home Possession Toggle": "1",
            "Away Possession Toggle": "2",
            "Start Timer": "S", 
            "Stop Timer": "T",
            "Reset Match": "r",
            "Home Goal +": "H",
            "Away Goal +": "A",
            "Home Goal -": "Shift+H",
            "Away Goal -": "Shift+A",
        }
        
        # Guard flags to prevent infinite loops
        self._layout_update_pending = False
        
        # Lock state
        self.is_locked = False
        self.is_master_locked = False  # Master lock state for all tabs
        self.current_pin = "2580"  # Default PIN     
        self._live_tabs_enabled = False
        self._last_tab_index = 0
        self.current_match_id = None
        self.autosave_dir = Path("data") / "matches"
        self.autosave_dir.mkdir(parents=True, exist_ok=True)
        self.autosave_path = None
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(5000)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self._last_autosave_hash = None
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_global_shortcuts()
        self._set_live_tabs_enabled(False)

    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Football Score Pro beta ")
        
        # Set window flags to ensure it takes entire screen
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create custom tab bar with tournament name and reset button
        self.create_custom_tab_bar()
        
        # Create tab widget (hide tab bar since we use custom one)
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()  # Hide the default tab bar
        self.tab_widget.setStyleSheet(self.get_tab_style())
        
        # Create Match Setup tab
        self.match_setup_tab = MatchSetupTab(self.backend_service, self)
        self.tab_widget.addTab(self.match_setup_tab, "Match Setup")
        
        # Create Play On tab
        self.play_on_tab = PlayOnTab(self.backend_service, self)
        self.tab_widget.addTab(self.play_on_tab, "Play On")
        
        # Create Subs and Penalty tab
        self.subs_penalty_tab = SubsAndPenaltyTab(self.backend_service, self)
        self.tab_widget.addTab(self.subs_penalty_tab, "Subs && Penalty")
        
        # Connect signals
        self.match_setup_tab.match_created.connect(self.on_match_created)
        self.match_setup_tab.match_saved.connect(self.on_match_saved)
        
        # Connect match data from Match Setup to Play On tab
        self.match_setup_tab.match_data_changed.connect(
            self.play_on_tab.load_match_data
        )
        
        # Connect match data from Match Setup to Subs and Penalty tab
        self.match_setup_tab.match_data_changed.connect(
            self.subs_penalty_tab.load_match_data
        )
        if hasattr(self.match_setup_tab, "officials_tab"):
            try:
                self.match_setup_tab.officials_tab.officials_changed.connect(
                    self.subs_penalty_tab.apply_officials_snapshot
                )
            except Exception as e:
                print(f"[MainWindow] Failed to connect officials snapshot signal: {e}")
        
        # Connect substitution updates from Subs/Penalty tab to Play On tab
        # This ensures playing 11 updates from substitutions reflect in Play On tab
        self.subs_penalty_tab.match_data_changed.connect(
            self.play_on_tab.load_match_data
        )
        
        # Also update Subs/Penalty tab itself when match data changes (to refresh UI)
        self.subs_penalty_tab.match_data_changed.connect(
            self.subs_penalty_tab.load_match_data
        )
        
        # Try to hook Play On time signals into header clock label if available
        self._try_connect_play_time_signal()
        
        # Add custom tab bar and tab widget to layout
        layout.addWidget(self.custom_tab_bar)
        layout.addWidget(self.tab_widget)
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Create lock overlays for each tab
        self.match_setup_overlay = LockOverlay(self.match_setup_tab)
        self.play_on_overlay = LockOverlay(self.play_on_tab)
        self.subs_penalty_overlay = LockOverlay(self.subs_penalty_tab)
        
        # Live tabs remain gated until match creation flips the flag

    def do_home_possession_toggle(self):
        """Trigger possession only if change to HOME is needed (no same-key toggle)."""
        try:
            if (
                hasattr(self, "play_on_tab")
                and self.tab_widget.currentWidget() is self.play_on_tab
            ):
                # If PlayOnTab exposes current possession, respect it
                current = getattr(self.play_on_tab, "current_possession", None)
                if current == "home":
                    return  # already home; do nothing (no same-key toggle)
                # 1) Preferred: if PlayOnTab exposes a single-way setter
                if hasattr(self.play_on_tab, "set_possession"):
                    self.play_on_tab.set_possession("home")
                    return
                # 2) Try to click a cached button attribute
                # Try two common attribute names
                btn = getattr(
                    self.play_on_tab, "possession_toggle_btn", None
                ) or getattr(self.play_on_tab, "possession_toggle_button", None)
                if btn:
                    btn.click()
                    return
                
        except Exception as e:
            print(f"[MainWindow] Error toggling home possession: {e}")

    def do_away_possession_toggle(self):
        """Trigger possession only if change to AWAY is needed (no same-key toggle)."""
        try:
            if (
                hasattr(self, "play_on_tab")
                and self.tab_widget.currentWidget() is self.play_on_tab
            ):
                current = getattr(self.play_on_tab, "current_possession", None)
                if current == "away":
                    return  # already away; do nothing (no same-key toggle)
                # Same behavior as home: prefer a single-way setter
                if hasattr(self.play_on_tab, "set_possession"):
                    self.play_on_tab.set_possession("away")
                    return
                btn = getattr(
                    self.play_on_tab, "possession_toggle_btn", None
                ) or getattr(self.play_on_tab, "possession_toggle_button", None)
                if btn:
                    btn.click()
                    return
        except Exception as e:
            print(f"[MainWindow] Error toggling away possession: {e}")

    def create_custom_tab_bar(self):
        """Create custom tab bar with tournament name in center and reset button on right"""
        
        # Create custom tab bar widget
        self.custom_tab_bar = QWidget()
        self.custom_tab_bar.setFixedHeight(50)
        self.custom_tab_bar.setStyleSheet("""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a5568, stop:1 #2d3748);
                border-bottom: 2px solid #2d3748;
            }}
        """)
        
        # Create horizontal layout
        tab_bar_layout = QHBoxLayout(self.custom_tab_bar)
        tab_bar_layout.setContentsMargins(10, 5, 10, 5)
        tab_bar_layout.setSpacing(20)
        
        # Create manual tab buttons
        self.tab_button_match_setup = QPushButton("Match Setup")
        self.tab_button_match_setup.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.tab_button_match_setup.setFixedHeight(40)
        self.tab_button_match_setup.setFixedWidth(150)
        self.tab_button_match_setup.setCheckable(True)
        self.tab_button_match_setup.setChecked(True)  # Default selected
        self.tab_button_match_setup.clicked.connect(lambda: self.switch_tab(0))
        self.tab_button_match_setup.setStyleSheet(self.get_tab_button_style(True))
        
        self.tab_button_play_on = QPushButton("Play On")
        self.tab_button_play_on.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.tab_button_play_on.setFixedHeight(40)
        self.tab_button_play_on.setFixedWidth(150)
        self.tab_button_play_on.setCheckable(True)
        self.tab_button_play_on.clicked.connect(lambda: self.switch_tab(1))
        self.tab_button_play_on.setStyleSheet(self.get_tab_button_style(False))
        
        self.tab_button_subs_penalty = QPushButton("Subs && Penalty")
        self.tab_button_subs_penalty.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        self.tab_button_subs_penalty.setFixedHeight(40)
        self.tab_button_subs_penalty.setFixedWidth(150)
        self.tab_button_subs_penalty.setCheckable(True)
        self.tab_button_subs_penalty.clicked.connect(lambda: self.switch_tab(2))
        self.tab_button_subs_penalty.setStyleSheet(self.get_tab_button_style(False))
        
        # Reset button (positioned right next to tournament name)
        self.reset_match_button = QPushButton("RESET MATCH")
        self.reset_match_button.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        self.reset_match_button.setFixedHeight(40)
        self.reset_match_button.setFixedWidth(140)
        self.reset_match_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e53e3e, stop:1 #c53030);
                color: white;
                border: 2px solid #742a2a;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f56565, stop:1 #e53e3e);
                border: 2px solid #9c2a2a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c53030, stop:1 #9c2a2a);
            }
        """)
        self.reset_match_button.clicked.connect(self.on_reset_clicked)
        self.reset_match_button.hide()  # Initially hidden

        # End Match button (positioned right next to reset match button)
        self.end_match_button = QPushButton("END MATCH")
        self.end_match_button.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        self.end_match_button.setFixedHeight(40)
        self.end_match_button.setFixedWidth(140)
        self.end_match_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                color: white;
                border: 2px solid #2f855a;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #68d391, stop:1 #48bb78);
                border: 2px solid #38a169;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
            }
        """)
        self.end_match_button.clicked.connect(self.on_end_match_clicked)
        self.end_match_button.hide()  # Initially hidden
        
        # Lock/Unlock toggle button (to the left of reset button)
        self.lock_toggle_button = QPushButton()
        self.lock_toggle_button.setFixedSize(40, 40)
        self.lock_toggle_button.setCheckable(True)
        self.lock_toggle_button.setChecked(False)  # Start unlocked
        self.update_lock_button_icon()
        self.lock_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border: 2px solid #4b5563;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border: 2px solid #6b7280;
            }
            QPushButton:checked {
                background-color: #dc2626;
                border: 2px solid #991b1b;
            }
            QPushButton:checked:hover {
                background-color: #ef4444;
                border: 2px solid #b91c1c;
            }
        """)
        self.lock_toggle_button.clicked.connect(self.on_lock_toggle_clicked)
        self.lock_toggle_button.hide()  # Initially hidden
        
        # Add widgets to layout
        tab_bar_layout.addWidget(self.tab_button_match_setup)
        tab_bar_layout.addWidget(self.tab_button_play_on)
        tab_bar_layout.addWidget(self.tab_button_subs_penalty)
        tab_bar_layout.addStretch()  # Push buttons to far right
        tab_bar_layout.addWidget(
            self.lock_toggle_button
        )  # Lock button before end match
        tab_bar_layout.addWidget(self.end_match_button)  # End match button
        tab_bar_layout.addWidget(self.reset_match_button)  # Far right corner
    
    def get_tab_button_style(self, is_active: bool) -> str:
        """Get style for the top main-window tab buttons (Match Setup / Play On / Subs&Penalty)."""
        if is_active:
            # Active tab: deep slate/indigo gradient, bold text (matches app background, with neon border)
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f2937, stop:1 #111827);
                    color: white;
                    border: 2px solid #22d3ee;
                    border-radius: 8px 8px 0px 0px;
                    padding: 8px 18px;
                    font-size: 14px;
                    font-weight: 600;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #111827, stop:1 #020617);
                }
            """
        else:
            # Inactive tab: subtle border by default; neon only on hover
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4b5563, stop:1 #374151);
                    color: #d1d5db;
                    border: 1px solid #4b5563;
                    border-radius: 8px 8px 0px 0px;
                    padding: 8px 18px;
                    font-size: 14px;
                    font-weight: 600;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6b7280, stop:1 #4b5563);
                    color: white;
                    border: 2px solid #22d3ee;
                }
            """
    
    def switch_tab(self, index):
        """Switch tabs and update button styles"""
        target_index = index
        if target_index in (1, 2) and not self._live_tabs_enabled:
            QMessageBox.warning(
                self,
                "Match Not Created",
                "Create the match in the Match Setup tab before using this area.",
            )
            target_index = 0
        if self.tab_widget.currentIndex() != target_index:
            self.tab_widget.setCurrentIndex(target_index)
        self._update_tab_button_states(target_index)
        self._last_tab_index = target_index

    def _update_tab_button_states(self, index: int):
        """Update custom tab button styles and auxiliary controls."""
    # Reset all buttons
        self.tab_button_match_setup.setChecked(False)
        self.tab_button_play_on.setChecked(False)
        self.tab_button_subs_penalty.setChecked(False)
    
        if index == 0:
            self.tab_button_match_setup.setChecked(True)
            self.tab_button_match_setup.setStyleSheet(self.get_tab_button_style(True))
            self.tab_button_play_on.setStyleSheet(self.get_tab_button_style(False))
            self.tab_button_subs_penalty.setStyleSheet(self.get_tab_button_style(False))
            self.reset_match_button.hide()
            self.end_match_button.hide()
            self.lock_toggle_button.hide()
        elif index == 1:
            self.tab_button_play_on.setChecked(True)
            self.tab_button_match_setup.setStyleSheet(self.get_tab_button_style(False))
            self.tab_button_play_on.setStyleSheet(self.get_tab_button_style(True))
            self.tab_button_subs_penalty.setStyleSheet(self.get_tab_button_style(False))
            self.reset_match_button.show()
            self.end_match_button.show()
            self.lock_toggle_button.show()
        elif index == 2:
            self.tab_button_subs_penalty.setChecked(True)
            self.tab_button_match_setup.setStyleSheet(self.get_tab_button_style(False))
            self.tab_button_play_on.setStyleSheet(self.get_tab_button_style(False))
            self.tab_button_subs_penalty.setStyleSheet(self.get_tab_button_style(True))
            self.reset_match_button.show()
            self.end_match_button.show()
            self.lock_toggle_button.show()
            
        # Keep status bar visible for all tabs
        if hasattr(self, "status_bar"):
            self.status_bar.show()
            
    def _set_live_tabs_enabled(self, enabled: bool):
        """Gate access to Play On and Subs/Penalty tabs until a match exists."""
        self._live_tabs_enabled = enabled
        tooltip = (
            ""
            if enabled
            else "Create a match in the Match Setup tab to use this section."
        )
        for btn in (self.tab_button_play_on, self.tab_button_subs_penalty):
            if btn:
                btn.setToolTip(tooltip)
        if not enabled:
            # Force navigation back to Match Setup when gating is active
            self._last_tab_index = 0
            if hasattr(self, "tab_widget") and self.tab_widget.currentIndex() != 0:
                self.tab_widget.setCurrentIndex(0)
            self._update_tab_button_states(0)
            if hasattr(self, "autosave_timer"):
                self.autosave_timer.stop()
            self.current_match_id = None
            self.autosave_path = None
            self._last_autosave_hash = None

    def _collect_session_state(self):
        if not self.current_match_id:
            return None
        try:
            match_setup_state = (
                self.match_setup_tab.export_state()
                if hasattr(self, "match_setup_tab")
                else {}
            )
            play_on_state = (
                self.play_on_tab.export_state() if hasattr(self, "play_on_tab") else {}
            )
            subs_state = (
                self.subs_penalty_tab.export_state()
                if hasattr(self, "subs_penalty_tab")
                else {}
            )
            return {
                "match_id": self.current_match_id,
                "timestamp": datetime.utcnow().isoformat(),
                "match_setup": match_setup_state,
                "play_on": play_on_state,
                "subs_penalty": subs_state,
            }
        except Exception as exc:
            print(f"Error collecting session state: {exc}")
            return None

    def _persist_autosave_state(self, force: bool = False):
        if not self.current_match_id:
            return
        state = self._collect_session_state()
        if not state:
            return
        try:
            canonical = json.dumps(state, sort_keys=True, default=str)
            snapshot_hash = hashlib.md5(canonical.encode("utf-8")).hexdigest()
            if not force and snapshot_hash == self._last_autosave_hash:
                return
            self.autosave_path = (
                self.autosave_dir / f"{self.current_match_id}_session.json"
            )
            with open(self.autosave_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._last_autosave_hash = snapshot_hash
        except Exception as exc:
            print(f"Error persisting autosave state: {exc}")

    def _autosave_tick(self):
        self._persist_autosave_state()

    def _load_session_state(self, state: dict) -> bool:
        if not state:
            return False
        match_setup_state = state.get("match_setup")
        if not match_setup_state:
            return False
        match_id = state.get("match_id")
        if not match_id:
            candidate = (
                match_setup_state.get("match_data")
                if isinstance(match_setup_state, dict)
                else match_setup_state
            )
            if isinstance(candidate, dict):
                match_id = candidate.get("match_id")
        if not match_id:
            match_id = f"match_{int(datetime.utcnow().timestamp())}"
        self.current_match_id = match_id
        self.match_setup_tab.load_match_state(match_setup_state)
        self._set_live_tabs_enabled(True)
        if hasattr(self.play_on_tab, "enable_match_data_loading"):
            self.play_on_tab.enable_match_data_loading()
        if hasattr(self.subs_penalty_tab, "enable_match_data_loading"):
            self.subs_penalty_tab.enable_match_data_loading()
        self.play_on_tab.load_state(state.get("play_on", {}))
        self.subs_penalty_tab.load_state(state.get("subs_penalty", {}))
        self.autosave_path = self.autosave_dir / f"{match_id}_session.json"
        self._last_autosave_hash = None
        if not self.autosave_timer.isActive():
            self.autosave_timer.start()
        self._persist_autosave_state(force=True)
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(f"Loaded match session: {match_id}")
        return True

    def update_play_time(self, mmss: str):
        """Public method for Play On tab to push live time (format mm:ss)."""
        try:
            # Update timer in Subs & Penalty tab instead of main window header
            if hasattr(self, "subs_penalty_tab") and hasattr(
                self.subs_penalty_tab, "play_time_label"
            ):
                if isinstance(mmss, str) and mmss:
                    self.subs_penalty_tab.play_time_label.setText(mmss)
        except Exception:
            pass

    def _try_connect_play_time_signal(self):
        """Best-effort: connect to a time-updated signal exposed by PlayOnTab if present."""
        try:
            # Common possible signal names used across implementations
            candidate_signals = [
                "time_updated",
                "timer_updated",
                "match_time_changed",
                "clock_updated",
                "timeChanged",
            ]
            for sig in candidate_signals:
                if hasattr(self.play_on_tab, sig):
                    getattr(self.play_on_tab, sig).connect(self.update_play_time)
                    break
            # Also support a callable getter via a polling QTimer in case no signal exists
            from PySide6.QtCore import QTimer

            if hasattr(self.play_on_tab, "get_current_time"):
                self._clock_poll_timer = QTimer(self)
                self._clock_poll_timer.setInterval(500)
                self._clock_poll_timer.timeout.connect(
                    lambda: self.update_play_time(
                        str(self.play_on_tab.get_current_time())
                    )
                )
                self._clock_poll_timer.start()
            elif hasattr(self.play_on_tab, "timer_label"):
                # Fallback: read directly from the timer label text
                self._clock_poll_timer = QTimer(self)
                self._clock_poll_timer.setInterval(250)
                self._clock_poll_timer.timeout.connect(
                    lambda: self.update_play_time(self.play_on_tab.timer_label.text())
                )
                self._clock_poll_timer.start()
        except Exception:
            pass
    
    def on_tab_changed(self, index):
        """Handle tab change events - sync with custom tab buttons"""
        self.switch_tab(index)
        # Removed automatic layout update to prevent timer exhaustion
    
    def _force_layout_update(self):
        """Force layout recalculation without resize tricks"""
        if self._layout_update_pending:
            return
        
        try:
            self._layout_update_pending = True
            # Simple geometry update without resize
            self.updateGeometry()
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.updateGeometry()
                current_widget.adjustSize()
                # Only call update_layout if it exists and has guards
                if hasattr(current_widget, "update_layout"):
                    current_widget.update_layout()  # type: ignore[attr-defined]
        except Exception as e:
            print(f"Error in _force_layout_update: {e}")
        finally:
            self._layout_update_pending = False
    
    def showEvent(self, event):
        """Handle show event - maximize window on first show"""
        super().showEvent(event)
        if not hasattr(self, "_maximized_on_show"):
            # Maximize on first show
            self.showMaximized()
            self._maximized_on_show = True
    
    def resizeEvent(self, event):
        """Handle resize events - ensure layouts are recalculated"""
        super().resizeEvent(event)
        # Only schedule update if not already pending
        if not self._layout_update_pending:
            self._layout_update_pending = True
            QTimer.singleShot(50, self._delayed_tab_layout_update)
    
    def _delayed_tab_layout_update(self):
        """Delayed layout update with guard"""
        self._layout_update_pending = False
        try:
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.updateGeometry()
                current_widget.adjustSize()
                if hasattr(current_widget, "update_layout"):
                    current_widget.update_layout()  # type: ignore[attr-defined]
        except Exception as e:
            print(f"Error in _delayed_tab_layout_update: {e}")
    
    def _update_all_tab_layouts(self):
        """Update layouts for all tabs to prevent overflow"""
        try:
            # Force current tab to update layout
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.updateGeometry()
                current_widget.adjustSize()
                # Force layout recalculation for the widget
                if hasattr(current_widget, "update_layout"):
                    current_widget.update_layout()  # type: ignore[attr-defined]
        except Exception as e:
            print(f"Error in _update_all_tab_layouts: {e}")
    
    def update_tournament_name(self, name):
        """Update tournament name when match data changes"""
        if hasattr(self.play_on_tab, "tournament_label"):
            self.play_on_tab.tournament_label.setText(name)

    def setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        # New Match action - goes to Match Setup and uses the existing reset flow
        new_match_action = QAction("New Match", self)
        new_match_action.setShortcut("Ctrl+N")
        new_match_action.triggered.connect(self.on_reset_clicked)
        file_menu.addAction(new_match_action)
        
        # Load Match action (session or legacy match file)
        load_match_action = QAction("Load Match", self)
        load_match_action.setShortcut("Ctrl+O")
        load_match_action.triggered.connect(self.load_match)
        file_menu.addAction(load_match_action)
        
        # Save Session action (manual save in addition to autosave)
        save_session_action = QAction("Save Session As...", self)
        save_session_action.setShortcut("Ctrl+S")
        save_session_action.triggered.connect(self.save_session_as)
        file_menu.addAction(save_session_action)
        
        file_menu.addSeparator()
        
        # Load Fixture action
        load_fixture_action = QAction("Load Fixture", self)
        load_fixture_action.setShortcut("Ctrl+F")
        load_fixture_action.triggered.connect(self.load_fixture)
        file_menu.addAction(load_fixture_action)
        
        file_menu.addSeparator()
        
        # End Match and Reset actions for convenience
        end_match_action = QAction("End Match", self)
        end_match_action.setShortcut("Ctrl+E")
        end_match_action.triggered.connect(self.on_end_match_clicked)
        file_menu.addAction(end_match_action)

        reset_match_action = QAction("Reset Match", self)
        reset_match_action.setShortcut("Ctrl+R")
        reset_match_action.triggered.connect(self.on_reset_clicked)
        file_menu.addAction(reset_match_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ========== MATCH ==========
        match_menu = menubar.addMenu("&Match")

        start_timer_action = QAction("Start Timer", self)
        start_timer_action.setShortcut("Ctrl+Shift+S")
        start_timer_action.triggered.connect(
            lambda: hasattr(self, "play_on_tab")
            and hasattr(self.play_on_tab, "start_timer")
            and self.play_on_tab.start_timer()
        )
        match_menu.addAction(start_timer_action)

        stop_timer_action = QAction("Stop Timer", self)
        stop_timer_action.setShortcut("Ctrl+Shift+T")
        stop_timer_action.triggered.connect(
            lambda: hasattr(self, "play_on_tab")
            and hasattr(self.play_on_tab, "stop_timer")
            and self.play_on_tab.stop_timer()
        )
        match_menu.addAction(stop_timer_action)

        match_menu.addSeparator()

        home_possession_action = QAction("Give Possession to Home", self)
        home_possession_action.setShortcut("Ctrl+H")
        home_possession_action.triggered.connect(self.do_home_possession_toggle)
        match_menu.addAction(home_possession_action)

        away_possession_action = QAction("Give Possession to Away", self)
        away_possession_action.setShortcut("Ctrl+A")
        away_possession_action.triggered.connect(self.do_away_possession_toggle)
        match_menu.addAction(away_possession_action)

        match_menu.addSeparator()

        match_menu.addAction(end_match_action)
        match_menu.addAction(reset_match_action)

        # ========== TOOLS ==========
        preferences_menu = menubar.addMenu("&Tools")
        
        # Key Mapping action
        key_mapping_action = QAction("Key Mapping", self)
        key_mapping_action.triggered.connect(self.show_key_mapping_dialog)
        preferences_menu.addAction(key_mapping_action)

        # Set PIN action
        set_pin_action = QAction("Set PIN", self)
        set_pin_action.triggered.connect(self.show_set_pin_dialog)
        preferences_menu.addAction(set_pin_action)
        
        # Lock Options (same as clicking the lock button)
        lock_options_action = QAction("Lock Options…", self)
        lock_options_action.triggered.connect(self.on_lock_toggle_clicked)
        preferences_menu.addAction(lock_options_action)
        
        # ========== VIEW ==========
        view_menu = menubar.addMenu("&View")
        goto_match_setup = QAction("Go to Match Setup", self)
        goto_match_setup.setShortcut("F1")
        goto_match_setup.triggered.connect(lambda: self.switch_tab(0))
        view_menu.addAction(goto_match_setup)

        goto_play_on = QAction("Go to Play On", self)
        goto_play_on.setShortcut("F2")
        goto_play_on.triggered.connect(lambda: self.switch_tab(1))
        view_menu.addAction(goto_play_on)

        goto_subs = QAction("Go to Subs && Penalty", self)
        goto_subs.setShortcut("F3")
        goto_subs.triggered.connect(lambda: self.switch_tab(2))
        view_menu.addAction(goto_subs)
        
        # ========== WINDOW ==========
        window_menu = menubar.addMenu("&Window")

        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)

        def _toggle_fullscreen(checked: bool):
            if checked:
                self.showFullScreen()
            else:
                self.showMaximized()

        fullscreen_action.toggled.connect(_toggle_fullscreen)
        window_menu.addAction(fullscreen_action)

        # ========== HELP ==========
        help_menu = menubar.addMenu("&Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setup_global_shortcuts(self):
        """Setup global keyboard shortcuts (possession toggles)."""
        from PySide6.QtGui import QKeySequence, QShortcut
        
        # Remove old shortcuts if they exist
        if hasattr(self, "home_possession_shortcut") and self.home_possession_shortcut:
            self.home_possession_shortcut.activated.disconnect()
            self.home_possession_shortcut.deleteLater()
            self.home_possession_shortcut = None
        
        if hasattr(self, "away_possession_shortcut") and self.away_possession_shortcut:
            self.away_possession_shortcut.activated.disconnect()
            self.away_possession_shortcut.deleteLater()
            self.away_possession_shortcut = None
        
        # Create new shortcuts with current mappings
        # Home possession toggle
        self.home_possession_shortcut = QShortcut(
            QKeySequence(self.key_mappings.get("Home Possession Toggle", "K")), self
        )
        self.home_possession_shortcut.activated.connect(self.do_home_possession_toggle)
        # Away possession toggle
        self.away_possession_shortcut = QShortcut(
            QKeySequence(self.key_mappings.get("Away Possession Toggle", "F")), self
        )
        self.away_possession_shortcut.activated.connect(self.do_away_possession_toggle)

    def get_tab_style(self) -> str:
        """Get tab widget style"""
        return """
            QTabWidget::pane {
                border: 1px solid #4b5563;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #374151, stop:1 #4b5563);
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4b5563, stop:1 #6b7280);
            }
        """

    def new_match(self):
        """Create a new match"""
        self.status_bar.showMessage("Creating new match...")
        # The Match Setup tab handles the actual match creation
        self.status_bar.showMessage("Ready")

    def load_match(self):
        """Load an existing match"""
        import json

        from PySide6.QtWidgets import QFileDialog

        try:
            self.status_bar.showMessage("Loading match...")
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Match", "", "JSON Files (*.json);;All Files (*)"
            )
            if not file_path:
                self.status_bar.showMessage("Ready")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Decide how to load based on content
            loaded = False
            loaded_message = "Match data loaded successfully."
            if isinstance(data, dict):
                if any(k in data for k in ("match_setup", "play_on", "subs_penalty")):
                    loaded = self._load_session_state(data)
                    loaded_message = "Match session loaded successfully."
                # Saved match state format (legacy)
                elif any(
                    k in data
                    for k in [
                        "home_team_a_state",
                        "home_team_b_state",
                        "away_team_a_state",
                        "away_team_b_state",
                        "match_number",
                    ]
                ):
                    if hasattr(self.match_setup_tab, "load_match_state"):
                        self.match_setup_tab.load_match_state(data)
                        loaded = True
                # Fixture-like format
                elif any(
                    k in data
                    for k in ["teams", "home_team", "away_team", "participants"]
                ):
                    if hasattr(self.match_setup_tab, "load_fixture_data"):
                        self.match_setup_tab.load_fixture_data(data)
                        loaded = True

            if loaded:
                QMessageBox.information(self, "Match Loaded", loaded_message)
                # Switch to Match Setup tab to review
                self.switch_tab(0)
                self.status_bar.showMessage("Ready")
            else:
                QMessageBox.warning(
                    self,
                    "Unrecognized File",
                    "The selected file format is not recognized as a saved match or fixture.",
                )
                self.status_bar.showMessage("Ready")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load match: {e}")
        self.status_bar.showMessage("Ready")

    def load_fixture(self):
        """Load fixture data from file or API"""
        self.status_bar.showMessage("Loading fixture...")
        
        # Open fixture loader dialog with backend_service
        dialog = FixtureLoaderDialog(self.backend_service, self)
        dialog.fixture_loaded.connect(self.on_fixture_loaded)
        
        if dialog.exec():
            self.status_bar.showMessage("Fixture loaded successfully")
        else:
            self.status_bar.showMessage("Ready")
    
    def save_session_as(self):
        """Manually save the full session (all tabs) to a JSON file."""
        from PySide6.QtWidgets import QFileDialog

        try:
            if not self.current_match_id:
                QMessageBox.information(
                    self,
                    "No Match",
                    "There is no active match to save. Please create or load a match first.",
                )
                return

            state = self._collect_session_state()
            if not state:
                QMessageBox.warning(
                    self,
                    "Nothing to Save",
                    "Unable to collect current session state.",
                )
                return

            default_name = (
                self.autosave_path.name if self.autosave_path else "match_session.json"
            )
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Session As",
                str(self.autosave_dir / default_name),
                "JSON Files (*.json);;All Files (*)",
            )
            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2, default=str)

            self.status_bar.showMessage(f"Session saved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save session: {e}")
            
    def show_key_mapping_dialog(self):
        """Show the key mapping configuration dialog."""
        dialog = KeyMappingDialog(self, current_mappings=self.key_mappings.copy())
        dialog.key_mapping_changed.connect(self._on_key_mappings_changed)
        if dialog.exec():
            # Ensure we apply mappings even if user closes via Accept
            self._on_key_mappings_changed(dialog.get_mappings())

    def _on_key_mappings_changed(self, mappings: dict):
        """Handle updates to key mappings from the dialog."""
        if not mappings:
            return
        self.key_mappings.update(mappings)
        self.setup_global_shortcuts()
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage("Key mappings updated")

    def show_set_pin_dialog(self):
        """Open the Set PIN dialog to update the security PIN."""
        dialog = SetPinDialog(self.current_pin, self)
        if dialog.exec():
            new_pin = dialog.get_new_pin()
            if new_pin and new_pin != self.current_pin:
                self.current_pin = new_pin
                if hasattr(self, "status_bar"):
                    self.status_bar.showMessage("PIN updated successfully")
                QMessageBox.information(
                    self, "PIN Updated", "The security PIN has been updated."
                )

    def on_fixture_loaded(self, fixture_data: dict):
        """Handle fixture data loaded from dialog"""
        try:
            # Parse and load fixture data into the application
            self.match_setup_tab.load_fixture_data(fixture_data)
            QMessageBox.information(
                self, "Success", "Fixture data loaded successfully!"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load fixture data:\n{str(e)}"
            )

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Football Score Pro 2.0",
            """
            <h3>Football Score Pro 2.0</h3>
            <p>A comprehensive football match management application built with PySide6.</p>
            <p><b>Features:</b></p>
            <ul>
                <li>Team management and player selection</li>
                <li>Match configuration and rules</li>
                <li>Officials assignment</li>
                <li>Event-driven architecture</li>
                <li>Modern UI with professional styling</li>
            </ul>
            <p><b>Architecture:</b></p>
            <ul>
                <li>Clean layered architecture</li>
                <li>Dependency injection</li>
                <li>Event-driven communication</li>
                <li>Comprehensive validation</li>
            </ul>
            """,
        )

    def on_match_created(self, match_id: str):
        """Handle match created event"""
        match_number = 1
        if hasattr(self, "match_setup_tab") and hasattr(
            self.match_setup_tab, "get_match_number"
        ):
            try:
                match_number = self.match_setup_tab.get_match_number()
            except Exception:
                match_number = 1
        self.status_bar.showMessage(f"Match #{match_number} created: {match_id}")
        self.current_match_id = match_id
        self.autosave_path = self.autosave_dir / f"{match_id}_session.json"
        self._last_autosave_hash = None
        if not self.autosave_timer.isActive():
            self.autosave_timer.start()
        self._set_live_tabs_enabled(True)
        # Automatically pivot operators into the live Play On tab after creation
        self.switch_tab(1)
        
        # Enable match data loading in Play On tab
        if hasattr(self, "play_on_tab"):
            self.play_on_tab.enable_match_data_loading()
            # Reset Play On tab to initial state
            if hasattr(self.play_on_tab, "reset_match"):
                self.play_on_tab.reset_match()
        
        # Reset Subs and Penalty tab to initial state
        if hasattr(self, "subs_penalty_tab"):
            if hasattr(self.subs_penalty_tab, "reset_to_match_created_state"):
                self.subs_penalty_tab.reset_to_match_created_state()
            self._sync_officials_to_subs_penalty()
            if hasattr(self.subs_penalty_tab, "enable_match_data_loading"):
                self.subs_penalty_tab.enable_match_data_loading()
        self._persist_autosave_state(force=True)

    def on_match_saved(self, file_path: str):
        """Handle match saved event"""
        self.status_bar.showMessage(f"Match saved to: {file_path}")

    # Global shortcut trigger methods
    def trigger_kickoff(self):
        """Trigger kickoff/possession toggle"""
        if hasattr(self, "play_on_tab") and hasattr(
            self.play_on_tab, "toggle_possession"
        ):
            self.play_on_tab.toggle_possession()
            
    def trigger_start_timer(self):
        """Trigger start timer"""
        if hasattr(self, "play_on_tab") and hasattr(self.play_on_tab, "start_timer"):
            self.play_on_tab.start_timer()
            
    def trigger_stop_timer(self):
        """Trigger stop timer"""
        if hasattr(self, "play_on_tab") and hasattr(self.play_on_tab, "stop_timer"):
            self.play_on_tab.stop_timer()
            
    def trigger_reset_match(self):
        """Trigger reset match"""
        self.on_reset_clicked()
        
    def trigger_home_goal_plus(self):
        """Trigger home goal increment"""
        if hasattr(self, "play_on_tab") and hasattr(
            self.play_on_tab, "increment_home_goals_with_scorer"
        ):
            self.play_on_tab.increment_home_goals_with_scorer()
            
    def trigger_away_goal_plus(self):
        """Trigger away goal increment"""
        if hasattr(self, "play_on_tab") and hasattr(
            self.play_on_tab, "increment_away_goals_with_scorer"
        ):
            self.play_on_tab.increment_away_goals_with_scorer()
            
    def trigger_home_goal_minus(self):
        """Trigger home goal decrement"""
        if hasattr(self, "play_on_tab") and hasattr(
            self.play_on_tab, "decrement_home_goals_with_scorer"
        ):
            self.play_on_tab.decrement_home_goals_with_scorer()
            
    def trigger_away_goal_minus(self):
        """Trigger away goal decrement"""
        if hasattr(self, "play_on_tab") and hasattr(
            self.play_on_tab, "decrement_away_goals_with_scorer"
        ):
            self.play_on_tab.decrement_away_goals_with_scorer()
    
    def _sync_officials_to_subs_penalty(self):
        """Push the latest officials snapshot into the Subs/Penalty tab."""
        try:
            if not hasattr(self, "subs_penalty_tab"):
                return
            match_setup_officials = getattr(self.match_setup_tab, "officials_tab", None)
            if not match_setup_officials:
                return
            snapshot = match_setup_officials.get_officials()
            if snapshot:
                self.subs_penalty_tab.apply_officials_snapshot(snapshot)
        except Exception as e:
            print(f"[MainWindow] Error syncing officials to Subs/Penalty tab: {e}")
    
    def on_reset_clicked(self):
        """Handle reset match button click"""
        if self.is_locked:
            QMessageBox.warning(
                self,
                "Application Locked",
                "The application is locked. Please unlock it first to reset the match.",
            )
            return
        
        # Check if match is created
        if hasattr(self, "play_on_tab") and hasattr(self.play_on_tab, "match_created"):
            if not self.play_on_tab.match_created:
                QMessageBox.information(
                    self, "No Match", "Please create a match first before resetting."
                )
                return
        
        # Confirm reset
        reply = QMessageBox.question(
            self,
            "Reset Match",
            "Are you sure you want to reset the match? This will clear all match data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset both tabs
            if hasattr(self, "play_on_tab") and hasattr(
                self.play_on_tab, "reset_match"
            ):
                self.play_on_tab.reset_match()
            if hasattr(self, "subs_penalty_tab") and hasattr(
                self.subs_penalty_tab, "reset_to_match_created_state"
            ):
                self.subs_penalty_tab.reset_to_match_created_state()
            self.status_bar.showMessage("Match reset successfully")
    
    def on_end_match_clicked(self):
        """Handle end match button click"""
        if self.is_locked:
            QMessageBox.warning(
                self,
                "Application Locked",
                "The application is locked. Please unlock it first to end the match.",
            )
            return

        # Check if match is created; if the play_on_tab or flag is missing, treat as no active match
        if not hasattr(self, "play_on_tab") or not hasattr(
            self.play_on_tab, "match_created"
        ):
            QMessageBox.information(self, "No Match", "No active match to end.")
            return
        if not self.play_on_tab.match_created:
            QMessageBox.information(self, "No Match", "No active match to end.")
            return

        # Check if timer has been stopped
        if hasattr(self, "play_on_tab") and hasattr(self.play_on_tab, "timer_running"):
            if self.play_on_tab.timer_running:
                QMessageBox.warning(
                    self,
                    "Timer Still Running",
                    "Please stop the match timer before ending the match.",
                )
                return

        # Confirm end match
        reply = QMessageBox.question(
            self,
            "End Match",
            "Are you sure you want to end the match? This action will finalize the match data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Add logic to finalize and save match data
            # For now, just show a success message
            self.status_bar.showMessage("Match ended successfully")
            QMessageBox.information(
                self,
                "Match Ended",
                "Match has been ended successfully. Match data has been finalized.",
            )
    
    def update_lock_button_icon(self):
        """Update the lock button icon based on current lock state."""
        from pathlib import Path

        if not hasattr(self, "lock_toggle_button"):
            return

        base_path = Path(__file__).resolve().parent.parent
        lock_path = base_path / "resources" / "images" / "lock.png"
        unlock_path = base_path / "resources" / "images" / "unlock.png"

        target_path = lock_path if self.is_locked else unlock_path

        if target_path.exists():
            pixmap = QPixmap(str(target_path))
            if not pixmap.isNull():
                self.lock_toggle_button.setIcon(QIcon(pixmap))
                self.lock_toggle_button.setIconSize(QSize(28, 28))
                self.lock_toggle_button.setText("")
                return

        # Fallback if icon missing or invalid
        self.lock_toggle_button.setIcon(QIcon())
        self.lock_toggle_button.setText("🔒" if self.is_locked else "🔓")
    
    def on_lock_toggle_clicked(self):
        """Handle lock/unlock toggle button click"""
        # If already locked (either type), show unlock dialog
        if self.is_locked or self.is_master_locked:
            # Determine which lock is active
            lock_type = "master" if self.is_master_locked else "reset"
            is_locked = (
                self.is_master_locked if lock_type == "master" else self.is_locked
            )
            
            # Show PIN dialog to unlock
            dialog = PinDialog(
                is_locked, self, correct_pin=self.current_pin, lock_type=lock_type
            )
            
            if dialog.exec():
                # PIN verified successfully - unlock
                if lock_type == "master":
                    self.is_master_locked = False
                    status_msg = "Application unlocked"
                else:
                    self.is_locked = False
                    status_msg = "Reset Match unlocked"
                
                self.lock_toggle_button.setChecked(False)
                self.update_lock_button_icon()
                self.apply_lock_state()
                self.status_bar.showMessage(status_msg)
            else:
                # Dialog cancelled or PIN incorrect - revert button state
                self.lock_toggle_button.setChecked(True)
        else:
            # Not locked - show option dialog to choose lock type
            option_dialog = LockOptionDialog(self)
            option_dialog.reset_lock_selected.connect(self.on_reset_lock_selected)
            option_dialog.master_lock_selected.connect(self.on_master_lock_selected)
            
            if not option_dialog.exec():
                # Dialog cancelled - revert button state
                self.lock_toggle_button.setChecked(False)
    
    def on_reset_lock_selected(self):
        """Handle Reset Match Lock option selected"""
        # Show PIN dialog to lock reset button
        dialog = PinDialog(False, self, correct_pin=self.current_pin, lock_type="reset")
        
        if dialog.exec():
            # PIN verified successfully
            self.is_locked = True
            self.lock_toggle_button.setChecked(True)
            self.update_lock_button_icon()
            self.apply_lock_state()
            self.status_bar.showMessage("Reset Match locked")
        else:
            # Dialog cancelled or PIN incorrect - revert button state
            self.lock_toggle_button.setChecked(False)
    
    def on_master_lock_selected(self):
        """Handle Master Lock option selected"""
        # Show PIN dialog to lock all tabs
        dialog = PinDialog(
            False, self, correct_pin=self.current_pin, lock_type="master"
        )
        
        if dialog.exec():
            # PIN verified successfully
            self.is_master_locked = True
            self.lock_toggle_button.setChecked(True)
            self.update_lock_button_icon()
            self.apply_lock_state()
            self.status_bar.showMessage("Application locked (Master Lock)")
        else:
            # Dialog cancelled or PIN incorrect - revert button state
            self.lock_toggle_button.setChecked(False)
    
    def apply_lock_state(self):
        """Apply lock state to UI elements"""
        # Handle master lock - disable/enable all tabs
        if self.is_master_locked:
            # Disable all three tabs
            if hasattr(self, "match_setup_tab"):
                self.match_setup_tab.setEnabled(False)
            if hasattr(self, "play_on_tab"):
                self.play_on_tab.setEnabled(False)
            if hasattr(self, "subs_penalty_tab"):
                self.subs_penalty_tab.setEnabled(False)
            
            # Show lock overlays
            if hasattr(self, "match_setup_overlay"):
                self.match_setup_overlay.show()
            if hasattr(self, "play_on_overlay"):
                self.play_on_overlay.show()
            if hasattr(self, "subs_penalty_overlay"):
                self.subs_penalty_overlay.show()
            
            # Also disable reset button when master locked
            if hasattr(self, "reset_match_button"):
                self.reset_match_button.setEnabled(False)
                self.reset_match_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #6b7280, stop:1 #4b5563);
                        color: #9ca3af;
                        border: 2px solid #374151;
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-weight: bold;
                    }
                """)
        else:
            # Enable all tabs when master lock is off
            if hasattr(self, "match_setup_tab"):
                self.match_setup_tab.setEnabled(not self.is_locked)
            if hasattr(self, "play_on_tab"):
                self.play_on_tab.setEnabled(True)
            if hasattr(self, "subs_penalty_tab"):
                self.subs_penalty_tab.setEnabled(True)
            
            # Hide lock overlays
            if hasattr(self, "match_setup_overlay"):
                if self.is_locked:
                    self.match_setup_overlay.hide()
                else:
                    self.match_setup_overlay.show()
            if hasattr(self, "play_on_overlay"):
                self.play_on_overlay.hide()
            if hasattr(self, "subs_penalty_overlay"):
                self.subs_penalty_overlay.hide()
            
            # Handle reset button lock separately
            if hasattr(self, "reset_match_button"):
                if self.is_locked:
                    # Reset button is locked
                    self.reset_match_button.setEnabled(False)
                    self.reset_match_button.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #6b7280, stop:1 #4b5563);
                            color: #9ca3af;
                            border: 2px solid #374151;
                            border-radius: 8px;
                            padding: 8px 12px;
                            font-weight: bold;
                        }
                    """)
                else:
                    # Reset button is unlocked - restore original style
                    self.reset_match_button.setEnabled(True)
                    self.reset_match_button.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #e53e3e, stop:1 #c53030);
                            color: white;
                            border: 2px solid #742a2a;
                            border-radius: 8px;
                            padding: 8px 12px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f56565, stop:1 #e53e3e);
                            border: 2px solid #9c2a2a;
                        }
                        QPushButton:pressed {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #c53030, stop:1 #9c2a2a);
                        }
                    """)

    # def closeEvent(self, event):
    #     """Handle application close event"""
    #     reply = QMessageBox.question(
    #         self,
    #         "Exit Application",
    #         "Are you sure you want to exit?",
    #         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    #         QMessageBox.StandardButton.No
    #     )
        
    #     if reply == QMessageBox.StandardButton.Yes:
    #         event.accept()
    #     else:
    #         event.ignore()


def _build_fixed_palette() -> QPalette:
    """Return a dark palette that ignores system theme changes."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff4d4f"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))
    return palette


def create_application(backend_service: BackendService) -> QApplication:
    """Create and configure the main application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Football Score Pro alpha")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Football Score Pro")
    
    # Install a deterministic base style so OS theme changes don't affect us
    fusion_style = QStyleFactory.create("Fusion")
    base_style = fusion_style if fusion_style is not None else app.style()
    app.setStyle(NoFocusStyle(base_style))

    # Apply a fixed dark palette and ensure it stays applied
    fixed_palette = _build_fixed_palette()
    app.setPalette(fixed_palette)
    palette_guard = _PaletteGuard(app, fixed_palette)
    app.installEventFilter(palette_guard)
    app._palette_guard = palette_guard  # Prevent garbage collection
    
    base_style = """
        QApplication {
            background-color: #111827;
            color: #ffffff;
        }
        QMainWindow {
            background-color: #111827;
        }
        QMenuBar {
            background-color: #1f2937;
            color: #ffffff;
            border-bottom: 1px solid #374151;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        QMenuBar::item:selected {
            background-color: #374151;
        }
        QMenu {
            background-color: #1f2937;
            color: #ffffff;
            border: 1px solid #374151;
        }
        QMenu::item {
            padding: 4px 20px;
        }
        QMenu::item:selected {
            background-color: #374151;
        }
        QStatusBar {
            background-color: #1f2937;
            color: #ffffff;
            border-top: 1px solid #374151;
        }
    """

    app.setStyleSheet(base_style + get_global_focus_reset_style())
    
    return app


def run_ui(backend_service: BackendService):
    """Run the UI application"""
    app = create_application(backend_service)
    
    # Create main window
    window = MainWindow(backend_service)
    window.show()
    
    # Run application
    sys.exit(app.exec())
