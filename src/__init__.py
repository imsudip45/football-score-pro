"""Football Score Pro 2.0 - Main Package"""

__version__ = "2.0.0"
__author__ = "Football Score Pro"
__description__ = "A comprehensive football match management system"

# Version info
VERSION_INFO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

def get_version_string() -> str:
    """Get formatted version string."""
    return f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}"
