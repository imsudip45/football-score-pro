"""
Official Selector Dialog for Football Score Pro 2.0
Popup dialog for selecting officials from the JSON data
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

# Match colors from subs_penalty_tab
COLORS = {
    "background": "#1a1a1a",
    "panel": "#1e1e1e",
    "card": "#28293A",
    "border": "#374151",
    "text": "#B0B4BB",
}


class OfficialSelectorDialog(QDialog):
    """Dialog for selecting officials from available data"""

    official_selected = Signal(dict)  # Emits selected official data

    def __init__(
        self,
        officials_data: List[Dict[str, Any]],
        title: str,
        parent=None,
        locked_names: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.officials_data = self._normalize_officials_data(officials_data)
        self.title = title
        self.selected_official = None
        self.locked_names = {name.strip().lower() for name in locked_names or []}
        self._has_unlockable_rows = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI matching substitution player selection dialog"""
        self.setWindowTitle(f"Select {self.title}")
        self.setModal(True)
        self.setFixedSize(450, 600)  # Match substitution dialog size
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS["card"]}, stop:1 {COLORS["panel"]});
                color: {COLORS["text"]};
            }}
        """)

        layout = QVBoxLayout(self)

        # Officials table (single column)
        self.officials_table = QTableWidget(self)
        self.officials_table.setColumnCount(1)
        self.officials_table.setHorizontalHeaderLabels(["Official Name"])
        self.officials_table.setStyleSheet(f"""
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
        """)
        self.officials_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.officials_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.officials_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        # Column sizing - single column stretches
        header = self.officials_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.populate_officials_table()
        layout.addWidget(self.officials_table)

        # Buttons - matching substitution dialog exactly
        button_layout = QHBoxLayout()

        ok_button = QPushButton("OK")
        ok_button.setFont(QFont("Verdana", 14))
        ok_button.setFixedHeight(44)
        ok_button.setMinimumWidth(120)
        ok_button.setStyleSheet("""
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
        ok_button.clicked.connect(self.accept_selection)
        button_layout.addWidget(ok_button)
        self.ok_button = ok_button

        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Verdana", 14))
        cancel_button.setFixedHeight(44)
        cancel_button.setMinimumWidth(120)
        cancel_button.setStyleSheet("""
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
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def populate_officials_table(self):
        """Populate the table with available officials"""
        if not self.officials_data:
            print("OfficialSelectorDialog: No officials data provided")
            self.officials_table.setRowCount(1)
            no_data_item = QTableWidgetItem("No officials available")
            no_data_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.officials_table.setItem(0, 0, no_data_item)
            return

        print(
            f"OfficialSelectorDialog: Populating table with {len(self.officials_data)} officials"
        )

        self.officials_table.setRowCount(len(self.officials_data))
        selectable_row_index = None

        for row_idx, official in enumerate(self.officials_data):
            full_name = official.get("full_name", official.get("name", "Unknown"))

            # Build full info string with additional details
            info_parts = [full_name]
            if "designation" in official and official["designation"]:
                info_parts.append(f"({official['designation']})")
            elif "nationality" in official and official["nationality"]:
                info_parts.append(f"({official['nationality']})")
            if "experience" in official and official["experience"]:
                info_parts.append(f"- {official['experience']}")
            if "fifa_qualified" in official and official["fifa_qualified"]:
                info_parts.append("- FIFA Qualified")

            item_text = " ".join(info_parts)

            # Single column with all info
            name_item = QTableWidgetItem(item_text)
            name_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            name_item.setData(Qt.ItemDataRole.UserRole, official)  # Store official data

            is_locked = full_name.strip().lower() in self.locked_names
            if is_locked:
                name_item.setForeground(QColor("#f87171"))
                name_item.setBackground(QColor("#3b0d0d"))
                name_item.setFlags(Qt.ItemFlag.NoItemFlags)
                name_item.setToolTip(
                    "Already selected - duplicate selections are not allowed."
                )
            else:
                self._has_unlockable_rows = True
                if selectable_row_index is None:
                    selectable_row_index = row_idx

            self.officials_table.setItem(row_idx, 0, name_item)

        if selectable_row_index is not None:
            self.officials_table.selectRow(selectable_row_index)
        else:
            self.officials_table.clearSelection()
            if hasattr(self, "ok_button"):
                self.ok_button.setEnabled(False)

    def _normalize_officials_data(self, officials_data: Any) -> List[Dict[str, Any]]:
        """Normalize officials data to list of dicts format"""
        if not officials_data:
            return []

        normalized = []

        for item in officials_data:
            if isinstance(item, dict):
                normalized_item = {
                    "full_name": item.get("full_name", item.get("name", "Unknown")),
                    "short_name": item.get("short_name", ""),
                    "nationality": item.get("nationality"),
                    "experience": item.get("experience"),
                    "fifa_qualified": item.get("fifa_qualified", False),
                    "designation": item.get("designation"),
                }
                if not normalized_item["short_name"]:
                    full_name = normalized_item["full_name"]
                    normalized_item["short_name"] = (
                        full_name.split()[-1] if " " in full_name else full_name
                    )
                normalized.append(normalized_item)
            elif isinstance(item, str):
                normalized.append(
                    {
                        "full_name": item,
                        "short_name": item.split()[-1] if " " in item else item,
                        "nationality": None,
                        "experience": None,
                        "fifa_qualified": False,
                        "designation": None,
                    }
                )
            else:
                item_str = str(item)
                normalized.append(
                    {
                        "full_name": item_str,
                        "short_name": item_str.split()[-1]
                        if " " in item_str
                        else item_str,
                        "nationality": None,
                        "experience": None,
                        "fifa_qualified": False,
                        "designation": None,
                    }
                )

        return normalized

    def accept_selection(self):
        """Accept the selected official"""
        selected_rows = self.officials_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select an official first."
            )
            return

        selected_row = selected_rows[0].row()
        name_item = self.officials_table.item(selected_row, 0)

        if name_item:
            official_data = name_item.data(Qt.ItemDataRole.UserRole)
            if official_data:
                self.selected_official = official_data
                self.official_selected.emit(self.selected_official)
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Invalid Selection", "Selected item has no data."
                )
        else:
            QMessageBox.warning(
                self, "No Selection", "Please select an official first."
            )
