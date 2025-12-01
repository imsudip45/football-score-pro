"""
Player Table Widget for FSP 2.0
Custom table for displaying and selecting players
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .modern_components import ModernCheckbox


class PlayerTable(QTableWidget):
    """Custom table widget for displaying and managing player lists"""

    # Signal emitted when player selection changes (list of selected row indices)
    selection_changed = Signal(list)

    def __init__(self, team_name: str, parent=None):
        super().__init__(0, 5, parent)
        self.team_name = team_name
        self.max_selected_players = 11
        self.setup_table()

    def setup_table(self):
        """Setup table headers and properties"""
        # Set headers
        headers = ["NUM", "NAME", "ID", "POSITION", "SELECT"]
        self.setHorizontalHeaderLabels(headers)

        # Configure table properties
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Disable built-in row selection so only checkbox state controls highlighting
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.verticalHeader().setVisible(False)

        # Configure column widths - match old app exactly
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )  # Name column stretches to fill space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        # Match old app column widths exactly
        self.setColumnWidth(0, 60)  # Num - was 80
        self.setColumnWidth(1, 130)  # Name (initial width, will stretch) - was 300
        self.setColumnWidth(2, 180)  # ID - was 120
        self.setColumnWidth(3, 100)  # Position - was 80
        self.setColumnWidth(4, 100)  # Select - was 60

        # Apply styling - match old app exactly
        self.setStyleSheet("""
            QTableWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #374151;
                border-radius: 3px;
                gridline-color: #374151;
                color: #ffffff;
                selection-background-color: #22c55e;
                font-size: 16px;
                font-weight: 500;
            }
            QHeaderView{
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3748, stop:1 #1a202c);
                color: #8b8b8f;
                padding: 8px 5px 8px 0px;
                border: none;
                border-right: 1px solid #374151;
                font-weight: 700;
                font-size: 16px;
                letter-spacing: 0.05em;
                min-height: 25px;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #374151, stop:1 #2d3748);
            }
            QTableWidget::item {
                padding: 8px 4px;
                border-bottom: 1px solid #374151;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22c55e, stop:1 #16a34a);
                color: white;
                font-weight: bold;
            }
        """)

    def populate_players(self, players: list):
        """Populate table with player data"""
        try:
            self.blockSignals(True)
            self.clearContents()

            # Sort players by name
            sorted_players = sorted(
                players,
                key=lambda p: p.get("full_name", "") if isinstance(p, dict) else p.name,
            )

            # Always show at least 24 rows
            min_rows = 24
            row_count = max(len(sorted_players), min_rows)
            self.setRowCount(row_count)

            for row, player in enumerate(sorted_players):
                # Set row height to 40 (match old app)
                self.setRowHeight(row, 40)

                # Handle both dict and Player object
                if isinstance(player, dict):
                    num = str(player.get("jersey_no", ""))
                    name = player.get("full_name", "")
                    player_id = player.get("id", "")
                    position = player.get("position", "")
                    selected = player.get("selected", False)
                else:
                    num = str(
                        player.jersey_no if hasattr(player, "jersey_no") else player.num
                    )
                    name = (
                        player.full_name
                        if hasattr(player, "full_name")
                        else player.name
                    )
                    player_id = player.id
                    position = player.position
                    selected = player.selected if hasattr(player, "selected") else False

                # Create table items
                num_item = QTableWidgetItem(num)
                name_item = QTableWidgetItem(name)
                id_item = QTableWidgetItem(player_id)
                pos_item = QTableWidgetItem(position)

                # Set items
                self.setItem(row, 0, num_item)
                self.setItem(row, 1, name_item)
                self.setItem(row, 2, id_item)
                self.setItem(row, 3, pos_item)

                # Create checkbox
                checkbox = ModernCheckbox()
                checkbox.setChecked(selected)
                checkbox.setEnabled(bool(name))
                checkbox.toggled.connect(
                    lambda checked, r=row: self.on_selection_changed(r, checked)
                )

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(
                    10, 0, 10, 0
                )  # Increased horizontal padding to prevent cutoff

                container.setEnabled(bool(name))
                self.setCellWidget(row, 4, container)

                # Apply highlighting if selected
                if selected:
                    self.update_row_highlighting(row, True)

            # Fill empty rows if needed
            for row in range(len(sorted_players), row_count):
                # Set row height to 40 (match old app)
                self.setRowHeight(row, 40)

                # Create empty table items
                for col in range(4):
                    empty_item = QTableWidgetItem("")
                    self.setItem(row, col, empty_item)

                # Create checkbox for empty row
                checkbox = ModernCheckbox()
                checkbox.setChecked(False)
                checkbox.setEnabled(False)
                checkbox.toggled.connect(
                    lambda checked, r=row: self.on_selection_changed(r, checked)
                )

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(10, 0, 10, 0)
                container.setEnabled(False)

                self.setCellWidget(row, 4, container)

            self.blockSignals(False)

            # Emit initial selection
            selected_rows = list(self.get_selected_rows())
            self.selection_changed.emit(selected_rows)

        except Exception as e:
            print(f"Error populating players: {e}")
            self.blockSignals(False)

    def is_row_selected(self, row: int) -> bool:
        """Check if a row is selected"""
        container = self.cellWidget(row, 4)
        if container:
            checkbox = container.findChild(ModernCheckbox)
            if checkbox:
                return checkbox.isChecked()
        return False

    def on_selection_changed(self, row: int, checked: bool):
        """Handle selection change for a row"""
        # Update row highlighting
        self.update_row_highlighting(row, checked)

        # Count selected rows
        selected_count = sum(
            1 for r in range(self.rowCount()) if self.is_row_selected(r)
        )

        # Disable other checkboxes if max reached
        if selected_count >= self.max_selected_players:
            for r in range(self.rowCount()):
                if not self.is_row_selected(r):
                    container = self.cellWidget(r, 4)
                    if container:
                        checkbox = container.findChild(ModernCheckbox)
                        if checkbox:
                            checkbox.setEnabled(False)
        else:
            # Re-enable all checkboxes
            for r in range(self.rowCount()):
                container = self.cellWidget(r, 4)
                if container:
                    checkbox = container.findChild(ModernCheckbox)
                    if checkbox:
                        checkbox.setEnabled(True)

        # Emit signal with selected rows list
        selected_rows = list(self.get_selected_rows())
        self.selection_changed.emit(selected_rows)

    def update_row_highlighting(self, row: int, selected: bool):
        """Update visual highlighting for a row - match old app green selection"""
        for col in range(4):  # Don't color the checkbox column
            item = self.item(row, col)
            if not item:
                continue

            if selected:
                # Use green background with white text for selected rows
                # Use setData with BackgroundRole to override stylesheet
                item.setData(Qt.ItemDataRole.ForegroundRole, QColor(34, 197, 94))
            else:
                # Reset to default background with light text
                default_brush = QBrush(QColor(31, 41, 55))  # #1f2937 - default dark
                item.setData(Qt.ItemDataRole.BackgroundRole, default_brush)
                item.setData(
                    Qt.ItemDataRole.ForegroundRole, QColor(229, 231, 235)
                )  # #e5e7eb - light text

        # Force the row to repaint
        self.viewport().update()

    def get_selected_rows(self) -> set:
        """Get set of selected row indices"""
        selected_rows = set()
        for row in range(self.rowCount()):
            if self.is_row_selected(row):
                selected_rows.add(row)
        return selected_rows

    def get_selected_players(self) -> list:
        """Get list of selected players"""
        selected_players = []
        for row in range(self.rowCount()):
            if self.is_row_selected(row):
                player = {
                    "jersey_no": self.item(row, 0).text() if self.item(row, 0) else "",
                    "full_name": self.item(row, 1).text() if self.item(row, 1) else "",
                    "id": self.item(row, 2).text() if self.item(row, 2) else "",
                    "position": self.item(row, 3).text() if self.item(row, 3) else "",
                    "selected": True,
                }
                selected_players.append(player)
        return selected_players

    def get_selected_count(self) -> int:
        """Get count of selected players"""
        return sum(1 for row in range(self.rowCount()) if self.is_row_selected(row))

    # NOTE: keep a single implementation that manipulates the actual checkboxes
    def apply_selected_rows(self, selected_rows):
        """Apply selected rows from an iterable of row indices"""
        try:
            rows = list(selected_rows)
            print(f"Applying selected rows: {rows}")
            # Block table signals (child checkbox signals will be blocked individually)
            self.blockSignals(True)
            # Clear selections
            for row in range(self.rowCount()):
                container = self.cellWidget(row, 4)
                if container:
                    checkbox = container.findChild(ModernCheckbox)
                    if checkbox:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(False)
                        checkbox.blockSignals(False)
                        self.update_row_highlighting(row, False)

            # Apply selections
            for row in rows:
                if 0 <= row < self.rowCount():
                    container = self.cellWidget(row, 4)
                    if container:
                        checkbox = container.findChild(ModernCheckbox)
                        if checkbox:
                            checkbox.blockSignals(True)
                            checkbox.setChecked(True)
                            checkbox.blockSignals(False)
                            self.update_row_highlighting(row, True)

            # Unblock signals and emit one consolidated signal
            self.blockSignals(False)
            self.selection_changed.emit(rows)
            print(f"Applied {len(rows)} selected rows")
        except Exception as e:
            print(f"Error applying selected rows: {e}")
            self.blockSignals(False)

    def clear_all(self):
        """Clear all table contents"""
        self.clearContents()
        self.setRowCount(0)

    def add_empty_rows(self, count: int):
        """Add empty rows to the table"""
        current_rows = self.rowCount()
        self.setRowCount(current_rows + count)
        for row in range(current_rows, current_rows + count):
            # Set row height to 40 (match old app)
            self.setRowHeight(row, 40)

            for col in range(4):
                self.setItem(row, col, QTableWidgetItem(""))

            # Add checkbox
            checkbox = ModernCheckbox()
            checkbox.setEnabled(False)
            checkbox.toggled.connect(
                lambda checked, r=row: self.on_selection_changed(r, checked)
            )

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)

            container.setEnabled(False)
            self.setCellWidget(row, 4, container)

    def clear_selections(self):
        """Clear all player selections"""
        try:
            print(f"[{self.team_name}] Clearing all player selections...")

            # Block table signals (child checkbox signals will be blocked individually)
            self.blockSignals(True)

            # Clear all checkboxes
            for row in range(self.rowCount()):
                checkbox_widget = self.cellWidget(row, 4)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(ModernCheckbox)
                    if checkbox:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(False)
                        checkbox.blockSignals(False)
                        self.update_row_highlighting(row, False)

            # Unblock signals
            self.blockSignals(False)

            print(f"[{self.team_name}] Cleared all player selections")

        except Exception as e:
            print(f"Error clearing player selections: {e}")
