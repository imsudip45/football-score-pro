"""Result and Error Handling Models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from .team import Team


class ErrorType(Enum):
    """Error type enumeration."""
    VALIDATION = "validation"
    IMPORT = "import"
    BUSINESS = "business"
    SYSTEM = "system"
    PERSISTENCE = "persistence"


@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation.
    
    Attributes:
        is_valid: Whether the validation passed
        errors: List of error messages
        warnings: List of warning messages
        field_errors: Dictionary mapping field names to their specific errors
        timestamp: When the validation was performed
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_errors: Dict[str, List[str]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str, field: Optional[str] = None):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
        
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(message)

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def get_error_count(self) -> int:
        """Get total number of errors."""
        return len(self.errors)

    def get_warning_count(self) -> int:
        """Get total number of warnings."""
        return len(self.warnings)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "field_errors": self.field_errors,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> 'ValidationResult':
        """Create a successful validation result."""
        return cls(
            is_valid=True,
            warnings=warnings or []
        )

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None) -> 'ValidationResult':
        """Create a failed validation result."""
        return cls(
            is_valid=False,
            errors=errors,
            warnings=warnings or []
        )


@dataclass
class ImportResult:
    """
    Represents the result of an import operation.
    
    Attributes:
        success: Whether the import was successful
        team: The imported team (if successful)
        errors: List of error messages
        warnings: List of warning messages
        file_path: Path to the imported file
        processed_players: Number of players processed
        timestamp: When the import was performed
    """
    success: bool
    team: Optional[Team] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    processed_players: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "team": self.team.to_dict() if self.team else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_path": self.file_path,
            "processed_players": self.processed_players,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success_result(cls, team: Team, file_path: str, warnings: Optional[List[str]] = None) -> 'ImportResult':
        """Create a successful import result."""
        return cls(
            success=True,
            team=team,
            file_path=file_path,
            processed_players=len(team.get_all_players()),
            warnings=warnings or []
        )

    @classmethod
    def failure_result(cls, errors: List[str], file_path: str, warnings: Optional[List[str]] = None) -> 'ImportResult':
        """Create a failed import result."""
        return cls(
            success=False,
            errors=errors,
            file_path=file_path,
            warnings=warnings or []
        )


@dataclass
class SaveResult:
    """
    Represents the result of a save operation.
    
    Attributes:
        success: Whether the save was successful
        saved_id: ID of the saved entity
        file_path: Path where the entity was saved
        errors: List of error messages
        warnings: List of warning messages
        timestamp: When the save was performed
    """
    success: bool
    saved_id: Optional[str] = None
    file_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "saved_id": self.saved_id,
            "file_path": self.file_path,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success_result(cls, saved_id: str, file_path: str, warnings: Optional[List[str]] = None) -> 'SaveResult':
        """Create a successful save result."""
        return cls(
            success=True,
            saved_id=saved_id,
            file_path=file_path,
            warnings=warnings or []
        )

    @classmethod
    def failure_result(cls, errors: List[str], warnings: Optional[List[str]] = None) -> 'SaveResult':
        """Create a failed save result."""
        return cls(
            success=False,
            errors=errors,
            warnings=warnings or []
        )


@dataclass
class CreateResult:
    """
    Represents the result of a create operation.
    
    Attributes:
        success: Whether the creation was successful
        created_id: ID of the created entity
        errors: List of error messages
        warnings: List of warning messages
        validation_result: Associated validation result
        timestamp: When the creation was performed
    """
    success: bool
    created_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "created_id": self.created_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success_result(cls, created_id: str, validation_result: Optional[ValidationResult] = None, warnings: Optional[List[str]] = None, data: Optional[Dict[str, Any]] = None) -> 'CreateResult':
        """Create a successful create result."""
        return cls(
            success=True,
            created_id=created_id,
            validation_result=validation_result,
            warnings=warnings or [],
            data=data or {}
        )

    @classmethod
    def failure_result(cls, errors: List[str], validation_result: Optional[ValidationResult] = None, warnings: Optional[List[str]] = None) -> 'CreateResult':
        """Create a failed create result."""
        return cls(
            success=False,
            errors=errors,
            validation_result=validation_result,
            warnings=warnings or []
        )


@dataclass
class ErrorResponse:
    """
    Represents a structured error response.
    
    Attributes:
        error_type: Type of error (validation, import, business, system)
        message: Main error message
        details: Additional error details
        suggestions: List of suggested fixes
        field_errors: Field-specific errors
        timestamp: When the error occurred
        context: Additional context information
    """
    error_type: ErrorType
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    field_errors: Dict[str, List[str]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)

    def add_suggestion(self, suggestion: str):
        """Add a suggestion for fixing the error."""
        self.suggestions.append(suggestion)

    def add_field_error(self, field: str, error: str):
        """Add a field-specific error."""
        if field not in self.field_errors:
            self.field_errors[field] = []
        self.field_errors[field].append(error)

    def add_context(self, key: str, value: Any):
        """Add context information."""
        self.context[key] = value

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "field_errors": self.field_errors,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }

    @classmethod
    def validation_error(cls, message: str, field_errors: Optional[Dict[str, List[str]]] = None, suggestions: Optional[List[str]] = None) -> 'ErrorResponse':
        """Create a validation error response."""
        return cls(
            error_type=ErrorType.VALIDATION,
            message=message,
            field_errors=field_errors or {},
            suggestions=suggestions or []
        )

    @classmethod
    def import_error(cls, message: str, file_path: str, suggestions: Optional[List[str]] = None) -> 'ErrorResponse':
        """Create an import error response."""
        error = cls(
            error_type=ErrorType.IMPORT,
            message=message,
            suggestions=suggestions or []
        )
        error.add_context("file_path", file_path)
        return error

    @classmethod
    def business_error(cls, message: str, suggestions: Optional[List[str]] = None) -> 'ErrorResponse':
        """Create a business logic error response."""
        return cls(
            error_type=ErrorType.BUSINESS,
            message=message,
            suggestions=suggestions or []
        )

    @classmethod
    def system_error(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'ErrorResponse':
        """Create a system error response."""
        return cls(
            error_type=ErrorType.SYSTEM,
            message=message,
            details=details or {}
        )


# Position standardization mapping
POSITION_MAPPING = {
    # Goalkeeper variations
    "goalkeeper": "GK",
    "goal keeper": "GK",
    "keeper": "GK",
    "gk": "GK",
    "goalie": "GK",
    
    # Defender variations
    "defender": "DEF",
    "defence": "DEF",
    "defense": "DEF",
    "def": "DEF",
    "center back": "DEF",
    "centre back": "DEF",
    "central defender": "DEF",
    "full back": "DEF",
    "fullback": "DEF",
    "left back": "DEF",
    "right back": "DEF",
    "wing back": "DEF",
    "wingback": "DEF",
    "cb": "DEF",
    "lb": "DEF",
    "rb": "DEF",
    "wb": "DEF",
    
    # Midfielder variations
    "midfielder": "MID",
    "mid fielder": "MID",
    "midfield": "MID",
    "mid": "MID",
    "central midfielder": "MID",
    "defensive midfielder": "MID",
    "attacking midfielder": "MID",
    "left midfielder": "MID",
    "right midfielder": "MID",
    "wing midfielder": "MID",
    "cm": "MID",
    "dm": "MID",
    "cdm": "MID",
    "cam": "MID",
    "am": "MID",
    "lm": "MID",
    "rm": "MID",
    
    # Forward variations
    "forward": "FWD",
    "striker": "FWD",
    "attacker": "FWD",
    "winger": "FWD",
    "left winger": "FWD",
    "right winger": "FWD",
    "center forward": "FWD",
    "centre forward": "FWD",
    "left forward": "FWD",
    "right forward": "FWD",
    "cf": "FWD",
    "lw": "FWD",
    "rw": "FWD",
    "lf": "FWD",
    "rf": "FWD",
    "st": "FWD"
}


def standardize_position(position: str) -> str:
    """
    Standardize a position string to one of: GK, DEF, MID, FWD.
    
    Args:
        position: Raw position string
        
    Returns:
        Standardized position string
        
    Raises:
        ValueError: If position cannot be standardized
    """
    if not position:
        raise ValueError("Position cannot be empty")
    
    # Clean the position string
    clean_position = position.strip().lower()
    
    # Check direct mapping
    if clean_position in POSITION_MAPPING:
        return POSITION_MAPPING[clean_position]
    
    # Check if it's already standardized
    if clean_position.upper() in ["GK", "DEF", "MID", "FWD"]:
        return clean_position.upper()
    
    # If no match found, raise error
    raise ValueError(f"Unknown position: {position}. Must be one of: GK, DEF, MID, FWD or a recognized variation.")


# Enum for common constants
class MatchConstants:
    """Constants for match validation."""
    MIN_PLAYERS_PER_TEAM = 11
    MAX_PLAYERS_PER_TEAM = 23
    MIN_JERSEY_NUMBER = 1
    MAX_JERSEY_NUMBER = 99
    FIFA_MAX_SUBSTITUTIONS = 5
    FIFA_MAX_SUBSTITUTION_WINDOWS = 3
    STANDARD_HALF_DURATION = 45
    MAX_HALF_DURATION = 60
    MAX_HALF_TIME_DURATION = 30
