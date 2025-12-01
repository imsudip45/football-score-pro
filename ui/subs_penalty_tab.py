"""
Subs and Penalty Tab for Football Score Pro 2.0
Handles substitutions and penalty management during matches
"""

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsBlurEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .backend_service import BackendService
from .play_on_tab import TimeColumnDelegate

# Local color palette matching Play On (no external imports)
COLORS = {
    "background": "#1a1a1a",
    "panel": "#1e1e1e",
    "card": "#28293A",
    "border": "#374151",
    "text": "#B0B4BB",
    "button_success": "#059669",
    "hover": "#3b82f6",
}

SUB_OUT_BUTTON_STYLE = """
    QPushButton {
        background-color: #4a4a4a;
        color: #ffffff;
        border-radius: 4px;
        font-weight: 500;
    }
    QPushButton:hover { background-color: #5a5a5a; }
"""

SUB_OUT_BUTTON_SENT_OFF_STYLE = """
    QPushButton {
        background-color: #7f1d1d;
        color: #ffffff;
        border-radius: 4px;
        font-weight: 600;
    }
"""

SENT_OFF_TEXT_COLOR = "#ff4d4f"

TIME_EDITOR_STYLE = """
    QLineEdit {
        background-color: #111827;
        color: #F8FAFC;
        border: 1px solid #475569;
        border-radius: 4px;
        padding: 4px 6px;
    }
    QLineEdit:focus {
        border: 1px solid #38bdf8;
        background-color: #1f2937;
    }
"""


