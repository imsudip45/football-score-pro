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
            # Note: We detect collision at the current mouse position, but _swap_positions
            # will use SAVED formation positions (not random mouse position) for the swap
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
                        # The swap will use proper formation positions from global pool
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
                        # Save the new position to global pool
                        self._save_position_to_global_pool()

        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """Handle position changes and constrain to field boundaries"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Constrain position to stay within field boundaries
            scene = self.scene()
            if scene:
                scene_rect = scene.sceneRect()
                # Get marker's bounding rect to ensure entire marker stays within bounds
                bounding = self.boundingRect()
                
                # Calculate min/max allowed positions
                # Account for marker size so it doesn't go outside field
                min_x = scene_rect.left() - bounding.left()
                max_x = scene_rect.right() - bounding.right()
                min_y = scene_rect.top() - bounding.top()
                max_y = scene_rect.bottom() - bounding.bottom()
                
                # Clamp the new position value
                new_pos = value
                clamped_x = max(min_x, min(new_pos.x(), max_x))
                clamped_y = max(min_y, min(new_pos.y(), max_y))
                
                # Return clamped position
                return QPointF(clamped_x, clamped_y)
        
        return super().itemChange(change, value)

    def _save_position_to_global_pool(self):
        """Save this marker's position to the global pool"""
        if self.content_panel and hasattr(
            self.content_panel, "_save_position_to_global_pool"
        ):
            # Build player key the same way ContentPanel does
            key = self.content_panel._player_key(self.player)
            
            # CRITICAL: Always save goalkeeper at goalkeeper position, even if swapped
            if self.content_panel._is_primary_goalkeeper_player(self.player):
                pos = self.content_panel._get_goalkeeper_position()
                player_name = self.content_panel._get_player_name(self.player)
                print(
                    f"[PlayerMarker] Saving position for {player_name} (GK) - FORCED to GK position ({pos.x():.1f}, {pos.y():.1f})"
                )
            else:
                pos = self.pos()
                player_name = self.content_panel._get_player_name(self.player)

            print(
                f"[PlayerMarker] Saving position for {player_name} (key: {key}) to ({pos.x():.1f}, {pos.y():.1f})"
            )
            self.content_panel._save_position_to_global_pool(key, pos)
        else:
            print(
                "[PlayerMarker] WARNING: Could not save position - content_panel not available or method missing"
            )

    def _swap_positions(self, other_marker):
        """Swap positions with another player marker

        When player A is dragged onto player B:
        - Player A moves to Player B's SAVED formation position (not random mouse position)
        - Player B automatically moves to Player A's ORIGINAL saved position
        
        This ensures swaps always use proper formation positions, not random intermediate positions.
        """
        print(f"[PlayerMarker] _swap_positions called!")
        if self._is_swapping or other_marker._is_swapping:
            print(f"[PlayerMarker] Swap already in progress, returning")
            return

        player_a_name = self.content_panel._get_player_name(self.player) if self.content_panel else self.player.get('name', '?')
        player_b_name = self.content_panel._get_player_name(other_marker.player) if self.content_panel else other_marker.player.get('name', '?')
        print(
            f"[PlayerMarker] Starting swap between {player_a_name} and {player_b_name}"
        )
        self._is_swapping = True
        other_marker._is_swapping = True

        try:
            # Use the canonical/original formation positions for swapping.
            # This prevents accidental mouse drops from influencing the swap destination.
            my_slot = QPointF(getattr(self, "_original_position", self.pos()))
            other_slot = QPointF(
                getattr(other_marker, "_original_position", other_marker.pos())
            )

            print(
                f"[PlayerMarker] Swapping slots: {player_a_name} -> ({other_slot.x():.1f},{other_slot.y():.1f}), "
                f"{player_b_name} -> ({my_slot.x():.1f},{my_slot.y():.1f})"
            )

            # The dragged player (self) goes to the target's formation slot
            # The target player goes to the dragged player's formation slot
            self.setPos(other_slot)
            other_marker.setPos(my_slot)

            # Update stored positions
            self.position = other_slot
            other_marker.position = my_slot

            # Update canonical slots so future swaps respect new ownership
            self._original_position = QPointF(other_slot)
            other_marker._original_position = QPointF(my_slot)

            # Mark that players have been manually positioned
            print(
                f"[PlayerMarker] Checking content_panel: {self.content_panel is not None}"
            )
            if self.content_panel:
                print(
                    f"[PlayerMarker] Has players_manually_positioned attr: {hasattr(self.content_panel, 'players_manually_positioned')}"
                )

            if self.content_panel and hasattr(
                self.content_panel, "players_manually_positioned"
            ):
                self.content_panel.players_manually_positioned = True
                print(
                    "[PlayerMarker] Marked players as manually positioned - formation will not auto-reset"
                )
                
                # CRITICAL: If goalkeeper was swapped, move them back to GK position
                if self.content_panel._is_primary_goalkeeper_player(self.player):
                    gk_pos = self.content_panel._get_goalkeeper_position()
                    self.setPos(gk_pos)
                    self.position = gk_pos
                    print(
                        f"[PlayerMarker] Goalkeeper {self.content_panel._get_player_name(self.player)} moved back to GK position after swap"
                    )
                if self.content_panel._is_primary_goalkeeper_player(other_marker.player):
                    gk_pos = self.content_panel._get_goalkeeper_position()
                    other_marker.setPos(gk_pos)
                    other_marker.position = gk_pos
                    print(
                        f"[PlayerMarker] Goalkeeper {self.content_panel._get_player_name(other_marker.player)} moved back to GK position after swap"
                    )
                
                # Save both players' new positions to global pool IMMEDIATELY after swap
                # This ensures swapped positions are persisted before any other operations
                print(f"[PlayerMarker] Saving swapped position for {self.content_panel._get_player_name(self.player)}...")
                self._save_position_to_global_pool()
                print(f"[PlayerMarker] Saving swapped position for {self.content_panel._get_player_name(other_marker.player)}...")
                other_marker._save_position_to_global_pool()
                print("[PlayerMarker] Both swapped positions saved to global pool")
            else:
                print(
                    f"[PlayerMarker] ERROR: Cannot save positions - content_panel check failed!"
                )

            player_a_num = self.content_panel._get_jersey_number(self.player) if self.content_panel else "?"
            player_b_num = self.content_panel._get_jersey_number(other_marker.player) if self.content_panel else "?"
            print(
                f"Swapped players: {player_a_num} (moved to {other_marker.player.get('position', '?')} position) <-> {player_b_num} (moved to {self.player.get('position', '?')} position)"
            )
        finally:
            # Reset flags after a short delay
            QTimer.singleShot(100, lambda: setattr(self, "_is_swapping", False))
            QTimer.singleShot(100, lambda: setattr(other_marker, "_is_swapping", False))


