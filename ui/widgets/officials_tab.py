"""
Officials Tab Widget for Football Score Pro 2.0
Comprehensive officials management interface - Based on Game_Setting.py layout
"""

import re
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, 
    QGroupBox, QFrame, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.models.official import OfficialType

from ..backend_service import BackendService
from .official_selector_dialog import OfficialSelectorDialog
from .guest_form_dialog import GuestFormDialog

TYPE_TO_PANEL = {
    "referee": "officials_panel",
    "assistant1": "officials_panel",
    "assistant2": "officials_panel",
    "fourth_official": "officials_panel",
    "host1": "hosts_panel",
    "host2": "hosts_panel",
    "host3": "hosts_panel",
    "host4": "hosts_panel",
    "host5": "hosts_panel",
    "host6": "hosts_panel",
    "organizer1": "organizers_panel",
    "organizer2": "organizers_panel",
    "organizer3": "organizers_panel",
    "organizer4": "organizers_panel",
    "organizer5": "organizers_panel",
    "organizer6": "organizers_panel",
    "commentator1": "commentators_panel",
    "commentator2": "commentators_panel",
    "commentator3": "commentators_panel",
    "commentator4": "commentators_panel",
    "commentator5": "commentators_panel",
    "commentator6": "commentators_panel"
}

TYPE_TO_BUTTON = {
    "referee": "btn_referee_name",
    "assistant1": "btn_linesman_1",
    "assistant2": "btn_linesman_2",
    "fourth_official": "btn_fourth_referee",
    "host1": "btn_host_1",
    "host2": "btn_host_2",
    "host3": "btn_host_3",
    "host4": "btn_host_4",
    "host5": "btn_host_5",
    "host6": "btn_host_6",
    "organizer1": "btn_organizer_1",
    "organizer2": "btn_organizer_2",
    "organizer3": "btn_organizer_3",
    "organizer4": "btn_organizer_4",
    "organizer5": "btn_organizer_5",
    "organizer6": "btn_organizer_6",
    "commentator1": "btn_commentator_1",
    "commentator2": "btn_commentator_2",
    "commentator3": "btn_commentator_3",
    "commentator4": "btn_commentator_4",
    "commentator5": "btn_commentator_5",
    "commentator6": "btn_commentator_6"
}

PANEL_BUTTON_ATTRS = {
    "officials_panel": ["btn_referee_name", "btn_linesman_1", "btn_linesman_2", "btn_fourth_referee"],
    "hosts_panel": [f"btn_host_{i}" for i in range(1, 7)],
    "organizers_panel": [f"btn_organizer_{i}" for i in range(1, 7)],
    "commentators_panel": [f"btn_commentator_{i}" for i in range(1, 7)]
}