class AnimatedToggle(QCheckBox):
    """A simple animated toggle switch based on QCheckBox with smooth knob movement."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._offset = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"offset")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(50, 28)
        # Remove native indicator
        self.setStyleSheet(
            "QCheckBox { spacing: 8px; } QCheckBox::indicator { width:0; height:0; }"
        )
        self.stateChanged.connect(self._start_animation)

    def sizeHint(self):
        return self.minimumSize()

    def _start_animation(self, state: int):
        try:
            checked_val = int(Qt.CheckState.Checked)
        except Exception:
            checked_val = 2
        target = 1.0 if int(state) == checked_val else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(target)
        self._anim.start()

    def getOffset(self) -> float:
        return self._offset

    def setOffset(self, value: float):
        self._offset = max(0.0, min(1.0, float(value)))
        self.update()

    offset = Property(float, fget=getOffset, fset=setOffset)

    def mouseReleaseEvent(self, event):
        # Ensure click toggles even if style removes native indicator
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        radius = h / 2
        margin = 2
        knob_d = h - 2 * margin
        # Interpolate knob x from left to right
        knob_x = margin + self._offset * (w - 2 * margin - knob_d)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Background
        if self.isChecked():
            bg = QColor("#10b981")
            border = QColor("#059669")
        else:
            bg = QColor("#4b5563")
            border = QColor("#374151")

        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(0, 0, w - 1, h - 1, radius, radius)

        # Knob
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(knob_x), margin, int(knob_d), int(knob_d))


class SubsAndPenaltyTab(QWidget):
    """Tab for managing substitutions and penalties during matches"""

    # Signals
    substitution_made = Signal(dict)  # Emit when substitution is made
    penalty_awarded = Signal(dict)  # Emit when penalty is awarded
    match_data_changed = Signal(
        dict
    )  # Emit when match data changes (e.g., after substitution)

    def __init__(self, backend_service: BackendService, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service
        self.match_data = {}
        self._right_panel_buttons = {}
        # Track substituted-out players by team (jersey numbers of players who were substituted out)
        self.substituted_out_home = []  # List of jersey numbers substituted out from home team
        self.substituted_out_away = []  # List of jersey numbers substituted out from away team
        # Track players who entered as substitutes so Select Out popup can highlight them
        self.substituted_in_home = []
        self.substituted_in_away = []
        # Track players sent off (red cards) so they can't be substituted
        self.sent_off_home_players = set()
        self.sent_off_away_players = set()
        self.match_created = False  # Gate match data loading until match is created
        self._pending_match_data = None
        self.setup_ui()
        # Listen for officials assignment updates to reflect on right panel
        try:
            self.backend_service.officials_assigned.connect(self._on_officials_assigned)
        except Exception:
            pass

    def setup_ui(self):
        """Setup the main UI with 5 sections layout"""
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
        """)

        # Main layout - grid layout for 5 sections
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left column: Home Substitution Panel (row 0)
        self.home_subs_panel = self.create_substitution_panel("Home Team")
        main_layout.addWidget(self.home_subs_panel, 0, 0)

        # Center column: Away Substitution Panel (row 0)
        self.away_subs_panel = self.create_substitution_panel("Away Team")
        main_layout.addWidget(self.away_subs_panel, 0, 1)

        # Row 1: Home Cards Panel (layout-based replica to render correctly in layouts)
        self.home_scorer_panel = self.create_cards_panel_layout("Home Team")
        main_layout.addWidget(self.home_scorer_panel, 1, 0)

        # Row 1: Away Cards Panel (layout-based replica to render correctly in layouts)
        self.away_scorer_panel = self.create_cards_panel_layout("Away Team")
        main_layout.addWidget(self.away_scorer_panel, 1, 1)

        # Section 5: Right side panel (placeholder for now)
        self.right_panel = self.create_right_panel()
        main_layout.addWidget(self.right_panel, 0, 2, 2, 1)  # Spans both rows

        # Set column proportions: Left=3, Center=3, Right=2 (wider for substitution panels)
        # Match old app: no column minimum widths set - let panels handle their own sizing
        main_layout.setColumnStretch(0, 3)
        main_layout.setColumnStretch(1, 3)
        main_layout.setColumnStretch(2, 2)

        # Ensure penalty panels start locked by default
        try:
            print(
                "[SubsAndPenaltyTab] Initializing: applying default penalty lock: unlocked=False"
            )
            self._apply_penalty_lock(False)
        except Exception:
            pass

    def showEvent(self, event):
        """Handle show event - Qt will handle layout automatically"""
        super().showEvent(event)
        # Re-apply lock state on show to avoid any late widget enabling
        try:
            current = getattr(self, "penalty_unlock_toggle", None)
            unlocked = bool(current.isChecked()) if current else False
            print(
                f"[SubsAndPenaltyTab] showEvent: toggle is_checked={unlocked} -> applying lock"
            )
            self._apply_penalty_lock(unlocked)
        except Exception:
            pass

    def enable_match_data_loading(self):
        """Allow match data to start flowing after match creation."""
        self.match_created = True
        print("[SubsAndPenaltyTab] Match creation gate opened - data loading enabled")
        pending = getattr(self, "_pending_match_data", None)
        if pending:
            self._pending_match_data = None
            self.load_match_data(pending)

    def reset_to_match_created_state(self):
        """Reset all panels to clean state right after match creation."""
        try:
            self.match_created = False

            # Helper to clear a QTableWidget inside a panel by objectName if present
            def clear_tables_in(panel: QWidget):
                try:
                    tables = panel.findChildren(QTableWidget)
                    for t in tables:
                        t.setRowCount(0)
                except Exception:
                    pass

            # Clear substitution and cards tables for both teams
            if hasattr(self, "home_subs_panel"):
                clear_tables_in(self.home_subs_panel)
            if hasattr(self, "away_subs_panel"):
                clear_tables_in(self.away_subs_panel)
            if hasattr(self, "home_scorer_panel"):
                clear_tables_in(self.home_scorer_panel)
            if hasattr(self, "away_scorer_panel"):
                clear_tables_in(self.away_scorer_panel)

            # Reset any internal selections/state
            try:
                self.home_selected_rows = []
                self.away_selected_rows = []
            except Exception:
                pass

            # Reset substituted-out tracking
            self.substituted_out_home = []
            self.substituted_out_away = []
            self.substituted_in_home = []
            self.substituted_in_away = []
            self.sent_off_home_players.clear()
            self.sent_off_away_players.clear()

            # Note: match_data will be reloaded when match_data_changed signal is emitted after reset
        except Exception as e:
            print(f"Error in reset_to_match_created_state: {e}")

    def create_substitution_panel(self, team_name):
        """Create substitution panel based on Substituted.py design"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        # Match old app: fixed minimum width prevents layout issues
        panel.setMinimumWidth(600)  # Same as old app - prevents overflow
        panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252525, stop:1 #1a1a1a);
                border: 2px solid #404040;

            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Team label with deploy button in top-right
        team_label_container = QFrame()
        team_label_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #404040;
            }
        """)
        team_label_layout = QHBoxLayout(team_label_container)
        team_label_layout.setContentsMargins(8, 8, 8, 8)

        # Team name with substitutions label - store reference for dynamic updates
        if "Home" in team_name:
            title_text = "HOME TEAM SUBSTITUTIONS"
        else:
            title_text = "AWAY TEAM SUBSTITUTIONS"

        team_label = QLabel(title_text)
        team_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        team_label.setStyleSheet("""
            QLabel {
                color: #B0B4BB;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        # Store reference to team label for dynamic updates
        if "Home" in team_name:
            self.home_substitution_label = team_label
        else:
            self.away_substitution_label = team_label
        # Add + button (left side)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 24)
        add_btn.setFont(QFont("Verdana", 12, QFont.Weight.ExtraBold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: white;
                border: 1px solid #2d3748;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6578;
            }
        """)
        add_btn.clicked.connect(lambda: self.add_substitution_row(team_name))
        team_label_layout.addWidget(add_btn)

        team_label_layout.addStretch()
        team_label_layout.addWidget(team_label)
        team_label_layout.addStretch()

        # Deploy button in top-right corner
        deploy_btn = QPushButton("DEPLOY")
        deploy_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        deploy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }
        """)
        deploy_btn.clicked.connect(lambda: self.deploy_substitutions(team_name))
        team_label_layout.addWidget(deploy_btn)

        layout.addWidget(team_label_container)

        # Substitution table
        sub_table = QTableWidget()
        sub_table.setRowCount(0)
        sub_table.setColumnCount(8)
        sub_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: #B0B4BB;
                font-family: "Verdana";
                font-size: 10px;
                border: 1px solid gray;
                border-radius: 5px;
                gridline-color: #3a4251;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                font-weight: bold;
                border: 1px solid gray;
                color: #8b8b8f;
                padding: 4px;
            }
            QTableWidget::item {
                border: 0px solid gray;
                border-bottom: 1px solid #272c39;
                border-right: 1px solid #272c39;
                padding: 2px;
            }
        """)
        # Configure header to control column resizing (match old app behavior)
        header = sub_table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Fixed)

        # Use fixed widths for ALL columns (like old app) - no stretch columns
        # Adjusted for 8 columns to fit within panel: 50 + 60 + 140 + 60 + 140 + 60 + 50 + 50 = 610px
        # This allows some margin within the 600px minimum panel width
        sub_table.setColumnWidth(0, 85)  # Time
        sub_table.setColumnWidth(1, 63)  # Num Out
        sub_table.setColumnWidth(2, 167)  # Player Out (fixed, wider)
        sub_table.setColumnWidth(3, 60)  # Num In
        sub_table.setColumnWidth(4, 167)  # Player In (fixed, wider)
        sub_table.setColumnWidth(5, 50)  # Export
        sub_table.setColumnWidth(6, 40)  # Lock
        sub_table.setColumnWidth(7, 42)  # Reset

        # Don't set explicit resize modes - use defaults (like old app)
        # This allows natural table behavior without stretch column calculations

        # Allow scrolling if needed (like old app) - don't force ScrollBarAlwaysOff
        # This prevents overflow issues when table width exceeds panel width
        sub_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sub_table.verticalHeader().setVisible(False)
        sub_table.horizontalHeader().setVisible(True)
        sub_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        # Disable selection highlighting
        sub_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        sub_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Set header labels
        header_labels = [
            "Time",
            "Num Out",
            "Player Out",
            "Num In",
            "Player In",
            "Export",
            "Lock",
            "Reset",
        ]
        sub_table.setHorizontalHeaderLabels(header_labels)

        # Apply colors to header items
        for col, label in enumerate(header_labels):
            item = sub_table.horizontalHeaderItem(col)
            if item:
                item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                if label == "Player Out":
                    item.setForeground(QColor("#CC0000"))
                elif label == "Player In":
                    item.setForeground(QColor("#00FF00"))
                else:
                    item.setForeground(QColor("#B0B4BB"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set custom delegate for time column to set border-radius to 0
        # Import shared TimeColumnDelegate from play_on_tab

        time_delegate = TimeColumnDelegate()
        sub_table.setItemDelegateForColumn(0, time_delegate)

        # Connect header click to toggle Export and Lock columns
        sub_table.horizontalHeader().sectionClicked.connect(
            lambda col, table=sub_table: self.on_substitution_header_clicked(table, col)
        )

        # Substitution table starts empty - rows will be added via + button

        layout.addWidget(sub_table)

        # Store references for later use
        panel.team_name = team_name
        panel.sub_table = sub_table
        panel.deploy_btn = deploy_btn

        # Expose team tables for handlers
        if "Home" in team_name:
            self.home_sub_table = sub_table
        else:
            self.away_sub_table = sub_table

        return panel

    def create_right_panel(self) -> QWidget:
        """Create the right-side panel with grouped green buttons mirroring Officials tab data."""
        from PySide6.QtWidgets import QGridLayout, QGroupBox, QSizePolicy, QVBoxLayout

        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        panel.setStyleSheet("""
            QFrame { background-color: transparent; border: 1px solid #374151; border-radius: 4px; }
            QLabel { color: #B0B4BB; font-weight: bold; }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top-right toggle row: Unlock Penalty Panels
        top_section = QFrame()
        top_section.setStyleSheet("""
            QFrame {
                border: 1px solid #374151;
                border-radius: 6px;
                background: transparent;
            }
        """)
        top_row = QHBoxLayout(top_section)
        top_row.setContentsMargins(12, 8, 12, 8)
        top_row.setSpacing(8)

        # Timer label (moved from main window header)
        self.play_time_label = QLabel("00:00")
        self.play_time_label.setFont(QFont("Verdana", 14, QFont.Weight.Normal))
        self.play_time_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 4px 10px;
                border: none;
                border-radius: 6px;
            }
            """
        )
        top_row.addWidget(self.play_time_label)
        top_row.addStretch(1)

        toggle_label = QLabel("Penalty On/Off")
        toggle_label.setStyleSheet(
            "color: #B0B4BB; font-weight: 700; font-size: 19px; background: transparent; border: none;"
        )
        toggle_label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.penalty_unlock_toggle = AnimatedToggle()
        self.penalty_unlock_toggle.setChecked(False)
        self.penalty_unlock_toggle.setToolTip(
            "Toggle to allow editing in Penalty panels"
        )
        self.penalty_unlock_toggle.stateChanged.connect(self._on_penalty_unlock_toggled)

        # Make label clickable to toggle as well
        def _label_click(_event):
            try:
                self.penalty_unlock_toggle.toggle()
            except Exception:
                pass

        toggle_label.mousePressEvent = _label_click

        top_row.addWidget(toggle_label)
        top_row.addWidget(self.penalty_unlock_toggle)

        layout.addWidget(top_section)
        layout.addSpacing(20)

        def make_section(
            title: str,
            keys: list[str],
            columns: int,
            override_labels: dict[str, str] | None = None,
        ) -> QGroupBox:
            box = QGroupBox(title)
            box.setStyleSheet("""
                QGroupBox {
                    color: #B0B4BB;
                    border: none;
                border-radius: 4px;
                    margin-top: 12px;
                    font-weight: bold;
                font-size: 14px;
                    background: transparent;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    top: 0px;
                    padding: 0 6px;
                    background: transparent;
                    font-weight: bold;
                    font-size: 14px;
            }
        """)
            box.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            box.setMinimumWidth(0)
            box.setMaximumWidth(16777215)
            grid = QGridLayout(box)
            grid.setContentsMargins(8, 12, 8, 8)
            grid.setSpacing(6)

            # Make all columns share available width equally
            for c in range(max(1, columns)):
                grid.setColumnStretch(c, 1)

            # Pre-compute number of rows for stretch distribution
            total = len(keys)
            rows = (total + columns - 1) // columns if columns > 0 else total

            for idx, key in enumerate(keys):
                display_text = (
                    override_labels.get(key, key.replace("_", " ").title())
                    if override_labels
                    else key.replace("_", " ").title()
                )
                btn = QPushButton(display_text)
                btn.setMinimumHeight(36)
                btn.setMinimumWidth(0)
                btn.setSizePolicy(
                    QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
                )
                btn.setStyleSheet(
                    """
                    QPushButton { background-color: #6b7280; color: #ffffff; border: 1px solid #4b5563; border-radius: 4px; font-weight: 600; }
                    QPushButton:hover { background-color: #4b5563; }
                    """
                )
                row = idx // columns
                col = idx % columns
                if override_labels and key in override_labels:
                    wrapper = QWidget()
                    wrapper.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                    )
                    wrapper_layout = QVBoxLayout(wrapper)
                    wrapper_layout.setContentsMargins(0, 0, 0, 0)
                    wrapper_layout.setSpacing(4)
                    label = QLabel(override_labels[key])
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    label.setStyleSheet(
                        "QLabel { border: none; color: #B0B4BB; font-weight: 600; }"
                    )
                    wrapper_layout.addWidget(label)
                    wrapper_layout.addWidget(btn)
                    grid.addWidget(wrapper, row, col)
                    self._right_panel_buttons[key] = btn
                else:
                    grid.addWidget(btn, row, col)
                    self._right_panel_buttons[key] = btn
            # Distribute extra vertical space evenly across rows
            for r in range(max(1, rows)):
                grid.setRowStretch(r, 1)
            return box

        # Sections and keys based on Officials tab expectations
        self._official_label_map = {
            "referee": "Refree",
            "linesman_1": "Linesman1",
            "linesman_2": "Linesman2",
            "fourth_official": "Fourth Official ",
        }
        officials_keys = list(self._official_label_map.keys())
        guests_keys = [f"guest{i}" for i in range(1, 7)]
        hosts_keys = [f"host{i}" for i in range(1, 7)]
        organizers_keys = [f"organizer{i}" for i in range(1, 7)]
        commentators_keys = [f"commentator{i}" for i in range(1, 7)]

        officials_box = make_section(
            "OFFICIALS",
            officials_keys,
            columns=2,
            override_labels=self._official_label_map,
        )
        guests_box = make_section("GUESTS", guests_keys, columns=3)
        hosts_box = make_section("HOSTS", hosts_keys, columns=3)
        organizers_box = make_section("ORGANIZERS", organizers_keys, columns=3)
        commentators_box = make_section("COMMENTATORS", commentators_keys, columns=3)

        scroll_container = QScrollArea()
        scroll_container.setWidgetResizable(True)
        scroll_container.setFrameShape(QScrollArea.NoFrame)
        scroll_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_container.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 20, 0, 0)
        scroll_layout.setSpacing(20)

        sections = [
            officials_box,
            commentators_box,
            guests_box,
            organizers_box,
            hosts_box,
        ]

        for idx, section in enumerate(sections):
            scroll_layout.addWidget(section)
            scroll_layout.setStretch(idx, 1)
            separator = QWidget()
            separator.setFixedHeight(6)
            scroll_layout.addWidget(separator)
        scroll_layout.addStretch(2)

        scroll_container.setWidget(scroll_widget)
        layout.addWidget(scroll_container)
        return panel

    def _on_penalty_unlock_toggled(self, state: int):
        """Enable/disable penalty panels based on toggle state."""
        try:
            checked_val = int(Qt.CheckState.Checked)
        except Exception:
            checked_val = 2  # Fallback
        unlocked = int(state) == checked_val
        print(
            f"[SubsAndPenaltyTab] Toggle changed: state={state} checked_val={checked_val} unlocked={unlocked}"
        )
        self._apply_penalty_lock(unlocked)

    def _apply_penalty_lock(self, unlocked: bool):
        """Lock/unlock penalty controls. Disable entire penalty (scorer) panels and their main interactive buttons."""
        try:
            # 1) Disable entire panels for a clear lock
            for panel_attr in ("home_scorer_panel", "away_scorer_panel"):
                pnl = getattr(self, panel_attr, None)
                if pnl is None:
                    print(f"[SubsAndPenaltyTab] Panel {panel_attr} not found (None)")
                    continue

                print(
                    f"[SubsAndPenaltyTab] Setting panel {panel_attr}.enabled={unlocked}"
                )
                pnl.setEnabled(unlocked)

                # Manage blur effect
                old_eff = getattr(pnl, "_lock_blur_effect", None)
                if not unlocked:
                    if old_eff is None:
                        eff = QGraphicsBlurEffect(pnl)
                        eff.setBlurRadius(3)
                        setattr(pnl, "_lock_blur_effect", eff)
                    pnl.setGraphicsEffect(getattr(pnl, "_lock_blur_effect"))
                else:
                    if old_eff is not None:
                        pnl.setGraphicsEffect(None)
                        setattr(pnl, "_lock_blur_effect", None)

                # Manage overlay label
                overlay = getattr(pnl, "_lock_overlay_label", None)
                if not unlocked:
                    if overlay is None:
                        overlay = QLabel("LOCKED", pnl)
                        overlay.setObjectName("penaltyLockOverlay")
                        overlay.setAlignment(Qt.AlignCenter)
                        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                        overlay.setStyleSheet("""
                            QLabel {
                                color: #f87171;
                                font: 900 28px "Verdana";
                                background-color: rgba(15, 15, 15, 180);
                                border: 2px solid #f87171;
                                border-radius: 10px;
                                padding: 12px 24px;
                                letter-spacing: 4px;
                            }
                        """)
                        setattr(pnl, "_lock_overlay_label", overlay)
                        if not getattr(pnl, "_lock_overlay_filter", False):
                            pnl.installEventFilter(self)
                            setattr(pnl, "_lock_overlay_filter", True)
                    overlay.setGeometry(pnl.rect())
                    overlay.show()
                    overlay.raise_()
                else:
                    if overlay is not None:
                        overlay.hide()

            # 2) Also explicitly enable/disable key widgets inside tables
            for table_attr in ("home_scorer_table", "away_scorer_table"):
                tbl = getattr(self, table_attr, None)
                if tbl is None:
                    print(f"[SubsAndPenaltyTab] Table {table_attr} not found (None)")
                    continue
                rows = tbl.rowCount()
                print(
                    f"[SubsAndPenaltyTab] Updating table {table_attr}: rows={rows}, unlocked={unlocked}"
                )
                for r in range(rows):
                    # Select Player button in column 2
                    w = tbl.cellWidget(r, 2)
                    if w:
                        w.setEnabled(unlocked)
                    # Deploy button in column 3
                    d = tbl.cellWidget(r, 3)
                    if d:
                        d.setEnabled(unlocked)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Ensure lock overlays track panel resize."""
        try:
            if event.type() == QEvent.Resize:
                overlay = getattr(obj, "_lock_overlay_label", None)
                if overlay is not None and overlay.isVisible():
                    overlay.setGeometry(obj.rect())
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _on_officials_assigned(self, event):
        """Handle OfficialsAssignedEvent to update right panel buttons text if possible."""
        try:
            officials = getattr(event, "officials", None)
            if isinstance(officials, dict):
                self.apply_officials_snapshot(officials)
        except Exception:
            pass

    def apply_officials_snapshot(self, officials: dict):
        """Public method to set button texts from an officials snapshot (from Officials tab)."""
        if not officials:
            return
        # Basic officials
        mapping = {
            "referee": officials.get("referee"),
            "linesman_1": officials.get("linesman_1"),
            "linesman_2": officials.get("linesman_2"),
            "fourth_official": officials.get("fourth_official"),
        }
        # Hosts
        hosts = officials.get("hosts", []) or []
        for i in range(6):
            mapping[f"host{i + 1}"] = hosts[i] if i < len(hosts) else None
        # Commentators
        commentators_1st = officials.get("commentators_1st", []) or []
        commentators_2nd = officials.get("commentators_2nd", []) or []
        all_commentators = list(commentators_1st) + list(commentators_2nd)
        for i in range(6):
            mapping[f"commentator{i + 1}"] = (
                all_commentators[i] if i < len(all_commentators) else None
            )
        # Organizers
        organizers = officials.get("organizers", []) or []
        for i in range(6):
            mapping[f"organizer{i + 1}"] = (
                organizers[i] if i < len(organizers) else None
            )
        # Guests (dict format expected: guest1..guest6 with full_name)
        guests = officials.get("guests", {}) or {}
        for i in range(6):
            g = guests.get(f"guest{i + 1}", {}) or {}
            name = g.get("full_name") or g.get("name") or None
            mapping[f"guest{i + 1}"] = name

        # Apply to buttons
        for key, value in mapping.items():
            btn = self._right_panel_buttons.get(key)
            if btn is None:
                continue
            if value and isinstance(value, str) and value.strip():
                display_text = value.strip()
                if key.startswith("organizer") and "(" in display_text:
                    display_text = display_text.split("(", 1)[0].strip()
                btn.setText(display_text)
            else:
                # Reset to default label if no value
                if key.startswith("guest"):
                    btn.setText(key.replace("guest", "Guest "))
                elif key.startswith("host"):
                    btn.setText(key.replace("host", "Host "))
                elif key.startswith("commentator"):
                    btn.setText(key.replace("commentator", "Commentator "))
                elif key.startswith("organizer"):
                    btn.setText(key.replace("organizer", "Organizer "))
                elif key in self._official_label_map:
                    btn.setText(self._official_label_map[key])
                else:
                    btn.setText(key.replace("_", " ").title())

    def toggle_scorer_row_lock(self, table: QTableWidget, row: int, state: int):
        try:
            is_locked = state == Qt.CheckState.Checked.value
            for col in [0, 1]:
                item = table.item(row, col)
                if item:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable
                        if is_locked
                        else (Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    )
            for col in [2, 3, 5]:
                w = table.cellWidget(row, col)
                if w:
                    w.setEnabled(not is_locked)
        except Exception:
            pass

    def reset_scorer_row(self, table: QTableWidget, row: int):
        try:
            # Preserve time - don't reset it
            # Reset other data
            n_item = table.item(row, 1)
            if n_item:
                n_item.setText("")
                n_item.setTextAlignment(Qt.AlignCenter)
                n_item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )

            # Reset name button
            name_btn = table.cellWidget(row, 2)
            if name_btn:
                name_btn.setText("Select Player")

            # Reset lock checkbox
            lock_widget = table.cellWidget(row, 4)
            if lock_widget:
                from PySide6.QtWidgets import QCheckBox

                lock_cb = lock_widget.findChild(QCheckBox)
                if lock_cb:
                    lock_cb.setChecked(False)
                    lock_cb.setEnabled(False)

            # Delete all rows below this one
            total_rows = table.rowCount()
            for r in range(row + 1, total_rows):
                table.removeRow(row + 1)  # Always remove row + 1 since rows shift up

        except Exception as e:
            print(f"Error in reset_scorer_row: {e}")
            import traceback

            traceback.print_exc()

    def show_scorer_player_list(self, table: QTableWidget, row: int, team_type: str):
        """Simple player chooser that fills Name and Num, enables Lock, and shows row."""
        try:
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QMessageBox,
                QPushButton,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"Select Player for {'Home' if team_type == 'home' else 'Away'} Scorer"
            )
            dialog.setStyleSheet(f"""
                QDialog {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {COLORS["card"]}, stop:1 {COLORS["panel"]});
                    color: {COLORS["text"]};
            }}
        """)
            dialog.setFixedSize(450, 600)

            layout = QVBoxLayout(dialog)
            player_table = QTableWidget(dialog)
            player_table.setColumnCount(2)
            player_table.setHorizontalHeaderLabels(["Player Name", "Number"])
            player_table.verticalHeader().setVisible(False)
            player_table.setStyleSheet(
                f"""
                QTableWidget {{
                    background: transparent;
                    border: 1px solid {COLORS["border"]};
                    gridline-color: {COLORS["border"]};
                    selection-background-color: #22c55e;
                    selection-color: #000000;
                    font-size: 14px;
                }}
                QHeaderView::section {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    color: #10b981;
                    padding: 8px 6px;
                    border: 1px solid {COLORS["border"]};
                    font-weight: 700;
                    font-size: 14px;
                }}
                QTableWidget::item {{
                    padding: 6px 4px;
                    border-bottom: 1px solid {COLORS["border"]};
                }}
                QTableWidget::item:selected {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white;
                font-weight: bold;
                }}
                """
            )
            # reasonable column widths
            header = player_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            player_table.setColumnWidth(1, 100)
            layout.addWidget(player_table)

            team = (self.match_data or {}).get(
                "team_a" if team_type == "home" else "team_b", {}
            )
            players = team.get("players", [])
            player_table.setRowCount(len(players))
            for i, p in enumerate(players):
                name = p.get("full_name") or p.get("player_fullname", "")
                num = str(p.get("jersey_number") or p.get("jersey_no") or "")
                player_table.setItem(i, 0, QTableWidgetItem(name))
                n = QTableWidgetItem(num)
                n.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                player_table.setItem(i, 1, n)

            def on_select():
                r = player_table.currentRow()
                if r < 0:
                    QMessageBox.warning(self, "No Selection", "Select a player.")
                    return
                name = player_table.item(r, 0).text()
                num = player_table.item(r, 1).text()
                name_btn = table.cellWidget(row, 2)
                if name_btn:
                    name_btn.setText(name)
                num_item = table.item(row, 1)
                if num_item:
                    num_item.setText(num)
                    num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # enable lock
                w = table.cellWidget(row, 4)
                if w:
                    from PySide6.QtWidgets import QCheckBox

                    cb = w.findChild(QCheckBox)
                    if cb:
                        cb.setEnabled(True)
                table.showRow(row)
                dialog.accept()

            btns = QHBoxLayout()
            ok = QPushButton("OK")
            ok.setFont(QFont("Verdana", 14))
            ok.setFixedHeight(44)
            ok.setMinimumWidth(120)
            ok.setStyleSheet("""
            QPushButton {
                    background-color: #4CAF50;
                    color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                    background-color: #45a049;
            }
        """)
            ok.clicked.connect(on_select)

            cancel = QPushButton("Cancel")
            cancel.setFont(QFont("Verdana", 14))
            cancel.setFixedHeight(44)
            cancel.setMinimumWidth(120)
            cancel.setStyleSheet("""
            QPushButton {
                    background-color: #f44336;
                    color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            cancel.clicked.connect(dialog.reject)

            btns.addWidget(ok)
            btns.addWidget(cancel)
            layout.addLayout(btns)
            dialog.exec()
        except Exception:
            pass

    def create_cards_panel(self, team_name):
        """Legacy geometry-based panel removed; reuse layout version."""
        return self.create_cards_panel_layout(team_name)

    def create_cards_panel_layout(self, team_name):
        """Layout-based cards panel for use inside layouts (exact look/function)."""
        outer = QFrame()
        outer.setFrameStyle(QFrame.Box)
        outer.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252525, stop:1 #1a1a1a);
                border: 2px solid #404040;

            }
        """)
        v = QVBoxLayout(outer)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        # Title row with Deploy - create a common container
        title_container = QFrame()
        title_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #404040;
            }
        """)
        title_row = QHBoxLayout(title_container)
        title_row.setContentsMargins(8, 8, 8, 8)
        title_container.setMinimumHeight(52)

        # Title - store reference for dynamic updates (penalty panels)
        title = QLabel("HOME PENALTY" if "Home" in team_name else "AWAY PENALTY")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #B0B4BB;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        # Store reference to title label for dynamic updates (penalty panels)
        if "Home" in team_name:
            self.home_penalty_label = title
        else:
            self.away_penalty_label = title
        deploy_btn = QPushButton("DEPLOY")
        deploy_btn.setFixedHeight(24)
        deploy_btn.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        deploy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38a169, stop:1 #2f855a);
                color: white;
                border: 2px solid #276749;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #48bb78, stop:1 #38a169);
                border: 2px solid #2f855a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2f855a, stop:1 #276749);
            }
        """)
        # Add + button (left side)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 24)
        add_btn.setFont(QFont("Verdana", 12, QFont.Weight.ExtraBold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: white;
                border: 1px solid #2d3748;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6578;
            }
        """)
        # Connect the click after the table is created (below)

        title_row.addWidget(add_btn, 0)
        title_row.addWidget(title, 1)
        title_row.addWidget(deploy_btn, 0)
        v.addWidget(title_container)

        # Table
        table = QTableWidget()
        table.setRowCount(0)
        table.setColumnCount(6)
        headers = ["Num", "Name", "Goal", "Missed", "Lock", "Reset"]
        table.setHorizontalHeaderLabels(headers)
        table.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; color: {COLORS["text"]}; font-family: 'Verdana'; font-size: 10px; border: 1px solid gray; border-radius: 5px; gridline-color: {COLORS["border"]}; }}
            QHeaderView::section {{ background-color: #1e1e1e;color: #8b8b8f; font-weight: bold; border: 1px solid gray; padding: 4px; min-height: 45px; }}
            QTableWidget::item {{ border: 0px; padding: 2px; }}
        """)
        table.setFrameShape(QFrame.NoFrame)
        table.setShowGrid(True)
        # Base widths (minima) so columns render properly
        table.setColumnWidth(0, 58)  # Num
        table.setColumnWidth(1, 240)  # Name
        table.setColumnWidth(2, 40)  # Goal (reduced width)
        table.setColumnWidth(3, 50)  # Missed
        table.setColumnWidth(4, 40)  # Lock
        table.setColumnWidth(5, 40)  # Reset
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Disable selection highlighting
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(1)
        header.setDefaultSectionSize(10)
        header.setFixedHeight(37)
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        try:
            header.setTextElideMode(Qt.ElideNone)
        except Exception:
            pass

        # Make the Name column (col 1) stretch to occupy remaining free width

        header.setSectionResizeMode(1, QHeaderView.Stretch)
        # Keep small/checkbox columns sized to content so they don't grow large
        for c in [0, 2, 3, 4, 5, 6]:
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        # Color Goal/Miss headers and keep all header texts centered
        for i, label in enumerate(headers):
            item = table.horizontalHeaderItem(i)
            if not item:
                continue
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if label == "Goal":
                item.setForeground(QColor("#00FF00"))  # Green
            elif label == "Missed":
                item.setForeground(QColor("#FF0000"))  # Red

        # Connect header click to toggle Lock column only
        header.sectionClicked.connect(
            lambda col, tbl=table: self.on_penalty_header_clicked(tbl, col)
        )

        # Penalty table starts empty - rows will be added via + button

        # Connect deploy and store penalty table references
        if "Home" in team_name:
            self.home_penalty_table = table
            deploy_btn.clicked.connect(
                lambda: self.deploy_selected_cards(self.home_penalty_table, "home")
            )
        else:
            self.away_penalty_table = table
            deploy_btn.clicked.connect(
                lambda: self.deploy_selected_cards(self.away_penalty_table, "away")
            )

        v.addWidget(table)

        # Now that table exists, wire + button to add rows to this specific table
        add_btn.clicked.connect(
            lambda checked=False, t=table: self.add_penalty_row_for_table(t)
        )
        return outer

    # ===== Cards behavior (ported from Play On) =====
    def show_card_player_list(self, table, row, team_type):
        try:
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QMessageBox,
                QPushButton,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
            )

            if not getattr(self, "match_created", False):
                QMessageBox.warning(
                    self,
                    "Match Not Created",
                    "Please create the match before selecting players.",
                )
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"Select Player for {'Home' if team_type == 'home' else 'Away'} Team"
            )
            dialog.setStyleSheet(f"""
                QDialog {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {COLORS["card"]}, stop:1 {COLORS["panel"]});
                    color: {COLORS["text"]};
                }}
            """)
            # Wider/taller to accommodate Goals/Missed columns and totals row when used for penalties
            dialog.setFixedSize(620, 720)

            layout = QVBoxLayout(dialog)

            # Detect if this popup is being used for penalty tables (7 columns)
            is_penalty_popup = table.columnCount() == 7

            player_table = QTableWidget(dialog)
            if is_penalty_popup:
                player_table.setColumnCount(5)
                player_table.setHorizontalHeaderLabels(
                    ["Name", "Number", "Position", "Goals", "Missed"]
                )
            else:
                player_table.setColumnCount(3)
                player_table.setHorizontalHeaderLabels(["Name", "Number", "Position"])
            player_table.verticalHeader().setVisible(False)
            player_table.setStyleSheet(
                f"""
                QTableWidget {{
                    background: transparent;
                    border: 1px solid {COLORS["border"]};
                    gridline-color: {COLORS["border"]};
                    selection-background-color: #22c55e;
                    selection-color: #000000;
                    font-size: 14px;
                }}
                QHeaderView::section {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    color: #10b981;
                    padding: 8px 6px;
                    border: 1px solid {COLORS["border"]};
                    font-weight: 700;
                    font-size: 14px;
                }}
                QTableWidget::item {{
                    padding: 6px 4px;
                    border-bottom: 1px solid {COLORS["border"]};
                }}
                QTableWidget::item:selected {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white;
                    font-weight: bold;
                }}
                """
            )
            player_table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            player_table.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )
            # Column sizing similar to scorer popup
            header = player_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # Number
            header.setSectionResizeMode(2, QHeaderView.Fixed)  # Position
            player_table.setColumnWidth(1, 100)
            player_table.setColumnWidth(2, 120)
            if is_penalty_popup:
                # Fixed widths for Goals/Missed
                header.setSectionResizeMode(3, QHeaderView.Fixed)
                header.setSectionResizeMode(4, QHeaderView.Fixed)
                player_table.setColumnWidth(3, 70)
                player_table.setColumnWidth(4, 70)
            layout.addWidget(player_table)

            # Resolve team data from multiple possible sources/keys
            team = {}
            md = self.match_data or {}
            if team_type == "home":
                for key in ("team_a", "home_team"):
                    team = md.get(key, {})
                    if team.get("players"):
                        break
                if not team.get("players") and hasattr(self.parent(), "home_team_data"):
                    team = getattr(self.parent(), "home_team_data", {}) or {}
            else:
                for key in ("team_b", "away_team"):
                    team = md.get(key, {})
                    if team.get("players"):
                        break
                if not team.get("players") and hasattr(self.parent(), "away_team_data"):
                    team = getattr(self.parent(), "away_team_data", {}) or {}

            players = team.get("players", []) or []
            sent_off_set = (
                self.sent_off_home_players
                if team_type == "home"
                else self.sent_off_away_players
            )
            extra_total_row = 1 if is_penalty_popup else 0
            player_table.setRowCount(len(players) + extra_total_row)

            def get_val(p, *keys, default=""):
                for k in keys:
                    if k in p and p[k] not in (None, ""):
                        return p[k]
                return default

            def _count_penalties_for_jersey(jersey_no: str) -> tuple[int, int]:
                try:
                    goals = 0
                    missed = 0
                    # Penalty table columns: Number=0, Name=1, Goal=2, Missed=3
                    rows = table.rowCount()
                    for r in range(rows):
                        num_item = table.item(r, 0)
                        num_text = num_item.text().strip() if num_item else ""
                        if num_text and jersey_no and num_text == jersey_no:
                            goal_w = table.cellWidget(r, 2)
                            miss_w = table.cellWidget(r, 3)
                            if goal_w:
                                cb = goal_w.findChild(QCheckBox)
                                if cb and cb.isChecked():
                                    goals += 1
                            if miss_w:
                                cb2 = miss_w.findChild(QCheckBox)
                                if cb2 and cb2.isChecked():
                                    missed += 1
                    return goals, missed
                except Exception:
                    return 0, 0

            total_goals = 0
            total_missed = 0

            for i, p in enumerate(players):
                name = get_val(p, "full_name", "player_fullname")
                num = str(get_val(p, "jersey_number", "jersey_no"))
                pos = get_val(p, "position")
                name_item = QTableWidgetItem(name)
                player_table.setItem(i, 0, name_item)
                item_num = QTableWidgetItem(num)
                item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                player_table.setItem(i, 1, item_num)
                item_pos = QTableWidgetItem(pos)
                item_pos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                player_table.setItem(i, 2, item_pos)
                if is_penalty_popup and num in sent_off_set:
                    warning_color = QColor(SENT_OFF_TEXT_COLOR)
                    name_item.setForeground(warning_color)
                    item_num.setForeground(warning_color)
                    item_pos.setForeground(warning_color)
                    name_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item_num.setFlags(Qt.ItemFlag.NoItemFlags)
                    item_pos.setFlags(Qt.ItemFlag.NoItemFlags)
                    tooltip = "Sent off (red card) – player cannot take penalties."
                    name_item.setToolTip(tooltip)
                    item_num.setToolTip(tooltip)
                    item_pos.setToolTip(tooltip)
                else:
                    # Check if player has yellow card
                    yellow_card_set = set()
                    try:
                        main_window = self.window()
                        if main_window and hasattr(main_window, "play_on_tab"):
                            play_on_tab = main_window.play_on_tab
                            if hasattr(play_on_tab, "yellow_card_players"):
                                normalized_team = (
                                    "home" if team_type == "home" else "away"
                                )
                                yellow_card_set = play_on_tab.yellow_card_players.get(
                                    normalized_team, set()
                                )
                    except Exception:
                        yellow_card_set = set()

                    if num in yellow_card_set:
                        # Yellow highlight for players with yellow cards
                        yellow_color = QColor("#fbbf24")  # Yellow/amber color
                        name_item.setForeground(yellow_color)
                        item_num.setForeground(yellow_color)
                        item_pos.setForeground(yellow_color)
                        name_item.setBackground(
                            QColor("#78350f")
                        )  # Dark amber background
                        item_num.setBackground(QColor("#78350f"))
                        item_pos.setBackground(QColor("#78350f"))
                        tooltip = "Yellow card — player is on a caution."
                        name_item.setToolTip(tooltip)
                        item_num.setToolTip(tooltip)
                        item_pos.setToolTip(tooltip)
                if is_penalty_popup:
                    g, m = _count_penalties_for_jersey(num)
                    total_goals += g
                    total_missed += m
                    item_g = QTableWidgetItem(str(g))
                    item_g.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_g.setForeground(QColor("#00FF00"))
                    player_table.setItem(i, 3, item_g)
                    item_m = QTableWidgetItem(str(m))
                    item_m.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_m.setForeground(QColor("#FF0000"))
                    player_table.setItem(i, 4, item_m)

            if is_penalty_popup:
                total_row = len(players)
                total_item = QTableWidgetItem("TOTAL")
                total_font = total_item.font()
                total_font.setBold(True)
                total_item.setFont(total_font)
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                player_table.setItem(total_row, 0, total_item)
                for col in (1, 2):
                    blank = QTableWidgetItem("")
                    blank.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    player_table.setItem(total_row, col, blank)
                total_g_item = QTableWidgetItem(str(total_goals))
                total_g_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                total_g_item.setFont(total_font)
                total_m_item = QTableWidgetItem(str(total_missed))
                total_m_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                total_m_item.setFont(total_font)
                player_table.setItem(total_row, 3, total_g_item)
                player_table.setItem(total_row, 4, total_m_item)

            def on_select():
                r = player_table.currentRow()
                if r < 0:
                    QMessageBox.warning(self, "No Selection", "Select a player.")
                    return
                name = player_table.item(r, 0).text()
                num = player_table.item(r, 1).text()

                # Determine table type: cards (8 cols) vs penalty (7 cols)
                is_penalty = table.columnCount() == 7
                if is_penalty:
                    name_col, num_col = 1, 0
                    enable_cols = [2, 3, 5]  # Goal, Missed, Lock
                    time_col = None
                else:
                    name_col, num_col = 2, 1
                    enable_cols = [3, 4, 6]  # Yellow, Red, Lock
                    time_col = 0

                # Update name button (handle direct QPushButton or wrapped widget)
                cell_widget = table.cellWidget(row, name_col)
                if cell_widget:
                    from PySide6.QtWidgets import QPushButton

                    if isinstance(cell_widget, QPushButton):
                        cell_widget.setText(name)
                    else:
                        btn = cell_widget.findChild(QPushButton)
                        if btn:
                            btn.setText(name)

                # Update jersey number
                num_item = table.item(row, num_col)
                if num_item:
                    num_item.setText(num)
                    num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Enable relevant checkboxes
                for c in enable_cols:
                    w = table.cellWidget(row, c)
                    if w:
                        cb = w.findChild(QCheckBox)
                        if cb:
                            cb.setEnabled(True)

                # Set time only for cards tables
                if time_col is not None:
                    t_item = table.item(row, time_col)
                    if t_item:
                        t_item.setText(self.get_current_time_text())
                # Update visibility only for cards
                if not is_penalty:
                    self.update_card_row_visibility(table, team_type)
                dialog.accept()

            btns = QHBoxLayout()
            ok = QPushButton("OK")
            ok.setFont(QFont("Verdana", 14))
            ok.setFixedHeight(44)
            ok.setMinimumWidth(120)
            ok.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
            }
        """)
            ok.clicked.connect(on_select)

            cancel = QPushButton("Cancel")
            cancel.setFont(QFont("Verdana", 14))
            cancel.setFixedHeight(44)
            cancel.setMinimumWidth(120)
            cancel.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            cancel.clicked.connect(dialog.reject)
            btns.addWidget(ok)
            btns.addWidget(cancel)
            layout.addLayout(btns)
            dialog.exec()
        except Exception as e:
            print(f"Error in show_card_player_list: {e}")

    def on_yellow_card_changed(self, state, team_type, row, table):
        try:
            from PySide6.QtCore import Qt

            if state == Qt.CheckState.Checked.value:
                # Uncheck red
                red_w = table.cellWidget(row, 4)
                if red_w:
                    red_cb = red_w.findChild(QCheckBox)
                    if red_cb and red_cb.isChecked():
                        red_cb.setChecked(False)
                self.add_new_card_row(table, team_type)
        except Exception as e:
            print(f"Error yellow change: {e}")

    def on_red_card_changed(self, state, team_type, row, table):
        try:
            from PySide6.QtCore import Qt

            if state == Qt.CheckState.Checked.value:
                # Uncheck yellow
                yellow_w = table.cellWidget(row, 3)
                if yellow_w:
                    yellow_cb = yellow_w.findChild(QCheckBox)
                    if yellow_cb and yellow_cb.isChecked():
                        yellow_cb.setChecked(False)
                self.add_new_card_row(table, team_type)
        except Exception as e:
            print(f"Error red change: {e}")

    def add_new_card_row(self, table, team_type):
        try:
            r = table.rowCount()
            table.setRowCount(r + 1)
            # Initialize identical to initialization loop
            from PySide6.QtWidgets import QCheckBox
            from PySide6.QtWidgets import QWidget as QWidgetContainer

            table.setRowHeight(r, 32)
            # Num column
            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(r, 0, num_item)

            # Name button
            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: #ffffff; border-radius: 4px; }
                QPushButton:hover { background-color: #5a5a5a; }
                QFont { color: #ffffff; }
            """)
            name_btn.clicked.connect(
                lambda checked=False, r2=r, t=team_type: self.show_card_player_list(
                    table, r2, t
                )
            )
            table.setCellWidget(r, 1, name_btn)

            # Goal/Missed/Export/Lock checkboxes (matching initial row creation)
            def _mk_cb(style):
                cb = QCheckBox()
                cb.setStyleSheet(style)
                return cb

            goal = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }"
            )
            missed = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #FF0000; border: 1px solid #B0B4BB; border-radius: 2px; }"
            )
            export = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }"
            )
            lock = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #FF0000; border: 1px solid #B0B4BB; border-radius: 2px; }"
            )
            for cb, col in [(goal, 2), (missed, 3), (export, 4), (lock, 5)]:
                w = QWidgetContainer()
                layout = QHBoxLayout(w)
                layout.addWidget(cb)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                table.setCellWidget(r, col, w)
            lock.setEnabled(False)

            # Signal connections (matching initial row creation)
            goal.stateChanged.connect(
                lambda state, r3=r, tbl=table: self.on_yellow_card_changed(
                    state, team_type, r3, tbl
                )
            )
            missed.stateChanged.connect(
                lambda state, r3=r, tbl=table: self.on_red_card_changed(
                    state, team_type, r3, tbl
                )
            )

            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet(
                "QPushButton { background-color:#f44336; color:white; border-radius:2px; } QPushButton:hover { background-color:#d32f2f; }"
            )
            reset_btn.setProperty("table", table)
            reset_btn.clicked.connect(self.on_reset_clicked)
            table.setCellWidget(r, 6, reset_btn)
        except Exception as e:
            print(f"Error add_new_card_row: {e}")

    def toggle_card_row_lock(self, table, row, state):
        try:
            is_locked = state == Qt.CheckState.Checked.value
            for col in [0, 1]:
                item = table.item(row, col)
                if item:
                    if is_locked:
                        item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    else:
                        item.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                        )
            for col in [2, 3, 4, 7]:
                w = table.cellWidget(row, col)
                if w:
                    w.setEnabled(not is_locked)
        except Exception as e:
            print(f"Error toggle_card_row_lock: {e}")

    def add_penalty_row(self, team_name):
        """Add a new row to the penalty table when + button is clicked"""
        # Find the table for this team
        table = (
            getattr(self, "home_penalty_table", None)
            if "Home" in team_name
            else getattr(self, "away_penalty_table", None)
        )
        if not table:
            print(f"DEBUG add_penalty_row: table not found for team_name={team_name}")
            return
        try:
            current_rows = table.rowCount()
            table.setRowCount(current_rows + 1)
            new_row = current_rows
            self._initialize_penalty_row(table, new_row)
            print(f"Added new penalty row for {team_name}")
        except Exception as e:
            print(f"Error in add_penalty_row: {e}")

    def add_penalty_row_for_table(self, table: QTableWidget):
        """Add a new penalty row to the specific table (used by + button)."""
        try:
            current_rows = table.rowCount()
            table.setRowCount(current_rows + 1)
            new_row = current_rows
            self._initialize_penalty_row(table, new_row)
            print("Added new penalty row via direct table ref")
        except Exception as e:
            print(f"Error in add_penalty_row_for_table: {e}")

    def _initialize_penalty_row(self, table, row):
        """Initialize a new penalty row with the same structure as existing rows"""
        try:
            # Num column
            num_item = QTableWidgetItem("")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(row, 0, num_item)

            # Name button
            name_btn = QPushButton("Select Player")
            name_btn.setFont(QFont("Verdana", 10))
            name_btn.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: #ffffff; border-radius: 4px; }
                QPushButton:hover { background-color: #5a5a5a; }
                QFont { color: #ffffff; }
            """)
            # Hook player selector for penalties (determine team by table identity)
            name_btn.clicked.connect(
                lambda checked=False, r=row, tbl=table: self.show_card_player_list(
                    tbl,
                    r,
                    "home"
                    if tbl is getattr(self, "home_penalty_table", None)
                    else "away",
                )
            )
            table.setCellWidget(row, 1, name_btn)

            # Goal/Missed/Lock checkboxes
            def _mk_cb(style):
                cb = QCheckBox()
                cb.setStyleSheet(style)
                return cb

            goal = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #10B981; border: 1px solid #059669; border-radius: 2px; }"
            )
            missed = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #FF0000; border: 1px solid #B0B4BB; border-radius: 2px; }"
            )
            lock = _mk_cb(
                "QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #B0B4BB; border-radius: 2px; } QCheckBox::indicator:checked { background-color: #FF0000; border: 1px solid #B0B4BB; border-radius: 2px; }"
            )
            for cb, col in [(goal, 2), (missed, 3), (lock, 4)]:
                w = QWidget()
                layout = QHBoxLayout(w)
                layout.addWidget(cb)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                table.setCellWidget(row, col, w)
            lock.setEnabled(False)
            goal.stateChanged.connect(
                lambda state,
                tbl=table,
                checkbox=goal: self._handle_penalty_checkbox_change(
                    tbl, checkbox, "goal", state
                )
            )
            missed.stateChanged.connect(
                lambda state,
                tbl=table,
                checkbox=missed: self._handle_penalty_checkbox_change(
                    tbl, checkbox, "missed", state
                )
            )
            lock.stateChanged.connect(
                lambda state,
                tbl=table,
                checkbox=lock: self._handle_penalty_lock_toggled(tbl, checkbox, state)
            )

            # Reset button
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet(
                "QPushButton { background-color: #f44336; color: white; border-radius: 2px; } QPushButton:hover { background-color: #d32f2f; }"
            )
            reset_btn.setProperty("table", table)
            reset_btn.clicked.connect(self.on_reset_clicked)
            table.setCellWidget(row, 5, reset_btn)

        except Exception as e:
            print(f"Error in _initialize_penalty_row: {e}")

    def reset_card_row(self, table, row):
        try:
            # Delete the entire row
            table.removeRow(row)
            print(f"Deleted penalty row {row}")

        except Exception as e:
            print(f"Error reset_card_row: {e}")

    def _find_penalty_checkbox_row(self, table: QTableWidget, checkbox: QCheckBox):
        """Find the row index for a penalty checkbox widget."""
        try:
            for row in range(table.rowCount()):
                for col in (2, 3):
                    widget = table.cellWidget(row, col)
                    if not widget:
                        continue
                    cb = widget.findChild(QCheckBox)
                    if cb is checkbox:
                        return row, col
        except Exception:
            pass
        return None, None

    def _find_penalty_lock_row(
        self, table: QTableWidget, checkbox: QCheckBox
    ) -> Optional[int]:
        """Locate the row for a penalty lock checkbox."""
        try:
            if not table or not checkbox:
                return None
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 4)
                if not widget:
                    continue
                cb = widget.findChild(QCheckBox)
                if cb is checkbox:
                    return row
        except Exception:
            pass
        return None

    def _handle_penalty_lock_toggled(
        self, table: QTableWidget, checkbox: QCheckBox, state: int
    ):
        """Route penalty lock checkbox toggles to the correct row."""
        try:
            row = self._find_penalty_lock_row(table, checkbox)
            if row is None:
                return
            self.toggle_penalty_row_lock(table, row, state)
        except Exception as exc:
            print(f"Error handling penalty lock toggle: {exc}")

    def toggle_penalty_row_lock(self, table: QTableWidget, row: int, state: int):
        """Enable/disable penalty row controls when locked."""
        try:
            is_locked = state == Qt.CheckState.Checked.value
            num_item = table.item(row, 0)
            if num_item:
                num_item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable
                    if is_locked
                    else (Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                )
            name_widget = table.cellWidget(row, 1)
            if name_widget:
                name_widget.setEnabled(not is_locked)
            for col in (2, 3):
                widget = table.cellWidget(row, col)
                if not widget:
                    continue
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setEnabled(not is_locked)
            reset_widget = table.cellWidget(row, 5)
            if reset_widget:
                reset_widget.setEnabled(not is_locked)
        except Exception as exc:
            print(f"Error toggling penalty row lock: {exc}")

    def _is_penalty_row_locked(self, table: QTableWidget, row: int) -> bool:
        """Return True when the penalty row's lock checkbox is checked."""
        try:
            if row < 0 or row >= table.rowCount():
                return False
            widget = table.cellWidget(row, 4)
            if not widget:
                return False
            cb = widget.findChild(QCheckBox)
            return bool(cb and cb.isChecked())
        except Exception:
            return False

    def _find_substitution_lock_row(
        self, table: QTableWidget, checkbox: QCheckBox
    ) -> Optional[int]:
        """Return the row index for a substitution lock checkbox."""
        try:
            if not table or not checkbox:
                return None
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 6)
                if not widget:
                    continue
                cb = widget.findChild(QCheckBox)
                if cb is checkbox:
                    return row
        except Exception:
            pass
        return None

    def _handle_substitution_lock_toggled(
        self, table: QTableWidget, checkbox: QCheckBox, state: int
    ):
        """Handle lock checkbox state changes for substitution rows."""
        try:
            row = self._find_substitution_lock_row(table, checkbox)
            if row is None:
                return
            self.toggle_row_lock(table, row, state)
        except Exception as exc:
            print(f"Error handling substitution lock toggle: {exc}")

    def _is_substitution_row_locked(self, table: QTableWidget, row: int) -> bool:
        """Return True if the substitution row's lock checkbox is checked."""
        try:
            if row < 0 or row >= table.rowCount():
                return False
            widget = table.cellWidget(row, 6)
            if not widget:
                return False
            cb = widget.findChild(QCheckBox)
            return bool(cb and cb.isChecked())
        except Exception:
            return False

    def _handle_penalty_checkbox_change(
        self, table: QTableWidget, checkbox: QCheckBox, role: str, state: int
    ):
        """Ensure goal/missed checkboxes act like radio buttons (mutually exclusive)."""
        try:
            if state != Qt.CheckState.Checked.value:
                return
            row, col = self._find_penalty_checkbox_row(table, checkbox)
            if row is None:
                return
            other_col = 3 if col == 2 else 2
            widget = table.cellWidget(row, other_col)
            if not widget:
                return
            other_cb = widget.findChild(QCheckBox)
            if other_cb and other_cb.isChecked():
                other_cb.blockSignals(True)
                other_cb.setChecked(False)
                other_cb.blockSignals(False)
        except Exception as e:
            print(f"Error handling penalty checkbox change: {e}")

    def delete_row_of_button(self, table: QTableWidget):
        """Delete the row that contains the clicked reset button (sender-based).
        For substitution tables, implements conditional reset logic:
        - If substituted-in player is in scorer/cards panels: revert substitution but keep row
        - If substituted-in player is NOT in scorer/cards panels: revert substitution and delete row
        """
        try:
            # Try to get sender; fall back to currently focused widget
            sender = self.sender() or QApplication.focusWidget()
            if sender is None:
                return

            # Scan reset column candidates from rightmost to left
            # Common reset columns by table type: scorer(5), cards(6 or 7), subs(7), penalty(6)
            candidate_cols = [7, 6, 5, 4, 3, 2, 1, 0]
            for row in range(table.rowCount()):
                for col in candidate_cols:
                    if col >= table.columnCount():
                        continue
                    w = table.cellWidget(row, col)
                    if w is None:
                        continue

                    # Check if this widget is the sender (or contains it)
                    is_sender = False
                    if w is sender:
                        is_sender = True
                    elif isinstance(w, QPushButton) and w is sender:
                        is_sender = True
                    else:
                        # Check descendants
                        descendants = w.findChildren(QPushButton)
                        for btn in descendants:
                            if btn is sender:
                                is_sender = True
                                break

                    if not is_sender:
                        continue

                    # Found the row! Now check if this is a substitution table
                    is_substitution_table = False
                    is_penalty_table = False
                    is_home = False

                    print(
                        "DEBUG delete_row_of_button: Found row",
                        row,
                        ", checking if substitution table",
                    )
                    print(
                        f"DEBUG delete_row_of_button: table.columnCount()={table.columnCount()}"
                    )

                    # Check if this is a substitution table (8 columns with specific headers)
                    if table.columnCount() == 8:
                        print(
                            "DEBUG delete_row_of_button: Table has 8 columns, checking table reference"
                        )
                        # Check if it's the home or away substitution table
                        if (
                            hasattr(self, "home_sub_table")
                            and table is self.home_sub_table
                        ):
                            is_substitution_table = True
                            is_home = True
                            print(
                                "DEBUG delete_row_of_button: Identified as HOME substitution table"
                            )
                        elif (
                            hasattr(self, "away_sub_table")
                            and table is self.away_sub_table
                        ):
                            is_substitution_table = True
                            is_home = False
                            print(
                                "DEBUG delete_row_of_button: Identified as AWAY substitution table"
                            )
                        else:
                            print(
                                "DEBUG delete_row_of_button: 8 columns but not a known substitution table"
                            )

                    if table.columnCount() == 7:
                        if (
                            hasattr(self, "home_penalty_table")
                            and table is self.home_penalty_table
                        ):
                            is_penalty_table = True
                        elif (
                            hasattr(self, "away_penalty_table")
                            and table is self.away_penalty_table
                        ):
                            is_penalty_table = True

                    # If this is a substitution table, apply conditional reset logic
                    if is_substitution_table:
                        if self._is_substitution_row_locked(table, row):
                            QMessageBox.warning(
                                self,
                                "Row Locked",
                                "This substitution row is locked. Unlock it before resetting.",
                            )
                            return
                        print(
                            f"DEBUG delete_row_of_button: Applying substitution reset logic for {'home' if is_home else 'away'} team"
                        )
                        # Extract the "Player In" jersey number
                        in_num_item = table.item(row, 3)  # Num In column
                        in_jersey_no = in_num_item.text().strip() if in_num_item else ""

                        print(
                            f"DEBUG delete_row_of_button: in_jersey_no='{in_jersey_no}'"
                        )

                        if in_jersey_no:
                            # Check if the substituted-in player is involved in scorer/cards panels
                            if self.is_player_in_scorer_or_cards(in_jersey_no, is_home):
                                # Player is involved in scorer/cards - show warning and do NOT revert or delete
                                QMessageBox.warning(
                                    self,
                                    "Cannot Reset Substitution",
                                    f"Player #{in_jersey_no} has recorded activities in the scorer or cards panels.\n\n"
                                    f"Please remove the player from all scorer and cards activities in the Play On tab first,\n"
                                    f"then you can reset this substitution.",
                                )
                                # Do NOT revert substitution and do NOT delete the row
                                return
                            else:
                                # Player is NOT involved - safe to delete row and revert substitution
                                print(
                                    f"DEBUG delete_row_of_button: Player #{in_jersey_no} not involved, reverting and deleting row"
                                )
                                self.revert_substitution(table, row, is_home)
                                table.removeRow(row)
                                return
                        else:
                            print(
                                "DEBUG delete_row_of_button: No in_jersey_no, just deleting empty substitution row"
                            )
                            table.removeRow(row)
                        return
                    elif is_penalty_table:
                        if self._is_penalty_row_locked(table, row):
                            QMessageBox.warning(
                                self,
                                "Row Locked",
                                "This penalty row is locked. Unlock it before resetting.",
                            )
                            return
                    else:
                        print(
                            "DEBUG delete_row_of_button: Not a substitution table, just deleting row"
                        )

                    # Delete the row (for non-substitution tables)
                    table.removeRow(row)
                    # Ensure remaining rows are visible
                    try:
                        for rr in range(table.rowCount()):
                            table.showRow(rr)
                    except Exception:
                        pass
                    return

            # Fallback: try to map via parent chain
            parent = sender.parent()
            while parent is not None and parent is not table:
                parent = parent.parent()
            # If reached table but no cell match found, no-op
        except Exception as e:
            print(f"Error delete_row_of_button: {e}")
            import traceback

            traceback.print_exc()

    def on_reset_clicked(self):
        try:
            sender = self.sender()
            if sender is None:
                print("DEBUG on_reset_clicked: no sender")
                return
            table = sender.property("table")
            if table is None:
                print("DEBUG on_reset_clicked: no table property on sender")
                return
            # Find the row containing this sender
            for row in range(table.rowCount()):
                for col in range(table.columnCount()):
                    w = table.cellWidget(row, col)
                    if w is None:
                        continue
                    if w is sender:
                        table.removeRow(row)
                        print(f"DEBUG on_reset_clicked: removed row {row} (direct)")
                        return
                    # Check descendants
                    from PySide6.QtWidgets import QPushButton

                    if isinstance(w, QPushButton) and w is sender:
                        table.removeRow(row)
                        print(
                            f"DEBUG on_reset_clicked: removed row {row} (button cell)"
                        )
                        return
                    for btn in w.findChildren(QPushButton):
                        if btn is sender:
                            table.removeRow(row)
                            print(
                                f"DEBUG on_reset_clicked: removed row {row} (descendant)"
                            )
                            return
            print("DEBUG on_reset_clicked: sender not found in any cell")
        except Exception as e:
            print(f"Error on_reset_clicked: {e}")

    def update_card_row_visibility(self, table, team_type):
        try:
            table.showRow(0)
            for r in range(table.rowCount() - 1):
                btn = table.cellWidget(r, 2)
                show_next = btn and btn.text() != "Select Player"
                if r + 1 < table.rowCount():
                    (table.showRow if show_next else table.hideRow)(r + 1)
        except Exception as e:
            print(f"Error update_card_row_visibility: {e}")

    def deploy_selected_cards(self, table: QTableWidget, team: str):
        """Replica deploy action; implement real logic later."""
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "Deploy", f"Cards deployed for {team} team")
        except Exception:
            pass

    def load_match_data(self, match_data):
        """Load match data and update UI"""
        self._pending_match_data = match_data
        if not getattr(self, "match_created", False):
            print("[SubsAndPenaltyTab] load_match_data skipped - match not created yet")
            return
        # Only reset substituted-out tracking if this is a fresh match data load (not from our own updates)
        # Check if match_data is significantly different from current match_data (e.g., different match_id)
        current_match_id = self.match_data.get("match_id") if self.match_data else None
        new_match_id = match_data.get("match_id")

        if current_match_id != new_match_id:
            # Reset substituted tracking when new match data is loaded (different match)
            self.substituted_out_home = []
            self.substituted_out_away = []
            self.substituted_in_home = []
            self.substituted_in_away = []
            self.sent_off_home_players.clear()
            self.sent_off_away_players.clear()

        # Update match_data
        self.match_data = match_data

        # Get team short names for updating panel titles
        home = (match_data or {}).get("home_team") or {}
        away = (match_data or {}).get("away_team") or {}
        home_short_name = home.get("short_name") or home.get("name") or "Home Team"
        away_short_name = away.get("short_name") or away.get("name") or "Away Team"

        # Update substitution panel titles with team short names
        try:
            if hasattr(self, "home_substitution_label"):
                self.home_substitution_label.setText(f"{home_short_name} SUBSTITUTIONS")
            if hasattr(self, "away_substitution_label"):
                self.away_substitution_label.setText(f"{away_short_name} SUBSTITUTIONS")
        except Exception as e:
            print(f"DEBUG: Unable to update substitution panel titles: {e}")

        # Update penalty panel titles with team short names
        try:
            if hasattr(self, "home_penalty_label"):
                self.home_penalty_label.setText(f"{home_short_name} PENALTY")
            if hasattr(self, "away_penalty_label"):
                self.away_penalty_label.setText(f"{away_short_name} PENALTY")
        except Exception as e:
            print(f"DEBUG: Unable to update penalty panel titles: {e}")

        # Update player lists for substitutions
        self.update_substitution_players()
        self.update_penalty_players()
        # Re-apply sent-off highlighting if needed
        self._update_sent_off_substitution_rows("home")
        self._update_sent_off_substitution_rows("away")

    def update_substitution_players(self):
        """Update player dropdowns for substitutions"""
        if not self.match_data:
            return

        # Handle both home_team/away_team and team_a/team_b key formats
        home_team = self.match_data.get("home_team") or self.match_data.get(
            "team_a", {}
        )
        away_team = self.match_data.get("away_team") or self.match_data.get(
            "team_b", {}
        )

        # Use playing_11 for "Player Out" (those on the field) and substitutions for "Player In"
        # If playing_11/substitutions don't exist, fall back to checking selected flag
        if hasattr(self, "home_player_out_combo") and hasattr(
            self, "home_player_in_combo"
        ):
            # For substitutions, player_out should be from playing_11, player_in from substitutions
            self.populate_player_combos(
                self.home_player_out_combo, self.home_player_in_combo, home_team, "home"
            )

        if hasattr(self, "away_player_out_combo") and hasattr(
            self, "away_player_in_combo"
        ):
            # For substitutions, player_out should be from playing_11, player_in from substitutions
            self.populate_player_combos(
                self.away_player_out_combo, self.away_player_in_combo, away_team, "away"
            )

    def update_penalty_players(self):
        """Update player dropdowns for penalties"""
        if not self.match_data:
            return

        # Handle both home_team/away_team and team_a/team_b key formats
        home_team = self.match_data.get("home_team") or self.match_data.get(
            "team_a", {}
        )
        away_team = self.match_data.get("away_team") or self.match_data.get(
            "team_b", {}
        )

        if hasattr(self, "home_penalty_player_combo"):
            self.populate_penalty_combo(self.home_penalty_player_combo, home_team)

        if hasattr(self, "away_penalty_player_combo"):
            self.populate_penalty_combo(self.away_penalty_player_combo, away_team)

    def _get_sent_off_set(self, team_type: str):
        normalized = "home" if str(team_type).lower().startswith("home") else "away"
        return (
            self.sent_off_home_players
            if normalized == "home"
            else self.sent_off_away_players
        )

    def handle_yellow_card_from_play_on(
        self,
        team_type: str,
        jersey_no: str,
        has_yellow: bool,
        player_name: str | None = None,
    ):
        """Called by Play On tab when a player receives/loses a yellow card."""
        # For now, this is just a notification mechanism
        # The highlighting is already handled in the player selection dialogs
        # which read from play_on_tab.yellow_card_players
        try:
            normalized = "home" if str(team_type).lower().startswith("home") else "away"
            print(
                f"DEBUG: Yellow card notification for {normalized} team - Player #{jersey_no} ({player_name}), has_yellow={has_yellow}"
            )
        except Exception as exc:
            print(f"Error handling yellow card notification: {exc}")

    def handle_sent_off_player_from_play_on(
        self,
        team_type: str,
        jersey_no: str,
        sent_off: bool,
        player_name: str | None = None,
        entity_type: str = "player",
    ):
        """Called by Play On tab when a player or official receives/loses a red card."""
        try:
            normalized = "home" if str(team_type).lower().startswith("home") else "away"
            if entity_type == "official":
                # Officials do not participate in substitution / penalty panels, so just acknowledge.
                print(
                    f"DEBUG handle_sent_off_player_from_play_on: official '{player_name}' flagged={sent_off} for {normalized}"
                )
                return

            if not jersey_no:
                return
            sent_off_set = self._get_sent_off_set(normalized)
            if sent_off:
                sent_off_set.add(jersey_no)
            else:
                sent_off_set.discard(jersey_no)
            self._update_sent_off_substitution_rows(normalized)
            # Refresh select lists so newly added playing 11 members honor red-card lock
            self.update_substitution_players()
            self.update_penalty_players()
        except Exception as exc:
            print(f"Error handling sent off player update: {exc}")

    def _update_sent_off_substitution_rows(self, team_type: str):
        """Refresh substitution rows to reflect sent-off players."""
        try:
            table = None
            if team_type == "home":
                table = getattr(self, "home_sub_table", None)
                sent_off_set = self.sent_off_home_players
            else:
                table = getattr(self, "away_sub_table", None)
                sent_off_set = self.sent_off_away_players
            if not table:
                return
            for row in range(table.rowCount()):
                num_item = table.item(row, 1)
                if not num_item:
                    continue
                jersey_no = num_item.text().strip()
                out_btn = table.cellWidget(row, 2)
                lock_widget = table.cellWidget(row, 6)
                lock_cb = lock_widget.findChild(QCheckBox) if lock_widget else None
                if jersey_no and jersey_no in sent_off_set:
                    num_item.setForeground(QColor(SENT_OFF_TEXT_COLOR))
                    if isinstance(out_btn, QPushButton):
                        out_btn.setStyleSheet(SUB_OUT_BUTTON_SENT_OFF_STYLE)
                        out_btn.setEnabled(False)
                    if lock_cb:
                        lock_cb.blockSignals(True)
                        lock_cb.setChecked(True)
                        lock_cb.blockSignals(False)
                        lock_cb.setProperty("sent_off_lock", True)
                        lock_cb.setEnabled(False)
                        self.toggle_row_lock(table, row, Qt.CheckState.Checked.value)
                else:
                    num_item.setForeground(QColor(COLORS["text"]))
                    if isinstance(out_btn, QPushButton):
                        out_btn.setStyleSheet(SUB_OUT_BUTTON_STYLE)
                        out_btn.setEnabled(True)
                    if lock_cb:
                        if lock_cb.property("sent_off_lock"):
                            lock_cb.blockSignals(True)
                            lock_cb.setChecked(False)
                            lock_cb.blockSignals(False)
                            self.toggle_row_lock(
                                table, row, Qt.CheckState.Unchecked.value
                            )
                            lock_cb.setProperty("sent_off_lock", False)
                        lock_cb.setEnabled(True)
        except Exception as exc:
            print(f"Error updating sent-off substitution rows: {exc}")

    def populate_player_combos(self, out_combo, in_combo, team_data, team_side: str):
        """Populate player out and in combos for a team"""
        # Clear existing items
        out_combo.clear()
        in_combo.clear()

        # Add default items
        out_combo.addItem("Select Out")
        in_combo.addItem("Select In")

        if not team_data:
            return

        # Get playing 11 (selected players) for "out" combo
        # Support new structure with playing_11 or fallback to selected_players or selected flag
        playing_11 = team_data.get("playing_11", [])
        if not playing_11:
            # Fallback to selected_players
            playing_11 = team_data.get("selected_players", [])
        if not playing_11:
            # Fallback to checking selected flag in players array
            all_players = team_data.get("players", [])
            playing_11 = [p for p in all_players if p.get("selected", False)]

        sent_off_set = (
            self.sent_off_home_players
            if team_side == "home"
            else self.sent_off_away_players
        )

        # Add playing 11 to "out" combo
        for player in playing_11:
            name = player.get("name") or player.get("full_name", "Unknown")
            jersey_num = player.get("jersey_no") or player.get("jersey_number", "")
            display_name = f"#{jersey_num} {name}" if jersey_num else name
            out_combo.addItem(display_name, player)
            if jersey_num and jersey_num in sent_off_set:
                item = out_combo.model().item(out_combo.count() - 1)
                if item:
                    item.setEnabled(False)
                    item.setForeground(QColor(SENT_OFF_TEXT_COLOR))
                    item.setText(f"{display_name} (Red Card)")

        # Get substitutions (unselected players) for "in" combo
        # CRITICAL: Filter out any players who are currently in playing 11
        substitutions = team_data.get("substitutions", [])
        if not substitutions:
            # Fallback: get all players and filter out playing 11
            all_players = team_data.get("players", [])
            playing_11_ids = {p.get("id") for p in playing_11 if p.get("id")}
            playing_11_jersey_nos = {
                p.get("jersey_no") or p.get("jersey_number", "") for p in playing_11
            }
            substitutions = [
                p
                for p in all_players
                if p.get("id") not in playing_11_ids
                and (p.get("jersey_no") or p.get("jersey_number", ""))
                not in playing_11_jersey_nos
            ]

        # CRITICAL: Filter out players who are currently in playing 11
        # This ensures players in playing 11 don't appear in substitutions list
        playing_11_jersey_nos_current = {
            p.get("jersey_no") or p.get("jersey_number", "") for p in playing_11
        }
        playing_11_ids_current = {p.get("id") for p in playing_11 if p.get("id")}
        substitutions = [
            p
            for p in substitutions
            if (p.get("jersey_no") or p.get("jersey_number", ""))
            not in playing_11_jersey_nos_current
            and (not p.get("id") or p.get("id") not in playing_11_ids_current)
        ]

        # Add substitutions to "in" combo
        for player in substitutions:
            name = player.get("name") or player.get("full_name", "Unknown")
            jersey_num = player.get("jersey_no") or player.get("jersey_number", "")
            display_name = f"#{jersey_num} {name}" if jersey_num else name
            in_combo.addItem(display_name, player)

    def populate_penalty_combo(self, combo, team_data):
        """Populate penalty player combo for a team"""
        combo.clear()
        combo.addItem("Select Player")

        if not team_data:
            return

        # Get selected players (those on field)
        selected_players = team_data.get("selected_players", [])
        for player in selected_players:
            name = player.get("full_name", "Unknown")
            jersey_num = player.get("jersey_number", "")
            display_name = f"#{jersey_num} {name}" if jersey_num else name
            combo.addItem(display_name, player)

    def show_sub_player_list(self, table, row, team_type, player_type):
        """Display a dialog to select players for substitution"""
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QColor, QFont
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QMessageBox,
                QPushButton,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
            )

            if not getattr(self, "match_created", False):
                QMessageBox.warning(
                    self,
                    "No Match Created",
                    "Please create the match before selecting players.",
                )
                return

            # Get team data from match data
            team_data = None
            is_home = "home" in team_type.lower()
            if is_home:
                team_data = self.match_data.get("home_team", {})
            else:
                team_data = self.match_data.get("away_team", {})

            if not team_data:
                QMessageBox.warning(
                    self,
                    "No Players",
                    f"No players loaded for {team_type}. Please load team data first.",
                )
                return

            # Get substituted tracking for this team
            substituted_out = (
                self.substituted_out_home if is_home else self.substituted_out_away
            )
            substituted_in = (
                self.substituted_in_home if is_home else self.substituted_in_away
            )
            sent_off_set = (
                self.sent_off_home_players if is_home else self.sent_off_away_players
            )

            # DEBUG: Log sent-off players
            print(
                f"[DEBUG show_sub_player_list] Team: {team_type}, Type: {player_type}"
            )
            print(f"[DEBUG show_sub_player_list] sent_off_set: {sent_off_set}")
            print(
                f"[DEBUG show_sub_player_list] sent_off_set type: {type(sent_off_set)}"
            )

            # Get players based on player_type
            if player_type == "out":
                # Show only playing 11 for "out"
                players = team_data.get("playing_11", [])
                if not players:
                    # Fallback: check selected flag in players array
                    all_players = team_data.get("players", [])
                    players = [p for p in all_players if p.get("selected", False)]
            else:
                # Show only substitutions for "in"
                # CRITICAL: Get current playing 11 first to filter out
                current_playing_11 = team_data.get("playing_11", [])
                if not current_playing_11:
                    # Fallback: check selected flag in players array
                    all_players = team_data.get("players", [])
                    current_playing_11 = [
                        p for p in all_players if p.get("selected", False)
                    ]

                # Get substitutions list
                players = team_data.get("substitutions", [])
                if not players:
                    # Fallback: get all players and filter out playing 11
                    all_players = team_data.get("players", [])
                    playing_11_jersey_nos = {
                        p.get("jersey_no") or p.get("jersey_number", "")
                        for p in current_playing_11
                    }
                    players = [
                        p
                        for p in all_players
                        if (p.get("jersey_no") or p.get("jersey_number", ""))
                        not in playing_11_jersey_nos
                    ]

                # CRITICAL: Filter out players who are currently in playing 11
                # This ensures players in playing 11 don't appear in substitutions list
                playing_11_jersey_nos_current = {
                    p.get("jersey_no") or p.get("jersey_number", "")
                    for p in current_playing_11
                }
                playing_11_ids_current = {
                    p.get("id") for p in current_playing_11 if p.get("id")
                }
                players = [
                    p
                    for p in players
                    if (p.get("jersey_no") or p.get("jersey_number", ""))
                    not in playing_11_jersey_nos_current
                    and (not p.get("id") or p.get("id") not in playing_11_ids_current)
                ]

                # Note: Substituted-out players will be in the substitutions list (added by perform_substitution)
                # They will be marked red and disabled in the popup (checked via substituted_out list)

            if not players:
                QMessageBox.warning(
                    self,
                    "No Players",
                    f"No {'playing 11' if player_type == 'out' else 'substitutions'} available for {team_type}.",
                )
                return

            # Sort players by jersey number
            try:

                def get_jersey_num(player):
                    jersey = (
                        player.get("jersey_number") or player.get("jersey_no") or "0"
                    )
                    try:
                        return int(jersey)
                    except (ValueError, TypeError):
                        return 0

                players = sorted(players, key=get_jersey_num)
            except Exception:
                pass

            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"Select {player_type.capitalize()} Player for {team_type}"
            )
            dialog.setStyleSheet(f"""
                QDialog {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {COLORS["card"]}, stop:1 {COLORS["panel"]});
                    color: {COLORS["text"]};
                }}
            """)
            dialog.setFixedSize(450, 600)

            layout = QVBoxLayout(dialog)

            player_table = QTableWidget(dialog)
            player_table.setColumnCount(2)
            player_table.setHorizontalHeaderLabels(["Player Name", "Number"])
            player_table.setStyleSheet(
                f"""
                QTableWidget {{
                    background: transparent;
                    border: 1px solid {COLORS["border"]};
                    gridline-color: {COLORS["border"]};
                    selection-background-color: #22c55e;
                    selection-color: #000000;
                    font-size: 14px;
                }}
                QHeaderView::section {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    color: #10b981;
                    padding: 8px 6px;
                    border: 1px solid {COLORS["border"]};
                    font-weight: 700;
                    font-size: 14px;
                }}
                QTableWidget::item {{
                    padding: 6px 4px;
                    border-bottom: 1px solid {COLORS["border"]};
                }}
                QTableWidget::item:selected {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white;
                    font-weight: bold;
                }}
                """
            )
            player_table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            player_table.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )
            # Column sizing similar to scorer popup
            header = player_table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            player_table.setColumnWidth(1, 100)
            layout.addWidget(player_table)

            # Populate players
            player_table.setRowCount(len(players))
            for row_idx, player in enumerate(players):
                # Handle both full_name/name and jersey_number/jersey_no
                name = player.get("full_name") or player.get("name") or ""
                jersey_num = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )

                # DEBUG: Check sent-off status for this player
                if player_type == "out":
                    print(
                        f"[DEBUG show_sub_player_list] Checking player: {name} (#{jersey_num})"
                    )
                    print(
                        f"[DEBUG show_sub_player_list] Is in sent_off_set? {jersey_num in sent_off_set}"
                    )

                name_item = QTableWidgetItem(name)
                name_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                number_item = QTableWidgetItem(jersey_num)
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # PRIORITY ORDER: Check sent-off status FIRST (highest priority)
                # Then check substitution status

                # Check for sent-off players (works for both "in" and "out" popups)
                if jersey_num in sent_off_set:
                    name_item.setForeground(QColor(SENT_OFF_TEXT_COLOR))
                    number_item.setForeground(QColor(SENT_OFF_TEXT_COLOR))
                    name_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    number_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    if player_type == "out":
                        tooltip = "Sent off (red card) – player cannot be replaced"
                    else:
                        tooltip = "Sent off (red card) – player cannot enter the field"
                    name_item.setToolTip(tooltip)
                    number_item.setToolTip(tooltip)
                # If this is "in" popup and player was substituted out, mark red and disable
                elif player_type == "in" and jersey_num in substituted_out:
                    # Mark as red and non-selectable
                    name_item.setForeground(QColor("#FF4444"))
                    number_item.setForeground(QColor("#FF4444"))
                    name_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    number_item.setFlags(Qt.ItemFlag.NoItemFlags)
                # Highlight players who entered as substitutes (green) - only if not sent off
                elif player_type == "out" and jersey_num in substituted_in:
                    # Highlight players who entered as substitutes
                    highlight_color = QColor("#22c55e")
                    name_item.setForeground(highlight_color)
                    number_item.setForeground(highlight_color)
                else:
                    # Check if player has yellow card
                    yellow_card_set = set()
                    try:
                        main_window = self.window()
                        if main_window and hasattr(main_window, "play_on_tab"):
                            play_on_tab = main_window.play_on_tab
                            if hasattr(play_on_tab, "yellow_card_players"):
                                normalized_team = "home" if is_home else "away"
                                yellow_card_set = play_on_tab.yellow_card_players.get(
                                    normalized_team, set()
                                )
                    except Exception:
                        yellow_card_set = set()

                    if jersey_num in yellow_card_set:
                        # Yellow highlight for players with yellow cards
                        yellow_color = QColor("#fbbf24")  # Yellow/amber color
                        name_item.setForeground(yellow_color)
                        number_item.setForeground(yellow_color)
                        name_item.setBackground(
                            QColor("#78350f")
                        )  # Dark amber background
                        number_item.setBackground(QColor("#78350f"))
                        tooltip = "Yellow card — player is on a caution."
                        name_item.setToolTip(tooltip)
                        number_item.setToolTip(tooltip)

                player_table.setItem(row_idx, 0, name_item)
                player_table.setItem(row_idx, 1, number_item)

            def update_selection():
                try:
                    selected_rows = player_table.selectedIndexes()
                    if not selected_rows:
                        dialog.reject()
                        return

                    selected_row = selected_rows[0].row()

                    # Check if row is disabled (substituted out player or red-carded player)
                    name_item = player_table.item(selected_row, 0)
                    if (
                        name_item
                        and (name_item.flags() & Qt.ItemFlag.ItemIsSelectable) == 0
                    ):
                        number_item = player_table.item(selected_row, 1)
                        jersey_value = number_item.text() if number_item else ""
                        message = "This player has already been substituted out and cannot be selected again."
                        if jersey_value in sent_off_set:
                            if player_type == "out":
                                message = "This player has received a red card and cannot be replaced."
                            else:
                                message = "This player has received a red card and cannot enter the field."
                        QMessageBox.warning(self, "Cannot Select", message)
                        dialog.reject()
                        return

                    player_name = player_table.item(selected_row, 0).text()
                    jersey_no = player_table.item(selected_row, 1).text()

                    # Get the actual player object
                    selected_player = None
                    for p in players:
                        p_jersey = str(
                            p.get("jersey_number") or p.get("jersey_no") or ""
                        )
                        if p_jersey == jersey_no:
                            selected_player = p
                            break

                    col = 2 if player_type == "out" else 4
                    btn = table.cellWidget(row, col)
                    if btn:
                        btn.setText(player_name)

                    if player_type == "out":
                        num_item = table.item(row, 1)
                        if num_item:
                            num_item.setText(jersey_no)
                            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            # Set red color for OUT numbers
                            num_item.setForeground(QColor("#ff4444"))  # Red color
                    else:
                        num_in_item = table.item(row, 3)
                        if num_in_item:
                            num_in_item.setText(jersey_no)
                            num_in_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            # Set green color for IN numbers
                            num_in_item.setForeground(QColor("#44ff44"))  # Green color

                        # When both out and in are selected, perform substitution
                        out_btn = table.cellWidget(row, 2)
                        if out_btn and out_btn.text() != "Select Out":
                            # Get out player jersey number
                            out_num_item = table.item(row, 1)
                            if out_num_item:
                                out_jersey_no = out_num_item.text()
                                # Perform substitution: update playing 11 and substitutions
                                self.perform_substitution(
                                    is_home, out_jersey_no, jersey_no, selected_player
                                )

                    # Enable Lock button if both Player Out and Player In are set
                    out_btn = table.cellWidget(row, 2)
                    in_btn = table.cellWidget(row, 4)
                    lock_widget = table.cellWidget(row, 6)
                    if lock_widget:
                        lock_cb = lock_widget.findChild(QCheckBox)
                        if lock_cb and out_btn and in_btn:
                            lock_cb.setEnabled(
                                out_btn.text() != "Select Out"
                                and in_btn.text() != "Select In"
                            )

                    self.update_row_visibility(table, team_type)
                    self.update_time(table, row, team_type)

                    dialog.accept()
                except Exception as e:
                    print(f"Error updating player selection: {str(e)}")
                    import traceback

                    traceback.print_exc()
                    dialog.reject()

            player_table.doubleClicked.connect(update_selection)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            ok_button.setFont(QFont("Verdana", 14))
            ok_button.setFixedHeight(40)
            ok_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            ok_button.clicked.connect(update_selection)
            button_layout.addWidget(ok_button)

            cancel_button = QPushButton("Cancel")
            cancel_button.setFont(QFont("Verdana", 14))
            cancel_button.setFixedHeight(40)
            cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)

            dialog.exec()
        except Exception as e:
            print(f"Error in show_sub_player_list for {team_type} row {row}: {str(e)}")

    def is_player_in_scorer_or_cards(self, jersey_no: str, is_home: bool) -> bool:
        """Check if a player (by jersey number) exists in any scorer or cards panel rows.

        Args:
            jersey_no: Jersey number of the player to check
            is_home: True if home team, False if away team

        Returns:
            True if player is found in any active row, False otherwise
        """
        try:
            if not jersey_no:
                print("DEBUG is_player_in_scorer_or_cards: empty jersey_no")
                return False

            print(
                f"DEBUG is_player_in_scorer_or_cards: Checking jersey #{jersey_no} for {'home' if is_home else 'away'} team"
            )

            # Get the Play On tab from parent window (MainWindow)
            # Use window() to get the top-level window reliably
            play_on_tab = None
            main_window = self.window()  # This gets the top-level window

            if main_window and hasattr(main_window, "play_on_tab"):
                play_on_tab = main_window.play_on_tab
                print(
                    "DEBUG is_player_in_scorer_or_cards: Found Play On tab through window()"
                )

            if not play_on_tab:
                print(
                    "DEBUG is_player_in_scorer_or_cards: Could not access Play On tab"
                )
                return False

            # Get all scorer and cards tables from Play On tab
            tables_to_check = []

            # Add Scorer Tables (Goals)
            if hasattr(play_on_tab, "home_scorer_panel"):
                children = play_on_tab.home_scorer_panel.findChildren(QTableWidget)
                if children:
                    tables_to_check.append(children[0])

            if hasattr(play_on_tab, "away_scorer_panel"):
                children = play_on_tab.away_scorer_panel.findChildren(QTableWidget)
                if children:
                    tables_to_check.append(children[0])

            # Add Cards Tables (Yellow/Red Cards)
            if hasattr(play_on_tab, "home_card_table"):
                tables_to_check.append(play_on_tab.home_card_table)

            if hasattr(play_on_tab, "away_card_table"):
                tables_to_check.append(play_on_tab.away_card_table)

            print(
                f"DEBUG is_player_in_scorer_or_cards: Found {len(tables_to_check)} tables in Play On tab to check"
            )

            for table_idx, table in enumerate(tables_to_check):
                col_count = table.columnCount()
                row_count = table.rowCount()

                # Check each row for the jersey number
                # The table structure may vary, so we'll check multiple possible column positions
                for row in range(row_count):
                    # Try different column positions for jersey number
                    # Common positions: column 0, 1, or 2
                    for num_col in [0, 1, 2]:
                        if num_col >= col_count:
                            continue

                        num_item = table.item(row, num_col)
                        if num_item:
                            num_text = num_item.text().strip()
                            if num_text == jersey_no:
                                # Found the jersey number! Now check if this row has actual EVENT data
                                # For scorer tables: check if a player name is present (not just jersey number)
                                # For cards tables: check if there's a yellow/red card checkbox checked
                                has_event = False

                                # Check all columns for meaningful data
                                for col in range(col_count):
                                    if (
                                        col == num_col
                                    ):  # Skip the jersey number column itself
                                        continue

                                    # Check for table items with player names (not empty, not "Select Player")
                                    item = table.item(row, col)
                                    if item:
                                        item_text = item.text().strip()
                                        # If there's meaningful text that's not just a number, it's likely a player name
                                        if (
                                            item_text
                                            and item_text != "Select Player"
                                            and not item_text.isdigit()
                                        ):
                                            has_event = True
                                            print(
                                                f"DEBUG is_player_in_scorer_or_cards: Found player name '{item_text}' in row {row}, col {col}"
                                            )
                                            break

                                    # Check for selected player (button with text other than "Select Player")
                                    widget = table.cellWidget(row, col)
                                    if widget:
                                        # Check if it's a button with a player name
                                        from PySide6.QtWidgets import (
                                            QCheckBox,
                                            QPushButton,
                                        )

                                        buttons = widget.findChildren(QPushButton)
                                        for btn in buttons:
                                            btn_text = btn.text().strip()
                                            if btn_text and btn_text != "Select Player":
                                                has_event = True
                                                print(
                                                    f"DEBUG is_player_in_scorer_or_cards: Found selected player button '{btn_text}' in row {row}, col {col}"
                                                )
                                                break

                                        # Also check for checked checkboxes (for cards tables)
                                        if not has_event:
                                            checkboxes = widget.findChildren(QCheckBox)
                                            for cb in checkboxes:
                                                if cb.isChecked():
                                                    has_event = True
                                                    print(
                                                        f"DEBUG is_player_in_scorer_or_cards: Found checked checkbox in row {row}, col {col}"
                                                    )
                                                    break

                                        if has_event:
                                            break

                                if has_event:
                                    print(
                                        f"DEBUG is_player_in_scorer_or_cards: Player #{jersey_no} IS INVOLVED in Play On scorer table row {row}!"
                                    )
                                    return True
                                else:
                                    # print(f"DEBUG is_player_in_scorer_or_cards: Found jersey #{jersey_no} in row {row} but no event data")
                                    pass

            print(
                f"DEBUG is_player_in_scorer_or_cards: Player #{jersey_no} NOT found in any Play On scorer/cards panels"
            )
            return False
        except Exception as e:
            print(f"Error in is_player_in_scorer_or_cards: {e}")
            import traceback

            traceback.print_exc()
            return False

    def revert_substitution(self, table: QTableWidget, row: int, is_home: bool) -> bool:
        """Revert a substitution by moving players back to their original lists.

        Args:
            table: The substitution table
            row: The row number to revert
            is_home: True if home team, False if away team

        Returns:
            True if revert was successful, False otherwise
        """
        try:
            # Extract player out and in jersey numbers from the row
            out_num_item = table.item(row, 1)  # Num Out column
            in_num_item = table.item(row, 3)  # Num In column

            if not out_num_item or not in_num_item:
                print("Cannot revert: missing player data in row")
                return False

            out_jersey_no = out_num_item.text().strip()
            in_jersey_no = in_num_item.text().strip()

            if not out_jersey_no or not in_jersey_no:
                print("Cannot revert: empty jersey numbers")
                return False

            # Get team data
            team_key = "home_team" if is_home else "away_team"
            team_data = self.match_data.get(team_key, {})

            if not team_data:
                print(f"No team data found for {'home' if is_home else 'away'} team")
                return False

            # Get current playing 11 and substitutions
            playing_11 = team_data.get("playing_11", [])
            substitutions = team_data.get("substitutions", [])

            # Find the "in" player in playing 11 and move back to substitutions
            in_player = None
            for i, player in enumerate(playing_11):
                p_jersey = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                if p_jersey == in_jersey_no:
                    in_player = playing_11.pop(i)
                    break

            if not in_player:
                print(f"Player {in_jersey_no} not found in playing 11")
                return False

            # Find the "out" player in substitutions and move back to playing 11
            out_player = None
            for i, player in enumerate(substitutions):
                p_jersey = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                if p_jersey == out_jersey_no:
                    out_player = substitutions.pop(i)
                    break

            if not out_player:
                print(f"Player {out_jersey_no} not found in substitutions")
                # Still add in_player back to substitutions even if out_player not found
                in_player["selected"] = False
                in_player["is_substitution"] = False
                substitutions.append(in_player)
                return False

            # Update player flags
            in_player["selected"] = False
            in_player["is_substitution"] = False
            in_player["entered_as_sub"] = False
            out_player["selected"] = True
            out_player["is_substitution"] = False

            # Add players back to their original lists
            substitutions.append(in_player)
            playing_11.append(out_player)

            # Update team_data
            team_data["playing_11"] = playing_11
            team_data["substitutions"] = substitutions

            # Update all_players array to reflect changes
            all_players = team_data.get("players", [])
            for player in all_players:
                p_jersey = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                if p_jersey == out_jersey_no:
                    player["selected"] = True
                    player["is_substitution"] = False
                elif p_jersey == in_jersey_no:
                    player["selected"] = False
                    player["is_substitution"] = False
                    player["entered_as_sub"] = False

            # Remove from substituted-out tracking
            substituted_out_list = (
                self.substituted_out_home if is_home else self.substituted_out_away
            )
            if out_jersey_no in substituted_out_list:
                substituted_out_list.remove(out_jersey_no)
            substituted_in_list = (
                self.substituted_in_home if is_home else self.substituted_in_away
            )
            if in_jersey_no in substituted_in_list:
                substituted_in_list.remove(in_jersey_no)

            # Refresh player lists in UI
            self.update_substitution_players()

            # Emit match_data_changed signal
            self.match_data_changed.emit(self.match_data)

            print(
                f"Reverted substitution: {out_jersey_no} back to playing 11, {in_jersey_no} back to substitutions"
            )
            return True

        except Exception as e:
            print(f"Error in revert_substitution: {e}")
            import traceback

            traceback.print_exc()
            return False

    def perform_substitution(
        self, is_home: bool, out_jersey_no: str, in_jersey_no: str, in_player: dict
    ):
        """Perform substitution: update playing 11 and substitutions lists"""
        try:
            # Get team data
            team_key = "home_team" if is_home else "away_team"
            team_data = self.match_data.get(team_key, {})

            if not team_data:
                print(f"No team data found for {'home' if is_home else 'away'} team")
                return

            # Get current playing 11 and substitutions
            playing_11 = team_data.get("playing_11", [])
            substitutions = team_data.get("substitutions", [])

            # Fallback: if lists don't exist, create them from all players
            if not playing_11 or not substitutions:
                all_players = team_data.get("players", [])
                if not playing_11:
                    playing_11 = [p for p in all_players if p.get("selected", False)]
                if not substitutions:
                    playing_11_jersey_nos = {
                        p.get("jersey_no") or p.get("jersey_number", "")
                        for p in playing_11
                    }
                    substitutions = [
                        p
                        for p in all_players
                        if (p.get("jersey_no") or p.get("jersey_number", ""))
                        not in playing_11_jersey_nos
                    ]

            # Find out player in playing 11
            out_player = None
            for i, player in enumerate(playing_11):
                p_jersey = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                if p_jersey == out_jersey_no:
                    out_player = playing_11.pop(i)
                    break

            if not out_player:
                print(f"Player {out_jersey_no} not found in playing 11")
                return

            # Update out player: set selected=False, is_substitution=True
            out_player["selected"] = False
            out_player["is_substitution"] = True

            # Update in player: set selected=True, is_substitution=False
            if in_player:
                in_player["selected"] = True
                in_player["is_substitution"] = False
            else:
                # Find in player in substitutions
                for i, player in enumerate(substitutions):
                    p_jersey = str(
                        player.get("jersey_number") or player.get("jersey_no") or ""
                    )
                    if p_jersey == in_jersey_no:
                        in_player = substitutions.pop(i)
                        in_player["selected"] = True
                        in_player["is_substitution"] = False
                        break

            # Add out player to substitutions
            substitutions.append(out_player)

            # Add in player to playing 11
            if in_player:
                in_player["entered_as_sub"] = True
                playing_11.append(in_player)

            # CRITICAL: Ensure substitutions list doesn't contain players who are in playing 11
            # Filter out any players from substitutions who are now in playing 11
            playing_11_jersey_nos = {
                p.get("jersey_no") or p.get("jersey_number", "") for p in playing_11
            }
            playing_11_ids = {p.get("id") for p in playing_11 if p.get("id")}
            substitutions = [
                p
                for p in substitutions
                if (p.get("jersey_no") or p.get("jersey_number", ""))
                not in playing_11_jersey_nos
                and (not p.get("id") or p.get("id") not in playing_11_ids)
            ]

            # Update team_data
            team_data["playing_11"] = playing_11
            team_data["substitutions"] = substitutions

            # Update all_players array to reflect changes
            all_players = team_data.get("players", [])
            for player in all_players:
                p_jersey = str(
                    player.get("jersey_number") or player.get("jersey_no") or ""
                )
                if p_jersey == out_jersey_no:
                    player["selected"] = False
                    player["is_substitution"] = True
                elif p_jersey == in_jersey_no:
                    player["selected"] = True
                    player["is_substitution"] = False
                    player["entered_as_sub"] = True

            # Track substituted-out player
            substituted_out_list = (
                self.substituted_out_home if is_home else self.substituted_out_away
            )
            if out_jersey_no not in substituted_out_list:
                substituted_out_list.append(out_jersey_no)
            substituted_in_list = (
                self.substituted_in_home if is_home else self.substituted_in_away
            )
            if in_jersey_no and in_jersey_no not in substituted_in_list:
                substituted_in_list.append(in_jersey_no)

            # Refresh player lists in UI
            self.update_substitution_players()

            # CRITICAL: Emit match_data_changed signal so Play On tab and other components can update
            # This ensures playing 11 changes from substitutions reflect globally
            self.match_data_changed.emit(self.match_data)

            # Also emit substitution_made signal for other purposes
            self.substitution_made.emit(
                {
                    "team": "home" if is_home else "away",
                    "out_jersey": out_jersey_no,
                    "in_jersey": in_jersey_no,
                    "match_data": self.match_data,
                }
            )

            print(
                f"Substitution performed: {out_jersey_no} out, {in_jersey_no} in for {'home' if is_home else 'away'} team"
            )

        except Exception as e:
            print(f"Error performing substitution: {str(e)}")
            import traceback

            traceback.print_exc()

    def toggle_row_lock(self, table, row, state):
        """Enable or disable a row in the table based on Lock checkbox state"""
        try:
            is_locked = state == Qt.CheckState.Checked.value

            # Time column (0) - should remain editable when unlocked
            time_item = table.item(row, 0)
            if time_item:
                if is_locked:
                    time_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                else:
                    time_item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsEditable
                    )

            # Other non-editable columns (1, 3)
            for col in [1, 3]:
                item = table.item(row, col)
                if item:
                    if is_locked:
                        item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    else:
                        item.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                        )
            for col in [2, 4]:
                widget = table.cellWidget(row, col)
                if widget:
                    widget.setEnabled(not is_locked)
            export_widget = table.cellWidget(row, 5)
            if export_widget:
                cb = export_widget.findChild(QCheckBox)
                if cb:
                    cb.setEnabled(not is_locked)
            reset_widget = table.cellWidget(row, 7)
            if reset_widget:
                reset_widget.setEnabled(not is_locked)
        except Exception as e:
            print(f"Error in toggle_row_lock for row {row}: {str(e)}")

    def _extract_button_text(self, widget) -> str:
        """Return the text of a QPushButton or nested button-like widget."""
        try:
            if widget is None:
                return ""
            if isinstance(widget, QPushButton):
                return widget.text()
            btn = widget.findChild(QPushButton)
            return btn.text() if btn else ""
        except Exception:
            return ""

    def _is_substitution_row_complete(self, table: QTableWidget, row: int) -> bool:
        """Determine if a substitution row has both players selected."""
        try:
            num_out = table.item(row, 1).text().strip() if table.item(row, 1) else ""
            num_in = table.item(row, 3).text().strip() if table.item(row, 3) else ""
            out_btn_text = self._extract_button_text(table.cellWidget(row, 2))
            in_btn_text = self._extract_button_text(table.cellWidget(row, 4))
            return all(
                [
                    num_out,
                    num_in,
                    out_btn_text and out_btn_text != "Select Out",
                    in_btn_text and in_btn_text != "Select In",
                ]
            )
        except Exception:
            return False

    def _are_substitution_rows_complete(self, table: QTableWidget) -> bool:
        """Ensure every existing substitution row is filled before adding another."""
        try:
            for row in range(table.rowCount()):
                if not self._is_substitution_row_complete(table, row):
                    return False
            return True
        except Exception:
            return False

    def _is_checkbox_checked(self, widget) -> bool:
        try:
            if not widget:
                return False
            cb = widget.findChild(QCheckBox)
            return bool(cb and cb.isChecked())
        except Exception:
            return False

    def _set_checkbox_checked(self, widget, value: bool):
        try:
            if not widget:
                return
            cb = widget.findChild(QCheckBox)
            if cb:
                cb.setChecked(bool(value))
        except Exception:
            pass

    def _serialize_substitution_table(self, table: QTableWidget) -> list:
        rows = []
        if not table:
            return rows
        try:
            for row in range(table.rowCount()):
                time_text = (
                    table.item(row, 0).text().strip() if table.item(row, 0) else ""
                )
                num_out = (
                    table.item(row, 1).text().strip() if table.item(row, 1) else ""
                )
                num_in = table.item(row, 3).text().strip() if table.item(row, 3) else ""
                player_out = self._extract_button_text(table.cellWidget(row, 2))
                player_in = self._extract_button_text(table.cellWidget(row, 4))
                if not any([num_out, num_in, player_out, player_in]):
                    continue
                rows.append(
                    {
                        "time": time_text,
                        "num_out": num_out,
                        "player_out": player_out,
                        "num_in": num_in,
                        "player_in": player_in,
                        "exported": self._is_checkbox_checked(table.cellWidget(row, 5)),
                        "locked": self._is_checkbox_checked(table.cellWidget(row, 6)),
                    }
                )
        except Exception as exc:
            print(f"Error serializing substitution table: {exc}")
        return rows

    def _serialize_penalty_table(self, table: QTableWidget) -> list:
        rows = []
        if not table:
            return rows
        try:
            for row in range(table.rowCount()):
                num_item = table.item(row, 0)
                name_widget = table.cellWidget(row, 1)
                name_text = self._extract_button_text(name_widget)
                num_text = num_item.text().strip() if num_item else ""
                if not num_text and (not name_text or name_text == "Select Player"):
                    continue
                rows.append(
                    {
                        "number": num_text,
                        "name": name_text,
                        "goal": self._is_checkbox_checked(table.cellWidget(row, 2)),
                        "missed": self._is_checkbox_checked(table.cellWidget(row, 3)),
                        "locked": self._is_checkbox_checked(table.cellWidget(row, 4)),
                    }
                )
        except Exception as exc:
            print(f"Error serializing penalty table: {exc}")
        return rows

    def _apply_substitution_rows(self, table: QTableWidget, rows: list):
        if not table:
            return
        try:
            table.setRowCount(0)
            for row_data in rows or []:
                row_index = table.rowCount()
                table.setRowCount(row_index + 1)
                self._initialize_substitution_row(table, row_index)
                if table.item(row_index, 0):
                    table.item(row_index, 0).setText(row_data.get("time", "00:00"))
                if table.item(row_index, 1):
                    table.item(row_index, 1).setText(row_data.get("num_out", ""))
                if table.item(row_index, 3):
                    table.item(row_index, 3).setText(row_data.get("num_in", ""))
                out_btn = table.cellWidget(row_index, 2)
                if out_btn:
                    out_btn.setText(row_data.get("player_out", "Select Out"))
                in_btn = table.cellWidget(row_index, 4)
                if in_btn:
                    in_btn.setText(row_data.get("player_in", "Select In"))
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 5), row_data.get("exported")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 6), row_data.get("locked")
                )
                table.showRow(row_index)
        except Exception as exc:
            print(f"Error applying substitution rows: {exc}")

    def _apply_penalty_rows(self, table: QTableWidget, rows: list):
        if not table:
            return
        try:
            table.setRowCount(0)
            for row_data in rows or []:
                row_index = table.rowCount()
                table.setRowCount(row_index + 1)
                self._initialize_penalty_row(table, row_index)
                if table.item(row_index, 0):
                    table.item(row_index, 0).setText(row_data.get("number", ""))
                name_btn = table.cellWidget(row_index, 1)
                if name_btn:
                    name_btn.setText(row_data.get("name", "Select Player"))
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 2), row_data.get("goal")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 3), row_data.get("missed")
                )
                self._set_checkbox_checked(
                    table.cellWidget(row_index, 4), row_data.get("locked")
                )
                table.showRow(row_index)
        except Exception as exc:
            print(f"Error applying penalty rows: {exc}")

    def export_state(self) -> dict:
        """Return serialized data for autosave."""
        try:
            return {
                "match_data": self.match_data,
                "home_substitutions": self._serialize_substitution_table(
                    getattr(self, "home_sub_table", None)
                ),
                "away_substitutions": self._serialize_substitution_table(
                    getattr(self, "away_sub_table", None)
                ),
                "home_penalties": self._serialize_penalty_table(
                    getattr(self, "home_penalty_table", None)
                ),
                "away_penalties": self._serialize_penalty_table(
                    getattr(self, "away_penalty_table", None)
                ),
            }
        except Exception as exc:
            print(f"Error exporting Subs & Penalty state: {exc}")
            return {}

    def load_state(self, state: dict):
        """Restore the tab from saved autosave data."""
        if not state:
            return
        try:
            match_data = state.get("match_data")
            if match_data:
                self.match_data = match_data
            self.match_created = True
            if match_data:
                self.load_match_data(match_data)
            self._apply_substitution_rows(
                getattr(self, "home_sub_table", None),
                state.get("home_substitutions", []),
            )
            self._apply_substitution_rows(
                getattr(self, "away_sub_table", None),
                state.get("away_substitutions", []),
            )
            self._apply_penalty_rows(
                getattr(self, "home_penalty_table", None),
                state.get("home_penalties", []),
            )
            self._apply_penalty_rows(
                getattr(self, "away_penalty_table", None),
                state.get("away_penalties", []),
            )
        except Exception as exc:
            print(f"Error loading Subs & Penalty state: {exc}")

    def on_penalty_header_clicked(self, table, column):
        """Toggle all checkboxes in Lock (col 4) column when header is clicked"""
        if column != 4:  # Only handle Lock column for penalty panels
            return

        # Count checked vs unchecked to determine toggle direction
        checked_count = 0
        total_count = 0

        for row in range(table.rowCount()):
            if table.isRowHidden(row):
                continue
            widget = table.cellWidget(row, column)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    total_count += 1
                    if cb.isChecked():
                        checked_count += 1

        # If more than half are checked, uncheck all; otherwise check all
        new_state = checked_count < (total_count / 2)

        # Toggle all checkboxes in this column
        for row in range(table.rowCount()):
            if table.isRowHidden(row):
                continue
            widget = table.cellWidget(row, column)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(new_state)

    def on_substitution_header_clicked(self, table, column):
        """Toggle all checkboxes in Export (col 5) or Lock (col 6) column when header is clicked"""
        if column not in [5, 6]:  # Only handle Export and Lock columns
            return

        # Count checked vs unchecked to determine toggle direction
        checked_count = 0
        total_count = 0

        for row in range(table.rowCount()):
            if table.isRowHidden(row):
                continue
            widget = table.cellWidget(row, column)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    total_count += 1
                    if cb.isChecked():
                        checked_count += 1

        # If more than half are checked, uncheck all; otherwise check all
        new_state = checked_count < (total_count / 2)

        # Toggle all checkboxes in this column
        for row in range(table.rowCount()):
            if table.isRowHidden(row):
                continue
            widget = table.cellWidget(row, column)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(new_state)

    def add_substitution_row(self, team_name):
        """Add a new row to the substitution table when + button is clicked"""
        try:
            # Find the table for this team
            if "Home" in team_name:
                table = self.home_subs_panel.findChild(QTableWidget)
            else:
                table = self.away_subs_panel.findChild(QTableWidget)

            if table:
                if not self._are_substitution_rows_complete(table):
                    QMessageBox.warning(
                        self,
                        "Incomplete Substitution",
                        "Please fill the current substitution row before adding a new one.",
                    )
                    return
                # Get current row count
                current_rows = table.rowCount()

                # Add one new row
                table.setRowCount(current_rows + 1)
                new_row = current_rows

                # Initialize the new row with the same structure as existing rows
                self._initialize_substitution_row(table, new_row)
                print(f"Added new substitution row for {team_name}")
        except Exception as e:
            print(f"Error in add_substitution_row: {e}")

    def _initialize_substitution_row(self, table, row):
        """Initialize a new substitution row with the same structure as existing rows"""
        try:
            # Time column - set to live match time
            ct = self.get_current_time_text()
            try:
                print(f"DEBUG subs _initialize_substitution_row: row={row}, time={ct}")
            except Exception:
                pass
            time_item = QTableWidgetItem(ct)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            time_item.setFont(QFont("Verdana", 12))
            table.setItem(row, 0, time_item)

            # Num Out column
            num_out_item = QTableWidgetItem("")
            num_out_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_out_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            num_out_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(row, 1, num_out_item)

            # Player Out button
            out_btn = QPushButton("Select Out")
            out_btn.setFont(QFont("Verdana", 10))
            out_btn.setStyleSheet(SUB_OUT_BUTTON_STYLE)
            # Wire Out button to player list
            out_btn.clicked.connect(
                lambda checked=False,
                r=row,
                tbl=table,
                t=(
                    "home" if table is getattr(self, "home_sub_table", None) else "away"
                ): self.show_sub_player_list(tbl, r, f"{t} team", "out")
            )
            table.setCellWidget(row, 2, out_btn)

            # Num In column
            num_in_item = QTableWidgetItem("")
            num_in_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_in_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            num_in_item.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
            table.setItem(row, 3, num_in_item)

            # Player In button
            in_btn = QPushButton("Select In")
            in_btn.setFont(QFont("Verdana", 10))
            in_btn.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: #ffffff; border-radius: 4px; }
                QPushButton:hover { background-color: #5a5a5a; }
                QFont { color: #ffffff; }
            """)
            # Wire In button to player list
            in_btn.clicked.connect(
                lambda checked=False,
                r=row,
                tbl=table,
                t=(
                    "home" if table is getattr(self, "home_sub_table", None) else "away"
                ): self.show_sub_player_list(tbl, r, f"{t} team", "in")
            )
            table.setCellWidget(row, 4, in_btn)

            # Export checkbox
            export_cb = QCheckBox()
            export_cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #10B981;
                    border: 1px solid #059669;
                    border-radius: 2px;
                }
            """)
            export_cb.setEnabled(True)
            export_widget = QWidget()
            export_widget.setStyleSheet("border: 0px;")
            export_layout = QHBoxLayout(export_widget)
            export_layout.addWidget(export_cb)
            export_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            export_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 5, export_widget)

            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("""
            QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                    background-color: #FF0000;
                    border: 1px solid #B0B4BB;
                    border-radius: 2px;
            }
        """)
            lock_cb.setEnabled(False)
            lock_widget = QWidget()
            lock_widget.setStyleSheet("border: 0px;")
            lock_layout = QHBoxLayout(lock_widget)
            lock_layout.addWidget(lock_cb)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 6, lock_widget)
            lock_cb.stateChanged.connect(
                lambda state,
                tbl=table,
                cb=lock_cb: self._handle_substitution_lock_toggled(tbl, cb, state)
            )

            # Reset button
            reset_btn = QPushButton("X")
            reset_btn.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
            reset_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            reset_btn.clicked.connect(
                lambda checked=False, tbl=table: self.delete_row_of_button(tbl)
            )
            table.setCellWidget(row, 7, reset_btn)

        except Exception as e:
            print(f"Error in _initialize_substitution_row: {e}")

    def reset_row(self, table, row):
        """Delete the clicked row completely"""
        try:
            # Delete the entire row
            table.removeRow(row)
            print(f"Deleted substitution row {row}")
        except Exception as e:
            print(f"Error in reset_row for row {row}: {str(e)}")

    def update_row_visibility(self, table, team_type):
        """Update visibility of rows in the table based on data"""
        try:
            table.showRow(0)
            for row in range(table.rowCount() - 1):
                num_item = table.item(row, 1)  # Num Out column
                next_row = row + 1
                if num_item and num_item.text().strip():
                    if next_row < table.rowCount():
                        table.showRow(next_row)
                else:
                    if next_row < table.rowCount():
                        table.hideRow(next_row)
        except Exception as e:
            print(f"Error in update_row_visibility for {team_type}: {str(e)}")

    def update_time(self, table, row, team_type):
        """Update the Time column with current time"""
        try:
            # Use live match clock if available
            current_time = self.get_current_time_text()

            time_item = table.item(row, 0)
            if time_item:
                time_item.setText(current_time)
                time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                time_item.setFont(QFont("Verdana", 12))
        except Exception as e:
            print(f"Error in update_time for {team_type}: {str(e)}")

    def get_current_time_text(self) -> str:
        """Derive current match time mm:ss.
        Attempts, in order:
        1) Parent hierarchy object exposing get_current_time_text()
        2) Parent with timer_label (QLabel) text()
        3) Parent with integer seconds attribute -> format mm:ss
        Falls back to "00:00".
        """

        # Helper to extract time from an object
        def _extract_time(obj):
            # Try method first
            method = getattr(obj, "get_current_time_text", None)
            if callable(method):
                result = method()
                if result:
                    return result

            # Try timer_label
            timer_label = getattr(obj, "timer_label", None)
            if timer_label:
                try:
                    result = timer_label.text()
                    if result:
                        return result
                except (AttributeError, RuntimeError):
                    pass

            # Try seconds attribute
            seconds = getattr(obj, "seconds", None)
            if seconds is not None:
                try:
                    total = int(seconds)
                    mins, secs = divmod(total, 60)
                    return f"{mins:02d}:{secs:02d}"
                except (ValueError, TypeError):
                    pass

            return None

        # Walk up parent chain (limit 6 levels)
        obj = self.parent()
        for _ in range(6):
            if obj is None:
                break

            result = _extract_time(obj)
            if result:
                return result

            obj = obj.parent() if hasattr(obj, "parent") else None

        # Check cached provider (only if valid)
        provider = getattr(self, "_time_provider", None)
        if provider is not None:
            try:
                # Validate provider still exists (Qt objects can be deleted)
                _ = provider.parent()
                result = _extract_time(provider)
                if result:
                    return result
            except RuntimeError:
                # Provider was deleted, clear cache
                self._time_provider = None

        # Search window tree for provider (only specific types, cache result)
        try:
            win = self.window()
            if win is not None:
                # Only search PlayOnTab instances (much faster than all QObjects)
                from ui.play_on_tab import PlayOnTab

                play_on_tabs = win.findChildren(PlayOnTab)
                if play_on_tabs:
                    provider = play_on_tabs[0]
                    self._time_provider = provider
                    result = _extract_time(provider)
                    if result:
                        return result
        except (AttributeError, RuntimeError, ImportError):
            pass

        return "00:00"

    def deploy_substitutions(self, team_name):
        """Deploy substitutions for the team"""
        try:
            # TODO: Implement actual substitution deployment logi
            QMessageBox.information(
                self, "Deploy", f"Substitutions deployed for {team_name}"
            )
        except Exception as e:
            print(f"Error deploying substitutions for {team_name}: {str(e)}")
