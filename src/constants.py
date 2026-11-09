"""
Football Score Pro 2.0 - Application Constants
"""

import os


class AppConstants:
    VERSION = "2.0.0"
    RELEASE = "stable"
    # PIN used by the operator lock until it is changed in Tools > Set PIN.
    DEFAULT_PIN = os.environ.get("FSP_DEFAULT_PIN", "2580")
    # Recovery PIN that can replace a forgotten PIN. Disabled unless
    # FSP_MASTER_PIN is set, so a published value can't unlock every install.
    MASTER_PIN = os.environ.get("FSP_MASTER_PIN") or None

class TeamConstants:
    TEAM_A = "Team A"
    TEAM_B = "Team B"
    SELECT_FORMATION = "Select Formation"
    DEFAULT_COLOR = "#000000"

class ValidationConstants:
    # Team Composition
    MIN_GOALKEEPERS = 1
    MAX_GOALKEEPERS_WARN = 3
    MIN_DEFENDERS_WARN = 3
    MIN_MIDFIELDERS_WARN = 3
    MIN_FORWARDS_WARN = 1
    STARTING_XI_COUNT = 11
    STARTING_GK_COUNT = 1
    
    # Match Rules
    MIN_HALF_DURATION = 1
    MAX_HALF_DURATION = 60
    MIN_HALF_TIME = 0
    MAX_HALF_TIME = 30
    MAX_SUBSTITUTIONS = 11
    MAX_SUB_WINDOWS = 5
    
    # FIFA Standards
    FIFA_MAX_SUBSTITUTIONS = 5
    FIFA_MAX_SUBSTITUTION_WINDOWS = 3
    STANDARD_HALF_DURATION = 45
    
    # Player Data
    MIN_PLAYERS_PER_TEAM = 11
    MAX_PLAYERS_PER_TEAM = 23
    MIN_JERSEY_NUMBER = 1
    MAX_JERSEY_NUMBER = 99

class UIConstants:
    # Fonts
    FONT_FAMILY_MAIN = "Verdana"
    FONT_SIZE_TITLE = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_NORMAL = 11
    FONT_WEIGHT_BOLD = 75  # QFont.Weight.Bold approx
    
    # Colors
    COLOR_BORDER_DEFAULT = "#4b5563"
    COLOR_BORDER_FOCUS = "#3b82f6"
    COLOR_BORDER_ERROR = "#ef4444"
    COLOR_PRIMARY = "#1d4ed8"
    COLOR_PRIMARY_HOVER = "#1e40af"
    COLOR_TEXT_WHITE = "#ffffff"
    COLOR_TEXT_LIGHT = "#e5e7eb"
    COLOR_BG_INPUT = "#1f2937"
    COLOR_BG_INPUT_FOCUS = "#374151"
    COLOR_BTN_CANCEL = "#6b7280"
    COLOR_BTN_CANCEL_HOVER = "#4b5563"
    COLOR_BTN_CANCEL_PRESSED = "#374151"
    
    # Dimensions
    DIALOG_WIDTH = 380
    DIALOG_HEIGHT = 260
    PADDING_LARGE = 24
    PADDING_NORMAL = 16
    PADDING_SMALL = 8
    BORDER_RADIUS = 8
    BORDER_WIDTH = 2

class DataKeys:
    # Team Data
    FORMATION = "formation"
    POSITIONS = "positions"
    PLAYERS = "players"
    JERSEY_NUMBER = "jersey_number"
    JERSEY_NO = "jersey_no"
    FULL_NAME = "full_name"
    NAME = "name"
    SHORT_NAME = "short_name"
    POSITION = "position"
    ID = "id"
    MANAGER = "manager"
    HEAD_COACH = "head_coach"
    COACH = "coach"
    COLOR_1 = "color_1"
    COLOR_2 = "color_2"
    COLOR_MODE = "color_mode"
    LOGO = "logo"
    LOGO_URL = "logo_url"
    KITS = "kits"
    KIT_IMAGE = "kit_image"
    SELECTED = "selected"
    IS_SUBSTITUTION = "is_substitution"
    PLAYING_11 = "playing_11"
    SUBSTITUTIONS = "substitutions"
    
    # Match Data
    HOME_TEAM = "home_team"
    AWAY_TEAM = "away_team"


