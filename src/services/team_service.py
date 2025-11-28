"""Team Service with JSON Import and Validation"""
import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from ..models.team import Team
from ..models.player import Player
from ..models.results import ImportResult, ValidationResult, standardize_position, POSITION_MAPPING
from .interfaces import ITeamService


class TeamService(ITeamService):
    """
    Service for managing teams with JSON import, validation, and CRUD operations.
    """

    def __init__(self, event_bus=None, validation_service=None):
        """
        Initialize TeamService.
        
        Args:
            event_bus: Event bus for publishing events (optional)
            validation_service: Validation service for team validation (optional)
        """
        self.event_bus = event_bus
        self.validation_service = validation_service
        self._teams: Dict[str, Team] = {}
        self._summary_cache: Dict[str, Dict[str, Any]] = {}

    def import_from_json_data(self, team_data: Dict[str, Any]) -> ImportResult:
        """
        Import team data from dictionary with comprehensive error handling.
        
        Args:
            team_data: Dictionary containing team data
            
        Returns:
            ImportResult: Result of the import operation
        """
        try:
            # Validate JSON structure
            structure_errors = self._validate_json_structure(team_data)
            if structure_errors:
                return ImportResult(
                    success=False,
                    errors=structure_errors,
                    warnings=[]
                )
            
            # Generate team ID if not provided
            team_id = team_data.get('id', str(uuid.uuid4()))
            
            # Process players
            players_data = team_data.get('players', [])
            players, warnings = self._process_players(players_data, team_id)
            
            # Create team object
            team = Team(
                id=team_id,
                full_name=team_data['full_name'],
                short_name=team_data['short_name'],
                manager=team_data.get('manager', ''),
                head_coach=team_data.get('head_coach', ''),
                season=team_data.get('season', ''),
                players=players
            )
            
            # Validate team composition
            if self.validation_service:
                validation_result = self.validation_service.validate_team_composition(team)
                if not validation_result.is_valid:
                    return ImportResult(
                        success=False,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                warnings.extend(validation_result.warnings)
            
            # Store team
            self._teams[team_id] = team
            
            # Invalidate cache
            if team_id in self._summary_cache:
                del self._summary_cache[team_id]
            
            # Publish event
            if self.event_bus:
                from ..events.match_events import TeamImportedEvent
                event = TeamImportedEvent(
                    team_id=team_id,
                    team_data=team,
                    players_count=len(players),
                    warnings=warnings
                )
                self.event_bus.publish("team_imported", event)
            
            return ImportResult(
                success=True,
                team=team,
                errors=[],
                warnings=warnings,
                processed_players=len(players)
            )
            
        except Exception as e:
            return ImportResult(
                success=False,
                errors=[f"Unexpected error during import: {str(e)}"],
                warnings=[]
            )

    def import_from_json(self, file_path: str) -> ImportResult:
        """
        Import team data from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            ImportResult: Result of the import operation
        """
        try:
            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                return ImportResult(
                    success=False,
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    file_path=file_path
                )
            
            # Read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as file:
                team_data = json.load(file)
            
            # Import using dictionary method
            result = self.import_from_json_data(team_data)
            result.file_path = file_path
            
            return result
            
        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                errors=[f"Invalid JSON format: {str(e)}"],
                warnings=[],
                file_path=file_path
            )
        except Exception as e:
            return ImportResult(
                success=False,
                errors=[f"Error reading file: {str(e)}"],
                warnings=[],
                file_path=file_path
            )

    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        return self._teams.get(team_id)

    def get_all_teams(self) -> List[Team]:
        """Get all imported teams."""
        return list(self._teams.values())

    def get_team_summary(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team summary for UI display."""
        # Check cache first
        if team_id in self._summary_cache:
            return self._summary_cache[team_id]

        team = self.get_team_by_id(team_id)
        if not team:
            return None
        
        all_players = team.get_all_players()
        goalkeepers = team.get_goalkeepers()
        
        summary = {
            "id": team.id,
            "full_name": team.full_name,
            "short_name": team.short_name,
            "manager": team.manager,
            "head_coach": team.head_coach,
            "season": team.season,
            "total_players": len(all_players),
            "main_squad": len(team.players),
            "substitutes": len(team.substitutes),
            "goalkeepers": len(goalkeepers),
            "position_counts": self._get_position_counts(all_players),
            "has_goalkeeper": team.has_goalkeeper(),
            "has_duplicate_jerseys": team.has_duplicate_jersey_numbers(),
            "created_date": team.created_date.isoformat()
        }
        
        # Store in cache
        self._summary_cache[team_id] = summary
        return summary

    def validate_team_composition(self, team_id: str) -> ValidationResult:
        """Validate team composition by ID."""
        team = self.get_team_by_id(team_id)
        if not team:
            return ValidationResult.failure([f"Team not found: {team_id}"])
        
        if self.validation_service:
            return self.validation_service.validate_team_composition(team)
        else:
            return ValidationResult.success()

    def _validate_json_structure(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate basic JSON structure and required fields."""
        errors = []
        
        # Check required fields
        required_fields = ['full_name', 'short_name']
        for field in required_fields:
            if field not in team_data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(team_data[field], str) or not team_data[field].strip():
                errors.append(f"Field '{field}' cannot be empty")
        
        # Validate short name length
        if 'short_name' in team_data and len(team_data['short_name']) > 4:
            errors.append("Short name cannot be longer than 4 characters")
        
        # Validate players array if present
        if 'players' in team_data:
            if not isinstance(team_data['players'], list):
                errors.append("Players must be an array")
            else:
                # Validate each player
                for i, player_data in enumerate(team_data['players']):
                    player_errors = self._validate_player_data(player_data, i)
                    errors.extend(player_errors)
        
        return errors

    def _validate_player_data(self, player_data: Dict[str, Any], index: int) -> List[str]:
        """Validate individual player data."""
        errors = []
        player_ref = f"Player {index + 1}"
        
        # Check required fields
        required_fields = ['full_name', 'jersey_number', 'position']
        for field in required_fields:
            if field not in player_data:
                errors.append(f"{player_ref}: Missing required field '{field}'")
            elif field == 'full_name' and (not isinstance(player_data[field], str) or not player_data[field].strip()):
                errors.append(f"{player_ref}: Full name cannot be empty")
            elif field == 'jersey_number' and not isinstance(player_data[field], int):
                errors.append(f"{player_ref}: Jersey number must be an integer")
            elif field == 'position' and (not isinstance(player_data[field], str) or not player_data[field].strip()):
                errors.append(f"{player_ref}: Position cannot be empty")
        
        # Validate jersey number range
        if 'jersey_number' in player_data and isinstance(player_data['jersey_number'], int):
            if player_data['jersey_number'] < 1 or player_data['jersey_number'] > 99:
                errors.append(f"{player_ref}: Jersey number must be between 1 and 99")
        
        # Validate position
        if 'position' in player_data and isinstance(player_data['position'], str):
            try:
                standardize_position(player_data['position'])
            except ValueError as e:
                errors.append(f"{player_ref}: {str(e)}")
        
        return errors

    def _process_players(self, players_data: List[Dict[str, Any]], team_id: str) -> tuple[List[Player], List[str]]:
        """Process players data and return list of Player objects and warnings."""
        players = []
        warnings = []
        
        for i, player_data in enumerate(players_data):
            try:
                # Generate player ID if not provided
                player_id = player_data.get('id', str(uuid.uuid4()))
                
                # Standardize position
                try:
                    position = standardize_position(player_data['position'])
                except ValueError:
                    position = player_data['position']  # Keep original if can't standardize
                    warnings.append(f"Player {player_data.get('full_name', f'#{i+1}')}: Unknown position '{player_data['position']}'")
                
                # Create player
                player = Player(
                    id=player_id,
                    team_id=team_id,
                    full_name=player_data['full_name'],
                    short_name=player_data.get('short_name', player_data['full_name']),
                    jersey_number=player_data['jersey_number'],
                    position=position,
                    nationality=player_data.get('nationality'),
                    photo_url=player_data.get('photo_url'),
                    video_url=player_data.get('video_url')
                )
                
                players.append(player)
                
            except Exception as e:
                warnings.append(f"Player {i + 1}: Error processing - {str(e)}")
        
        return players, warnings

    def _get_position_counts(self, players: List[Player]) -> Dict[str, int]:
        """Get count of players by position."""
        counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
        
        for player in players:
            try:
                standardized_pos = standardize_position(player.position)
                counts[standardized_pos] += 1
            except ValueError:
                # If position can't be standardized, skip counting
                pass
        
        return counts

    def clear_teams(self):
        """Clear all imported teams (useful for testing)."""
        self._teams.clear()
        self._summary_cache.clear()

    def remove_team(self, team_id: str) -> bool:
        """Remove a team by ID."""
        if team_id in self._teams:
            del self._teams[team_id]
            if team_id in self._summary_cache:
                del self._summary_cache[team_id]
            return True
        return False

    def update_team(self, team_id: str, team_data: Dict[str, Any]) -> ImportResult:
        """Update an existing team with new data."""
        if team_id not in self._teams:
            return ImportResult(
                success=False,
                errors=[f"Team not found: {team_id}"],
                warnings=[]
            )
        
        # Merge team_data with existing team ID
        team_data['id'] = team_id
        
        # Import updated data
        result = self.import_from_json_data(team_data)
        
        return result