class OfficialsTab(QWidget):
    """Officials Tab matching Game_Setting.py layout with modern design"""

    officials_changed = Signal(dict)
    data_changed = Signal()  # Add missing data_changed signal

    def __init__(self, backend_service: BackendService, parent=None):
        super().__init__(parent)
        self.backend_service = backend_service
        self.current_officials = {}
        self.officials_data = {}  # Store loaded officials data (DEPRECATED - use service)
        self.members_data = {}
        self.panel_data_sources = self._create_empty_panel_data()
        self._button_defaults: Dict[QPushButton, str] = {}
        self.setup_ui()
        
        # Subscribe to officials pool loaded event
        self.backend_service.officials_pool_loaded.connect(self.on_officials_pool_loaded)

    def setup_ui(self):
        # Set background color using our modern design language
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
            }
        """)
        
        # Create scrollable layout to fit within boundaries
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #374151;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #6b7280;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9ca3af;
            }
            QScrollBar:horizontal {
                background: #374151;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #6b7280;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #9ca3af;
            }
        """)
        
        # Create main content widget
        content_widget = QWidget()
        content_widget.setMinimumSize(1200, 700)  # Set minimum size for grid layout
        
        # Create grid layout for content - 2 columns, 3 rows
        main_layout = QGridLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        main_layout.setRowStretch(0, 1)  # Equal row heights
        main_layout.setRowStretch(1, 1)
        main_layout.setRowStretch(2, 1)
        main_layout.setColumnStretch(0, 1)  # Equal column widths
        main_layout.setColumnStretch(1, 1)
        
        # Create sections in a responsive layout
        officials_panel = self.create_officials_panel_responsive()
        hosts_panel = self.create_hosts_panel_responsive()
        commentators_panel = self.create_commentators_panel_responsive()
        tournament_panel = self.create_tournament_panel_responsive()
        
        # Create unified guests panel
        guests_panel = self.create_guests_panel_unified_responsive()
        members_panel = self.create_members_panel_responsive()
        
        # Add panels to grid layout
        # Row 0: Officials and Commentators (moved from row 1)
        main_layout.addWidget(officials_panel, 0, 0)
        main_layout.addWidget(commentators_panel, 0, 1)
        
        # Row 1-2: Guests (unified panel spanning 2 rows) and Hosts (moved from row 2)
        main_layout.addWidget(guests_panel, 1, 0, 1, 1)  # Span 2 rows, 1 column
        main_layout.addWidget(hosts_panel, 1, 1)
        main_layout.addWidget(members_panel, 2, 0, 1, 1)  # New members panel spanning both columns
        main_layout.addWidget(tournament_panel, 2, 1)  # Tournament moved to row 2
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Create main layout for the tab
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
    
    def _create_empty_panel_data(self) -> Dict[str, list]:
        """Return an empty structure for panel data sources."""
        return {
            "officials_panel": [],
            "hosts_panel": [],
            "commentators_panel": [],
            "organizers_panel": []
        }
    
    def _register_button_default(self, button: QPushButton, default_text: str):
        """Track each button's default label text for duplicate detection."""
        self._button_defaults[button] = default_text
    
    def _get_button_default_text(self, button: QPushButton) -> str:
        return self._button_defaults.get(button, "")
    
    def _normalize_name_entries(self, raw_list: Any) -> List[Dict[str, str]]:
        """Normalize mixed string/dict lists into [{'full_name','short_name'}] entries."""
        normalized: List[Dict[str, str]] = []
        if not raw_list:
            return normalized
        for item in raw_list:
            try:
                if isinstance(item, dict):
                    full_name = item.get("full_name") or item.get("name")
                    if not full_name:
                        continue
                    short_name = item.get("short_name") or (full_name.split()[-1] if " " in full_name else full_name)
                    normalized.append({"full_name": full_name.strip(), "short_name": short_name.strip()})
                elif isinstance(item, str):
                    name = item.strip()
                    if not name:
                        continue
                    short_name = name.split()[-1] if " " in name else name
                    normalized.append({"full_name": name, "short_name": short_name})
            except Exception:
                continue
        return normalized
    
    def _merge_official_role_lists(self, source: Dict[str, Any]) -> List[Any]:
        """Merge legacy official role lists into one."""
        combined: List[Any] = []
        legacy_keys = [
            "referees",
            "assistant_referees",
            "assistant_referee_1",
            "assistant_referee_2",
            "linesmen",
            "linesman_1",
            "linesman_2",
            "fourth_officials",
            "var_referees"
        ]
        for key in legacy_keys:
            data = source.get(key)
            if data:
                combined.extend(data if isinstance(data, list) else [data])
        return combined
    
    def _rebuild_panel_data_sources(self, source: Dict[str, Any]):
        """Populate panel data structure from raw dict using fallbacks."""
        panel_data = self._create_empty_panel_data()
        
        officials_panel = source.get("officials_panel")
        if not officials_panel:
            officials_panel = self._merge_official_role_lists(source)
        panel_data["officials_panel"] = self._normalize_name_entries(officials_panel)
        
        hosts_panel = source.get("hosts_panel") or source.get("hosts") or source.get("available_hosts")
        panel_data["hosts_panel"] = self._normalize_name_entries(hosts_panel)
        
        commentators_panel = (
            source.get("commentators_panel")
            or source.get("commentators")
            or (
                (source.get("commentators_1st") or []) + (source.get("commentators_2nd") or [])
                if any(key in source for key in ("commentators_1st", "commentators_2nd")) else None
            )
            or source.get("available_commentators")
        )
        panel_data["commentators_panel"] = self._normalize_name_entries(commentators_panel)
        
        organizers_panel = source.get("organizers_panel") or source.get("organizers")
        organizer_entries = self._coerce_entry_list(organizers_panel)
        if organizer_entries:
            panel_data["organizers_panel"] = organizer_entries
        else:
            panel_data["organizers_panel"] = []
        
        self.panel_data_sources = panel_data
    
    def _panel_data_from_pool(self, pool) -> Dict[str, list]:
        """Convert OfficialsPool object into panel-based lists."""
        def to_dict_list(items):
            return [{"full_name": o.full_name, "short_name": o.short_name} for o in items]
        
        panel_data = self._create_empty_panel_data()
        combined_officials = pool.referees + pool.linesmen + pool.fourth_officials + pool.var_referees
        panel_data["officials_panel"] = to_dict_list(combined_officials)
        panel_data["hosts_panel"] = to_dict_list(pool.hosts)
        panel_data["commentators_panel"] = to_dict_list(pool.commentators)
        # Organizers are not part of OfficialsPool yet; leave empty
        return panel_data
    
    def _ensure_panel_data_available(self) -> bool:
        """Ensure panel data sources are populated, falling back to backend pool."""
        if any(self.panel_data_sources.values()):
            return True
        pool = self.backend_service.get_officials_pool()
        if not pool:
            return False
        self.panel_data_sources = self._panel_data_from_pool(pool)
        self.officials_data = self.panel_data_sources.copy()
        return True
    
    def _collect_locked_names(self, panel_key: str, skip_attr: Optional[str]) -> List[str]:
        """Gather already-selected names for a panel, excluding the invoking button."""
        locked = []
        for attr in PANEL_BUTTON_ATTRS.get(panel_key, []):
            if skip_attr and attr == skip_attr:
                continue
            button = getattr(self, attr, None)
            if not button:
                continue
            selected_name = self._button_selected_name(button)
            default_text = self._get_button_default_text(button)
            if not selected_name:
                continue
            if default_text and button.text().strip() == default_text.strip():
                continue
            locked.append(selected_name)
        return locked

    def _button_selected_name(self, button: Optional[QPushButton]) -> str:
        """Return the canonical full name stored on a button."""
        if not button:
            return ""
        stored = button.property("selected_full_name")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        text = button.text().strip()
        if not text:
            return ""
        if text.endswith(")") and "(" in text:
            text = text.rsplit("(", 1)[0].strip()
        return text

    def _create_base_panel(self, title: str, reset_slot, min_height: int = 200) -> tuple[QWidget, QVBoxLayout]:
        """
        Create a base panel with consistent styling, header, and reset button.
        Returns the panel widget and the main layout to add content to.
        """
        panel = QWidget()
        panel.setStyleSheet(self.get_panel_style())
        if min_height:
            panel.setMinimumHeight(min_height)
        
        # Main layout
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Header with title and reset button
        header_layout = QHBoxLayout()
        
        # Label
        label = QLabel(title)
        label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(self.get_label_style())
        
        # Reset button
        btn_reset = QPushButton("RESET")
        btn_reset.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_reset.setStyleSheet(self.get_reset_button_style())
        btn_reset.clicked.connect(reset_slot)
        btn_reset.setFixedSize(80, 35)
        
        header_layout.addWidget(label)
        header_layout.addStretch()
        header_layout.addWidget(btn_reset)
        
        layout.addLayout(header_layout)
        
        return panel, layout

    def create_officials_panel(self):
        """Create officials panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(20, 10, 650, 10)
        panel.setStyleSheet(self.get_panel_style())
        
        # Officials label
        officials_label = QLabel("OFFICIALS", panel)
        officials_label.setGeometry(10, 10, 630, 40)
        officials_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        officials_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        officials_label.setStyleSheet(self.get_label_style())
        
        # Create clickable buttons for officials (matching Game_Setting.py)
        self.btn_referee_name = self.create_official_button("Referee Name", 10, 60, 150, 40, "referee", panel)
        self.btn_linesman_1 = self.create_official_button("Linesman 1 Name", 170, 60, 150, 40, "assistant1", panel)
        self.btn_linesman_2 = self.create_official_button("Linesman 2 Name", 330, 60, 150, 40, "assistant2", panel)
        self.btn_fourth_referee = self.create_official_button("Fourth Official Name", 490, 60, 150, 40, "fourth_official", panel)
        
        # Reset button
        btn_reset_officials = QPushButton("RESET", panel)
        btn_reset_officials.setGeometry(580, 10, 60, 30)
        btn_reset_officials.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        btn_reset_officials.setStyleSheet(self.get_reset_button_style())
        btn_reset_officials.clicked.connect(self.reset_officials)
        
        return panel

    def create_hosts_panel(self):
        """Create hosts panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(20, 140, 650, 110)
        panel.setStyleSheet(self.get_panel_style())
        
        # Hosts label
        hosts_label = QLabel("HOSTS", panel)
        hosts_label.setGeometry(10, 10, 630, 40)
        hosts_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        hosts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hosts_label.setStyleSheet(self.get_label_style())
        
        # Create clickable buttons for hosts
        self.btn_host_1 = self.create_official_button("Host 1", 10, 60, 200, 40, "host1", panel)
        self.btn_host_2 = self.create_official_button("Host 2", 225, 60, 200, 40, "host2", panel)
        self.btn_host_3 = self.create_official_button("Host 3", 440, 60, 200, 40, "host3", panel)
        
        # Reset button
        btn_reset_hosts = QPushButton("RESET", panel)
        btn_reset_hosts.setGeometry(580, 10, 60, 30)
        btn_reset_hosts.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        btn_reset_hosts.setStyleSheet(self.get_reset_button_style())
        btn_reset_hosts.clicked.connect(self.reset_hosts)
        
        return panel

    def create_guests_panel(self):
        """Create guests panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(20, 270, 650, 110)
        panel.setStyleSheet(self.get_panel_style())
        
        # Guests label
        guests_label = QLabel("GUESTS", panel)
        guests_label.setGeometry(10, 10, 630, 40)
        guests_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        guests_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        guests_label.setStyleSheet(self.get_label_style())
        
        # Create clickable buttons for guests
        self.btn_guest_1 = self.create_official_button("Guest 1", 10, 60, 200, 40, "guest1", panel)
        self.btn_guest_2 = self.create_official_button("Guest 2", 225, 60, 200, 40, "guest2", panel)
        self.btn_guest_3 = self.create_official_button("Guest 3", 440, 60, 200, 40, "guest3", panel)
        
        # Reset button
        btn_reset_guests = QPushButton("RESET", panel)
        btn_reset_guests.setGeometry(580, 10, 60, 30)
        btn_reset_guests.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        btn_reset_guests.setStyleSheet(self.get_reset_button_style())
        btn_reset_guests.clicked.connect(self.reset_guests)
        
        return panel

    def create_commentators_panel(self):
        """Create commentators panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(720, 10, 650, 240)
        panel.setStyleSheet(self.get_panel_style())
        
        # First half commentators label
        first_half_label = QLabel("1st HALF COMMENTATORS", panel)
        first_half_label.setGeometry(10, 10, 630, 40)
        first_half_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        first_half_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        first_half_label.setStyleSheet(self.get_label_style())
        
        # First half commentators
        self.btn_commentator_1 = self.create_official_button("Commentator 1", 10, 55, 200, 40, "commentator1", panel)
        self.btn_commentator_2 = self.create_official_button("Commentator 2", 225, 55, 200, 40, "commentator2", panel)
        self.btn_commentator_3 = self.create_official_button("Commentator 3", 440, 55, 200, 40, "commentator3", panel)
        
        # Second half commentators label
        second_half_label = QLabel("2nd HALF COMMENTATORS", panel)
        second_half_label.setGeometry(10, 140, 630, 40)
        second_half_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        second_half_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        second_half_label.setStyleSheet(self.get_label_style())
        
        # Second half commentators
        self.btn_commentator_4 = self.create_official_button("Commentator 4", 10, 185, 200, 40, "commentator4", panel)
        self.btn_commentator_5 = self.create_official_button("Commentator 5", 225, 185, 200, 40, "commentator5", panel)
        self.btn_commentator_6 = self.create_official_button("Commentator 6", 440, 185, 200, 40, "commentator6", panel)
        
        # Reset button
        btn_reset_commentators = QPushButton("RESET", panel)
        btn_reset_commentators.setGeometry(580, 10, 60, 30)
        btn_reset_commentators.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        btn_reset_commentators.setStyleSheet(self.get_reset_button_style())
        btn_reset_commentators.clicked.connect(self.reset_commentators)
        
        return panel

    def create_special_guests_panel(self):
        """Create special guests panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(720, 270, 650, 110)
        panel.setStyleSheet(self.get_panel_style())
        
        # Special guests label
        special_guests_label = QLabel("SPECIAL GUESTS", panel)
        special_guests_label.setGeometry(10, 10, 630, 40)
        special_guests_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        special_guests_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        special_guests_label.setStyleSheet(self.get_label_style())
        
        # Create clickable buttons for special guests
        self.btn_special_guest_1 = self.create_official_button("Special Guest 1", 10, 60, 200, 40, "special_guest1", panel)
        self.btn_special_guest_2 = self.create_official_button("Special Guest 2", 225, 60, 200, 40, "special_guest2", panel)
        self.btn_special_guest_3 = self.create_official_button("Special Guest 3", 440, 60, 200, 40, "special_guest3", panel)
        
        # Reset button
        btn_reset_special_guests = QPushButton("RESET", panel)
        btn_reset_special_guests.setGeometry(580, 10, 60, 30)
        btn_reset_special_guests.setFont(QFont("Verdana", 8, QFont.Weight.Bold))
        btn_reset_special_guests.setStyleSheet(self.get_reset_button_style())
        btn_reset_special_guests.clicked.connect(self.reset_special_guests)
        
        return panel

    def create_tournament_panel(self):
        """Create tournament panel matching Game_Setting.py layout"""
        panel = QWidget(self)
        panel.setGeometry(1400, 10, 480, 390)
        panel.setStyleSheet(self.get_panel_style())
        
        # Tournament label
        tournament_label = QLabel("TOURNAMENT/LEAGUE DETAILS", panel)
        tournament_label.setGeometry(10, 10, 460, 30)
        tournament_label.setFont(QFont("Verdana", 12, QFont.Weight.Bold))
        tournament_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tournament_label.setStyleSheet(self.get_label_style())
        
        # Tournament details (uneditable fields)
        self.tournament_name_label = self.create_info_label("Tournament Name: Not Set", 10, 50, 460, 35, panel)
        self.tournament_shortname_label = self.create_info_label("Short Name: Not Set", 10, 95, 460, 35, panel)
        self.year_label = self.create_info_label("Year: Not Set", 10, 140, 460, 35, panel)
        self.season_label = self.create_info_label("Season: Not Set", 10, 185, 460, 35, panel)
        self.title_sponsor_label = self.create_info_label("Sponsor: Not Set", 10, 230, 460, 35, panel)
        self.hastag_label = self.create_info_label("Hashtag: Not Set", 10, 275, 460, 35, panel)
        self.tagline_label = self.create_info_label("Tagline: Not Set", 10, 320, 460, 35, panel)
        
        return panel

    def create_officials_panel_responsive(self):
        """Create responsive officials panel using layout"""
        panel, layout = self._create_base_panel("OFFICIALS", self.reset_officials, min_height=None)
        
        # Officials buttons layout with labels above each button
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        # Create clickable buttons for officials
        self.btn_referee_name = self.create_official_button_responsive("Referee Name", "referee")
        self.btn_linesman_1 = self.create_official_button_responsive("Linesman 1", "assistant1")
        self.btn_linesman_2 = self.create_official_button_responsive("Linesman 2", "assistant2")
        self.btn_fourth_referee = self.create_official_button_responsive("Fourth Official Name", "fourth_official")

        def labeled_layout(button: QPushButton, text: str) -> QVBoxLayout:
            column = QVBoxLayout()
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(5)  # Increase spacing between label and button
            column.addStretch()  # Add top stretch for centering

            label = QLabel(text)
            label.setMargin(0)
            label.setContentsMargins(0, 0, 0, 0)
            label.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: grey; background-color: transparent; border: none; padding-top: 0px; padding-bottom: 0; margin: 0;")
            
            column.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(button)
            column.addStretch()  # Force packing to top
            return column

        buttons_layout.addLayout(labeled_layout(self.btn_referee_name, "Referee"))
        buttons_layout.addLayout(labeled_layout(self.btn_linesman_1, "Linesman 1"))
        buttons_layout.addLayout(labeled_layout(self.btn_linesman_2, "Linesman 2"))
        buttons_layout.addLayout(labeled_layout(self.btn_fourth_referee, "Fourth Official"))
        
        layout.addLayout(buttons_layout)
        
        return panel

    def create_hosts_panel_responsive(self):
        """Create responsive hosts panel using layout"""
        panel, layout = self._create_base_panel("HOSTS", self.reset_hosts, min_height=200)
        
        # First row of hosts (1-3)
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(6)
        
        self.btn_host_1 = self.create_official_button_responsive("Host 1", "host1")
        self.btn_host_2 = self.create_official_button_responsive("Host 2", "host2")
        self.btn_host_3 = self.create_official_button_responsive("Host 3", "host3")
        
        first_row_layout.addWidget(self.btn_host_1)
        first_row_layout.addWidget(self.btn_host_2)
        first_row_layout.addWidget(self.btn_host_3)
        
        # Second row of hosts (4-6)
        second_row_layout = QHBoxLayout()
        second_row_layout.setSpacing(6)
        
        self.btn_host_4 = self.create_official_button_responsive("Host 4", "host4")
        self.btn_host_5 = self.create_official_button_responsive("Host 5", "host5")
        self.btn_host_6 = self.create_official_button_responsive("Host 6", "host6")
        
        second_row_layout.addWidget(self.btn_host_4)
        second_row_layout.addWidget(self.btn_host_5)
        second_row_layout.addWidget(self.btn_host_6)
        
        layout.addLayout(first_row_layout)
        layout.addLayout(second_row_layout)
        
        return panel


    def create_guests_panel_unified_responsive(self):
        """Create unified guests panel spanning two rows"""
        panel, layout = self._create_base_panel("GUESTS", self.reset_all_guests, min_height=200)
        
        # First row of guests (1-3)
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(6)
        
        self.btn_guest_1 = self.create_guest_button_responsive("Guest 1", "guest1")
        self.btn_guest_2 = self.create_guest_button_responsive("Guest 2", "guest2")
        self.btn_guest_3 = self.create_guest_button_responsive("Guest 3", "guest3")
        
        first_row_layout.addWidget(self.btn_guest_1)
        first_row_layout.addWidget(self.btn_guest_2)
        first_row_layout.addWidget(self.btn_guest_3)
        
        # Second row of guests (4-6)
        second_row_layout = QHBoxLayout()
        second_row_layout.setSpacing(6)
        
        self.btn_guest_4 = self.create_guest_button_responsive("Guest 4", "guest4")
        self.btn_guest_5 = self.create_guest_button_responsive("Guest 5", "guest5")
        self.btn_guest_6 = self.create_guest_button_responsive("Guest 6", "guest6")
        
        second_row_layout.addWidget(self.btn_guest_4)
        second_row_layout.addWidget(self.btn_guest_5)
        second_row_layout.addWidget(self.btn_guest_6)
        
        layout.addLayout(first_row_layout)
        layout.addLayout(second_row_layout)
        
        # Initialize guest data storage
        self.guest_data = {}
        
        return panel

    def create_members_panel_responsive(self):
        """Create responsive organizers panel using layout"""
        panel, layout = self._create_base_panel("ORGANIZERS", self.reset_organizers, min_height=200)
        
        #6 Buttos 
        first_row_buttons_layout = QHBoxLayout()
        first_row_buttons_layout.setSpacing(6)
        
        self.btn_organizer_1 = self.create_official_button_responsive("Organizer 1", "organizer1")
        self.btn_organizer_2 = self.create_official_button_responsive("Organizer 2", "organizer2")
        self.btn_organizer_3 = self.create_official_button_responsive("Organizer 3", "organizer3")
        self.btn_organizer_4 = self.create_official_button_responsive("Organizer 4", "organizer4")
        self.btn_organizer_5 = self.create_official_button_responsive("Organizer 5", "organizer5")
        self.btn_organizer_6 = self.create_official_button_responsive("Organizer 6", "organizer6")
        
        first_row_buttons_layout.addWidget(self.btn_organizer_1)
        first_row_buttons_layout.addWidget(self.btn_organizer_2)
        first_row_buttons_layout.addWidget(self.btn_organizer_3)
       
        second_row_buttons_layout = QHBoxLayout()
        second_row_buttons_layout.setSpacing(6)
        second_row_buttons_layout.addWidget(self.btn_organizer_4)
        second_row_buttons_layout.addWidget(self.btn_organizer_5)
        second_row_buttons_layout.addWidget(self.btn_organizer_6)

        layout.addLayout(first_row_buttons_layout)
        layout.addLayout(second_row_buttons_layout)
        return panel

    def create_commentators_panel_responsive(self):
        """Create responsive commentators panel using layout"""
        panel, layout = self._create_base_panel("COMMENTATORS", self.reset_commentators, min_height=200)
        
        # First half commentators - simplified layout
        first_half_layout = QHBoxLayout()
        first_half_layout.setSpacing(4)
        
        self.btn_commentator_1 = self.create_official_button_responsive("Commentator 1", "commentator1")
        self.btn_commentator_2 = self.create_official_button_responsive("Commentator 2", "commentator2")
        self.btn_commentator_3 = self.create_official_button_responsive("Commentator 3", "commentator3")
        
        first_half_layout.addWidget(self.btn_commentator_1)
        first_half_layout.addWidget(self.btn_commentator_2)
        first_half_layout.addWidget(self.btn_commentator_3)
        
        # Second half commentators - simplified layout
        second_half_layout = QHBoxLayout()
        second_half_layout.setSpacing(4)
        
        self.btn_commentator_4 = self.create_official_button_responsive("Commentator 4", "commentator4")
        self.btn_commentator_5 = self.create_official_button_responsive("Commentator 5", "commentator5")
        self.btn_commentator_6 = self.create_official_button_responsive("Commentator 6", "commentator6")
        
        second_half_layout.addWidget(self.btn_commentator_4)
        second_half_layout.addWidget(self.btn_commentator_5)
        second_half_layout.addWidget(self.btn_commentator_6)
        
        layout.addLayout(first_half_layout)
        layout.addLayout(second_half_layout)
        
        return panel


    def create_tournament_panel_responsive(self):
        """Create responsive tournament panel using layout"""
        panel = QWidget()
        panel.setStyleSheet(self.get_panel_style())
        panel.setMinimumHeight(200)  # Set minimum height for tournament details in grid
        
        # Main layout
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Tournament label
        tournament_label = QLabel("TOURNAMENT/LEAGUE DETAILS")
        tournament_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        tournament_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tournament_label.setStyleSheet(self.get_tournament_label_style())
        
        # Tournament details grid
        details_layout = QGridLayout()
        details_layout.setSpacing(6)
        
        # Tournament details (uneditable fields)
        self.tournament_name_label = self.create_info_label_responsive("Tournament Name: Not Set")
        self.tournament_shortname_label = self.create_info_label_responsive("Short Name: Not Set")
        self.year_label = self.create_info_label_responsive("Year: Not Set")
        self.season_label = self.create_info_label_responsive("Season: Not Set")
        self.title_sponsor_label = self.create_info_label_responsive("Sponsor: Not Set")
        self.hastag_label = self.create_info_label_responsive("Hashtag: Not Set")
        self.tagline_label = self.create_info_label_responsive("Tagline: Not Set")
        
        details_layout.addWidget(self.tournament_name_label, 0, 0)
        details_layout.addWidget(self.tournament_shortname_label, 0, 1)
        details_layout.addWidget(self.year_label, 1, 0)
        details_layout.addWidget(self.season_label, 1, 1)
        details_layout.addWidget(self.title_sponsor_label, 2, 0)
        details_layout.addWidget(self.hastag_label, 2, 1)
        details_layout.addWidget(self.tagline_label, 3, 0, 1, 2)
        
        layout.addWidget(tournament_label)
        layout.addLayout(details_layout)
        
        return panel

    def create_official_button_responsive(self, text: str, official_type: str):
        """Create a responsive clickable button for official selection"""
        button = QPushButton(text)
        button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        button.setStyleSheet(self.get_button_style())
        button.clicked.connect(lambda: self.open_official_selector(official_type))
        button.setMinimumHeight(40)
        
        # Enable context menu
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos: self.show_button_context_menu(button, official_type, pos)
        )
        
        self._register_button_default(button, text)
        return button
        
    def create_guest_button_responsive(self, text: str, guest_id: str):
        """Create a responsive clickable button for guest form (opens unified dialog)."""
        button = QPushButton(text)
        button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        button.setStyleSheet(self.get_button_style())
        button.clicked.connect(self.open_all_guests_form)
        button.setMinimumHeight(45)
        
        # Enable context menu
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos: self.show_button_context_menu(button, guest_id, pos)
        )
        
        self._register_button_default(button, text)
        return button

    def create_info_label_responsive(self, text: str):
        """Create a responsive info label for tournament details"""
        label = QLabel(text)
        label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(self.get_info_label_style())
        label.setMinimumHeight(40)
        return label

    def create_official_button(self, text: str, x: int, y: int, width: int, height: int, official_type: str, parent=None):
        """Create a clickable button for official selection matching Game_Setting.py style"""
        if parent is None:
            parent = self
        button = QPushButton(text, parent)
        button.setGeometry(x, y, width, height)
        button.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        button.setStyleSheet(self.get_button_style())
        button.clicked.connect(lambda: self.open_official_selector(official_type))
        
        # Enable context menu
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos: self.show_button_context_menu(button, official_type, pos)
        )
        
        self._register_button_default(button, text)
        return button
        
    def create_info_label(self, text: str, x: int, y: int, width: int, height: int, parent=None):
        """Create an info label for tournament details"""
        if parent is None:
            parent = self
        label = QLabel(text, parent)
        label.setGeometry(x, y, width, height)
        label.setFont(QFont("Verdana", 10, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(self.get_info_label_style())
        return label

    def on_officials_changed(self):
        """Handle officials data changes"""
        officials = self.get_officials()
        self.officials_changed.emit(officials)
        self.data_changed.emit()  # Emit data_changed signal

    def get_officials(self) -> Dict[str, Any]:
        """Get current officials data"""
        return {
            "referee": self.btn_referee_name.text() if hasattr(self, 'btn_referee_name') else "Not Set",
            "linesman_1": self.btn_linesman_1.text() if hasattr(self, 'btn_linesman_1') else "Not Set",
            "linesman_2": self.btn_linesman_2.text() if hasattr(self, 'btn_linesman_2') else "Not Set",
            "fourth_official": self.btn_fourth_referee.text() if hasattr(self, 'btn_fourth_referee') else "Not Set",
            "tournament": {
                "name": self.tournament_name_label.text().replace("Tournament Name: ", "") if hasattr(self, 'tournament_name_label') else "Not Set",
                "season": self.season_label.text().replace("Season: ", "") if hasattr(self, 'season_label') else "Not Set",
                "sponsor": self.title_sponsor_label.text().replace("Sponsor: ", "") if hasattr(self, 'title_sponsor_label') else "Not Set",
                "hashtag": self.hastag_label.text().replace("Hashtag: ", "") if hasattr(self, 'hastag_label') else "Not Set",
                "tagline": self.tagline_label.text().replace("Tagline: ", "") if hasattr(self, 'tagline_label') else "Not Set"
            },
            "hosts": [
                self.btn_host_1.text() if hasattr(self, 'btn_host_1') else "Not Set",
                self.btn_host_2.text() if hasattr(self, 'btn_host_2') else "Not Set",
                self.btn_host_3.text() if hasattr(self, 'btn_host_3') else "Not Set",
                self.btn_host_4.text() if hasattr(self, 'btn_host_4') else "Not Set",
                self.btn_host_5.text() if hasattr(self, 'btn_host_5') else "Not Set",
                self.btn_host_6.text() if hasattr(self, 'btn_host_6') else "Not Set"
            ],
            "organizers": [
                self.btn_organizer_1.text() if hasattr(self, 'btn_organizer_1') else "Not Set",
                self.btn_organizer_2.text() if hasattr(self, 'btn_organizer_2') else "Not Set",
                self.btn_organizer_3.text() if hasattr(self, 'btn_organizer_3') else "Not Set",
                self.btn_organizer_4.text() if hasattr(self, 'btn_organizer_4') else "Not Set",
                self.btn_organizer_5.text() if hasattr(self, 'btn_organizer_5') else "Not Set",
                self.btn_organizer_6.text() if hasattr(self, 'btn_organizer_6') else "Not Set",
            ],
            "commentators_1st": [
                self.btn_commentator_1.text() if hasattr(self, 'btn_commentator_1') else "Not Set",
                self.btn_commentator_2.text() if hasattr(self, 'btn_commentator_2') else "Not Set",
                self.btn_commentator_3.text() if hasattr(self, 'btn_commentator_3') else "Not Set"
            ],
            "commentators_2nd": [
                self.btn_commentator_4.text() if hasattr(self, 'btn_commentator_4') else "Not Set",
                self.btn_commentator_5.text() if hasattr(self, 'btn_commentator_5') else "Not Set",
                self.btn_commentator_6.text() if hasattr(self, 'btn_commentator_6') else "Not Set"
            ],
            "guests": {
                "guest1": self.guest_data.get("guest1", {}) if hasattr(self, 'guest_data') else {},
                "guest2": self.guest_data.get("guest2", {}) if hasattr(self, 'guest_data') else {},
                "guest3": self.guest_data.get("guest3", {}) if hasattr(self, 'guest_data') else {},
                "guest4": self.guest_data.get("guest4", {}) if hasattr(self, 'guest_data') else {},
                "guest5": self.guest_data.get("guest5", {}) if hasattr(self, 'guest_data') else {},
                "guest6": self.guest_data.get("guest6", {}) if hasattr(self, 'guest_data') else {}
            }
        }

    def set_officials(self, officials: Dict[str, Any]):
        """Set officials data"""
        if not officials:
            return
            
        # Set basic officials
        if hasattr(self, 'btn_referee_name'):
            self.btn_referee_name.setText(officials.get("referee", "Referee Name"))
        if hasattr(self, 'btn_linesman_1'):
            self.btn_linesman_1.setText(officials.get("linesman_1", "Linesman 1"))
            self.btn_linesman_1.setStyleSheet(self.get_button_style())
            self.btn_linesman_2.setText(officials.get("linesman_2", "Linesman 2"))
        if hasattr(self, 'btn_fourth_referee'):
            self.btn_fourth_referee.setText(officials.get("fourth_official", "4th Referee Name"))
        
        # Set tournament data
        tournament = officials.get("tournament", {})
        if hasattr(self, 'tournament_name_label'):
            self.tournament_name_label.setText(f"Tournament Name: {tournament.get('name', 'Not Set')}")
        if hasattr(self, 'season_label'):
            self.season_label.setText(f"Season: {tournament.get('season', 'Not Set')}")
        if hasattr(self, 'title_sponsor_label'):
            self.title_sponsor_label.setText(f"Sponsor: {tournament.get('sponsor', 'Not Set')}")
        if hasattr(self, 'hastag_label'):
            self.hastag_label.setText(f"Hashtag: {tournament.get('hashtag', 'Not Set')}")
        if hasattr(self, 'tagline_label'):
            self.tagline_label.setText(f"Tagline: {tournament.get('tagline', 'Not Set')}")
        
        # Set hosts
        hosts = officials.get("hosts", [])
        if hasattr(self, 'btn_host_1'):
            self.btn_host_1.setText(hosts[0] if len(hosts) > 0 else "Host 1")
        if hasattr(self, 'btn_host_2'):
            self.btn_host_2.setText(hosts[1] if len(hosts) > 1 else "Host 2")
        if hasattr(self, 'btn_host_3'):
            self.btn_host_3.setText(hosts[2] if len(hosts) > 2 else "Host 3")
        if hasattr(self, 'btn_host_4'):
            self.btn_host_4.setText(hosts[3] if len(hosts) > 3 else "Host 4")
        if hasattr(self, 'btn_host_5'):
            self.btn_host_5.setText(hosts[4] if len(hosts) > 4 else "Host 5")
        if hasattr(self, 'btn_host_6'):
            self.btn_host_6.setText(hosts[5] if len(hosts) > 5 else "Host 6")

        # Set organizers (supports both list and dict payloads)
        organizers_payload = officials.get("organizers", [])
        organizer_entries = self._coerce_entry_list(organizers_payload)
        for idx in range(1, 7):
            attr = f"btn_organizer_{idx}"
            if not hasattr(self, attr):
                continue
            button = getattr(self, attr)
            if idx - 1 < len(organizer_entries):
                full_name = organizer_entries[idx - 1].get("full_name", "")
                designation = organizer_entries[idx - 1].get("designation")
                display_text = f"{full_name} ({designation})" if designation else full_name
                final_text = display_text or f"Organizer {idx}"
                button.setText(final_text)
                button.setStyleSheet(self.get_selected_button_style())
                button.setProperty("selected_full_name", full_name.strip())
            else:
                default_text = self._get_button_default_text(button) or f"Organizer {idx}"
                button.setText(default_text)
                button.setStyleSheet(self.get_button_style())
                button.setProperty("selected_full_name", None)
        
        # Set commentators
        commentators_1st = officials.get("commentators_1st", [])
        if hasattr(self, 'btn_commentator_1'):
            self.btn_commentator_1.setText(commentators_1st[0] if len(commentators_1st) > 0 else "Commentator 1")
        if hasattr(self, 'btn_commentator_2'):
            self.btn_commentator_2.setText(commentators_1st[1] if len(commentators_1st) > 1 else "Commentator 2")
        if hasattr(self, 'btn_commentator_3'):
            self.btn_commentator_3.setText(commentators_1st[2] if len(commentators_1st) > 2 else "Commentator 3")
        
        commentators_2nd = officials.get("commentators_2nd", [])
        if hasattr(self, 'btn_commentator_4'):
            self.btn_commentator_4.setText(commentators_2nd[0] if len(commentators_2nd) > 0 else "Commentator 4")
        if hasattr(self, 'btn_commentator_5'):
            self.btn_commentator_5.setText(commentators_2nd[1] if len(commentators_2nd) > 1 else "Commentator 5")
        if hasattr(self, 'btn_commentator_6'):
            self.btn_commentator_6.setText(commentators_2nd[2] if len(commentators_2nd) > 2 else "Commentator 6")
        
        # Set guests (consolidated structure)
        guests = officials.get("guests", {})
        if hasattr(self, 'guest_data'):
            self.guest_data.clear()
            
        # Handle both old array format and new dict format for backward compatibility
        if isinstance(guests, list):
            # Old format - convert to new format
            for i, guest_name in enumerate(guests[:6], 1):
                if guest_name and guest_name != "Not Set":
                    guest_id = f"guest{i}"
                    self.guest_data[guest_id] = {
                        "full_name": guest_name,
                        "guest_type": "VIP Guest"
                    }
                    # Update button
                    button_attr = f"btn_guest_{i}"
                    if hasattr(self, button_attr):
                        button = getattr(self, button_attr)
                        button.setText(guest_name)
                        button.setStyleSheet(self.get_selected_button_style())
        else:
            # New dict format
            for guest_id, guest_data in guests.items():
                if guest_data:
                    self.guest_data[guest_id] = guest_data
                    # Update button (convert guest1 -> btn_guest_1)
                    guest_num = guest_id.replace('guest', '')
                    button_attr = f"btn_guest_{guest_num}"
                    if hasattr(self, button_attr):
                        button = getattr(self, button_attr)
                        display_name = guest_data.get("full_name", "Guest")
                        button.setText(display_name)
                        button.setStyleSheet(self.get_selected_button_style())
        
        # Emit data_changed signal after setting all officials data
        self.data_changed.emit()
        
    def on_officials_pool_loaded(self, event):
        """
        Handle officials pool loaded event from service
        This is the NEW event-driven approach
        """
        print(f" OfficialsTab: Officials pool loaded event received - {event.total_officials} officials")
        
        # Convert Officials pool to the old format for backward compatibility
        # This allows existing UI code to work without changes
        pool = event.pool
        
        self.officials_data = {
            'referees': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.referees],
            'linesmen': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.linesmen],
            'fourth_officials': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.fourth_officials],
            'var_officials': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.var_referees],
            'commentators': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.commentators],
            'hosts': [{'full_name': o.full_name, 'short_name': o.short_name} for o in pool.hosts]
        }
        
    
    def load_officials_data(self, officials_data: Dict[str, Any]):
        """
        DEPRECATED: Load officials data from JSON
        This method is kept for backward compatibility.
        New code should use backend_service.load_officials_pool() instead
        """
        # DEPRECATED: This method is kept for backward compatibility only
        self.officials_data = officials_data or {}
        self._rebuild_panel_data_sources(self.officials_data)
        
    def load_tournament_data(self, tournament_data: Dict[str, Any]):
        """Load tournament data from JSON and update the tournament panel"""
        
        # Update tournament labels with actual data
        if hasattr(self, 'tournament_name_label'):
            self.tournament_name_label.setText(f"Tournament Name: {tournament_data.get('name', 'Not Set')}")
        if hasattr(self, 'tournament_shortname_label'):
            self.tournament_shortname_label.setText(f"Short Name: {tournament_data.get('short_name', 'Not Set')}")
        if hasattr(self, 'year_label'):
            self.year_label.setText(f"Year: {tournament_data.get('year', 'Not Set')}")
        if hasattr(self, 'season_label'):
            self.season_label.setText(f"Season: {tournament_data.get('season', 'Not Set')}")
        if hasattr(self, 'title_sponsor_label'):
            self.title_sponsor_label.setText(f"Sponsor: {tournament_data.get('sponsor', 'Not Set')}")
        if hasattr(self, 'hastag_label'):
            self.hastag_label.setText(f"Hashtag: {tournament_data.get('hashtag', 'Not Set')}")
        if hasattr(self, 'tagline_label'):
            self.tagline_label.setText(f"Tagline: {tournament_data.get('tagline', 'Not Set')}")
            
        print(f"OfficialsTab: Tournament data loaded and displayed successfully")
        
        # Emit data_changed signal after loading tournament data
        self.data_changed.emit()
    
    def get_officials_data(self) -> Dict[str, Any]:
        """Get officials data for match setup tab"""
        return self.get_officials()
        
    def open_official_selector(self, official_type: str):
        """Open official selector dialog"""
        print(f"OfficialsTab: Opening selector for {official_type}")
        
        if not self._ensure_panel_data_available():
                print("OfficialsTab: No officials pool found in backend service!")
                QMessageBox.warning(self, "No Data", "No officials pool data available. Please load a fixture with officials pool data.")
                return
            
        panel_key = TYPE_TO_PANEL.get(official_type)
        if not panel_key:
            print(f"OfficialsTab: Unknown official type: {official_type}")
            QMessageBox.warning(self, "Invalid Type", f"Unknown official type: {official_type}")
            return
            
        panel_list = self.panel_data_sources.get(panel_key, [])
        if not panel_list:
            print(f"OfficialsTab: No data found for {panel_key}.")
            QMessageBox.warning(self, "No Data", f"No {panel_key.replace('_', ' ')} data available. Please load a fixture with officials pool data.")
            return
            
        button_attr = TYPE_TO_BUTTON.get(official_type)
        locked_names = self._collect_locked_names(panel_key, button_attr)
        
        print(f"OfficialsTab: Opening selector for {official_type} with {len(panel_list)} items")
        
        # String-to-dict conversion is now handled by OfficialsService
        # Data coming from service is already normalized
        # This ensures DRY principle - transformation happens in ONE place
        
        title = official_type.replace("_", " ").title()
        
        dialog = OfficialSelectorDialog(panel_list, title, self, locked_names=locked_names)
        dialog.official_selected.connect(lambda official: self.set_selected_official(official_type, official))
        dialog.exec()
        
    def set_selected_official(self, official_type: str, official: Dict[str, Any]):
        """Set the selected official"""
        official_name = official.get("full_name", "Not Set")
        designation = official.get("designation") or official.get("title")
        if official_type.startswith("organizer") and designation:
            official_name = f"{official_name} ({designation})"
        
        # Map official types to button attributes
        button_attr = TYPE_TO_BUTTON.get(official_type)
        if not button_attr and official_type.startswith("guest"):
            button_attr = f"btn_{official_type}"
        elif not button_attr and official_type.startswith("special_guest"):
            button_attr = f"btn_{official_type}"
        
        if button_attr and hasattr(self, button_attr):
            button = getattr(self, button_attr)
            button.setText(official_name)
            # Apply selected style
            button.setStyleSheet(self.get_selected_button_style())
            button.setProperty("selected_full_name", official.get("full_name", "").strip())
            
        self.on_officials_changed()
    
    def show_button_context_menu(self, button: QPushButton, official_type: str, position):
        """Show context menu for resetting individual buttons"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1f2937;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #ffffff;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
        """)
        
        reset_action = menu.addAction("Reset")
        reset_action.triggered.connect(lambda: self.reset_single_button(button, official_type))
        
        menu.exec(button.mapToGlobal(position))
    
    def reset_single_button(self, button: QPushButton, official_type: str):
        """Reset a single button to its default text and style"""
        # Map official types to default text
        default_texts = {
            "referee": "Referee Name",
            "assistant1": "Linesman 1",
            "assistant2": "Linesman 2",
            "fourth_official": "4th Referee Name",
            "var_referee": "VAR Referee",
            "avar_referee": "AVAR Referee",
            "host1": "Host 1",
            "host2": "Host 2",
            "host3": "Host 3",
            "host4": "Host 4",
            "host5": "Host 5",
            "host6": "Host 6",
            "organizer1": "Organizer 1",
            "organizer2": "Organizer 2",
            "organizer3": "Organizer 3",
            "organizer4": "Organizer 4",
            "organizer5": "Organizer 5",
            "organizer6": "Organizer 6",
            "guest1": "Guest 1",
            "guest2": "Guest 2",
            "guest3": "Guest 3",
            "guest4": "Guest 4",
            "guest5": "Guest 5",
            "guest6": "Guest 6",
            "commentator1": "Commentator 1",
            "commentator2": "Commentator 2",
            "commentator3": "Commentator 3",
            "commentator4": "Commentator 4",
            "commentator5": "Commentator 5",
            "commentator6": "Commentator 6",
            "special_guest1": "Special Guest 1",
            "special_guest2": "Special Guest 2",
            "special_guest3": "Special Guest 3"
        }
        
        default_text = self._get_button_default_text(button) or default_texts.get(official_type, button.text())
        button.setText(default_text)
        button.setStyleSheet(self.get_button_style())
        button.setProperty("selected_full_name", None)
        
        # If it's a guest button, also clear the guest data
        if official_type.startswith("guest"):
            guest_num = official_type.replace("guest", "")
            if hasattr(self, 'guest_data') and f"guest{guest_num}" in self.guest_data:
                del self.guest_data[f"guest{guest_num}"]
        
        self.on_officials_changed()
        
    def reset_officials(self):
        """Reset officials section"""
        if hasattr(self, 'btn_referee_name'):
            self.btn_referee_name.setText("Referee Name")
        if hasattr(self, 'btn_linesman_1'):
            self.btn_linesman_1.setText("Linesman 1")
        if hasattr(self, 'btn_linesman_2'):
            self.btn_linesman_2.setText("Linesman 2")
        if hasattr(self, 'btn_fourth_referee'):
            self.btn_fourth_referee.setText("4th Referee Name")
        self.on_officials_changed()
        
    def reset_hosts(self):
        """Reset hosts section"""
        if hasattr(self, 'btn_host_1'):
            self.btn_host_1.setText("Host 1")
        if hasattr(self, 'btn_host_2'):
            self.btn_host_2.setText("Host 2")
        if hasattr(self, 'btn_host_3'):
            self.btn_host_3.setText("Host 3")
        if hasattr(self, 'btn_host_4'):
            self.btn_host_4.setText("Host 4")
        if hasattr(self, 'btn_host_5'):
            self.btn_host_5.setText("Host 5")
        if hasattr(self, 'btn_host_6'):
            self.btn_host_6.setText("Host 6")
        self.on_officials_changed()
        
    def reset_commentators(self):
        """Reset commentators section"""
        if hasattr(self, 'btn_commentator_1'):
            self.btn_commentator_1.setText("Commentator 1")
        if hasattr(self, 'btn_commentator_2'):
            self.btn_commentator_2.setText("Commentator 2")
        if hasattr(self, 'btn_commentator_3'):
            self.btn_commentator_3.setText("Commentator 3")
        if hasattr(self, 'btn_commentator_4'):
            self.btn_commentator_4.setText("Commentator 4")
        if hasattr(self, 'btn_commentator_5'):
            self.btn_commentator_5.setText("Commentator 5")
        if hasattr(self, 'btn_commentator_6'):
            self.btn_commentator_6.setText("Commentator 6")
        self.on_officials_changed()

    def reset_organizers(self):
        """Reset organizers section"""
        for idx in range(1, 7):
            attr = f"btn_organizer_{idx}"
            if hasattr(self, attr):
                button = getattr(self, attr)
                button.setText(f"Organizer {idx}")
                button.setStyleSheet(self.get_button_style())
        self.on_officials_changed()
        
    def reset_all_guests(self):
        """Reset all guests section (consolidated)"""
        # Reset all guest buttons
        guest_buttons = [
            'btn_guest_1', 'btn_guest_2', 'btn_guest_3',
            'btn_guest_4', 'btn_guest_5', 'btn_guest_6'
        ]
        
        for i, btn_attr in enumerate(guest_buttons, 1):
            if hasattr(self, btn_attr):
                button = getattr(self, btn_attr)
                button.setText(f"Guest {i}")
                button.setStyleSheet(self.get_button_style())  # Reset to default style
        
        # Clear guest data
        if hasattr(self, 'guest_data'):
            self.guest_data.clear()
            
        self.on_officials_changed()

    def reset_members(self):
        """Reset members section"""
        if hasattr(self, 'members_data'):
            self.members_data.clear()
        self.on_officials_changed()
        
    def open_all_guests_form(self):
        """Open a single form to edit all guests at once."""
        try:
            from .multi_guest_form_dialog import MultiGuestFormDialog
            existing = getattr(self, 'guest_data', {}) if hasattr(self, 'guest_data') else {}
            dialog = MultiGuestFormDialog(existing, self)
            dialog.guests_saved.connect(self.save_all_guests_data)
            dialog.exec()
        except Exception as e:
            print(f"Error opening MultiGuestFormDialog: {e}")

    def save_all_guests_data(self, all_guests: Dict[str, Any]):
        """Save multiple guests at once and update buttons."""
        if not hasattr(self, 'guest_data'):
            self.guest_data = {}
        # Merge
        for guest_id, data in all_guests.items():
            self.guest_data[guest_id] = data
            # Update button text
            try:
                guest_num = guest_id.replace('guest', '')
                button_attr = f"btn_guest_{guest_num}"
                if hasattr(self, button_attr):
                    btn = getattr(self, button_attr)
                    btn.setText(data.get('full_name', f'Guest {guest_num}'))
                    btn.setStyleSheet(self.get_selected_button_style())
            except Exception:
                pass
        self.on_officials_changed()
        
    def save_guest_data(self, guest_id: str, guest_data: Dict[str, Any]):
        """Save guest data and update button"""
        print(f"Saving guest data for {guest_id}: {guest_data}")
        
        # Store guest data
        self.guest_data[guest_id] = guest_data
        
        # Update button text and style (convert guest1 -> btn_guest_1)
        guest_num = guest_id.replace('guest', '')
        button_attr = f"btn_guest_{guest_num}"
        print(f"Looking for button: {button_attr}")
        
        if hasattr(self, button_attr):
            button = getattr(self, button_attr)
            display_name = guest_data.get("full_name", "Guest")
            print(f"Setting button text to: {display_name}")
            button.setText(display_name)
            button.setStyleSheet(self.get_selected_button_style())
            print(f"Button text updated successfully")
        else:
            print(f"Button {button_attr} not found!")
            
        self.on_officials_changed()

    @staticmethod
    def _coerce_name_list(payload: Any) -> List[str]:
        """Convert various payload shapes to a list of display names."""
        names: List[str] = []
        if isinstance(payload, list):
            for entry in payload:
                name = OfficialsTab._value_to_name(entry)
                if name:
                    names.append(name)
        elif isinstance(payload, dict):
            def sort_key(key: Any):
                key_str = str(key)
                match = re.search(r'(\d+)$', key_str)
                return (int(match.group(1)) if match else 0, key_str)
            for item_key in sorted(payload.keys(), key=sort_key):
                name = OfficialsTab._value_to_name(payload[item_key])
                if name:
                    names.append(name)
        else:
            name = OfficialsTab._value_to_name(payload)
            if name:
                names.append(name)
        return names

    @staticmethod
    def _value_to_name(value: Any) -> str:
        """Extract a readable name from dicts/strings."""
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("full_name", "name", "short_name", "display_name", "title", "label"):
                if value.get(key):
                    return str(value[key])
            return ""
        return str(value).strip()

    @staticmethod
    def _coerce_entry_list(payload: Any) -> List[Dict[str, Any]]:
        """Convert payload into list of dict entries with full_name/short_name/designation."""
        entries: List[Dict[str, Any]] = []
        def build_entry(val: Any) -> Optional[Dict[str, Any]]:
            if isinstance(val, dict):
                entry = {
                    "full_name": val.get("full_name") or val.get("name") or "",
                    "short_name": val.get("short_name") or val.get("full_name", "").split()[-1] if val.get("full_name") else "",
                    "designation": val.get("designation")
                }
                return entry if entry["full_name"] else None
            text = str(val).strip()
            if not text:
                return None
            short = text.split()[-1] if " " in text else text
            return {"full_name": text, "short_name": short, "designation": None}
        
        if isinstance(payload, list):
            for item in payload:
                entry = build_entry(item)
                if entry:
                    entries.append(entry)
        elif isinstance(payload, dict):
            def sort_key(key: Any):
                key_str = str(key)
                match = re.search(r'(\d+)$', key_str)
                return (int(match.group(1)) if match else 0, key_str)
            for item_key in sorted(payload.keys(), key=sort_key):
                entry = build_entry(payload[item_key])
                if entry:
                    entries.append(entry)
        else:
            entry = build_entry(payload)
            if entry:
                entries.append(entry)
        return entries

    def get_panel_style(self) -> str:
        """Get panel style using our modern design language"""
        return """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2937, stop:1 #111827);
                border: 1px solid #4b5563;
                border-radius: 12px;
            }
        """

    def get_tournament_label_style(self) -> str:
        return """
            QLabel {
                background: none;
                color: #ffffff;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 12px;
            }
        """
    def get_label_style(self) -> str:
        """Get label style using our modern design language"""
        return """
            QLabel {
                background: none;
                color: #ffffff;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 0px 0px 0px 20px;
                margin: 0px 0px 0px 0px;
            }
        """

    def get_button_style(self) -> str:
        """Get button style using our modern design language"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #374151, stop:1 #4b5563);
                color: #ffffff;
                border: 1px solid #6b7280;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 12px;
                letter-spacing: 0.025em;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4b5563, stop:1 #6b7280);
                border: 1px solid #9ca3af;
            }
        """

    def get_selected_button_style(self) -> str:
        """Get selected button style using our modern design language"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #047857);
                color: #ffffff;
                border: 1px solid #10b981;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 12px;
                letter-spacing: 0.025em;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34d399, stop:1 #10b981);
            }
        """

    def get_info_label_style(self) -> str:
        """Get info label style for tournament details using our modern design language"""
        return """
            QLabel {
                background: transparent;
                color: #d1d5db;
                border: none;
                font-size: 13px;
                font-weight: 500;
                padding: 4px 0px;
                letter-spacing: 0.025em;
            }
        """
        
    def get_reset_button_style(self) -> str:
        """Get reset button style using our modern design language"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
                color: #ffffff;
                border: 1px solid #dc2626;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                letter-spacing: 0.025em;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b91c1c, stop:1 #991b1b);
            }
        """
