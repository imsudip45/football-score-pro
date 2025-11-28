"""
Fixture Service for Football Score Pro 2.0
Handles fixture bundle loading and data extraction
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from .interfaces import IFixtureService
from ..models.results import ImportResult


class FixtureService(IFixtureService):
    """
    Service for managing fixture data loading and parsing
    Centralizes fixture data processing
    """
    
    def __init__(self):
        """Initialize Fixture Service"""
        pass
    
    def load_fixture_bundle(self, source: str) -> ImportResult:
        """
        Load fixture bundle from file or API URL
        
        Args:
            source: File path or API URL
            
        Returns:
            ImportResult with parsed fixture data
        """
        try:
            # Determine if source is URL or file path
            if source.startswith(('http://', 'https://')):
                return self._load_from_api(source)
            else:
                return self._load_from_file(source)
                
        except Exception as e:
            error_msg = f"Failed to load fixture bundle: {str(e)}"
            print(f"❌ {error_msg}")
            return ImportResult(
                success=False,
                errors=[error_msg],
                file_path=source
            )
    
    def _load_from_file(self, file_path: str) -> ImportResult:
        """Load fixture from JSON file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ImportResult(
                    success=False,
                    errors=[f"File not found: {file_path}"],
                    file_path=file_path
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Parse the data
            parsed_data = self.parse_fixture_data(raw_data)
            
            print(f"✅ Fixture loaded from file: {file_path}")
            return ImportResult(
                success=True,
                data=parsed_data,
                file_path=file_path
            )
            
        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                errors=[f"Invalid JSON format: {str(e)}"],
                file_path=file_path
            )
        except Exception as e:
            return ImportResult(
                success=False,
                errors=[f"Error loading file: {str(e)}"],
                file_path=file_path
            )
    
    def _load_from_api(self, url: str) -> ImportResult:
        """Load fixture from API URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            raw_data = response.json()
            
            # Parse the data
            parsed_data = self.parse_fixture_data(raw_data)
            
            print(f"✅ Fixture loaded from API: {url}")
            return ImportResult(
                success=True,
                data=parsed_data,
                file_path=url
            )
            
        except requests.RequestException as e:
            return ImportResult(
                success=False,
                errors=[f"API request failed: {str(e)}"],
                file_path=url
            )
        except Exception as e:
            return ImportResult(
                success=False,
                errors=[f"Error loading from API: {str(e)}"],
                file_path=url
            )
    
    def parse_fixture_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize fixture data
        
        Handles different fixture data structures:
        - Single fixture
        - Fixture bundle with multiple fixtures
        - Comprehensive fixture with officials pools
        
        Args:
            raw_data: Raw fixture data
            
        Returns:
            Normalized fixture data with metadata
        """
        parsed = {
            'is_bundle': False,
            'fixtures': [],
            'officials_pool': None,
            'commentators_pool': None,
            'hosts_pool': None,
            'tournament': None,
            'raw_data': raw_data  # Keep raw data for backward compatibility
        }
        
        # Extract tournament data if present
        if 'tournament' in raw_data:
            parsed['tournament'] = raw_data['tournament']
        
        # Extract officials pools if present
        officials_pool = self.extract_officials_pool(raw_data)
        if officials_pool:
            parsed['officials_pool'] = officials_pool.get('available_officials')
            parsed['commentators_pool'] = officials_pool.get('available_commentators')
            parsed['hosts_pool'] = officials_pool.get('available_hosts')
        
        # Determine structure and extract fixtures
        if 'fixtures' in raw_data and isinstance(raw_data['fixtures'], list):
            # Multiple fixtures in a bundle
            parsed['is_bundle'] = True
            parsed['fixtures'] = raw_data['fixtures']
            print(f"📦 Fixture bundle detected: {len(parsed['fixtures'])} fixtures")
            
        elif isinstance(raw_data, list):
            # List of fixtures
            parsed['is_bundle'] = True
            parsed['fixtures'] = raw_data
            print(f"📦 Fixture list detected: {len(parsed['fixtures'])} fixtures")
            
        else:
            # Single fixture
            parsed['is_bundle'] = False
            parsed['fixtures'] = [raw_data]
            print(f"📄 Single fixture detected")
        
        return parsed
    
    def extract_officials_pool(self, fixture_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract officials pool from fixture data
        
        Args:
            fixture_data: Raw fixture data
            
        Returns:
            Dictionary with officials pools or None
        """
        pool_data = {}
        
        # Check for available_officials (comprehensive fixture format)
        if 'available_officials' in fixture_data:
            pool_data['available_officials'] = fixture_data['available_officials']
        
        # Check for available_commentators
        if 'available_commentators' in fixture_data:
            pool_data['available_commentators'] = fixture_data['available_commentators']
        
        # Check for available_hosts
        if 'available_hosts' in fixture_data:
            pool_data['available_hosts'] = fixture_data['available_hosts']
        
        # Also check for 'officials' key (old format)
        if 'officials' in fixture_data:
            pool_data['officials'] = fixture_data['officials']
        
        return pool_data if pool_data else None
    
    def extract_teams(self, fixture_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract team data from fixture
        
        Handles different team data structures:
        - 'teams' array (comprehensive format)
        - 'home_team' and 'away_team' (legacy format)
        - 'participants' array
        
        Args:
            fixture_data: Fixture data
            
        Returns:
            List of team data dictionaries
        """
        teams = []
        
        # Handle new comprehensive format with teams array
        if 'teams' in fixture_data and isinstance(fixture_data['teams'], list):
            teams = fixture_data['teams']
            
        # Handle legacy format with separate home/away team objects
        elif 'home_team' in fixture_data and 'away_team' in fixture_data:
            teams = [fixture_data['home_team'], fixture_data['away_team']]
            
        # Handle participants array
        elif 'participants' in fixture_data:
            teams = fixture_data['participants']
            
        # Try to find team-like objects in the data
        else:
            for key, value in fixture_data.items():
                if isinstance(value, list) and len(value) >= 2:
                    # Check if the list contains team-like objects
                    first_item = value[0] if value else {}
                    if isinstance(first_item, dict) and ('name' in first_item or 'team_name' in first_item):
                        teams = value[:2]  # Take first two items as teams
                        break
        
        return teams
    
    def get_fixture_summary(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary information about a fixture
        
        Args:
            fixture_data: Fixture data
            
        Returns:
            Dictionary with summary information
        """
        summary = {
            'fixture_id': fixture_data.get('fixture_id', fixture_data.get('id', 'unknown')),
            'match_number': fixture_data.get('match_number', ''),
            'date': fixture_data.get('date', ''),
            'time': fixture_data.get('time', ''),
            'venue': fixture_data.get('venue', ''),
            'round': fixture_data.get('round', ''),
            'status': fixture_data.get('status', 'scheduled')
        }
        
        # Extract team names
        teams = self.extract_teams(fixture_data)
        if len(teams) >= 2:
            summary['home_team'] = teams[0].get('name', teams[0].get('team_name', 'Unknown'))
            summary['away_team'] = teams[1].get('name', teams[1].get('team_name', 'Unknown'))
        
        return summary

