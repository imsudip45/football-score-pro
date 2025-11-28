"""Match Service with Configuration Validation and Officials Management"""
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from ..models.match import Match, MatchOfficials, MatchStatus
from ..models.match_config import MatchConfiguration
from ..models.team import Team
from ..models.tournament import Tournament
from ..models.results import CreateResult, ValidationResult, SaveResult, MatchConstants, ImportResult
from .interfaces import IMatchService


class MatchService(IMatchService):
    """
    Service for managing matches with configuration validation and officials management.
    """

    def __init__(self, event_bus=None, validation_service=None, data_dir: str = "data/matches"):
        """
        Initialize MatchService.
        
        Args:
            event_bus: Event bus for publishing events (optional)
            validation_service: Validation service for match validation (optional)
            data_dir: Directory for storing match data files
        """
        self.event_bus = event_bus
        self.validation_service = validation_service
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._matches: Dict[str, Match] = {}
        self._load_matches()

    def create_match(self, match_data: Dict[str, Any]) -> CreateResult:
        """
        Create a new match with comprehensive validation.
        
        Args:
            match_data: Dictionary containing match information
            
        Returns:
            CreateResult with success/failure status and details
        """
        try:
            # Generate match ID if not provided
            match_id = match_data.get('id') or str(uuid.uuid4())
            
            # Validate required fields
            validation_errors = self._validate_match_data(match_data)
            if validation_errors:
                return CreateResult.failure_result(errors=validation_errors)
            
            # Extract teams
            home_team = match_data['home_team']
            away_team = match_data['away_team']
            
            # Validate team differences
            team_validation = self.validate_team_differences(home_team, away_team)
            if not team_validation.is_valid:
                return CreateResult.failure_result(
                    errors=[f"Team validation failed: {', '.join(team_validation.errors)}"],
                    validation_result=team_validation
                )
            
            # Create or validate match configuration
            if 'configuration' in match_data:
                configuration = self._create_match_configuration(match_data['configuration'])
            else:
                configuration = MatchConfiguration()  # Use defaults
            
            # Validate configuration
            config_validation = self.validate_configuration(configuration)
            if not config_validation.is_valid:
                return CreateResult.failure_result(
                    errors=[f"Configuration validation failed: {', '.join(config_validation.errors)}"],
                    validation_result=config_validation
                )
            
            # Parse match date and time
            match_date = self._parse_datetime(match_data.get('match_date', datetime.utcnow()))
            match_time = match_data.get('match_time', "15:00")
            
            # Generate match name and number
            match_name = match_data.get('match_name', f"{home_team.short_name} vs {away_team.short_name}")
            match_number = match_data.get('match_number', 1)
            
            # Create default officials (empty)
            officials = MatchOfficials(referee="TBD")
            
            # Create match object
            match = Match(
                id=match_id,
                tournament_id=match_data.get('tournament_id'),
                match_name=match_name,
                match_number=match_number,
                match_date=match_date,
                match_time=match_time,
                venue=match_data.get('venue', 'TBD'),
                home_team=home_team,
                away_team=away_team,
                configuration=configuration,
                officials=officials,
                status=MatchStatus.SETUP,
                notes=match_data.get('notes')
            )
            
            # Store match
            self._matches[match.id] = match
            
            # Persist to file
            save_result = self._save_match_to_file(match)
            if not save_result.success:
                return CreateResult.failure_result(
                    errors=[f"Failed to save match: {', '.join(save_result.errors)}"]
                )
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import MatchCreatedEvent
                event = MatchCreatedEvent(
                    match_id=match.id,
                    match_data=match,
                    home_team_summary=self._get_team_summary(home_team),
                    away_team_summary=self._get_team_summary(away_team)
                )
                self.event_bus.publish("match_created", event)
            
            warnings = []
            warnings.extend(team_validation.warnings)
            warnings.extend(config_validation.warnings)
            
            return CreateResult.success_result(
                created_id=match.id,
                warnings=warnings
            )
            
        except Exception as e:
            return CreateResult.failure_result(
                errors=[f"Unexpected error creating match: {str(e)}"]
            )

    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get match by ID."""
        return self._matches.get(match_id)

    def validate_configuration(self, config: MatchConfiguration) -> ValidationResult:
        """Validate match configuration."""
        if self.validation_service:
            return self.validation_service.validate_match_configuration(config)
        else:
            return ValidationResult.success()

    def validate_team_differences(self, home_team: Team, away_team: Team) -> ValidationResult:
        """Validate that teams are different and eligible."""
        result = ValidationResult(is_valid=True)
        
        # Check if teams are different
        if home_team.id == away_team.id:
            result.add_error("Home team and away team must be different")
        
        # Check if teams have same name (even with different IDs)
        if home_team.full_name.lower() == away_team.full_name.lower():
            result.add_error(f"Teams cannot have the same name: {home_team.full_name}")
        
        # Validate individual team compositions
        if self.validation_service:
            home_validation = self.validation_service.validate_team_composition(home_team)
            away_validation = self.validation_service.validate_team_composition(away_team)
            
            if not home_validation.is_valid:
                result.errors.extend([f"Home team: {error}" for error in home_validation.errors])
                result.is_valid = False
            
            if not away_validation.is_valid:
                result.errors.extend([f"Away team: {error}" for error in away_validation.errors])
                result.is_valid = False
            
            result.warnings.extend([f"Home team: {warning}" for warning in home_validation.warnings])
            result.warnings.extend([f"Away team: {warning}" for warning in away_validation.warnings])
        
        return result

    def validate_complete_setup(self, match_id: str) -> ValidationResult:
        """Validate complete match setup."""
        match = self.get_match_by_id(match_id)
        if not match:
            return ValidationResult.failure([f"Match not found: {match_id}"])
        
        result = ValidationResult(is_valid=True)
        
        # Validate teams
        team_validation = self.validate_team_differences(match.home_team, match.away_team)
        if not team_validation.is_valid:
            result.errors.extend(team_validation.errors)
            result.is_valid = False
        result.warnings.extend(team_validation.warnings)
        
        # Validate configuration
        config_validation = self.validate_configuration(match.configuration)
        if not config_validation.is_valid:
            result.errors.extend(config_validation.errors)
            result.is_valid = False
        result.warnings.extend(config_validation.warnings)
        
        # Validate officials
        if self.validation_service:
            officials_data = match.officials.to_dict()
            officials_validation = self.validation_service.validate_officials_assignment(officials_data)
            if not officials_validation.is_valid:
                result.errors.extend(officials_validation.errors)
                result.is_valid = False
            result.warnings.extend(officials_validation.warnings)
        
        # Check if match is ready to start
        if not match.is_ready_to_start():
            missing_requirements = []
            
            if not match.home_team.has_goalkeeper():
                missing_requirements.append("Home team needs a goalkeeper")
            
            if not match.away_team.has_goalkeeper():
                missing_requirements.append("Away team needs a goalkeeper")
            
            if match.home_team.has_duplicate_jersey_numbers():
                missing_requirements.append("Home team has duplicate jersey numbers")
            
            if match.away_team.has_duplicate_jersey_numbers():
                missing_requirements.append("Away team has duplicate jersey numbers")
            
            if not match.officials.referee or match.officials.referee == "TBD":
                missing_requirements.append("Match needs a referee assigned")
            
            if missing_requirements:
                result.add_warning(f"Match not ready to start: {', '.join(missing_requirements)}")
        
        return result

    def assign_officials(self, match_id: str, officials: Dict[str, str]) -> SaveResult:
        """Assign officials to match."""
        try:
            match = self.get_match_by_id(match_id)
            if not match:
                return SaveResult.failure_result([f"Match not found: {match_id}"])
            
            # Validate officials assignment
            if self.validation_service:
                validation_result = self.validation_service.validate_officials_assignment(officials)
                if not validation_result.is_valid:
                    return SaveResult.failure_result(validation_result.errors)
            
            # Create new officials object
            new_officials = MatchOfficials(
                referee=officials.get('referee', 'TBD'),
                assistant_referee_1=officials.get('assistant_referee_1'),
                assistant_referee_2=officials.get('assistant_referee_2'),
                fourth_official=officials.get('fourth_official'),
                var_referee=officials.get('var_referee'),
                avar_referee=officials.get('assistant_var')
            )
            
            # Update match
            match.officials = new_officials
            
            # Persist changes
            save_result = self._save_match_to_file(match)
            if not save_result.success:
                return save_result
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import OfficialsAssignedEvent
                event = OfficialsAssignedEvent(
                    match_id=match.id,
                    officials=new_officials,
                    is_complete_team=new_officials.has_complete_officiating_team()
                )
                self.event_bus.publish("officials_assigned", event)
            
            return SaveResult.success_result(
                saved_id=match.id,
                file_path=str(self.data_dir / f"{match.id}.json"),
                warnings=validation_result.warnings if self.validation_service else []
            )
            
        except Exception as e:
            return SaveResult.failure_result([f"Failed to assign officials: {str(e)}"])

    def update_configuration(self, match_id: str, config_updates: Dict[str, Any]) -> SaveResult:
        """Update match configuration."""
        try:
            match = self.get_match_by_id(match_id)
            if not match:
                return SaveResult.failure_result([f"Match not found: {match_id}"])
            
            # Update configuration
            config_dict = match.configuration.to_dict()
            config_dict.update(config_updates)
            
            # Create new configuration
            new_config = MatchConfiguration.from_dict(config_dict)
            
            # Validate new configuration
            validation_result = self.validate_configuration(new_config)
            if not validation_result.is_valid:
                return SaveResult.failure_result(validation_result.errors)
            
            # Update match
            match.configuration = new_config
            
            # Persist changes
            save_result = self._save_match_to_file(match)
            if not save_result.success:
                return save_result
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import MatchConfigurationUpdatedEvent
                event = MatchConfigurationUpdatedEvent(
                    match_id=match.id,
                    configuration=new_config,
                    changes=config_updates
                )
                self.event_bus.publish("match_configuration_updated", event)
            
            return SaveResult.success_result(
                saved_id=match.id,
                file_path=str(self.data_dir / f"{match.id}.json"),
                warnings=validation_result.warnings
            )
            
        except Exception as e:
            return SaveResult.failure_result([f"Failed to update configuration: {str(e)}"])

    def save_match(self, match_id: str, file_path: str) -> SaveResult:
        """Save match to file."""
        match = self.get_match_by_id(match_id)
        if not match:
            return SaveResult.failure_result([f"Match not found: {match_id}"])
        
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(match.to_dict(), file, indent=2, ensure_ascii=False)
            
            return SaveResult.success_result(
                saved_id=match.id,
                file_path=file_path
            )
            
        except Exception as e:
            return SaveResult.failure_result([f"Failed to save match: {str(e)}"])

    def load_match(self, file_path: str) -> ImportResult:
        """Load match from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                match_data = json.load(file)
            
            match = Match.from_dict(match_data)
            self._matches[match.id] = match
            
            return ImportResult(
                success=True,
                file_path=file_path
            )
            
        except Exception as e:
            return ImportResult(
                success=False,
                errors=[f"Failed to load match: {str(e)}"],
                file_path=file_path
            )

    def get_saved_matches(self, directory: str) -> List[Dict[str, Any]]:
        """Get list of saved matches with metadata."""
        matches = []
        dir_path = Path(directory)
        
        # Optimization: Use in-memory matches if querying the main data directory
        # and matches are already loaded
        if dir_path.resolve() == self.data_dir.resolve() and self._matches:
            for match in self._matches.values():
                matches.append({
                    "id": match.id,
                    "name": match.match_name,
                    "home_team": match.home_team.short_name if match.home_team else "Unknown",
                    "away_team": match.away_team.short_name if match.away_team else "Unknown",
                    "date": match.match_date.isoformat() if isinstance(match.match_date, datetime) else match.match_date,
                    "venue": match.venue,
                    "status": match.status.value if hasattr(match.status, 'value') else str(match.status),
                    "file_path": str(self.data_dir / f"{match.id}.json")
                })
            return matches

        if not dir_path.exists():
            return matches
        
        for file_path in dir_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    match_data = json.load(file)
                
                matches.append({
                    "id": match_data.get("id"),
                    "name": match_data.get("match_name"),
                    "home_team": match_data.get("home_team", {}).get("short_name", "Unknown"),
                    "away_team": match_data.get("away_team", {}).get("short_name", "Unknown"),
                    "date": match_data.get("match_date"),
                    "venue": match_data.get("venue"),
                    "status": match_data.get("status", "setup"),
                    "file_path": str(file_path)
                })
                
            except Exception as e:
                print(f"Failed to read match file {file_path}: {str(e)}")
        
        return matches

    # ----------------- Runtime state persistence -----------------
    def update_runtime_state(self, match_id: str, runtime_state: Dict[str, Any]) -> SaveResult:
        """Persist runtime state (scores, events, stats, possession) into match JSON under 'runtime'."""
        try:
            file_path = self.data_dir / f"{match_id}.json"
            if not file_path.exists():
                match = self.get_match_by_id(match_id)
                if not match:
                    return SaveResult.failure_result([f"Match not found: {match_id}"])
                # Create a base file if missing
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(match.to_dict(), f, indent=2, ensure_ascii=False)

            # Load current JSON, update runtime, write back
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['runtime'] = runtime_state or {}

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return SaveResult.success_result(saved_id=match_id, file_path=str(file_path))
        except Exception as e:
            return SaveResult.failure_result([f"Failed to update runtime state: {str(e)}"])

    def get_runtime_state(self, match_id: str) -> Dict[str, Any]:
        """Read runtime state from match JSON. Returns empty dict if missing."""
        try:
            file_path = self.data_dir / f"{match_id}.json"
            if not file_path.exists():
                return {}
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('runtime', {}) or {}
        except Exception:
            return {}

    def delete_match(self, match_id: str) -> SaveResult:
        """Delete match and cleanup."""
        try:
            if match_id not in self._matches:
                return SaveResult.failure_result([f"Match not found: {match_id}"])
            
            # Remove from memory
            match = self._matches.pop(match_id)
            
            # Remove file
            file_path = self.data_dir / f"{match_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import MatchDeletedEvent
                event = MatchDeletedEvent(
                    match_id=match_id,
                    match_name=match.match_name
                )
                self.event_bus.publish("match_deleted", event)
            
            return SaveResult.success_result(
                saved_id=match_id,
                file_path=str(file_path)
            )
            
        except Exception as e:
            return SaveResult.failure_result([f"Failed to delete match: {str(e)}"])

    def _validate_match_data(self, match_data: Dict[str, Any]) -> List[str]:
        """Validate basic match data structure."""
        errors = []
        
        # Check required fields
        required_fields = ['home_team', 'away_team']
        for field in required_fields:
            if field not in match_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate team objects
        if 'home_team' in match_data:
            if not isinstance(match_data['home_team'], Team):
                errors.append("home_team must be a Team object")
        
        if 'away_team' in match_data:
            if not isinstance(match_data['away_team'], Team):
                errors.append("away_team must be a Team object")
        
        return errors

    def _parse_datetime(self, date_input) -> datetime:
        """Parse datetime from various input formats."""
        if isinstance(date_input, datetime):
            return date_input
        
        if isinstance(date_input, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_input, fmt)
                except ValueError:
                    continue
        
        # Default to current datetime
        return datetime.utcnow()

    def _create_match_configuration(self, config_data: Dict[str, Any]) -> MatchConfiguration:
        """Create match configuration from data."""
        if isinstance(config_data, MatchConfiguration):
            return config_data
        
        return MatchConfiguration.from_dict(config_data)

    def _get_team_summary(self, team: Team) -> Dict[str, Any]:
        """Get team summary for events."""
        return {
            "id": team.id,
            "name": team.full_name,
            "short_name": team.short_name,
            "player_count": len(team.get_all_players())
        }

    def _save_match_to_file(self, match: Match) -> SaveResult:
        """Save match to JSON file."""
        try:
            file_path = self.data_dir / f"{match.id}.json"
            match_data = match.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(match_data, file, indent=2, ensure_ascii=False)
            
            return SaveResult.success_result(
                saved_id=match.id,
                file_path=str(file_path)
            )
            
        except Exception as e:
            return SaveResult.failure_result([f"Failed to save match to file: {str(e)}"])

    def _load_matches(self):
        """Load matches from data directory."""
        if not self.data_dir.exists():
            return
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    match_data = json.load(file)
                
                match = Match.from_dict(match_data)
                self._matches[match.id] = match
                
            except Exception as e:
                print(f"Failed to load match from {file_path}: {str(e)}")

    def get_all_matches(self) -> List[Match]:
        """Get all matches."""
        return list(self._matches.values())

    def get_matches_by_tournament(self, tournament_id: str) -> List[Match]:
        """Get all matches for a specific tournament."""
        return [match for match in self._matches.values() if match.tournament_id == tournament_id]

    def get_matches_by_team(self, team_id: str) -> List[Match]:
        """Get all matches involving a specific team."""
        return [match for match in self._matches.values() if match.involves_team(team_id)]
