"""
Football Score Pro 2.0 - Main Application Entry Point
Service Container with Dependency Injection and Event-Driven Architecture
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.interfaces import (
    IValidationService, ITeamService, ITournamentService,
    IMatchService, IEventBus, IOfficialsService, IFixtureService,
    ISideAssignmentService, ITeamSelectionService, IFormationLayoutService
)
from src.services.validation_service import ValidationService
from src.services.team_service import TeamService
from src.services.tournament_service import TournamentService
from src.services.match_service import MatchService
from src.services.officials_service import OfficialsService
from src.services.fixture_service import FixtureService
from src.services.side_assignment_service import SideAssignmentService
from src.services.team_selection_service import TeamSelectionService
from src.services.formation_layout_service import FormationLayoutService
from src.events.event_bus import EventBus
from src.models.results import CreateResult, ValidationResult, SaveResult


class ServiceContainer:
    """
    Service Container for Dependency Injection
    Manages service lifecycle and dependencies
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
        
    def initialize(self):
        """Initialize all services with proper dependency injection"""
        if self._initialized:
            return
            
        print("Initializing Football Score Pro 2.0 Services...")
        
        # 1. Create Event Bus (no dependencies)
        event_bus = EventBus(enable_logging=True)
        self._services['event_bus'] = event_bus
        print("Event Bus initialized")
        
        # 2. Create Validation Service (no dependencies)
        validation_service = ValidationService()
        self._services['validation_service'] = validation_service
        print("Validation Service initialized")
        
        # 3. Create Team Service (depends on EventBus, ValidationService)
        team_service = TeamService(
            event_bus=event_bus,
            validation_service=validation_service
        )
        self._services['team_service'] = team_service
        print("Team Service initialized")
        
        # 4. Create Tournament Service (depends on ValidationService)
        tournament_service = TournamentService(
            validation_service=validation_service,
            data_dir="data/tournaments"
        )
        self._services['tournament_service'] = tournament_service
        print("Tournament Service initialized")
        
        # 5. Create Match Service (depends on EventBus, ValidationService)
        match_service = MatchService(
            event_bus=event_bus,
            validation_service=validation_service,
            data_dir="data/matches"
        )
        self._services['match_service'] = match_service
        print("Match Service initialized")
        
        # 6. Create Officials Service (depends on EventBus)
        officials_service = OfficialsService(
            event_bus=event_bus
        )
        self._services['officials_service'] = officials_service
        print("Officials Service initialized")
        
        # 7. Create Fixture Service (no dependencies)
        fixture_service = FixtureService()
        self._services['fixture_service'] = fixture_service
        print("Fixture Service initialized")

        # 8. Create Side Assignment Service (depends on EventBus)
        side_assignment_service = SideAssignmentService(event_bus)
        self._services['side_assignment_service'] = side_assignment_service
        print("Side Assignment Service initialized")

        # 9. Create Team Selection Service (depends on EventBus)
        team_selection_service = TeamSelectionService(event_bus)
        self._services['team_selection_service'] = team_selection_service
        print("Team Selection Service initialized")

        # 10. Create Formation Layout Service (depends on EventBus)
        formation_layout_service = FormationLayoutService(event_bus)
        self._services['formation_layout_service'] = formation_layout_service
        print("Formation Layout Service initialized")

        self._initialized = True
        print("All services initialized successfully!")
        
        # 8. Setup event subscriptions (after initialization is complete)
        self._setup_event_subscriptions()
        
    def _setup_event_subscriptions(self):
        """Setup event subscriptions for cross-service communication"""
        event_bus = self.get_service('event_bus')
        
        # Subscribe to team import events
        def on_team_imported(event):
            print(f"Team imported: {event.team_id} ({event.players_count} players)")
            
        def on_match_created(event):
            print(f"Match created: {event.match_id} - {event.get_match_title()}")
            
        def on_officials_assigned(event):
            print(f"Officials assigned to match: {event.match_id}")
            
        def on_match_configuration_updated(event):
            print(f"Match configuration updated: {event.match_id}")
        
        def on_officials_pool_loaded(event):
            print(f"Officials pool loaded: {event.total_officials} officials")

        def on_side_assignment_changed(event):
            print(f"Side assignment changed: home_uses_a={event.home_uses_a}")
            if event.effective_home_team:
                print(f"   Home team: {event.effective_home_team}")
            if event.effective_away_team:
                print(f"   Away team: {event.effective_away_team}")

        def on_team_selection_changed(event):
            print(f"Team selection changed: {event.team_id} side {event.side} - {event.selection_count}/11 players")

        def on_formation_position_changed(event):
            if event.position_changed:
                print(f"Formation position saved: {event.player_name} at ({event.x}, {event.y})")
            else:
                print(f"Formation position cleared: {event.player_name}")

        event_bus.subscribe("team_imported", on_team_imported)
        event_bus.subscribe("match_created", on_match_created)
        event_bus.subscribe("officials_assigned", on_officials_assigned)
        event_bus.subscribe("match_configuration_updated", on_match_configuration_updated)
        event_bus.subscribe("officials_pool_loaded", on_officials_pool_loaded)
        event_bus.subscribe("side_assignment_changed", on_side_assignment_changed)
        event_bus.subscribe("team_selection_changed", on_team_selection_changed)
        event_bus.subscribe("formation_position_changed", on_formation_position_changed)
        
        print("Event subscriptions configured")
    
    def get_service(self, service_name: str) -> Any:
        """Get service by name"""
        if not self._initialized:
            raise RuntimeError("Service container not initialized. Call initialize() first.")
        
        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found")
            
        return self._services[service_name]
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all services"""
        return self._services.copy()
    
    def shutdown(self):
        """Shutdown all services"""
        print("Shutting down services...")
        
        # Clear event bus subscribers
        event_bus = self._services.get('event_bus')
        if event_bus:
            event_bus.clear_subscribers()
            
        self._services.clear()
        self._initialized = False
        print("Services shutdown complete")


class FootballScoreProApp:
    """
    Main Application Class
    Coordinates between UI and backend services
    """
    
    def __init__(self):
        self.container = ServiceContainer()
        self.ui = None
        
    def initialize(self):
        """Initialize the application"""
        print("Starting Football Score Pro 2.0...")
        
        # Initialize service container
        self.container.initialize()
        
        # Create data directories
        self._create_data_directories()
        
        print("Application initialized successfully!")
        
    def _create_data_directories(self):
        """Create necessary data directories"""
        directories = [
            "data/teams",
            "data/tournaments", 
            "data/matches",
            "resources/images"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def get_team_service(self) -> ITeamService:
        """Get team service"""
        return self.container.get_service('team_service')
    
    def get_match_service(self) -> IMatchService:
        """Get match service"""
        return self.container.get_service('match_service')
    
    def get_tournament_service(self) -> ITournamentService:
        """Get tournament service"""
        return self.container.get_service('tournament_service')
    
    def get_validation_service(self) -> IValidationService:
        """Get validation service"""
        return self.container.get_service('validation_service')
    
    def get_event_bus(self) -> IEventBus:
        """Get event bus"""
        return self.container.get_service('event_bus')
    
    def get_officials_service(self) -> IOfficialsService:
        """Get officials service"""
        return self.container.get_service('officials_service')
    
    def get_fixture_service(self) -> IFixtureService:
        """Get fixture service"""
        return self.container.get_service('fixture_service')

    def get_side_assignment_service(self) -> ISideAssignmentService:
        """Get side assignment service"""
        return self.container.get_service('side_assignment_service')

    def get_team_selection_service(self) -> ITeamSelectionService:
        """Get team selection service"""
        return self.container.get_service('team_selection_service')

    def get_formation_layout_service(self) -> IFormationLayoutService:
        """Get formation layout service"""
        return self.container.get_service('formation_layout_service')
    
    def run_demo(self):
        """Run a demonstration of the backend services"""
        print("\n🎮 Running Football Score Pro 2.0 Demo...")
        
        # Demo 1: Create a tournament
        print("\n📋 Demo 1: Creating Tournament")
        tournament_service = self.get_tournament_service()
        
        tournament_data = {
            "name": "Premier League 2024",
            "season": "2024/25",
            "start_date": "2024-08-17",
            "end_date": "2025-05-25",
            "rules": {
                "first_half_duration": 45,
                "second_half_duration": 45,
                "max_substitutions": 5,
                "var_available": True
            }
        }
        
        tournament_result = tournament_service.create_tournament(tournament_data)
        if tournament_result.success:
            print(f"Tournament created: {tournament_result.created_id}")
        else:
            print(f"Tournament creation failed: {tournament_result.errors}")
        
        # Demo 2: Import team data
        print("\nDemo 2: Importing Team Data")
        team_service = self.get_team_service()
        
        # Create sample team data
        sample_team_data = {
            "id": "arsenal_2024",
            "full_name": "Arsenal Football Club",
            "short_name": "AFC",
            "manager": "Mikel Arteta",
            "head_coach": "Mikel Arteta",
            "players": [
                {
                    "id": "player_1",
                    "team_id": "arsenal_2024",
                    "full_name": "Aaron Ramsdale",
                    "short_name": "A. Ramsdale",
                    "jersey_number": 1,
                    "position": "GK"
                },
                {
                    "id": "player_2", 
                    "team_id": "arsenal_2024",
                    "full_name": "William Saliba",
                    "short_name": "W. Saliba",
                    "jersey_number": 2,
                    "position": "DEF"
                },
                {
                    "id": "player_3",
                    "team_id": "arsenal_2024", 
                    "full_name": "Gabriel Magalhães",
                    "short_name": "Gabriel",
                    "jersey_number": 6,
                    "position": "DEF"
                },
                {
                    "id": "player_4",
                    "team_id": "arsenal_2024",
                    "full_name": "Martin Ødegaard",
                    "short_name": "M. Ødegaard", 
                    "jersey_number": 8,
                    "position": "MID"
                },
                {
                    "id": "player_5",
                    "team_id": "arsenal_2024",
                    "full_name": "Bukayo Saka",
                    "short_name": "B. Saka",
                    "jersey_number": 7,
                    "position": "FWD"
                },
                {
                    "id": "player_6",
                    "team_id": "arsenal_2024",
                    "full_name": "Gabriel Jesus",
                    "short_name": "G. Jesus",
                    "jersey_number": 9,
                    "position": "FWD"
                },
                {
                    "id": "player_7",
                    "team_id": "arsenal_2024",
                    "full_name": "Thomas Partey",
                    "short_name": "T. Partey",
                    "jersey_number": 5,
                    "position": "MID"
                },
                {
                    "id": "player_8",
                    "team_id": "arsenal_2024",
                    "full_name": "Granit Xhaka",
                    "short_name": "G. Xhaka",
                    "jersey_number": 34,
                    "position": "MID"
                },
                {
                    "id": "player_9",
                    "team_id": "arsenal_2024",
                    "full_name": "Ben White",
                    "short_name": "B. White",
                    "jersey_number": 4,
                    "position": "DEF"
                },
                {
                    "id": "player_10",
                    "team_id": "arsenal_2024",
                    "full_name": "Oleksandr Zinchenko",
                    "short_name": "O. Zinchenko",
                    "jersey_number": 35,
                    "position": "DEF"
                },
                {
                    "id": "player_11",
                    "team_id": "arsenal_2024",
                    "full_name": "Gabriel Martinelli",
                    "short_name": "G. Martinelli",
                    "jersey_number": 11,
                    "position": "FWD"
                }
            ]
        }
        
        result = team_service.import_from_json_data(sample_team_data)
        if result.success:
            print(f"Team imported: {result.team.id if result.team else 'Unknown'}")
        else:
            print(f"Team import failed: {result.errors}")
        
        # Demo 3: Create a match
        print("\nDemo 3: Creating Match")
        match_service = self.get_match_service()
        
        # Get the imported team
        arsenal_team = team_service.get_team_by_id("arsenal_2024")
        if arsenal_team:
            # Create a simple match with the same team (for demo purposes)
            match_data = {
                "home_team": arsenal_team,
                "away_team": arsenal_team,  # Same team for demo
                "venue": "Emirates Stadium",
                "match_date": "2024-08-17",
                "match_time": "15:00",
                "tournament_id": tournament_result.created_id if tournament_result.success else None
            }
            
            result = match_service.create_match(match_data)
            if result.success:
                print(f"Match created: {result.created_id}")
                
                # Demo 4: Assign officials
                print("\nDemo 4: Assigning Officials")
                officials = {
                    "referee": "Michael Oliver",
                    "assistant_referee_1": "Stuart Burt",
                    "assistant_referee_2": "Simon Bennett",
                    "fourth_official": "David Coote",
                    "var_referee": "Paul Tierney"
                }
                
                result = match_service.assign_officials(result.created_id, officials)
                if result.success:
                    print("Officials assigned successfully")
                else:
                    print(f"Officials assignment failed: {result.errors}")
                    
            else:
                print(f"Match creation failed: {result.errors}")
        else:
            print("Could not find imported team")
        
        # Demo 5: Show service statistics
        print("\nDemo 5: Service Statistics")
        event_bus = self.get_event_bus()
        stats = event_bus.get_stats()
        print(f"Event Bus Stats: {stats}")
        
        print("\nDemo completed successfully!")
        print("\nNext steps:")
        print("   - Run the UI to see the Match Setup interface")
        print("   - Import real team data from JSON files")
        print("   - Create matches with different teams")
        print("   - Configure match rules and officials")
    
    def run_ui(self):
        """Run the UI application"""
        try:
            # Import UI components
            from ui.backend_service import BackendService
            from ui.main_window import run_ui
            
            print("Initializing UI components...")
            
            # Create BackendService wrapper
            backend_service = BackendService(
                team_service=self.get_team_service(),
                match_service=self.get_match_service(),
                tournament_service=self.get_tournament_service(),
                validation_service=self.get_validation_service(),
                event_bus=self.get_event_bus(),
                officials_service=self.get_officials_service(),
                fixture_service=self.get_fixture_service(),
                side_assignment_service=self.get_side_assignment_service(),
                team_selection_service=self.get_team_selection_service(),
                formation_layout_service=self.get_formation_layout_service()
            )
            
            print("Backend service wrapper created")
            print("Launching UI application...")
            
            # Run the UI
            run_ui(backend_service)
            
        except ImportError as e:
            print(f" UI import error: {e}")
            print(" Make sure PySide6 is installed: pip install PySide6")
        except Exception as e:
            print(f" UI error: {e}")
            import traceback
            traceback.print_exc()
    
    def shutdown(self):
        """Shutdown the application"""
        print(" Shutting down Football Score Pro 2.0...")
        self.container.shutdown()
        print(" Application shutdown complete")


def main():
    """Main entry point"""
    try:
        # Create and initialize application
        app = FootballScoreProApp()
        app.initialize()
        
        # Determine mode (UI by default)
        mode = "ui"
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg in {"--demo", "demo"}:
                mode = "demo"
            elif arg in {"--ui", "ui"}:
                mode = "ui"
        
        if mode == "ui":
            print("Launching UI...")
            app.run_ui()
        else:
            print("Running backend demo...")
            app.run_demo()
        
        # Shutdown
        app.shutdown()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"\nApplication error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
