"""Tournament Service with CRUD Operations"""
import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from ..models.tournament import Tournament
from ..models.match_config import MatchConfiguration
from ..models.results import CreateResult, SaveResult, ValidationResult
from .interfaces import ITournamentService


class TournamentService(ITournamentService):
    """
    Service for managing tournaments with CRUD operations, validation, and persistence.
    """

    def __init__(self, event_bus=None, validation_service=None, data_dir: str = "data/tournaments"):
        """
        Initialize TournamentService.
        
        Args:
            event_bus: Event bus for publishing events (optional)
            validation_service: Validation service for tournament validation (optional)
            data_dir: Directory for storing tournament data files
        """
        self.event_bus = event_bus
        self.validation_service = validation_service
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._tournaments: Dict[str, Tournament] = {}
        self._load_tournaments()

    def get_tournaments(self) -> List[Tournament]:
        """
        Get all tournaments.
        
        Returns:
            List of all tournaments
        """
        return list(self._tournaments.values())

    def create_tournament(self, tournament_data: Dict[str, Any]) -> CreateResult:
        """
        Create a new tournament with validation.
        
        Args:
            tournament_data: Dictionary containing tournament information
            
        Returns:
            CreateResult with success/failure status and details
        """
        try:
            # Generate tournament ID if not provided
            tournament_id = tournament_data.get('id') or str(uuid.uuid4())
            
            # Validate required fields
            validation_errors = self._validate_tournament_data(tournament_data)
            if validation_errors:
                return CreateResult.failure_result(
                    errors=validation_errors
                )
            
            # Parse dates
            start_date = self._parse_date(tournament_data['start_date'])
            end_date = self._parse_date(tournament_data['end_date'])
            
            # Create match configuration
            rules_data = tournament_data.get('rules', {})
            rules = self._create_match_configuration(rules_data)
            
            # Create tournament object
            tournament = Tournament(
                id=tournament_id,
                name=tournament_data['name'],
                season=tournament_data['season'],
                start_date=start_date,
                end_date=end_date,
                rules=rules,
                description=tournament_data.get('description'),
                organizer=tournament_data.get('organizer'),
                venue=tournament_data.get('venue')
            )
            
            # Validate tournament
            if self.validation_service:
                validation_result = self.validation_service.validate_tournament_rules(tournament)
                if not validation_result.is_valid:
                    return CreateResult.failure_result(
                        errors=[f"Tournament validation failed: {', '.join(validation_result.errors)}"],
                        validation_result=validation_result
                    )
            
            # Store tournament
            self._tournaments[tournament.id] = tournament
            
            # Persist to file
            save_result = self._save_tournament_to_file(tournament)
            if not save_result.success:
                return CreateResult.failure_result(
                    errors=[f"Failed to save tournament: {', '.join(save_result.errors)}"]
                )
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import TournamentCreatedEvent
                event = TournamentCreatedEvent(
                    tournament_id=tournament.id,
                    tournament_data=tournament
                )
                self.event_bus.publish("tournament_created", event)
            
            return CreateResult.success_result(
                created_id=tournament.id,
                warnings=validation_result.warnings if self.validation_service else []
            )
            
        except Exception as e:
            return CreateResult.failure_result(
                errors=[f"Unexpected error creating tournament: {str(e)}"]
            )

    def get_tournament_by_id(self, tournament_id: str) -> Optional[Tournament]:
        """
        Get tournament by ID.
        
        Args:
            tournament_id: ID of the tournament
            
        Returns:
            Tournament object or None if not found
        """
        return self._tournaments.get(tournament_id)

    def get_tournament_rules(self, tournament_id: str) -> Optional[MatchConfiguration]:
        """
        Get tournament-specific match configuration.
        
        Args:
            tournament_id: ID of the tournament
            
        Returns:
            MatchConfiguration or None if tournament not found
        """
        tournament = self.get_tournament_by_id(tournament_id)
        return tournament.rules if tournament else None

    def get_configuration_presets(self) -> Dict[str, MatchConfiguration]:
        """
        Get predefined match configuration presets.
        
        Returns:
            Dictionary of preset configurations
        """
        return MatchConfiguration.get_preset_configurations()

    def export_tournaments(self, file_path: str) -> bool:
        """
        Export tournaments to file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            tournaments_data = [tournament.to_dict() for tournament in self._tournaments.values()]
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(tournaments_data, file, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Failed to export tournaments: {str(e)}")
            return False

    def _validate_tournament_data(self, tournament_data: Dict[str, Any]) -> List[str]:
        """Validate basic tournament data structure."""
        errors = []
        
        # Check required fields
        required_fields = ['name', 'season', 'start_date', 'end_date']
        for field in required_fields:
            if field not in tournament_data:
                errors.append(f"Missing required field: {field}")
            elif not tournament_data[field]:
                errors.append(f"Field '{field}' cannot be empty")
        
        # Validate dates if present
        if 'start_date' in tournament_data and 'end_date' in tournament_data:
            try:
                start_date = self._parse_date(tournament_data['start_date'])
                end_date = self._parse_date(tournament_data['end_date'])
                
                if start_date >= end_date:
                    errors.append("Start date must be before end date")
                    
            except ValueError as e:
                errors.append(f"Invalid date format: {str(e)}")
        
        return errors

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        if isinstance(date_str, datetime):
            return date_str
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_str}")

    def _create_match_configuration(self, rules_data: Dict[str, Any]) -> MatchConfiguration:
        """Create match configuration from rules data."""
        # Use preset if specified
        if 'preset' in rules_data:
            preset_name = rules_data['preset']
            presets = MatchConfiguration.get_preset_configurations()
            if preset_name in presets:
                config = presets[preset_name]
                # Override with any custom values
                for key, value in rules_data.items():
                    if key != 'preset' and hasattr(config, key):
                        setattr(config, key, value)
                return config
        
        # Create from individual settings
        return MatchConfiguration(
            first_half_duration=rules_data.get('first_half_duration', 45),
            second_half_duration=rules_data.get('second_half_duration', 45),
            half_time_duration=rules_data.get('half_time_duration', 15),
            points_for_win=rules_data.get('points_for_win', 3),
            points_for_draw=rules_data.get('points_for_draw', 1),
            points_for_loss=rules_data.get('points_for_loss', 0),
            draw_allowed=rules_data.get('draw_allowed', True),
            extra_time_required=rules_data.get('extra_time_required', False),
            penalty_shootout=rules_data.get('penalty_shootout', False),
            max_substitutions=rules_data.get('max_substitutions', 5),
            substitution_windows=rules_data.get('substitution_windows', 3),
            var_available=rules_data.get('var_available', True),
            goal_line_technology=rules_data.get('goal_line_technology', True),
            match_type=rules_data.get('match_type', 'League')
        )

    def _save_tournament_to_file(self, tournament: Tournament) -> SaveResult:
        """Save tournament to JSON file."""
        try:
            file_path = self.data_dir / f"{tournament.id}.json"
            tournament_data = tournament.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(tournament_data, file, indent=2, ensure_ascii=False)
            
            return SaveResult.success_result(
                saved_id=tournament.id,
                file_path=str(file_path)
            )
            
        except Exception as e:
            return SaveResult.failure_result(
                errors=[f"Failed to save tournament to file: {str(e)}"]
            )

    def _load_tournaments(self):
        """Load tournaments from data directory."""
        if not self.data_dir.exists():
            return
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    tournament_data = json.load(file)
                
                tournament = Tournament.from_dict(tournament_data)
                self._tournaments[tournament.id] = tournament
                
            except Exception as e:
                print(f"Failed to load tournament from {file_path}: {str(e)}")

    def delete_tournament(self, tournament_id: str) -> SaveResult:
        """Delete tournament and its file."""
        try:
            if tournament_id not in self._tournaments:
                return SaveResult.failure_result(
                    errors=[f"Tournament not found: {tournament_id}"]
                )
            
            # Remove from memory
            tournament = self._tournaments.pop(tournament_id)
            
            # Remove file
            file_path = self.data_dir / f"{tournament_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import TournamentDeletedEvent
                event = TournamentDeletedEvent(
                    tournament_id=tournament_id,
                    tournament_name=tournament.name
                )
                self.event_bus.publish("tournament_deleted", event)
            
            return SaveResult.success_result(
                saved_id=tournament_id,
                file_path=str(file_path)
            )
            
        except Exception as e:
            return SaveResult.failure_result(
                errors=[f"Failed to delete tournament: {str(e)}"]
            )

    def update_tournament(self, tournament_id: str, updates: Dict[str, Any]) -> CreateResult:
        """Update an existing tournament."""
        tournament = self.get_tournament_by_id(tournament_id)
        if not tournament:
            return CreateResult.failure_result(
                errors=[f"Tournament not found: {tournament_id}"]
            )
        
        # Create updated tournament data
        tournament_data = tournament.to_dict()
        tournament_data.update(updates)
        tournament_data['id'] = tournament_id  # Ensure ID doesn't change
        
        # Delete old tournament
        self.delete_tournament(tournament_id)
        
        # Create updated tournament
        return self.create_tournament(tournament_data)

    def get_active_tournaments(self) -> List[Tournament]:
        """Get currently active tournaments."""
        return [t for t in self._tournaments.values() if t.is_active()]

    def get_upcoming_tournaments(self) -> List[Tournament]:
        """Get upcoming tournaments."""
        return [t for t in self._tournaments.values() if t.is_upcoming()]

    def get_finished_tournaments(self) -> List[Tournament]:
        """Get finished tournaments."""
        return [t for t in self._tournaments.values() if t.is_finished()]