class ContentPanel(QWidget):
    """Panel for displaying the football field with player positions"""

    # Field dimension constants
    STANDARD_FIELD_WIDTH = 1000
    STANDARD_FIELD_HEIGHT = 750

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
        self.formation_already_applied = (
            False  # Flag to prevent reapplying formation on team toggle
        )
        self._formation_just_changed = False  # Flag to track when formation was just changed by user
        self._saved_positions = {}  # Store player positions by player key (includes team prefix)
        self.current_team_source = "Team A"  # Track which team data is currently loaded
        self._scaling_timer = None  # Timer for debouncing view scaling
        self._initial_scaling_done = False  # Flag to track if initial scaling is done
        self._first_show_done = False  # Flag to track if first show event is done
        self.field_frame = None  # Will be set in setup_ui
        self._primary_goalkeeper_key = None  # Track which GK should occupy GK slot
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
        # Use full viewport updates so dragged markers repaint cleanly (prevents dotted trails/artifacts)
        # Slightly more expensive but safe for our small number of items.
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
        # Disable automatic view adjustment to prevent shaking when adding players
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

        # Set a consistent scene rectangle for all panels - moderately larger for good visibility
        # This ensures both home and away team panels have the same ground size
        self.scene.setSceneRect(0, 0, self.STANDARD_FIELD_WIDTH, self.STANDARD_FIELD_HEIGHT)

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
                        (self.STANDARD_FIELD_WIDTH - pixmap.width()) / 2,
                        (self.STANDARD_FIELD_HEIGHT - pixmap.height()) / 2,
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

    def update_selected_players(
        self, players: List[Dict[str, Any]], team_source: str = None
    ):
        """Old-app parity: preserve positions for still-selected players; diff changes"""
        try:
            import traceback

            # Store OLD team source BEFORE updating - needed to save positions to correct pool
            old_team_source = self.current_team_source
            
            # Update current team source if provided - CRITICAL for correct pool access
            if team_source:
                self.current_team_source = team_source
                if old_team_source != team_source:
                    print(
                        f"[ContentPanel {self.team_name}] Team source changed: {old_team_source} -> {team_source}"
                    )
            elif not self.current_team_source:
                # Fallback: if team_source not provided and current_team_source not set, default to Team A
                self.current_team_source = "Team A"
                old_team_source = "Team A"
                print(
                    f"[ContentPanel {self.team_name}] WARNING: team_source not provided, defaulting to Team A"
                )

            print(
                f"\n[ContentPanel {self.team_name}] ========== update_selected_players called with {len(players)} players for {self.current_team_source} =========="
            )

            # Build maps for new selection using NEW team source
            new_players_by_key = {self._player_key(p): p for p in (players or [])}

            # Determine which goalkeeper (if any) should occupy the GK slot
            self._primary_goalkeeper_key = None
            for key, player in new_players_by_key.items():
                if self._is_goalkeeper(player):
                    self._primary_goalkeeper_key = key
                    break

            # Get global pool size for debugging (using NEW team source)
            pool = self._get_position_pool()
            global_pool_size = len(pool) if pool else 0

            print(
                f"[ContentPanel {self.team_name}] Team: {self.current_team_source}, Pool has {global_pool_size} positions"
            )

            # CRITICAL: Save current screen positions to the OLD team's pool BEFORE clearing
            # This ensures positions are saved to the correct pool when switching teams
            if len(self.player_markers) > 0 and old_team_source and old_team_source != self.current_team_source:
                # Team source changed - save current positions to OLD team's pool
                print(
                    f"[DEBUG] Team source changed - saving {len(self.player_markers)} current screen positions to OLD team pool ({old_team_source})"
                )
                # Temporarily set current_team_source to old value for saving
                temp_source = self.current_team_source
                self.current_team_source = old_team_source
                for m in list(self.player_markers):
                    try:
                        key = self._player_key(m.player, old_team_source)
                        if key:
                            pos = m.pos()
                            self._save_position_to_global_pool(key, pos)
                            print(
                                f"[SAVE] {self._get_player_name(m.player)} to {old_team_source} pool at ({pos.x():.1f}, {pos.y():.1f})"
                            )
                    except Exception as e:
                        print(f"  - Error saving position: {e}")
                # Restore current team source
                self.current_team_source = temp_source
            elif global_pool_size == 0 or (self.players_manually_positioned and len(players) > 0):
                # Save current positions to pool if:
                # 1. Pool is empty (first time), OR
                # 2. Players have been manually positioned AND we have players to save
                print(
                    f"[DEBUG] Saving {len(self.player_markers)} current screen positions to pool (pool_size={global_pool_size}, manually_positioned={self.players_manually_positioned})"
                )
                for m in list(self.player_markers):
                    try:
                        key = self._player_key(m.player)
                        if key:
                            pos = m.pos()
                            self._save_position_to_global_pool(key, pos)
                            print(
                                f"[SAVE] {self._get_player_name(m.player)} at ({pos.x():.1f}, {pos.y():.1f})"
                            )
                    except Exception as e:
                        print(f"  - Error saving position: {e}")
            else:
                print(
                    f"[DEBUG] Pool has {global_pool_size} positions and players not manually positioned - NOT overwriting with screen positions"
                )

            # Remove positions for players that were previously selected but are now unchecked,
            # so that when they are checked again they are treated as NEW players and assigned
            # fresh formation slots instead of reusing stale pool positions.
            try:
                if self.selected_players and self.current_team_source == old_team_source:
                    old_keys = {
                        self._player_key(p, old_team_source)
                        for p in (self.selected_players or [])
                        if p is not None
                    }
                    new_keys = set(new_players_by_key.keys())
                    deselected_keys = old_keys - new_keys
                    if deselected_keys:
                        print(
                            f"[ContentPanel {self.team_name}] Removing {len(deselected_keys)} deselected players from pool"
                        )
                        for key in deselected_keys:
                            self._remove_position_from_global_pool(key)
            except Exception as e:
                print(f"[ContentPanel] Error while removing deselected players from pool: {e}")

            # Clear all existing markers
            self._clear_all_markers()

            if len(players) == 0:
                print(
                    f"[ContentPanel {self.team_name}] 0 players selected - preserving all positions in pool"
                )

            # CRITICAL: If formation was just changed, create markers at center first, then apply formation
            # This ensures new formation positions are used, not old positions from pool
            if (
                self._formation_just_changed
                and len(players) == 11
                and self.formation != "Select Formation"
            ):
                print(
                    f"[ContentPanel] Formation was just changed - creating markers at center, then applying new formation {self.formation}"
                )
                # Create markers at center positions first (apply_formation_to_players needs existing markers)
                self.view.setUpdatesEnabled(False)
                cx, cy = self._get_scene_center()
                
                for key, p in new_players_by_key.items():
                    # Place all players at center initially (formation will reposition them)
                    pos = (
                        self._get_goalkeeper_position()
                        if self._is_primary_goalkeeper_player(p)
                        else QPointF(cx, cy)
                    )
                    self._create_marker(p, pos)
                
                self.view.setUpdatesEnabled(True)
                self.selected_players = players
                self._update_border_state()
                
                # Now apply the new formation - it will reposition all markers
                self.players_manually_positioned = False  # Reset manual flag for new formation
                self.apply_formation_to_players(self.formation)
                # Clear the flag after applying
                self._formation_just_changed = False
                return  # Exit early - formation application has repositioned markers

            # Batch add markers to prevent viewport updates for each item
            # Disable viewport updates temporarily
            self.view.setUpdatesEnabled(False)

            # Create fresh markers for all players, loading positions from global pool
            cx, cy = self._get_scene_center()

            for key, p in new_players_by_key.items():
                # Check if we have a saved position for this player from global pool
                saved_pos = self._get_position_from_global_pool(key)
                
                # CRITICAL: Only the designated primary GK is forced to GK position
                if self._is_primary_goalkeeper_player(p):
                    pos = self._get_goalkeeper_position()
                    player_name = self._get_player_name(p)
                    print(
                        f"[LOAD] {player_name} (GK) | Key: {key[:30]}... | Pos: FORCED to GK position ({pos.x():.1f}, {pos.y():.1f})"
                    )
                elif saved_pos:
                    pos = saved_pos
                    player_name = self._get_player_name(p)
                    print(
                        f"[LOAD] {player_name} | Key: {key[:30]}... | Pos: ({pos.x():.1f}, {pos.y():.1f})"
                    )
                else:
                    pos = QPointF(cx, cy)

                self._create_marker(p, pos)

            # Re-enable viewport updates after all items are added
            self.view.setUpdatesEnabled(True)

            # Update internal selection list
            self.selected_players = players

            # Update border state based on player count
            self._update_border_state()

            if self.formation == "Select Formation":
                self.clear_field()
                return

            # Formation-aware behavior after rebuilding markers:
            # - First time (no pool entries yet): apply full formation to all players.
            # - Later: for players that ALREADY have saved positions, keep those;
            #          for players WITHOUT saved positions, assign them to free
            #          formation slots only (do not reshuffle existing players).
            if len(players) > 0 and self.formation != "Select Formation":
                pool = self._get_position_pool() or {}

                if len(pool) == 0:
                    print(
                        f"[ContentPanel] Global pool empty - applying full formation {self.formation} for current selection"
                    )
                    self.apply_formation_to_players(self.formation)
                else:
                    # Determine which selected players do NOT yet have a saved position
                    missing_players: List[Dict[str, Any]] = []
                    for p in players:
                        key = self._player_key(p)
                        if key not in pool:
                            missing_players.append(p)

                    if missing_players:
                        print(
                            f"[ContentPanel] Assigning formation slots only for "
                            f"{len(missing_players)} newly-selected players under formation {self.formation}"
                        )
                        self._assign_formation_to_new_players(missing_players)

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

    def set_coordinate_display(self, show: bool):
        """Compatibility wrapper used by TeamPanel to set coordinate visibility."""
        self.toggle_coordinate_display(show)

    def toggle_coordinate_display(self, show: Optional[bool] = None):
        """Toggle coordinate display for all player markers"""
        if show is None:
            # Toggle current state
            show = not getattr(self, "show_coordinates", False)

        self.show_coordinates = show
        print(
            f"[ContentPanel {self.team_name}] Setting show_coordinates to {show} for {len(self.player_markers)} markers"
        )

        # Update all existing markers
        for marker in self.player_markers:
            if hasattr(marker, "show_coordinates"):
                marker.show_coordinates = show
                print(
                    f"  - Set marker {marker.player.get('name', '?')} show_coordinates to {show}"
                )
                marker.update()  # Force repaint of this marker

        # Force scene update to show coordinates
        if self.scene:
            self.scene.update()
            print(f"[ContentPanel {self.team_name}] Scene updated")


    def update_player_positions(self):
        """Update player positions based on formation and selected players"""
        # Clear existing markers
        self._clear_all_markers()

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
                marker = PlayerMarker(player, position, self.team_color, self)
                marker.show_coordinates = getattr(self, "show_coordinates", True)
                self.scene.addItem(marker)
                self.player_markers.append(marker)

        # Don't force immediate update to avoid shake
        # self.scene.update()

    def apply_formation(self, formation: str, silent: bool = False):
        """Apply formation with advanced positioning logic"""
        try:
            if formation == "Select Formation":
                return
            if len(self.selected_players) == 11:
                self.formation = formation
                self.formation_state["formation"] = formation
                self.formation_already_applied = False  # Reset flag to allow new formation
                self.apply_formation_to_players(formation)
                self.formation_already_applied = True  # Mark as applied
                self.formation_applied.emit(formation)
            else:
                self.formation = formation
                self.formation_state["formation"] = formation
        except Exception as e:
            error_msg = f"Error in apply_formation: {str(e)}"
            if not silent:
                print(error_msg)

    def apply_formation_silent(self, formation: str):
        """Apply formation without showing warnings (for automatic application)"""
        self.apply_formation(formation, silent=True)

    def update_formation(self, formation: str):
        """Update formation and apply it if formation actually changed"""
        try:
            old_formation = self.formation
            print(f"[ContentPanel] update_formation called with: {formation} (old: {old_formation})")
            
            # Check if formation actually changed
            formation_changed = (old_formation != formation)
            
            self.formation = formation
            self.formation_state["formation"] = formation
            
            # If formation changed and we have 11 players, set flag to apply it in update_selected_players
            # This allows users to change formations even if players were manually positioned
            if formation_changed and len(self.selected_players) == 11 and formation != "Select Formation":
                print(
                    f"[ContentPanel] Formation changed from {old_formation} to {formation} - will apply in update_selected_players"
                )
                # Set flag to indicate formation was just changed by user
                # This will allow formation to be applied in update_selected_players even if players were manually positioned
                self._formation_just_changed = True
                # Reset manual positioning flag - user wants new formation positions
                self.players_manually_positioned = False
            else:
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
            import traceback

            print(
                f"[ContentPanel {self.team_name}] apply_formation_to_players called with: {formation}"
            )
            print(f"[ContentPanel {self.team_name}] Call stack:")
            for line in traceback.format_stack()[-5:-1]:
                print(line.strip())
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
            center_x, center_y = self._get_scene_center()

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

            # 2) Separate goalkeeper from outfield players
            # The GK position is at index 0 in positions, but we should only assign it to the actual GK
            gk_marker = None
            outfield_markers = []
            for m in self.player_markers:
                if self._is_primary_goalkeeper_player(m.player):
                    gk_marker = m
                else:
                    outfield_markers.append(m)
            
            # 3) Current marker centers in center-relative coords (only for outfield players)
            marker_centers = []
            for m in outfield_markers:
                mx = m.x()
                my = m.y()
                marker_centers.append(
                    (m, int(mx - center_x), int(my - center_y))
                )

            # 4) Closest assignment for outfield players only (skip GK position at index 0)
            # Use only outfield positions (positions[1:]) for outfield players
            outfield_positions = positions[1:] if len(positions) > 1 else positions
            available = outfield_positions.copy()
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

            # If there are remaining positions and unassigned markers, assign them
            if available and len(assignments) < len(outfield_markers):
                unassigned_markers = [m for m in outfield_markers if m not in [a[0] for a in assignments]]
                for i, m in enumerate(unassigned_markers):
                    if i < len(available):
                        assignments.append((m, available[i]))

            # 5) Apply center coordinates (invert Y to match inverted ground image)
            # Build final_centers list in the SAME ORDER as self.selected_players
            # Create a mapping from marker to assigned position
            marker_to_position = {}
            for m, (rx, ry) in assignments:
                ry = -ry
                cx = center_x + rx
                cy = center_y + ry
                marker_to_position[m] = (int(cx), int(cy))
            
            # Also add GK position for GK marker
            if gk_marker:
                gk_rx, gk_ry = positions[0]
                gk_ry = -gk_ry
                gk_cx = center_x + gk_rx
                gk_cy = center_y + gk_ry
                marker_to_position[gk_marker] = (int(gk_cx), int(gk_cy))
            
            # Build final_centers in the order of self.selected_players
            final_centers = []
            for player in self.selected_players:
                player_marker = self._match_player_to_marker(player)
                
                if player_marker and player_marker in marker_to_position:
                    final_centers.append(marker_to_position[player_marker])
                else:
                    # Fallback to center if marker not found - but log it for debugging
                    print(f"[WARNING] Could not find position for player {self._get_player_name(player)} (ID: {player.get('id', 'N/A')}, Jersey: {self._get_jersey_number(player)})")
                    final_centers.append((int(center_x), int(center_y)))

            # Fill any missing with true center
            while len(final_centers) < sel_count:
                final_centers.append((int(center_x), int(center_y)))

            self.update_player_markers_with_positions(final_centers)
            self.save_formation_state()
        except Exception as e:
            print(f"Error in apply_formation_to_players: {e}")

    def _assign_formation_to_new_players(self, new_players: List[Dict[str, Any]]):
        """Assign formation slots ONLY to players that don't yet have saved positions.

        Existing players keep their saved positions from the global pool. We compute
        formation slots using the SAME center-relative grid as apply_formation_to_players
        so new players line up with the existing formation layout.
        """
        try:
            if not new_players or self.formation == "Select Formation":
                return

            # Rebuild the center-relative formation grid (same logic as in apply_formation_to_players)
            try:
                layers = [int(n) for n in self.formation.split("-")]
            except Exception:
                print(f"[ContentPanel] _assign_formation_to_new_players: invalid formation {self.formation}")
                return

            total_layers = 1 + len(layers)
            if total_layers < 2:
                return

            center_x, center_y = self._get_scene_center()

            # Build relative positions: index 0 is GK (0, -300), rest are outfield
            rel_positions = [(0, -300)]  # GK
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
                    rel_positions.append((int(x), int(y)))

            # Convert relative positions to absolute QPointF positions
            abs_positions: List[QPointF] = []
            for rx, ry in rel_positions:
                ry = -ry
                cx = center_x + rx
                cy = center_y + ry
                abs_positions.append(QPointF(cx, cy))

            if not abs_positions:
                return

            gk_abs_pos = abs_positions[0]
            outfield_abs_positions = abs_positions[1:] if len(abs_positions) > 1 else []

            # Track which formation slots are already effectively used by players
            used_indices = set()

            # Helper to find closest outfield slot index for a given QPointF
            def _closest_index(target: QPointF, candidates: List[QPointF]) -> int:
                best_idx = -1
                best_dist = float("inf")
                for idx, pos in enumerate(candidates):
                    dist = sqrt((target.x() - pos.x()) ** 2 + (target.y() - pos.y()) ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx
                return best_idx

            # Mark slots used by players that already have saved positions
            for p in self.selected_players:
                key = self._player_key(p)
                saved_pos = self._get_position_from_global_pool(key)
                if not saved_pos:
                    continue

                if self._is_primary_goalkeeper_player(p):
                    # Reserve GK slot index 0
                    used_indices.add(0)
                else:
                    if outfield_abs_positions:
                        idx = _closest_index(saved_pos, outfield_abs_positions)
                        if idx >= 0:
                            # shift by 1 because 0 is GK
                            used_indices.add(idx + 1)

            # Assign free formation slots to new players
            for p in new_players:
                key = self._player_key(p)
                marker = self._match_player_to_marker(p)
                if not marker:
                    continue

                if self._is_primary_goalkeeper_player(p):
                    target_pos = gk_abs_pos
                    used_indices.add(0)
                else:
                    chosen_index = -1
                    # search only outfield indices (1..len(abs_positions)-1)
                    for idx in range(1, len(abs_positions)):
                        if idx not in used_indices:
                            chosen_index = idx
                            break

                    if chosen_index == -1:
                        # No free formation slot; keep current marker position
                        continue

                    used_indices.add(chosen_index)
                    target_pos = abs_positions[chosen_index]

                marker.setPos(target_pos)
                marker.position = QPointF(target_pos)
                marker._original_position = QPointF(target_pos)
                self._save_position_to_global_pool(key, target_pos)

            if self.scene:
                self.scene.update()
        except Exception as e:
            print(f"[ContentPanel] Error in _assign_formation_to_new_players: {e}")

    def update_player_markers_with_positions(self, positions: List[tuple]):
        """Update player markers with calculated positions"""
        try:
            # Clear existing markers
            self._clear_all_markers()

            # CRITICAL: Separate goalkeeper from outfield players
            # The positions list is in the same order as self.selected_players
            # We need to:
            # 1. Always place goalkeeper at goalkeeper position (ignore their position in the list)
            # 2. Assign formation positions to outfield players only (skip GK's position in the list)
            
            # Get goalkeeper position for reference
            gk_pos = self._get_goalkeeper_position()
            gk_x, gk_y = gk_pos.x(), gk_pos.y()
            
            # Find which position in the list is the GK position (if any)
            # The GK position from formation is typically at the goal box area
            # We'll identify it by checking if it's close to the actual GK position
            # Use a more lenient tolerance to catch GK positions
            gk_position_index = -1
            tolerance = 100  # pixels - increased to catch GK positions
            min_dist = float('inf')
            for i, (x, y) in enumerate(positions):
                dist = sqrt((x - gk_x) ** 2 + (y - gk_y) ** 2)
                if dist < tolerance and dist < min_dist:
                    gk_position_index = i
                    min_dist = dist
                    print(f"[ContentPanel {self.team_name}] Found GK position in positions list at index {i} (distance: {dist:.1f})")
            
            # Count how many outfield players we have
            outfield_player_count = sum(
                1 for p in self.selected_players if not self._is_primary_goalkeeper_player(p)
            )
            
            # Build list of outfield positions (excluding GK position)
            outfield_positions = []
            for i, pos in enumerate(positions):
                if i != gk_position_index:
                    outfield_positions.append(pos)
            
            # Ensure we have enough positions for all outfield players
            if len(outfield_positions) < outfield_player_count:
                print(f"[WARNING] Only {len(outfield_positions)} outfield positions for {outfield_player_count} outfield players. Adding center positions.")
                cx, cy = self._get_scene_center()
                while len(outfield_positions) < outfield_player_count:
                    outfield_positions.append((int(cx), int(cy)))
            
            # Create markers for all players
            outfield_pos_idx = 0
            for i, player in enumerate(self.selected_players):
                if self._is_primary_goalkeeper_player(player):
                    # CRITICAL: Always place goalkeeper at goalkeeper position
                    position = self._get_goalkeeper_position()
                    print(
                        f"[ContentPanel {self.team_name}] FORCING goalkeeper {self._get_player_name(player)} to GK position ({position.x():.1f}, {position.y():.1f})"
                    )
                else:
                    # For outfield players, use saved pool position if it exists;
                    # otherwise use the next available formation outfield slot.
                    player_key = self._player_key(player)
                    saved_pos = self._get_position_from_global_pool(player_key)

                    if saved_pos:
                        position = saved_pos
                        print(
                            f"[ContentPanel {self.team_name}] Using saved position for {self._get_player_name(player)} at ({position.x():.1f}, {position.y():.1f})"
                        )
                    elif outfield_pos_idx < len(outfield_positions):
                        x, y = outfield_positions[outfield_pos_idx]
                        position = QPointF(x, y)
                        outfield_pos_idx += 1
                    else:
                        # Fallback to center if not enough positions
                        cx, cy = self._get_scene_center()
                        position = QPointF(cx, cy)
                
                # Create new marker with improved visual style
                self._create_marker(player, position)

            # Only save positions to global pool if players haven't been manually positioned
            # OR if this is the first time (pool is empty)
            pool = self._get_position_pool()
            pool_size = len(pool) if pool else 0
            
            if not self.players_manually_positioned or pool_size == 0:
                # Save positions to global pool after formation application
                print(
                    f"[ContentPanel {self.team_name}] Saving {len(self.player_markers)} formation positions to global pool..."
                )
                for marker in self.player_markers:
                    marker._save_position_to_global_pool()
            else:
                print(
                    f"[ContentPanel {self.team_name}] Skipping position save - players manually positioned (preserving swapped positions)"
                )

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

    def _get_goalkeeper_position(self) -> QPointF:
        """Get the standard goalkeeper position on the field"""
        goal_box_depth = self.STANDARD_FIELD_HEIGHT * 0.11
        gk_y = self.STANDARD_FIELD_HEIGHT - goal_box_depth - 15 + 25  # A bit more space from goal box, moved down 25px
        gk_x = self.STANDARD_FIELD_WIDTH / 2 + 30 - 20 - 10  # Moved left by 10px (was 10px right of center, now at center)
        return QPointF(gk_x, gk_y)

    def _is_goalkeeper(self, player: Dict[str, Any]) -> bool:
        """Check if a player is a goalkeeper"""
        position = player.get("position", "").upper()
        # Check various goalkeeper position indicators
        return position in ["GK", "GOALKEEPER", "GOAL KEEPER", "KEEPER", "GOALIE"]

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
        # Define field boundaries with proper margins
        margin = 50  # Slightly larger margin from field edges
        goal_box_depth = self.STANDARD_FIELD_HEIGHT * 0.11  # Slightly smaller goal box depth

        # Goalkeeper at the edge of goal box (not inside) - shifted more right
        gk_pos = self._get_goalkeeper_position()
        positions.append(gk_pos)  # Center-based positioning with more right shift

        # Calculate safe field area for outfield players
        safe_width = self.STANDARD_FIELD_WIDTH - (2 * margin)
        safe_height = self.STANDARD_FIELD_HEIGHT - goal_box_depth - (margin * 1.5)
        right_offset = 30  # Shift players 30px to the right

        # Defenders closer to goalkeeper but with more spacing (defensive third) - shifted more right
        if defenders > 0:
            spacing = safe_width / (defenders + 1)
            def_y = self.STANDARD_FIELD_HEIGHT - (safe_height * 0.35)  # 35% from bottom for better spacing
            for i in range(defenders):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, def_y))

        # Midfielders in the middle (middle third) - centered around field center, shifted more right
        if midfielders > 0:
            spacing = safe_width / (midfielders + 1)
            mid_y = self.STANDARD_FIELD_HEIGHT - (safe_height * 0.60)  # 60% from bottom for better distribution
            for i in range(midfielders):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, mid_y))

        # Forwards at the top (attacking third) - centered around field center, shifted more right
        if forwards > 0:
            spacing = safe_width / (forwards + 1)
            fwd_y = self.STANDARD_FIELD_HEIGHT - (safe_height * 0.85)  # 85% from bottom for better attacking position
            for i in range(forwards):
                x = margin + spacing * (i + 1) + right_offset
                positions.append(QPointF(x, fwd_y))

        return positions

    def clear_players(self):
        """Clear all players from the field"""
        try:
            import traceback

            print(f"[{self.team_name}] clear_players called")
            print(f"[{self.team_name}] clear_players called from:")
            for line in traceback.format_stack()[-4:-1]:
                print(line.strip())
            # Clear existing markers
            self._clear_all_markers()

            # Clear selected players
            self.selected_players = []

            # Reset formation flag when clearing players
            # NOTE: Don't reset players_manually_positioned - it should persist across team toggles
            self.formation_already_applied = False

            # Force scene update
            self.scene.update()
        except Exception as e:
            print(f"Error clearing players: {str(e)}")

    def resizeEvent(self, event):
        """Handle resize events - update scaling to fit new size"""
        super().resizeEvent(event)
        # Only update scaling if this is an actual resize (not initial layout)
        # and if the size actually changed
        if self._initial_scaling_done and event.oldSize().isValid():
            # Check if size actually changed significantly (more than 5 pixels)
            old_size = event.oldSize()
            new_size = event.size()
            if (
                abs(old_size.width() - new_size.width()) > 5
                or abs(old_size.height() - new_size.height()) > 5
            ):
                self.update_view_scaling()

    def showEvent(self, event):
        """Handle show events - update scaling when panel becomes visible"""
        super().showEvent(event)
        # Only scale on the FIRST show event (when tab first becomes visible)
        # This prevents shake when selecting players but ensures proper scaling
        if not self._first_show_done:
            self._first_show_done = True
            self.update_view_scaling()

    def update_view_scaling(self):
        """Scale view to fit available space without overflow"""
        # No debouncing - scale immediately since we have safeguards to prevent excessive calls
        self._do_view_scaling()

    def _do_view_scaling(self):
        """Perform the actual view scaling"""
        if hasattr(self, "view") and self.scene.sceneRect().isValid():
            scene_rect = self.scene.sceneRect()
            self.view.resetTransform()
            # Let Qt compute the proper uniform scale to maximize the scene in the view
            self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.view.centerOn(scene_rect.center())
            QTimer.singleShot(0, self.scene.update)
            # Mark initial scaling as done
            self._initial_scaling_done = True

    def force_update_scaling(self):
        """Force update the scaling shortly after layout changes (e.g., tab switch)"""
        # Single late pass so it wins over any earlier scaling
        QTimer.singleShot(200, self.update_view_scaling)

    def clear_field(self):
        """Clear all player markers from the field"""
        try:
            import traceback

            print(f"[{self.team_name}] Clearing field display...")
            print(f"[{self.team_name}] clear_field called from:")
            for line in traceback.format_stack()[-4:-1]:
                print(line.strip())

            # Remove all player markers
            for item in self.scene.items():
                if isinstance(item, PlayerMarker):
                    self.scene.removeItem(item)

            # Clear player markers list
            self.player_markers.clear()
            self.selected_markers.clear()

            # Reset formation flag when clearing field
            # NOTE: Don't reset players_manually_positioned - it should persist across team toggles
            self.formation_already_applied = False

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

    def _get_match_setup_tab(self):
        """Traverse up parent hierarchy to find MatchSetupTab"""
        parent = self.parent()
        while parent:
            if hasattr(parent, "pool_a_positions"):
                return parent
            parent = parent.parent() if hasattr(parent, "parent") else None
        return None

    def _get_position_pool(self):
        """Get the appropriate position pool (Team A or Team B)"""
        match_setup_tab = self._get_match_setup_tab()
        if match_setup_tab:
            return (
                match_setup_tab.pool_a_positions
                if self.current_team_source == "Team A"
                else match_setup_tab.pool_b_positions
            )
        return None

    def _get_scene_center(self):
        """Get the center coordinates of the scene as (x, y) tuple"""
        rect = self.scene.sceneRect()
        return rect.width() / 2.0, rect.height() / 2.0

    def _player_key(self, player: Dict[str, Any], team_src: str = None) -> str:
        """Generate a unique key for a player"""
        src = team_src or self.current_team_source
        return f"{src}|{player.get('id') or ''}|{self._get_jersey_number(player)}|{self._get_player_name(player)}"

    def _is_primary_goalkeeper_player(self, player: Dict[str, Any]) -> bool:
        """Check if player is the designated primary goalkeeper for GK slot"""
        if not player:
            return False
        if not self._primary_goalkeeper_key:
            return False
        return self._player_key(player) == self._primary_goalkeeper_key

    def _get_jersey_number(self, player: Dict[str, Any]) -> str:
        """Get jersey number from player dict with fallback"""
        return str(player.get('jersey_number', player.get('jersey_no', '')))

    def _get_player_name(self, player: Dict[str, Any]) -> str:
        """Get player name from player dict with fallback"""
        return player.get('full_name', player.get('name', ''))

    def _clear_all_markers(self):
        """Clear all player markers from the scene"""
        for marker in list(self.player_markers):
            self.scene.removeItem(marker)
        self.player_markers.clear()

    def _create_marker(self, player: Dict[str, Any], position: QPointF) -> PlayerMarker:
        """Create a new player marker with standard settings"""
        marker = PlayerMarker(player, position, self.team_color, self)
        marker.show_coordinates = getattr(self, "show_coordinates", False)
        self.scene.addItem(marker)
        self.player_markers.append(marker)
        return marker

    def _match_player_to_marker(self, player: Dict[str, Any]) -> Optional[PlayerMarker]:
        """Find the marker matching a given player"""
        player_id = player.get('id', '')
        player_jersey = self._get_jersey_number(player)
        player_name = self._get_player_name(player)
        
        for m in self.player_markers:
            marker_id = m.player.get('id', '')
            marker_jersey = self._get_jersey_number(m.player)
            marker_name = self._get_player_name(m.player)
            
            if (player_id and marker_id and player_id == marker_id) or \
               (player_jersey and marker_jersey and player_jersey == marker_jersey) or \
               (player_name and marker_name and player_name == marker_name):
                return m
        return None

    def _save_position_to_global_pool(self, key: str, position: QPointF):
        """Save position to global pool in parent MatchSetupTab"""
        pool = self._get_position_pool()
        if pool is not None:
            pool_name = "pool_a_positions" if self.current_team_source == "Team A" else "pool_b_positions"
            old_pos = pool.get(key)
            pool[key] = position
            if old_pos:
                print(
                    f"[ContentPanel] UPDATED position for {key[:40]}... in {pool_name}: OLD ({old_pos.x():.1f}, {old_pos.y():.1f}) -> NEW ({position.x():.1f}, {position.y():.1f})"
                )
            else:
                print(
                    f"[ContentPanel] Saved NEW position for {key[:40]}... to {pool_name}: ({position.x():.1f}, {position.y():.1f})"
                )

    def _get_position_from_global_pool(self, key: str) -> Optional[QPointF]:
        """Get position from global pool in parent MatchSetupTab"""
        pool = self._get_position_pool()
        if pool is not None:
            pool_name = "pool_a_positions" if self.current_team_source == "Team A" else "pool_b_positions"
            pos = pool.get(key)
            if pos:
                print(
                    f"[ContentPanel {self.team_name}] Found position in {pool_name} for {key[:40]}...: ({pos.x():.1f}, {pos.y():.1f})"
                )
            else:
                print(
                    f"[ContentPanel {self.team_name}] No position found in {pool_name} for {key[:40]}... (pool has {len(pool)} entries)"
                )
            return pos
        print(
            f"[ContentPanel {self.team_name}] WARNING: Could not get match_setup_tab for position lookup"
        )
        return None

    def _remove_position_from_global_pool(self, key: str):
        """Remove position from global pool in parent MatchSetupTab"""
        pool = self._get_position_pool()
        if pool is not None:
            pool_name = "pool_a_positions" if self.current_team_source == "Team A" else "pool_b_positions"
            pool.pop(key, None)
            print(
                f"[ContentPanel] Removed position for {key} from {pool_name}"
            )
