"""
Content Panel Widget for Football Score Pro 2.0
Panel for displaying the football field with player positions
"""

from math import sqrt
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PlayerMarker(QGraphicsItem):
    """Graphics item for displaying a player on the field"""

    BASE_JERSEY_PATH = Path("resources/images/ground_jersey.png")
    BASE_JERSEY_PIXMAP = None
    TINT_CACHE: Dict[str, QPixmap] = {}
    JERSEY_WIDTH = 72
    JERSEY_HEIGHT = 72

    def __init__(
        self,
        player: Dict[str, Any],
        position: QPointF,
        team_color: str,
        content_panel=None,
    ):
        super().__init__()
        self.player = player
        self.position = position
        self.team_color = team_color
        self.content_panel = content_panel  # Reference to ContentPanel for flag access
        self.show_coordinates = (
            False  # Flag to control coordinate display - hidden by default
        )
        self._original_position = position  # Store original position for swap detection
        self._is_swapping = False  # Flag to prevent recursive swaps
        self._drag_start_pos = position  # Store drag start position

        # Set position and flags after all attributes are initialized
        self.setPos(position)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )  # Enable geometry change notifications

    def boundingRect(self):
        label_height = 26
        extra_height = 25 if self.show_coordinates else 0
        total_height = self.JERSEY_HEIGHT + label_height + extra_height
        width = max(self.JERSEY_WIDTH, len(self.player.get("id", "")) * 8 + 20)
        return QRectF(-width / 2, -self.JERSEY_HEIGHT, width, total_height)

    def paint(self, painter: QPainter, option, widget=None):
        jersey_pixmap = self._get_colored_jersey_pixmap()
        if jersey_pixmap and not jersey_pixmap.isNull():
            painter.drawPixmap(
                int(-jersey_pixmap.width() / 2), -self.JERSEY_HEIGHT, jersey_pixmap
            )

            # Draw jersey number on top
            painter.setPen(QPen(QColor("#ffffff"), 2))
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            painter.setFont(font)

            jersey_number = str(
                self.player.get("jersey_number", self.player.get("jersey_no", 0))
            )
            number_rect = QRectF(
                -self.JERSEY_WIDTH / 2, -self.JERSEY_HEIGHT + 20, self.JERSEY_WIDTH, 30
            )
            painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter, jersey_number)

        # Draw player name/ID below the circle
        id_font = QFont()
        id_font.setBold(True)
        id_font.setPointSize(12)
        painter.setFont(id_font)

        player_id = self.player.get("id", "")
        text_metrics = painter.fontMetrics()
        text_width = text_metrics.horizontalAdvance(player_id)
        text_height = text_metrics.height()
        padding = 8
        label_width = max(text_width + (padding * 2), self.JERSEY_WIDTH)
        label_height = text_height + (padding * 1.5)
        label_x = -label_width / 2
        label_y = 5
        id_rect = QRectF(label_x, label_y, label_width, label_height)

        # Use black text for better visibility on green background
        painter.setPen(QColor("#000000"))
        painter.drawText(id_rect, Qt.AlignmentFlag.AlignCenter, player_id)

        # Draw coordinates if enabled
        if self.show_coordinates:
            coord_font = QFont()
            coord_font.setBold(True)
            coord_font.setPointSize(8)
            painter.setFont(coord_font)

            # Get current position relative to field center (0,0)
            pos = self.pos()
            scene = self.scene()
            if scene:
                scene_rect = scene.sceneRect()
                field_center_x = scene_rect.width() / 2.0
                field_center_y = scene_rect.height() / 2.0

                # Calculate coordinates relative to field center
                x_coord = int(pos.x() - field_center_x)
                y_coord = int(pos.y() - field_center_y)
            else:
                # Fallback to absolute coordinates if no scene
                x_coord = int(pos.x())
                y_coord = int(pos.y())

            coord_text = f"({x_coord}, {y_coord})"

            # Draw coordinate text below player name
            coord_text_metrics = painter.fontMetrics()
            coord_text_width = coord_text_metrics.horizontalAdvance(coord_text)
            coord_text_height = coord_text_metrics.height()
            coord_padding = 4
            coord_label_width = coord_text_width + (coord_padding * 2)
            coord_label_height = coord_text_height + (coord_padding * 1)
            coord_label_x = -coord_label_width / 2
            coord_label_y = label_y + label_height + 5

            # Draw coordinate text with subtle outline for readability on the field
            coord_text_rect = QRectF(
                coord_label_x, coord_label_y, coord_label_width, coord_label_height
            )
            # Shadow stroke
            painter.setPen(QPen(QColor(0, 0, 0, 180), 2))
            painter.drawText(coord_text_rect, Qt.AlignmentFlag.AlignCenter, coord_text)
            # Foreground text
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawText(coord_text_rect, Qt.AlignmentFlag.AlignCenter, coord_text)

    @classmethod
    def _load_base_pixmap(cls):
        if cls.BASE_JERSEY_PIXMAP is None and cls.BASE_JERSEY_PATH.exists():
            pixmap = QPixmap(str(cls.BASE_JERSEY_PATH))
            if not pixmap.isNull():
                cls.BASE_JERSEY_PIXMAP = pixmap

    def _get_colored_jersey_pixmap(self) -> Optional[QPixmap]:
        self._load_base_pixmap()
        if not self.BASE_JERSEY_PIXMAP:
            return None

        color_hex = self.team_color or "#2563eb"
        cached = self.TINT_CACHE.get(color_hex)
        if cached:
            return cached

        tinted = QPixmap(self.BASE_JERSEY_PIXMAP.size())
        tinted.fill(Qt.GlobalColor.transparent)

        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, self.BASE_JERSEY_PIXMAP)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color_hex))
        painter.end()

        scaled = tinted.scaled(
            self.JERSEY_WIDTH,
            self.JERSEY_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.TINT_CACHE[color_hex] = scaled
        return scaled

    def _invalidate_cache(self):
        # Force re-tint on next paint when color changes
        if hasattr(self, "team_color") and self.team_color in self.TINT_CACHE:
            self.TINT_CACHE.pop(self.team_color, None)

    def mousePressEvent(self, event):
        """Store starting position when drag begins"""
        self._drag_start_pos = self.pos()
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Check for collisions and swap when player is released"""
        event.accept()

        if not self._is_swapping:
            swapped = False
            # Check for collisions with other PlayerMarker items at release position
            # Use a slightly larger bounding rect for easier collision detection
            collision_rect = self.boundingRect()
            collision_rect.adjust(-10, -10, 10, 10)  # Add padding for easier collision

            # Get all items in the scene that intersect with our position
            scene = self.scene()
            if scene:
                items_at_pos = scene.items(self.pos())
                for item in items_at_pos:
                    if (
                        isinstance(item, PlayerMarker)
                        and item != self
                        and not item._is_swapping
                    ):
                        # Found another player - swap positions
                        self._swap_positions(item)
                        swapped = True
                        break

            # If player was moved (not swapped), mark as manually positioned
            if not swapped and hasattr(self, "_drag_start_pos"):
                # Check if position actually changed
                if self.pos() != self._drag_start_pos:
                    if self.content_panel and hasattr(
                        self.content_panel, "players_manually_positioned"
                    ):
                        self.content_panel.players_manually_positioned = True
                        print("Player manually moved - formation will not auto-reset")

        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """Handle position changes"""
        return super().itemChange(change, value)

    def _swap_positions(self, other_marker):
        """Swap positions with another player marker

        When player A is dragged onto player B:
        - Player A moves to Player B's position
        - Player B automatically moves to Player A's original position
        """
        if self._is_swapping or other_marker._is_swapping:
            return

        self._is_swapping = True
        other_marker._is_swapping = True

        try:
            # Get the dragged player's ORIGINAL position (before dragging started)
            my_original_pos = getattr(self, "_drag_start_pos", self.pos())
            # Get the target player's current position
            other_pos = other_marker.pos()

            # The dragged player (self) goes to the target's position
            # The target player goes to the dragged player's ORIGINAL position
            self.setPos(other_pos)
            other_marker.setPos(my_original_pos)

            # Update stored positions
            self.position = other_pos
            other_marker.position = my_original_pos

            # Mark that players have been manually positioned
            if self.content_panel and hasattr(
                self.content_panel, "players_manually_positioned"
            ):
                self.content_panel.players_manually_positioned = True
                print(
                    "Marked players as manually positioned - formation will not auto-reset"
                )

            player_a_num = self.player.get(
                "jersey_number", self.player.get("jersey_no", "?")
            )
            player_b_num = other_marker.player.get(
                "jersey_number", other_marker.player.get("jersey_no", "?")
            )
            print(
                f"Swapped players: {player_a_num} (moved to {other_marker.player.get('position', '?')} position) <-> {player_b_num} (moved to {self.player.get('position', '?')} position)"
            )
        finally:
            # Reset flags after a short delay
            QTimer.singleShot(100, lambda: setattr(self, "_is_swapping", False))
            QTimer.singleShot(100, lambda: setattr(other_marker, "_is_swapping", False))


class ContentPanel(QWidget):
    """Panel for displaying the football field with player positions"""

    formation_applied = Signal(str)

    def __init__(self, team_name: str, parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self.formation = "Select Formation"
        self.selected_players = []
        self.team_color = "#2563eb"
        self.player_markers = []
        self.selected_markers = set()
        self.formation_state = {}
        self.show_coordinates = (
            False  # Initialize coordinate display as hidden by default
        )
        self.manager_text_item = None  # Manager label on the field
        self.players_manually_positioned = (
            False  # Flag to track if players have been manually moved/swapped
        )
        self.field_frame = None  # Will be set in setup_ui
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setup_ui()

    def setup_ui(self):
        """Setup the content panel UI"""
        frame = QFrame()
        self.field_frame = frame  # Store reference for border updates
        frame.setStyleSheet(self.get_field_style())

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet(
            "QGraphicsView { border: none; background: transparent; }"
        )
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Remove fixed minimum size - allow view to scale to fit available space
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # Set a reasonable minimum size hint based on scene, but allow smaller
        self.view.setMinimumSize(
            400, 300
        )  # Allow much smaller minimum to prevent overflow
        # Ensure identical presentation across panels
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # Set a consistent scene rectangle for all panels - moderately larger for good visibility
        # This ensures both home and away team panels have the same ground size
        STANDARD_FIELD_WIDTH = 1000  # Moderately larger than original 800
        STANDARD_FIELD_HEIGHT = 750  # Moderately larger than original 600
        self.scene.setSceneRect(0, 0, STANDARD_FIELD_WIDTH, STANDARD_FIELD_HEIGHT)

        # Try to load ground image
        ground_path = Path("resources/images/Ground.png")
        if ground_path.exists():
            try:
                pixmap = QPixmap(str(ground_path))
                if not pixmap.isNull():
                    field_item = self.scene.addPixmap(pixmap)
                    field_item.setZValue(0)
                    # Center the image in the scene
                    field_item.setPos(
                        (STANDARD_FIELD_WIDTH - pixmap.width()) / 2,
                        (STANDARD_FIELD_HEIGHT - pixmap.height()) / 2,
                    )
                else:
                    self.set_placeholder_text("Failed to load Ground.png")
            except Exception as e:
                print(f"Error loading image {ground_path}: {e}")
                self.set_placeholder_text("Error loading Ground.png")
        else:
            self.set_placeholder_text("Ground.png not found")

        layout.addWidget(self.view)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Add Manager label to the bottom-left corner of the field
        self._add_manager_label_to_field()

        # Set initial scaling to fit the view properly
        QTimer.singleShot(100, self.update_view_scaling)

        # Update border based on player count
        self._update_border_state()

    def _update_border_state(self):
        """Update border color based on number of selected players"""
        player_count = len(self.selected_players)

        if player_count >= 11:
            # Show normal field with no border
            if self.field_frame:
                self.field_frame.setStyleSheet(self.get_field_style())
        else:
            # Show red border (no blinking)
            if self.field_frame:
                self.field_frame.setStyleSheet(self.get_field_style(incomplete=True))

    def set_placeholder_text(self, text: str):
        """Set placeholder text when image is not available"""
        label = QLabel(f"{text}\n\nPlace your Ground.png file in:\nresources/images/")
        label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 14px;
                font-weight: 500;
                text-align: center;
                padding: 20px;
                border: 2px dashed #4b5563;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
            }
        """)
        label.setWordWrap(True)
        self.scene.addWidget(label)

    def update_selected_players(self, players: List[Dict[str, Any]]):
        """Old-app parity: preserve positions for still-selected players; diff changes"""
        try:
            print(
                f"[ContentPanel] update_selected_players called with {len(players)} players"
            )

            def _player_key(p: Dict[str, Any]) -> str:
                return f"{p.get('id') or ''}|{p.get('jersey_number', p.get('jersey_no', ''))}|{p.get('full_name', p.get('name', ''))}"

            # Build maps for new selection
            new_players_by_key = {_player_key(p): p for p in (players or [])}

            # Map existing markers by the same key
            existing_by_key = {}
            for m in list(self.player_markers):
                try:
                    key = _player_key(m.player)
                except Exception:
                    key = None
                if key:
                    existing_by_key[key] = m

            # Remove markers for deselected players
            for key, m in list(existing_by_key.items()):
                if key not in new_players_by_key:
                    self.scene.removeItem(m)
                    if m in self.player_markers:
                        self.player_markers.remove(m)
                    existing_by_key.pop(key, None)

            # Add markers for newly selected players at center
            rect = self.scene.sceneRect()
            cx = rect.width() / 2.0
            cy = rect.height() / 2.0
            for key, p in new_players_by_key.items():
                if key not in existing_by_key:
                    pos = QPointF(cx, cy)
                    marker = PlayerMarker(p, pos, self.team_color, self)
                    marker.show_coordinates = getattr(self, "show_coordinates", False)
                    self.scene.addItem(marker)
                    self.player_markers.append(marker)
                    existing_by_key[key] = marker
                else:
                    # Ensure marker holds latest player reference and color
                    existing_by_key[key].player = p
                    existing_by_key[key].team_color = self.team_color

            # Update internal selection list
            self.selected_players = players

            # Update border state based on player count
            self._update_border_state()

            if self.formation == "Select Formation":
                self.clear_field()
                return
            # Apply formation only when exactly 11 and valid, AND players haven't been manually positioned
            if (
                len(players) == 11
                and self.formation != "Select Formation"
                and not self.players_manually_positioned
            ):
                self.apply_formation_to_players(self.formation)
                print(
                    f"[ContentPanel] Applied formation {self.formation} to {len(players)} players"
                )
            elif self.players_manually_positioned:
                print(
                    "[ContentPanel] Skipping formation application - players have been manually positioned"
                )
            else:
                print(
                    f"[ContentPanel] Showing {len(players)} players without formation (formation={self.formation})"
                )

            self.scene.update()
        except Exception as e:
            print(f"[ContentPanel] Error in update_selected_players: {e}")
            import traceback

            traceback.print_exc()

    def update_team_color(self, color: str):
        """Update team color for player markers"""
        self.team_color = color
        # Update existing markers with new color
        for marker in self.player_markers:
            marker.team_color = color
            marker._invalidate_cache()
            marker.update()
        self.scene.update()

    def toggle_coordinate_display(self, show: Optional[bool] = None):
        """Toggle coordinate display for all player markers"""
        if show is None:
            # Toggle current state
            show = not getattr(self, "show_coordinates", False)

        self.show_coordinates = show

        # Update all existing markers
        for marker in self.player_markers:
            if hasattr(marker, "show_coordinates"):
                marker.show_coordinates = show

        # Force update
        self.scene.update()

    def set_coordinate_display(self, show: bool):
        """Set coordinate display for all player markers"""
        self.toggle_coordinate_display(show)

    def update_player_positions(self):
        """Update player positions based on formation and selected players"""
        # Clear existing markers
        for marker in self.player_markers:
            self.scene.removeItem(marker)
        self.player_markers.clear()

        # Only show players if we have both players and a valid formation
        if (
            not self.selected_players
            or self.formation == "Select Formation"
            or not self.formation
        ):
            return

        # Get formation positions and create new markers
        positions = self.get_formation_positions(self.formation)
        for i, player in enumerate(self.selected_players[:11]):
            if i < len(positions):
                position = positions[i]
                # Create new player marker with updated visual style
                marker = PlayerMarker(player, position, self.team_color)
                # Set coordinate display setting
                marker.show_coordinates = getattr(self, "show_coordinates", True)
                self.scene.addItem(marker)
                self.player_markers.append(marker)

        # Force visual update without rescaling to prevent shrinking
        self.scene.update()

    def apply_formation(self, formation: str):
        """Apply formation with advanced positioning logic"""
        try:
            if formation == "Select Formation":
                return
            if len(self.selected_players) == 11:
                self.formation = formation
                self.formation_state["formation"] = formation
                self.apply_formation_to_players(formation)
                self.formation_applied.emit(formation)
            else:
                self.formation = formation
                self.formation_state["formation"] = formation
        except Exception as e:
            print(f"Error in apply_formation: {str(e)}")

    def apply_formation_silent(self, formation: str):
        """Apply formation without showing warnings (for automatic application)"""
        try:
            if formation == "Select Formation":
                return
            if len(self.selected_players) == 11:
                self.formation = formation
                self.formation_state["formation"] = formation
                self.apply_formation_to_players(formation)
                self.formation_applied.emit(formation)
            else:
                self.formation = formation
                self.formation_state["formation"] = formation
        except Exception as e:
            print(f"Error in apply_formation_silent: {str(e)}")

    def update_formation(self, formation: str):
        """Update formation without applying it immediately (let update_selected_players handle application)"""
        try:
            print(f"[ContentPanel] update_formation called with: {formation}")
            self.formation = formation
            self.formation_state["formation"] = formation
            # Don't apply formation here - let update_selected_players handle it
            print(
                f"[ContentPanel] Formation updated to {formation}, waiting for players to be set"
            )
        except Exception as e:
            print(f"[ContentPanel] Error in update_formation: {e}")
            import traceback

            traceback.print_exc()

    # (Removed duplicate update_selected_players implementation)

    def apply_formation_to_players(
        self,
        formation: str,
        marker_d_override: Optional[float] = None,
    ):
        """Mirror old app: center-relative lanes + closest-assignment; set marker centers"""
        try:
            print(f"[ContentPanel] apply_formation_to_players called with: {formation}")
            if formation == "Select Formation":
                return

            try:
                layers = [int(n) for n in formation.split("-")]
                # expected_players = sum(layers) + 1  # include GK (unused)
            except Exception:
                print(f"Invalid formation format: {formation}")
                return

            sel_count = len(self.selected_players)
            if sel_count == 0:
                return

            # Scene center
            rect = self.scene.sceneRect()
            center_x = rect.width() / 2.0
            center_y = rect.height() / 2.0

            # 1) Build target positions (center-relative like old app)
            positions = [(0, -300)]  # GK
            total_layers = 1 + len(layers)
            if total_layers < 2:
                print(f"Invalid formation: {formation} has no field layers")
                return

            y_step = 750 / total_layers
            y_positions = [-350 + (i + 1) * y_step for i in range(len(layers))]
            max_players = max(layers) if layers else 1
            spacing = 700 / (max_players - 1) if max_players > 1 else 0

            for layer_idx, num_players in enumerate(layers):
                y = y_positions[layer_idx]
                if num_players <= 0:
                    continue
                if num_players == 1:
                    xs = [0]
                else:
                    if num_players % 2 == 1:
                        mid = num_players // 2
                        xs = [0.0] * num_players
                        for i in range(mid):
                            xs[mid - (i + 1)] = int(-(i + 1) * spacing)
                            xs[mid + (i + 1)] = int((i + 1) * spacing)
                    else:
                        start_x = -(num_players - 1) * spacing / 2
                        xs = [start_x + i * spacing for i in range(num_players)]
                for x in xs:
                    positions.append((int(x), int(y)))

            if len(positions) > sel_count:
                positions = positions[:sel_count]

            # 2) Current marker centers in center-relative coords
            markers = list(self.player_markers)
            marker_centers = []
            for m in markers:
                # br = m.boundingRect()  # unused
                mx = m.x()
                my = m.y()
                marker_centers.append((m, int(mx - center_x), int(my - center_y)))

            # 3) Closest assignment (using sqrt like old app)
            available = positions.copy()
            assignments = []
            for m, lx, ly in marker_centers:
                min_dist = float("inf")
                best = None
                best_idx = -1
                for i, (px, py) in enumerate(available):
                    dist = sqrt((lx - px) ** 2 + (ly - py) ** 2)
                    if dist < min_dist:
                        min_dist = dist
                        best = (px, py)
                        best_idx = i
                if best is not None:
                    assignments.append((m, best))
                    available.pop(best_idx)

            # 4) Apply center coordinates (invert Y to match inverted ground image)
            final_centers = []
            for m, (rx, ry) in assignments:
                ry = -ry
                cx = center_x + rx
                cy = center_y + ry
                final_centers.append((int(cx), int(cy)))

            # Fill any missing with true center
            while len(final_centers) < sel_count:
                final_centers.append((int(center_x), int(center_y)))

            self.update_player_markers_with_positions(final_centers)
            self.save_formation_state()
        except Exception as e:
            print(f"Error in apply_formation_to_players: {e}")

    def update_player_markers_with_positions(self, positions: List[tuple]):
        """Update player markers with calculated positions"""
        try:
            # Clear existing markers
            for marker in self.player_markers:
                self.scene.removeItem(marker)
            self.player_markers.clear()

            # Create new markers with updated positions
            for i, (player, (x, y)) in enumerate(zip(self.selected_players, positions)):
                position = QPointF(x, y)
                # Create new marker with improved visual style
                marker = PlayerMarker(player, position, self.team_color)
                # Set coordinate display setting
                marker.show_coordinates = getattr(self, "show_coordinates", False)
                self.scene.addItem(marker)
                self.player_markers.append(marker)

            # Force scene update without rescaling to prevent shrinking
            self.scene.update()
        except Exception as e:
            print(f"Error updating player markers: {str(e)}")

    def save_formation_state(self):
        """Save current formation state"""
        try:
            state = {"formation": self.formation, "player_positions": []}
            for marker in self.player_markers:
                pos = marker.pos()
                state["player_positions"].append(
                    {
                        "player_num": marker.player.get(
                            "jersey_number", marker.player.get("jersey_no", 0)
                        ),
                        "x": pos.x(),
                        "y": pos.y(),
                    }
                )
            self.formation_state = state
        except Exception as e:
            print(f"Error saving formation state: {str(e)}")

    def get_formation_positions(self, formation: str) -> List[QPointF]:
        """Get player positions for a given formation"""
        try:
            parts = formation.split("-")
            if len(parts) >= 3:
                defenders = int(parts[0])
                midfielders = int(parts[1])
                forwards = int(parts[2])
            else:
                defenders, midfielders, forwards = 4, 4, 2
        except Exception:
            defenders, midfielders, forwards = 4, 4, 2

        positions = []
        # Use standard field dimensions for consistent positioning
        field_width = 1000  # STANDARD_FIELD_WIDTH (moderately larger than original)
        field_height = 750  # STANDARD_FIELD_HEIGHT (moderately larger than original)

        # Define field boundaries with proper margins
        margin = 50  # Slightly larger margin from field edges
        goal_box_depth = field_height * 0.11  # Slightly smaller goal box depth

        # Goalkeeper at the edge of goal box (not inside) - shifted more right
        gk_y = field_height - goal_box_depth - 15  # A bit more space from goal box
        gk_x = field_width / 2 + 30  # Shift goalkeeper 30px to the right
        positions.append(
            QPointF(gk_x, gk_y)
        )  # Center-based positioning with more right shift

        # Calculate safe field area for outfield players
        safe_width = field_width - (2 * margin)
        safe_height = field_height - goal_box_depth - (margin * 1.5)

        # Defenders closer to goalkeeper but with more spacing (defensive third) - shifted more right
        if defenders > 0:
            spacing = safe_width / (defenders + 1)
            def_y = field_height - (
                safe_height * 0.35
            )  # 35% from bottom for better spacing
            right_offset = 30  # Shift players 30px to the right
            for i in range(defenders):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, def_y))

        # Midfielders in the middle (middle third) - centered around field center, shifted more right
        if midfielders > 0:
            spacing = safe_width / (midfielders + 1)
            mid_y = field_height - (
                safe_height * 0.60
            )  # 60% from bottom for better distribution
            right_offset = 30  # Shift players 30px to the right
            for i in range(midfielders):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, mid_y))

        # Forwards at the top (attacking third) - centered around field center, shifted more right
        if forwards > 0:
            spacing = safe_width / (forwards + 1)
            fwd_y = field_height - (
                safe_height * 0.85
            )  # 85% from bottom for better attacking position
            right_offset = 30  # Shift players 30px to the right
            for i in range(forwards):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, fwd_y))

        return positions

    def clear_players(self):
        """Clear all players from the field"""
        try:
            # Clear existing markers
            for marker in self.player_markers:
                self.scene.removeItem(marker)
            self.player_markers.clear()

            # Clear selected players
            self.selected_players = []

            # Force scene update
            self.scene.update()
        except Exception as e:
            print(f"Error clearing players: {str(e)}")

    def resizeEvent(self, event):
        """Handle resize events - update scaling to fit new size"""
        super().resizeEvent(event)
        # Update scaling when widget is resized to prevent overflow
        QTimer.singleShot(50, self.update_view_scaling)

    def showEvent(self, event):
        """Handle show events - update scaling when panel becomes visible"""
        super().showEvent(event)
        # Update scaling when tab becomes visible to fit available space
        QTimer.singleShot(100, self.update_view_scaling)

    def update_view_scaling(self):
        """Scale view to fit available space without overflow"""
        if hasattr(self, "view") and self.scene.sceneRect().isValid():
            scene_rect = self.scene.sceneRect()
            self.view.resetTransform()
            # Let Qt compute the proper uniform scale to maximize the scene in the view
            self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.view.centerOn(scene_rect.center())
            QTimer.singleShot(0, self.scene.update)

    def force_update_scaling(self):
        """Force update the scaling shortly after layout changes (e.g., tab switch)"""
        # Single late pass so it wins over any earlier scaling
        QTimer.singleShot(200, self.update_view_scaling)

    def clear_field(self):
        """Clear all player markers from the field"""
        try:
            print(f"[{self.team_name}] Clearing field display...")

            # Remove all player markers
            for item in self.scene.items():
                if isinstance(item, PlayerMarker):
                    self.scene.removeItem(item)

            # Clear player markers list
            self.player_markers.clear()
            self.selected_markers.clear()

            print(f"[{self.team_name}] Field cleared successfully")

        except Exception as e:
            print(f"Error clearing field for {self.team_name}: {e}")

    def _add_manager_label_to_field(self):
        """Add Manager label to the bottom-left corner of the field"""
        try:
            # Create text item for Manager label
            manager_text = "Manager: Not Set"
            self.manager_text_item = QGraphicsTextItem(manager_text)

            # Style the manager label with larger font
            font = QFont()
            font.setPointSize(13)  # Increased from 12 to 16
            font.setBold(False)
            self.manager_text_item.setFont(font)
            self.manager_text_item.setDefaultTextColor(QColor("#ffffff"))  # White text

            # Position at bottom-left corner of the field with safe bottom margin
            # Compute text height so it doesn't get clipped by the scene boundary
            field_rect = self.scene.sceneRect()
            metrics = QFont()
            metrics.setPointSize(16)
            metrics.setBold(True)
            fm = self.view.fontMetrics() if hasattr(self, "view") else None
            text_height = (fm.height() if fm else 20) + 4
            x_pos = 10  # left margin
            y_pos = (
                field_rect.height() - text_height + 24
            )  # move slightly lower while staying inside
            self.manager_text_item.setPos(x_pos, y_pos)
            self.manager_text_item.setZValue(100)  # High z-value to appear above field

            # Add to scene
            self.scene.addItem(self.manager_text_item)
        except Exception as e:
            print(f"Error adding manager label to field: {e}")

    def update_manager_label(self, manager_text: str):
        """Update the Manager label text on the field"""
        try:
            if self.manager_text_item:
                display_text = (
                    f"Manager: {manager_text}"
                    if manager_text and manager_text != "Not Set"
                    else "Manager: Not Set"
                )
                self.manager_text_item.setPlainText(display_text)
        except Exception as e:
            print(f"Error updating manager label: {e}")

    def get_field_style(self, incomplete: bool = False) -> str:
        """Get field style with optional red border for incomplete selection"""
        if incomplete:
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    border: 3px solid #ef4444;
                    border-radius: 4px;
                }
            """
        else:
            return """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    border: none;
                    border-radius: 4px;
                }
            """
