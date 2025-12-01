"""
Control Panel Widget for FSP 2.0
Contains formation selector, kit selector, jersey image, and color panel
Migrated from team_panel.py to centralize control panel functionality
"""

import re
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QColor, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .color_panel import ColorPanel
from .color_utils import extract_bottom_left_color, extract_top_colors


class ControlPanel(QFrame):
    """Control panel with formation selector, kit selector, jersey image, and color panel"""

    formation_changed = Signal(str)
    kit_changed = Signal(str)
    color_changed = Signal()
    data_changed = Signal()

    def __init__(self, team_name: str, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.formation_input = None
        self.kit_button = None
        self.kit_options = ["Home Kit", "Away Kit", "Third Kit"]
        self.current_kit_index = 0
        self.image_label = None
        self.color_panel = None
        self.coord_toggle_button = None
        self.bg_color_display = None
        self.bg_color_hex = "#000000"
        self.app_logo_label = None
        self._formation_formatting = False
        self._last_valid_formation = "Select Formation"

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the control panel UI - migrated from team_panel.create_control_panel()"""
        # Set the outer border style for the control panel widget
        self.setStyleSheet(self.get_panel_style("control"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Formation section
        formation_group = QFrame()
        formation_group.setStyleSheet(self.get_group_style())
        formation_layout = QVBoxLayout(formation_group)
        formation_layout.setContentsMargins(4, 4, 4, 4)
        formation_layout.setSpacing(3)

        # Formation textbox (accepts up to 4 digits and auto-formats with dashes)
        self.formation_input = QLineEdit()
        self.formation_input.setPlaceholderText("Enter 4 digits (e.g. 4331 → 4-3-3-1)")
        self.formation_input.setMaxLength(7)  # allow digits + dashes when formatted
        self.formation_input.setStyleSheet(self.get_lineedit_style())
        regex = QRegularExpression(r"[0-9\-]{0,7}")
        self.formation_validator = QRegularExpressionValidator(
            regex, self.formation_input
        )
        self.formation_input.setValidator(self.formation_validator)
        formation_layout.addWidget(self.formation_input)

        layout.addWidget(formation_group)
        layout.addStretch(1)

        # Jersey kit selection section
        kit_group = QFrame()
        kit_group.setStyleSheet(self.get_group_style())
        kit_layout = QVBoxLayout(kit_group)
        kit_layout.setContentsMargins(4, 4, 4, 4)
        kit_layout.setSpacing(3)

        # Kit selector label
        kit_label = QLabel("Select Kit")
        kit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kit_label.setFrameShape(QFrame.Shape.NoFrame)
        kit_label.setFrameShadow(QFrame.Shadow.Plain)
        kit_label.setLineWidth(0)
        kit_label.setMidLineWidth(0)
        kit_label.setStyleSheet(
            self.get_label_style()
            + """
            QLabel {
                border: none;
                border-width: 0px;
                border-style: none;
                outline: none;
                margin: 0px;
            }
        """
        )
        kit_layout.addWidget(kit_label)

        # Kit selector button (cycles through kits)
        self.kit_button = QPushButton("No kits loaded")
        self.kit_button.setStyleSheet(self.get_kit_button_style())
        self.kit_button.setMinimumHeight(38)  # Set minimum height for better visibility
        self.kit_button.setEnabled(False)  # Disabled until kits are loaded from JSON
        self.kit_button.clicked.connect(self.cycle_kit)
        kit_layout.addWidget(self.kit_button)

        layout.addWidget(kit_group)

        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(140, 140)
        self.image_label.setStyleSheet(self.get_image_label_style())
        layout.addWidget(self.image_label)

        # Add spacing
        layout.addStretch(1)

        # Color panel
        self.color_panel = ColorPanel(self.team_name, self)
        self.color_panel.color_changed.connect(self.on_color_changed)
        layout.addWidget(self.color_panel)

        # Coordinate toggle group
        coord_group = QFrame()
        coord_group.setStyleSheet(self.get_group_style())
        coord_layout = QVBoxLayout(coord_group)
        coord_layout.setContentsMargins(4, 4, 4, 4)

        # Coordinate toggle button
        self.coord_toggle_button = QPushButton("Show Coordinates")
        self.coord_toggle_button.setCheckable(True)
        self.coord_toggle_button.setChecked(False)  # Start hidden until user toggles on
        self.coord_toggle_button.clicked.connect(self.toggle_coordinate_display)
        self.coord_toggle_button.setStyleSheet(self.get_button_style())
        coord_layout.addWidget(self.coord_toggle_button)

        layout.addWidget(coord_group)

        # Background color swatch group
        bg_group = QFrame()
        bg_group.setStyleSheet(self.get_group_style())
        bg_layout = QVBoxLayout(bg_group)
        bg_layout.setContentsMargins(4, 4, 4, 4)
        bg_layout.setSpacing(6)

        bg_label = QLabel("Brand Color")
        bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_label.setStyleSheet(self.get_label_style())
        bg_layout.addWidget(bg_label)

        self.bg_color_display = QLabel(self.bg_color_hex.upper())
        self.bg_color_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_color_display.setFixedHeight(36)
        self.bg_color_display.setStyleSheet("""
            QLabel {
                border: 1px solid #4b5563;
                border-radius: 6px;
                font-weight: 600;
                color: #e5e7eb;
                background: #1f2937;
            }
        """)
        bg_layout.addWidget(self.bg_color_display)

        layout.addWidget(bg_group)
        self.update_bg_color_display(self.bg_color_hex)

        # App logo in its own area (no frame) under the coordinates group
        try:
            self.app_logo_label = QLabel()
            self.app_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.app_logo_label.setStyleSheet(
                "QLabel { background: transparent; border: none; }"
            )
            self.app_logo_label.setFixedHeight(200)
            self.app_logo_label.setFixedWidth(140)
            logo_path = Path("resources/images") / "app logo.png"
            if logo_path.exists():
                pix = QPixmap(str(logo_path))
                if not pix.isNull():
                    target_h = max(24, 115)
                    scaled = pix.scaledToHeight(
                        target_h, Qt.TransformationMode.SmoothTransformation
                    )
                    self.app_logo_label.setPixmap(scaled)
                    logo_opacity = QGraphicsOpacityEffect(self.app_logo_label)
                    logo_opacity.setOpacity(
                        0.3
                    )  # 0.0 = fully transparent, 1.0 = opaque
                    self.app_logo_label.setGraphicsEffect(logo_opacity)
            layout.addWidget(self.app_logo_label)
        except Exception:
            pass

        layout.addStretch(10)

    def connect_signals(self):
        """Connect all signals"""
        if self.formation_input:
            self.formation_input.editingFinished.connect(
                self.on_formation_text_committed
            )
        if self.color_panel:
            self.color_panel.color_changed.connect(self.on_color_changed)

    def on_formation_text_committed(self):
        """Normalize manual formation input, validate, and emit change event."""
        if self._formation_formatting or not self.formation_input:
            return
        raw = self.formation_input.text().strip()
        formatted = self._format_formation_text(raw)
        if formatted == "Select Formation":
            self._formation_formatting = True
            self.formation_input.clear()
            self._formation_formatting = False
            self._last_valid_formation = "Select Formation"
            self.on_formation_changed(formatted)
            return

        is_valid, error_msg = self._validate_formation_digits(formatted)
        if not is_valid:
            self._show_warning_dialog("Invalid Formation", error_msg)
            self._formation_formatting = True
            if self._last_valid_formation == "Select Formation":
                self.formation_input.clear()
            else:
                self.formation_input.setText(self._last_valid_formation)
            self._formation_formatting = False
            return

        self._formation_formatting = True
        self.formation_input.setText(formatted)
        self._formation_formatting = False
        self._last_valid_formation = formatted
        self.on_formation_changed(formatted)

    @staticmethod
    def _format_formation_text(text: str) -> str:
        digits = re.findall(r"\d", text)[:5]
        if not digits:
            return "Select Formation"
        return "-".join(digits)

    @staticmethod
    def _validate_formation_digits(formatted: str) -> tuple[bool, str]:
        digits = formatted.split("-")
        if not (1 <= len(digits) <= 5):
            return (
                False,
                "Please enter between 1 and 5 single-digit numbers (e.g. 4-3-3-0-0).",
            )
        try:
            ints = [int(d) for d in digits]
        except ValueError:
            return False, "Formation must contain only digits."
        if any(d < 0 or d > 9 for d in ints):
            return False, "Each number must be between 0 and 9."
        if sum(ints) != 10:
            return False, "The numbers must sum to 10 (goalkeeper excluded)."
        return True, ""

    def cycle_kit(self):
        """Cycle through kit options when button is clicked"""
        try:
            # Don't cycle if button is disabled (no kits loaded)
            if not self.kit_button or not self.kit_button.isEnabled():
                return
            self.current_kit_index = (self.current_kit_index + 1) % len(
                self.kit_options
            )
            new_kit = self.kit_options[self.current_kit_index]
            self.kit_button.setText(new_kit)
            # This is a user action, not a load, so is_loading=False
            self.on_kit_changed(new_kit, is_loading=False)
        except Exception as e:
            print(f"Error cycling kit: {e}")
            traceback.print_exc()

    def on_kit_changed(self, kit_type: str, is_loading: bool = False):
        """Handle kit type changes

        Args:
            kit_type: The new kit type (e.g., "Home Kit", "Away Kit", "Third Kit")
            is_loading: If True, this is a load operation and we should NOT save to pool
        """
        try:
            print(f"Kit changed to: {kit_type} (is_loading={is_loading})")
            self.load_jersey_image()

            # Only save to pool if this is an actual user change, not a load operation
            if not is_loading:
                # Find MatchSetupTab to save to pool
                team_panel = self._find_team_panel_parent()
                if team_panel:
                    match_setup_tab = team_panel.parent()
                    while match_setup_tab and not hasattr(
                        match_setup_tab, "pool_a_kit_index"
                    ):
                        match_setup_tab = match_setup_tab.parent()  # type: ignore[union-attr]

                    if match_setup_tab:
                        current_source = getattr(team_panel, "current_data_source", "")
                        # Save kit index to appropriate pool
                        if current_source == "Team A":
                            setattr(
                                match_setup_tab,
                                "pool_a_kit_index",
                                self.current_kit_index,
                            )
                            print(
                                f"Saved kit index {self.current_kit_index} to Team A pool"
                            )
                        elif current_source == "Team B":
                            setattr(
                                match_setup_tab,
                                "pool_b_kit_index",
                                self.current_kit_index,
                            )
                            print(
                                f"Saved kit index {self.current_kit_index} to Team B pool"
                            )

            self.kit_changed.emit(kit_type)
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling kit change: {e}")
            traceback.print_exc()

    def _find_team_panel_parent(self):
        """Traverse widget hierarchy to find TeamPanel parent"""
        widget = self.parent()
        while widget:
            # Check if this widget has player_table attribute (TeamPanel has it)
            if hasattr(widget, "player_table"):
                return widget
            widget = widget.parent()
        return None

    def on_formation_changed(self, formation: str):
        """Handle formation changes"""
        try:
            print(
                f"[ControlPanel] Formation changed to: {formation} in {self.team_name}"  # noqa: F541
            )

            # Allow "Select Formation" to be selected without validation
            if formation == "Select Formation":
                print("[ControlPanel] Allowing 'Select Formation' selection")
                self.formation_changed.emit(formation)
                self.data_changed.emit()
                return

            # For actual formations, check if 11 players are selected
            # Traverse up to find TeamPanel (which has player_table)
            team_panel = self._find_team_panel_parent()
            selected_count = 0
            player_table = (
                getattr(team_panel, "player_table", None) if team_panel else None
            )
            if player_table is not None:
                selected_count = player_table.get_selected_count()
                print(f"[ControlPanel] Selected players count: {selected_count}/11")
            else:
                print(
                    f"[ControlPanel] Warning: Could not access player_table. TeamPanel: {team_panel}, has player_table: {hasattr(team_panel, 'player_table') if team_panel else False}"
                )

            if selected_count != 11:
                # Show warning popup
                msg_text = (
                    f"Please select exactly 11 players before changing formation.\n"
                    f"Current selection: {selected_count}/11"
                )
                self._show_warning_dialog("Insufficient Players", msg_text)
                # Reset to previous formation
                if self.formation_input:
                    self.formation_input.blockSignals(True)
                    previous_formation = "Select Formation"
                    if team_panel:
                        current_source = getattr(team_panel, "current_data_source", "")
                        if current_source == "Team A":
                            previous_formation = getattr(
                                team_panel, "team_a_formation", "Select Formation"
                            )
                        elif current_source == "Team B":
                            previous_formation = getattr(
                                team_panel, "team_b_formation", "Select Formation"
                            )
                    if previous_formation == "Select Formation":
                        self.formation_input.clear()
                    else:
                        self.formation_input.setText(previous_formation)
                    self.formation_input.blockSignals(False)
                print(
                    f"[ControlPanel] Formation change blocked - only {selected_count} players selected"
                )
                return

            print("[ControlPanel] Validation passed, emitting formation_changed signal")
            self.formation_changed.emit(formation)
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling formation change: {e}")
            traceback.print_exc()

    def on_color_changed(self):
        """Handle color changes"""
        try:
            if self.color_panel:
                c1, c2, mode = self.color_panel.get_colors()
                # Update team color in team_panel if available
                team_panel = self._find_team_panel_parent()
                if team_panel:
                    # Determine current data source
                    current_source = getattr(team_panel, "current_data_source", "")
                    if current_source == "Team A":
                        setattr(team_panel, "team_a_color_1", c1)
                    elif current_source == "Team B":
                        setattr(team_panel, "team_b_color_1", c1)

                    # Update content panel
                    content_panel = getattr(team_panel, "content_panel", None)
                    if content_panel is not None:
                        content_panel.update_team_color(c1)

                    # Sync with sibling panel
                    if hasattr(team_panel, "parent"):
                        match_setup_tab = team_panel.parent()
                        while match_setup_tab and not hasattr(
                            match_setup_tab, "home_team_panel"
                        ):
                            match_setup_tab = match_setup_tab.parent()  # type: ignore[union-attr]

                        home_team_panel = (
                            getattr(match_setup_tab, "home_team_panel", None)
                            if match_setup_tab
                            else None
                        )
                        away_team_panel = (
                            getattr(match_setup_tab, "away_team_panel", None)
                            if match_setup_tab
                            else None
                        )
                        if home_team_panel is not None and away_team_panel is not None:
                            sibling = None
                            if home_team_panel is not team_panel:
                                sibling = home_team_panel
                            elif away_team_panel is not team_panel:
                                sibling = away_team_panel

                            sibling_content_panel = (
                                getattr(sibling, "content_panel", None)
                                if sibling
                                else None
                            )
                            if sibling_content_panel is not None:
                                if (
                                    getattr(sibling, "current_data_source", "")
                                    == current_source
                                ):
                                    if current_source == "Team A":
                                        setattr(sibling, "team_a_color_1", c1)
                                    else:
                                        setattr(sibling, "team_b_color_1", c1)
                                    sibling_content_panel.update_team_color(c1)

            self.color_changed.emit()
            self.data_changed.emit()
        except Exception as e:
            print(f"Error handling color change: {e}")
            traceback.print_exc()

    def load_jersey_image(self):
        """Load and display jersey image based on kit type or stored kit_image from JSON"""
        try:

            def resolve_image_path(filename: Optional[str]) -> Optional[Path]:
                """Resolve kit filename to an existing Path."""
                if not filename:
                    return None
                # Support @ prefix (like other resources)
                clean_name = filename[1:] if filename.startswith("@") else filename
                candidates = [
                    Path("resources/images") / filename,
                    Path("resources/images") / clean_name,
                    Path("resources/images/jersey") / filename,
                    Path("resources/images/jersey") / clean_name,
                    Path(filename),
                    Path(clean_name),
                ]
                for candidate in candidates:
                    if candidate.exists():
                        return candidate
                return None

            image_path: Optional[Path] = None
            team_panel = self._find_team_panel_parent()

            # Prefer explicit kits array when available
            kits = []
            team_data = getattr(team_panel, "team_data", None) if team_panel else None
            if team_panel and isinstance(team_data, dict):
                kits = team_data.get("kits", []) or []

            if kits and self.kit_button:
                kit_type_map = {
                    "Home Kit": "home",
                    "Away Kit": "away",
                    "Third Kit": "third",
                }
                selected_label = self.kit_button.text() or "Home Kit"
                selected_type = kit_type_map.get(selected_label, "home")
                kit = next((k for k in kits if k.get("type") == selected_type), None)
                if not kit:
                    # Fallback to home kit if selected type missing
                    kit = next((k for k in kits if k.get("type") == "home"), None)
                if kit:
                    image_path = resolve_image_path(kit.get("image"))

            # Fallback to single kit_image stored on the team (default kit)
            if not image_path or not image_path.exists():
                if team_panel:
                    kit_image_filename = None
                    current_source = getattr(team_panel, "current_data_source", "")
                    team_a_kit_image = getattr(team_panel, "team_a_kit_image", None)
                    team_b_kit_image = getattr(team_panel, "team_b_kit_image", None)
                    if current_source == "Team A" and team_a_kit_image:
                        kit_image_filename = team_a_kit_image
                    elif current_source == "Team B" and team_b_kit_image:
                        kit_image_filename = team_b_kit_image
                    image_path = resolve_image_path(kit_image_filename) or image_path

            # Final fallback to known filenames by kit label
            if (not image_path or not image_path.exists()) and self.kit_button:
                kit_type = self.kit_button.text() if self.kit_button else "Home Kit"
                kit_images = {
                    "Home Kit": [
                        "home_kit.png",
                        "Home_kit.png",
                        "homekit.png",
                        "Homekit.png",
                    ],
                    "Away Kit": [
                        "away_kit.png",
                        "Awaykit.png",
                        "awaykit.png",
                        "Away_kit.png",
                    ],
                    "Third Kit": [
                        "third_kit.png",
                        "Third_kit.png",
                        "thirdkit.png",
                        "Thirdkit.png",
                    ],
                }
                filename_variants = kit_images.get(kit_type, ["home_kit.png"])
                for filename in filename_variants:
                    candidate = resolve_image_path(filename)
                    if candidate:
                        image_path = candidate
                        break

            # Absolute last resort placeholder
            if not image_path or not image_path.exists():
                image_path = resolve_image_path("jersey.png")

            if image_path and image_path.exists() and self.image_label is not None:
                pixmap = QPixmap(str(image_path))
                if not pixmap.isNull():
                    # Scale the image to fit the label
                    scaled_pixmap = pixmap.scaled(
                        self.image_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                    print(f"Loaded kit image: {image_path} for {self.team_name}")
                    try:
                        c1, c2, mode = extract_top_colors(str(image_path))
                        if self.color_panel:
                            self.color_panel.update_colors(
                                c1,
                                c2 if c2 is not None and mode == "double" else c1,
                                mode,
                            )
                            # Propagate change to field and pools
                            self.on_color_changed()
                    except Exception as _e:
                        print(f"Color extraction failed for {image_path}: {_e}")
                    try:
                        bg_hex = extract_bottom_left_color(str(image_path))
                        self.update_bg_color_display(bg_hex)
                    except Exception as _bg_err:
                        print(
                            f"Background color extraction failed for {image_path}: {_bg_err}"
                        )
                else:
                    if self.image_label is not None:
                        self.image_label.setText("Image\nLoad Error")
                    self.update_bg_color_display("#000000")
            else:
                if self.image_label is not None:
                    self.image_label.setText("Kit image\nNot Found")
                self.update_bg_color_display("#000000")

        except Exception as e:
            print(f"Error loading jersey image: {e}")
            traceback.print_exc()
            if self.image_label:
                self.image_label.setText("Image\nLoad Error")
            self.update_bg_color_display("#000000")

    def toggle_coordinate_display(self):
        """Toggle coordinate display for player markers"""
        if self.coord_toggle_button is None:
            print(f"[ControlPanel] ERROR: coord_toggle_button is None!")
            return
        show_coords = self.coord_toggle_button.isChecked()
        print(
            f"[ControlPanel] Toggling coordinate display: {show_coords} in {self.team_name}"
        )

        # Update button text
        if show_coords:
            self.coord_toggle_button.setText("Hide Coordinates")
        else:
            self.coord_toggle_button.setText("Show Coordinates")

        # Update content panel - traverse up to find TeamPanel
        current = self.parent()
        team_panel = None
        attempts = 0
        while current and attempts < 5:
            print(
                f"[ControlPanel] Checking parent {attempts}: {current} ({type(current).__name__})"
            )
            if hasattr(current, "content_panel"):
                team_panel = current
                break
            current = current.parent() if hasattr(current, "parent") else None
            attempts += 1

        if team_panel:
            content_panel = team_panel.content_panel
            print(f"[ControlPanel] Found content_panel: {content_panel}")
            print(f"[ControlPanel] Calling set_coordinate_display({show_coords})")
            content_panel.set_coordinate_display(show_coords)
        else:
            print(
                f"[ControlPanel] ERROR: Could not find TeamPanel with content_panel attribute!"
            )

        # Emit data changed signal
        self.data_changed.emit()

    def get_panel_style(self, panel_type: str) -> str:
        """Get styling for different panel types"""
        base_style = """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
                margin: 5px;
            }
        """

        if panel_type == "left":
            return (
                base_style
                + """
                QFrame {
                    max-width: 780px;
                }
            """
            )
        elif panel_type == "right":
            return base_style
        elif panel_type == "control":
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f2937, stop:1 #111827);
                    border: 1px solid #4b5563;
                    border-radius: 6px;
                    margin: 2px;
                }
            """
        else:
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #374151, stop:1 #1f2937);
                    border: 1px solid #4b5563;
                    border-radius: 6px;
                    margin: 2px;
                }
            """

    def get_group_style(self) -> str:
        """Get styling for group frames"""
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 8px;
                margin: 1px;
            }
        """

    def get_label_style(self) -> str:
        """Get styling for labels"""
        return """
            QLabel {
                border: none;
                background: transparent;
                color: #e5e7eb;
                font-size: 12px;
                font-weight: 600;
                padding: 2px;
            }
        """

    def get_lineedit_style(self) -> str:
        """Get styling for formation text input."""
        return """
            QLineEdit {
                background: #0f172a;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 6px 10px;
                color: #e5e7eb;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """

    def get_combobox_style(self) -> str:
        """Get styling for combo boxes"""
        return """
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: none;
                color: #e5e7eb;
                font-size: 12px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 10px;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: url("resources/images/dropdown.png");
                width: 20px;
                height: 24px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }
            QComboBox QAbstractItemView {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border:none;
                color: #e5e7eb;
                selection-background-color: #3b82f6;
            }
        """

    def get_kit_button_style(self) -> str:
        """Get styling for kit selector button"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #3b82f6;
                border-radius: 4px;
                color: #e5e7eb;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 12px;
                min-height: 32px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #374151, stop:1 #1f2937);
                border-color: #3b82f6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #111827, stop:1 #0f172a);
                border-color: #3b82f6;
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                color: #6b7280;
                border-color: #374151;
            }
        """

    def get_image_label_style(self) -> str:
        """Get styling for image labels"""
        return """
            QLabel {
                background: #374151;
                border: 2px solid #4b5563;
                border-radius: 8px;
                color: #9ca3af;
                font-size: 10px;
                font-weight: 500;
            }
        """

    def get_button_style(self) -> str:
        """Get styling for buttons"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
                border: 1px solid #1e40af;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 #1e3a8a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1d4ed8, stop:1 #1e40af);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
                border-color: #065f46;
            }
        """

    def _show_warning_dialog(self, title: str, text: str):
        """Display a warning dialog without extra label borders."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #111827;
                color: #e5e7eb;
                border: none;
            }
            QMessageBox QLabel {
                border: none;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background: #1f2937;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 12px;
                min-width: 60px;
            }
        """)
        msg.exec()

    def update_formation(self, formation: str):
        """Update the formation input field."""
        if not self.formation_input:
            return
        self.formation_input.blockSignals(True)
        if formation and formation != "Select Formation":
            self.formation_input.setText(formation)
            self._last_valid_formation = formation
        else:
            self.formation_input.clear()
            self._last_valid_formation = "Select Formation"
        self.formation_input.blockSignals(False)

    def update_colors(self, color_1: str, color_2: str, color_mode: str):
        """Update color panel"""
        if self.color_panel:
            self.color_panel.update_colors(color_1, color_2, color_mode)

    def update_bg_color_display(self, color_hex: str):
        """Update the background color swatch below the coordinate button."""
        self.bg_color_hex = color_hex
        if not self.bg_color_display:
            return
        self.bg_color_display.setText(color_hex.upper())
        qcolor = QColor(color_hex)
        brightness = (
            0.299 * qcolor.red() + 0.587 * qcolor.green() + 0.114 * qcolor.blue()
        )
        text_color = "#111827" if brightness > 180 else "#e5e7eb"
        self.bg_color_display.setStyleSheet(f"""
            QLabel {{
                border: 1px solid #4b5563;
                border-radius: 6px;
                font-weight: 600;
                color: {text_color};
                background: {color_hex};
            }}
        """)

    def get_colors(self) -> tuple:
        """Get colors from color panel"""
        if self.color_panel:
            return self.color_panel.get_colors()
        return ("#000000", "#000000", "single")

    def set_kit_combo_enabled(self, enabled: bool):
        """Enable or disable kit button and update text"""
        if self.kit_button:
            self.kit_button.setEnabled(enabled)
            if not enabled:
                self.kit_button.setText("No kits loaded")
