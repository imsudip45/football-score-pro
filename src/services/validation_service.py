"""Validation Service with Comprehensive Business Rules"""
from typing import List, Dict, Set, Optional
from ..models.team import Team
from ..models.player import Player
from ..models.match_config import MatchConfiguration
from ..models.match import MatchOfficials
from ..models.tournament import Tournament
from ..models.results import ValidationResult, standardize_position
from ..constants import ValidationConstants
from .interfaces import IValidationService


class ValidationService(IValidationService):
    """
    Service for validating teams, matches, configurations, and tournaments
    according to FIFA and business rules.
    """

    def validate_team_composition(self, team: Team) -> ValidationResult:
        """
        Validate team composition according to FIFA rules.
        
        Args:
            team: Team to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult(is_valid=True)
        
        # Get all players (main squad + substitutes)
        all_players = team.get_all_players()
        
        # Check minimum and maximum players
        if len(all_players) < ValidationConstants.MIN_PLAYERS_PER_TEAM:
            result.add_error(
                f"Team must have at least {ValidationConstants.MIN_PLAYERS_PER_TEAM} players. "
                f"Currently has {len(all_players)} players.",
                "players"
            )
        
        if len(all_players) > ValidationConstants.MAX_PLAYERS_PER_TEAM:
            result.add_error(
                f"Team cannot have more than {ValidationConstants.MAX_PLAYERS_PER_TEAM} players. "
                f"Currently has {len(all_players)} players.",
                "players"
            )
        
        # Check for at least one goalkeeper
        goalkeepers = [p for p in all_players if p.position == "GK"]
        if len(goalkeepers) < ValidationConstants.MIN_GOALKEEPERS:
            result.add_error("Team must have at least one goalkeeper.", "goalkeeper")
        elif len(goalkeepers) > ValidationConstants.MAX_GOALKEEPERS_WARN:
            result.add_warning(f"Team has {len(goalkeepers)} goalkeepers. Consider having 2-3 goalkeepers.")
        
        # Validate jersey number uniqueness
        jersey_numbers = [p.jersey_number for p in all_players if p.jersey_number is not None]
        duplicate_numbers = self._find_duplicates(jersey_numbers)
        
        if duplicate_numbers:
            for number in duplicate_numbers:
                players_with_number = [p.full_name for p in all_players if p.jersey_number == number]
                result.add_error(
                    f"Jersey number {number} is assigned to multiple players: {', '.join(players_with_number)}",
                    "jersey_numbers"
                )
        
        # Validate jersey number ranges
        for player in all_players:
            if player.jersey_number is not None:
                if (player.jersey_number < ValidationConstants.MIN_JERSEY_NUMBER or 
                    player.jersey_number > ValidationConstants.MAX_JERSEY_NUMBER):
                    result.add_error(
                        f"Player {player.full_name} has invalid jersey number {player.jersey_number}. "
                        f"Must be between {ValidationConstants.MIN_JERSEY_NUMBER} and {ValidationConstants.MAX_JERSEY_NUMBER}.",
                        "jersey_numbers"
                    )
        
        # Validate player positions
        position_counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
        for player in all_players:
            try:
                standardized_pos = standardize_position(player.position)
                position_counts[standardized_pos] += 1
            except ValueError as e:
                result.add_error(f"Player {player.full_name}: {str(e)}", "positions")
        
        # Check position distribution (recommendations)
        if position_counts["DEF"] < ValidationConstants.MIN_DEFENDERS_WARN:
            result.add_warning(f"Consider having at least {ValidationConstants.MIN_DEFENDERS_WARN} defenders in the squad.")
        if position_counts["MID"] < ValidationConstants.MIN_MIDFIELDERS_WARN:
            result.add_warning(f"Consider having at least {ValidationConstants.MIN_MIDFIELDERS_WARN} midfielders in the squad.")
        if position_counts["FWD"] < ValidationConstants.MIN_FORWARDS_WARN:
            result.add_warning(f"Consider having at least {ValidationConstants.MIN_FORWARDS_WARN} forward in the squad.")
        
        # Validate starting XI if specified
        starting_players = [p for p in team.players if len(team.players) >= ValidationConstants.MIN_PLAYERS_PER_TEAM]
        if len(team.players) == ValidationConstants.MIN_PLAYERS_PER_TEAM:
            starting_gk = [p for p in team.players if p.position == "GK"]
            if len(starting_gk) != ValidationConstants.STARTING_GK_COUNT:
                result.add_error("Starting XI must have exactly one goalkeeper.", "starting_xi")
        
        return result

    def validate_match_configuration(self, config: MatchConfiguration) -> ValidationResult:
        """
        Validate match configuration against FIFA rules.
        
        Args:
            config: Match configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Validate half durations
        if config.first_half_duration < ValidationConstants.MIN_HALF_DURATION or config.first_half_duration > ValidationConstants.MAX_HALF_DURATION:
            result.add_error(
                f"First half duration must be between {ValidationConstants.MIN_HALF_DURATION} and {ValidationConstants.MAX_HALF_DURATION} minutes. "
                f"Current: {config.first_half_duration}",
                "first_half_duration"
            )
        
        if config.second_half_duration < ValidationConstants.MIN_HALF_DURATION or config.second_half_duration > ValidationConstants.MAX_HALF_DURATION:
            result.add_error(
                f"Second half duration must be between {ValidationConstants.MIN_HALF_DURATION} and {ValidationConstants.MAX_HALF_DURATION} minutes. "
                f"Current: {config.second_half_duration}",
                "second_half_duration"
            )
        
        # Validate half time duration
        if config.half_time_duration < ValidationConstants.MIN_HALF_TIME or config.half_time_duration > ValidationConstants.MAX_HALF_TIME:
            result.add_error(
                f"Half time duration must be between {ValidationConstants.MIN_HALF_TIME} and {ValidationConstants.MAX_HALF_TIME} minutes. "
                f"Current: {config.half_time_duration}",
                "half_time_duration"
            )
        
        # Validate substitutions
        if config.max_substitutions < 0 or config.max_substitutions > ValidationConstants.MAX_SUBSTITUTIONS:
            result.add_error(
                f"Max substitutions must be between 0 and {ValidationConstants.MAX_SUBSTITUTIONS}. Current: {config.max_substitutions}",
                "max_substitutions"
            )
        
        if config.substitution_windows < 0 or config.substitution_windows > ValidationConstants.MAX_SUB_WINDOWS:
            result.add_error(
                f"Substitution windows must be between 0 and {ValidationConstants.MAX_SUB_WINDOWS}. Current: {config.substitution_windows}",
                "substitution_windows"
            )
        
        # FIFA compliance warnings
        if not config.is_fifa_compliant():
            if config.first_half_duration != ValidationConstants.STANDARD_HALF_DURATION:
                result.add_warning(f"Non-FIFA standard first half duration: {config.first_half_duration} minutes (FIFA: {ValidationConstants.STANDARD_HALF_DURATION})")
            
            if config.second_half_duration != ValidationConstants.STANDARD_HALF_DURATION:
                result.add_warning(f"Non-FIFA standard second half duration: {config.second_half_duration} minutes (FIFA: {ValidationConstants.STANDARD_HALF_DURATION})")
            
            if config.max_substitutions > ValidationConstants.FIFA_MAX_SUBSTITUTIONS:
                result.add_warning(f"More substitutions than FIFA allows: {config.max_substitutions} (FIFA: {ValidationConstants.FIFA_MAX_SUBSTITUTIONS})")
            
            if config.substitution_windows > ValidationConstants.FIFA_MAX_SUBSTITUTION_WINDOWS:
                result.add_warning(f"More substitution windows than FIFA allows: {config.substitution_windows} (FIFA: {ValidationConstants.FIFA_MAX_SUBSTITUTION_WINDOWS})")
        
        # Validate points system
        if config.points_for_win < 0:
            result.add_error("Points for win cannot be negative", "points_for_win")
        
        if config.points_for_draw < 0:
            result.add_error("Points for draw cannot be negative", "points_for_draw")
        
        if config.points_for_loss < 0:
            result.add_error("Points for loss cannot be negative", "points_for_loss")
        
        # Logical validation
        if config.points_for_win <= config.points_for_draw:
            result.add_warning("Points for win should be greater than points for draw")
        
        if config.points_for_draw < config.points_for_loss:
            result.add_warning("Points for draw should be greater than or equal to points for loss")
        
        return result

    def validate_officials_assignment(self, officials: Dict[str, str]) -> ValidationResult:
        """
        Validate referee and assistant assignments.
        
        Args:
            officials: Dictionary with official assignments
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Check required officials
        required_officials = ["referee"]
        for official_type in required_officials:
            if not officials.get(official_type):
                result.add_error(f"{official_type.replace('_', ' ').title()} is required", official_type)
        
        # Check for duplicate assignments
        official_names = [name.strip().lower() for name in officials.values() if name and name.strip()]
        duplicate_names = self._find_duplicates(official_names)
        
        if duplicate_names:
            for name in duplicate_names:
                positions = [role for role, assigned_name in officials.items() 
                           if assigned_name and assigned_name.strip().lower() == name]
                result.add_error(
                    f"'{name}' is assigned to multiple positions: {', '.join(positions)}",
                    "duplicate_assignments"
                )
        
        # Recommendations for complete officiating team
        recommended_officials = ["assistant_referee_1", "assistant_referee_2", "fourth_official"]
        missing_recommended = [off for off in recommended_officials if not officials.get(off)]
        
        if missing_recommended:
            result.add_warning(
                f"Consider assigning: {', '.join([off.replace('_', ' ').title() for off in missing_recommended])}"
            )
        
        # VAR validation
        if officials.get("var_referee") and not officials.get("assistant_var"):
            result.add_warning("VAR Referee assigned but no Assistant VAR. Consider assigning both.")
        
        if officials.get("assistant_var") and not officials.get("var_referee"):
            result.add_warning("Assistant VAR assigned but no VAR Referee. Consider assigning both.")
        
        return result

    def validate_tournament_rules(self, tournament: Tournament) -> ValidationResult:
        """
        Validate tournament-specific rules and configuration.
        
        Args:
            tournament: Tournament to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Validate basic tournament data
        if not tournament.name.strip():
            result.add_error("Tournament name cannot be empty", "name")
        
        if not tournament.season.strip():
            result.add_error("Tournament season cannot be empty", "season")
        
        # Validate dates
        if tournament.start_date >= tournament.end_date:
            result.add_error("Tournament start date must be before end date", "dates")
        
        # Validate tournament duration
        duration_days = tournament.get_duration_days()
        if duration_days < 1:
            result.add_error("Tournament duration must be at least 1 day", "dates")
        elif duration_days > 365:
            result.add_warning("Tournament duration is more than 1 year. Please verify this is correct.")
        
        # Validate tournament rules (match configuration)
        config_validation = self.validate_match_configuration(tournament.rules)
        if not config_validation.is_valid:
            result.errors.extend([f"Tournament rules: {error}" for error in config_validation.errors])
            result.is_valid = False
        
        result.warnings.extend([f"Tournament rules: {warning}" for warning in config_validation.warnings])
        
        # Tournament-specific validations based on match type
        if tournament.rules.match_type.lower() == "cup":
            if tournament.rules.draw_allowed and not tournament.rules.extra_time_required:
                result.add_warning("Cup tournaments typically don't allow draws or require extra time")
        
        elif tournament.rules.match_type.lower() == "league":
            if not tournament.rules.draw_allowed:
                result.add_warning("League tournaments typically allow draws")
        
        return result

    def _find_duplicates(self, items: List) -> Set:
        """Find duplicate items in a list."""
        seen = set()
        duplicates = set()
        for item in items:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        return duplicates

    def _validate_name_format(self, name: str, field_name: str) -> List[str]:
        """Validate name format and return list of errors."""
        errors = []
        
        if not name or not name.strip():
            errors.append(f"{field_name} cannot be empty")
        elif len(name.strip()) < 2:
            errors.append(f"{field_name} must be at least 2 characters long")
        elif len(name.strip()) > 100:
            errors.append(f"{field_name} cannot be longer than 100 characters")
        
        return errors

    def validate_team_eligibility(self, team: Team, tournament_rules: MatchConfiguration) -> ValidationResult:
        """
        Validate if team is eligible for a specific tournament.
        
        Args:
            team: Team to validate
            tournament_rules: Tournament-specific rules
            
        Returns:
            ValidationResult with eligibility details
        """
        result = ValidationResult(is_valid=True)
        
        # First validate basic team composition
        team_validation = self.validate_team_composition(team)
        if not team_validation.is_valid:
            result.errors.extend(team_validation.errors)
            result.is_valid = False
        
        result.warnings.extend(team_validation.warnings)
        
        # Tournament-specific validations
        all_players = team.get_all_players()
        
        # Check if team has enough players for substitutions
        max_subs = tournament_rules.max_substitutions
        if len(team.substitutes) < max_subs:
            result.add_warning(
                f"Team has {len(team.substitutes)} substitutes but tournament allows {max_subs} substitutions. "
                "Consider having more substitute players."
            )
        
        # Friendly match specific rules
        if tournament_rules.match_type.lower() == "friendly":
            if len(all_players) < ValidationConstants.MIN_PLAYERS_PER_TEAM:
                # More lenient for friendly matches
                result.add_warning(
                    f"Friendly match: Team has only {len(all_players)} players. "
                    "This is allowed for friendly matches but not recommended."
                )
        
        return result
