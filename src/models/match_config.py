"""Match Configuration Data Model"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchConfiguration:
    """
    Represents match configuration and rules.
    
    Attributes:
        first_half_duration: Duration of first half in minutes
        second_half_duration: Duration of second half in minutes
        half_time_duration: Duration of half time break in minutes
        points_for_win: Points awarded for a win
        points_for_draw: Points awarded for a draw
        points_for_loss: Points awarded for a loss
        draw_allowed: Whether draws are allowed in this match type
        extra_time_required: Whether extra time is required if match is drawn
        penalty_shootout: Whether penalty shootout follows extra time
        max_substitutions: Maximum number of substitutions allowed
        substitution_windows: Number of substitution windows allowed
        var_available: Whether VAR (Video Assistant Referee) is available
        goal_line_technology: Whether Goal Line Technology is available
        match_type: Type of match (League, Cup, Friendly, etc.)
    """
    first_half_duration: int = 45
    second_half_duration: int = 45
    half_time_duration: int = 15
    points_for_win: int = 3
    points_for_draw: int = 1
    points_for_loss: int = 0
    draw_allowed: bool = True
    extra_time_required: bool = False
    penalty_shootout: bool = False
    max_substitutions: int = 5
    substitution_windows: int = 3
    var_available: bool = True
    goal_line_technology: bool = True
    match_type: str = "League"

    def __post_init__(self):
        """Validate match configuration after initialization."""
        if self.first_half_duration <= 0 or self.first_half_duration > 60:
            raise ValueError("First half duration must be between 1 and 60 minutes")
        if self.second_half_duration <= 0 or self.second_half_duration > 60:
            raise ValueError("Second half duration must be between 1 and 60 minutes")
        if self.half_time_duration < 0 or self.half_time_duration > 30:
            raise ValueError("Half time duration must be between 0 and 30 minutes")
        if self.points_for_win < 0:
            raise ValueError("Points for win cannot be negative")
        if self.points_for_draw < 0:
            raise ValueError("Points for draw cannot be negative")
        if self.points_for_loss < 0:
            raise ValueError("Points for loss cannot be negative")
        if self.max_substitutions < 0 or self.max_substitutions > 11:
            raise ValueError("Max substitutions must be between 0 and 11")
        if self.substitution_windows < 0 or self.substitution_windows > 5:
            raise ValueError("Substitution windows must be between 0 and 5")

    def get_total_match_duration(self) -> int:
        """Get total match duration excluding extra time."""
        return self.first_half_duration + self.second_half_duration

    def is_fifa_compliant(self) -> bool:
        """Check if configuration follows FIFA regulations."""
        # FIFA standard: 45+45 minutes, max 5 substitutions, max 3 windows
        return (
            self.first_half_duration == 45 and
            self.second_half_duration == 45 and
            self.max_substitutions <= 5 and
            self.substitution_windows <= 3
        )

    def requires_decisive_result(self) -> bool:
        """Check if match requires a decisive result (no draws)."""
        return not self.draw_allowed or self.extra_time_required

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return {
            "first_half_duration": self.first_half_duration,
            "second_half_duration": self.second_half_duration,
            "half_time_duration": self.half_time_duration,
            "points_for_win": self.points_for_win,
            "points_for_draw": self.points_for_draw,
            "points_for_loss": self.points_for_loss,
            "draw_allowed": self.draw_allowed,
            "extra_time_required": self.extra_time_required,
            "penalty_shootout": self.penalty_shootout,
            "max_substitutions": self.max_substitutions,
            "substitution_windows": self.substitution_windows,
            "var_available": self.var_available,
            "goal_line_technology": self.goal_line_technology,
            "match_type": self.match_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MatchConfiguration':
        """Create configuration from dictionary."""
        return cls(
            first_half_duration=data.get("first_half_duration", 45),
            second_half_duration=data.get("second_half_duration", 45),
            half_time_duration=data.get("half_time_duration", 15),
            points_for_win=data.get("points_for_win", 3),
            points_for_draw=data.get("points_for_draw", 1),
            points_for_loss=data.get("points_for_loss", 0),
            draw_allowed=data.get("draw_allowed", True),
            extra_time_required=data.get("extra_time_required", False),
            penalty_shootout=data.get("penalty_shootout", False),
            max_substitutions=data.get("max_substitutions", 5),
            substitution_windows=data.get("substitution_windows", 3),
            var_available=data.get("var_available", True),
            goal_line_technology=data.get("goal_line_technology", True),
            match_type=data.get("match_type", "League")
        )

    @classmethod
    def get_preset_configurations(cls) -> dict:
        """Get common preset configurations for different match types."""
        return {
            "League": cls(
                match_type="League",
                draw_allowed=True,
                extra_time_required=False,
                penalty_shootout=False
            ),
            "Cup": cls(
                match_type="Cup",
                draw_allowed=False,
                extra_time_required=True,
                penalty_shootout=True
            ),
            "Friendly": cls(
                match_type="Friendly",
                points_for_win=0,
                points_for_draw=0,
                points_for_loss=0,
                max_substitutions=11,
                substitution_windows=5
            ),
            "Champions League": cls(
                match_type="Champions League",
                draw_allowed=True,
                var_available=True,
                goal_line_technology=True
            )
        }
