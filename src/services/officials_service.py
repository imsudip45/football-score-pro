"""
Officials Service for Football Score Pro 2.0
Handles officials pool management and normalization
"""

import uuid
from typing import Dict, Any, List, Optional
from .interfaces import IOfficialsService, IEventBus
from ..models.official import Official, OfficialsPool, OfficialType
from ..models.results import CreateResult
from ..events.officials_events import OfficialsPoolLoadedEvent, OfficialsPoolClearedEvent


class OfficialsService(IOfficialsService):
    """
    Service for managing officials pools
    Centralizes officials data loading and normalization
    """
    
    def __init__(self, event_bus: IEventBus):
        """
        Initialize Officials Service
        
        Args:
            event_bus: Event bus for publishing events
        """
        self.event_bus = event_bus
        self._pools: Dict[Optional[str], OfficialsPool] = {}  # tournament_id -> OfficialsPool
    
    def load_officials_pool(self, pool_data: Dict[str, Any], tournament_id: Optional[str] = None) -> CreateResult:
        """
        Load officials pool from data
        
        Args:
            pool_data: Raw officials data (can be strings or dicts)
            tournament_id: Optional tournament ID
            
        Returns:
            CreateResult with success status
        """
        try:
            pool = OfficialsPool(tournament_id=tournament_id)
            
            # Load referees
            if 'referees' in pool_data:
                pool.referees = self.normalize_officials_data(
                    pool_data['referees'], 
                    OfficialType.REFEREE
                )
            
            
            # Load linesmen
            if 'linesmen' in pool_data:
                pool.linesmen = self.normalize_officials_data(
                    pool_data['linesmen'], 
                    OfficialType.LINESMAN
                )
            
            # Load fourth officials
            if 'fourth_officials' in pool_data:
                pool.fourth_officials = self.normalize_officials_data(
                    pool_data['fourth_officials'], 
                    OfficialType.FOURTH_OFFICIAL
                )
            
            # Load VAR referees
            if 'var_referees' in pool_data:
                pool.var_referees = self.normalize_officials_data(
                    pool_data['var_referees'], 
                    OfficialType.VAR_REFEREE
                )
            
            # Load commentators (handle both 'commentators' and 'available_commentators')
            commentators_key = 'commentators' if 'commentators' in pool_data else 'available_commentators'
            if commentators_key in pool_data:
                pool.commentators = self.normalize_officials_data(
                    pool_data[commentators_key], 
                    OfficialType.COMMENTATOR
                )
            
            # Load hosts (handle both 'hosts' and 'available_hosts')
            hosts_key = 'hosts' if 'hosts' in pool_data else 'available_hosts'
            if hosts_key in pool_data:
                pool.hosts = self.normalize_officials_data(
                    pool_data[hosts_key], 
                    OfficialType.HOST
                )
            
            # Store the pool
            self._pools[tournament_id] = pool
            
            # Publish event
            total_officials = len(pool.get_all())
            event = OfficialsPoolLoadedEvent(
                tournament_id=tournament_id,
                pool=pool,
                total_officials=total_officials
            )
            self.event_bus.publish("officials_pool_loaded", event)
            
            print(f"✅ Officials pool loaded: {total_officials} officials")
            print(f"   - Referees: {len(pool.referees)}")
            print(f"   - Linesmen: {len(pool.linesmen)}")
            print(f"   - Fourth Officials: {len(pool.fourth_officials)}")
            print(f"   - VAR Referees: {len(pool.var_referees)}")
            print(f"   - Commentators: {len(pool.commentators)}")
            print(f"   - Hosts: {len(pool.hosts)}")
            
            return CreateResult.success_result(
                created_id=tournament_id or "default",
                data={"total_officials": total_officials}
            )
            
        except Exception as e:
            error_msg = f"Failed to load officials pool: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return CreateResult.failure_result([error_msg])
    
    def get_officials_pool(self, tournament_id: Optional[str] = None) -> Optional[OfficialsPool]:
        """
        Get loaded officials pool
        
        Args:
            tournament_id: Optional tournament ID (None for default pool)
            
        Returns:
            OfficialsPool or None if not loaded
        """
        return self._pools.get(tournament_id)
    
    def get_available_officials(self, official_type: OfficialType, tournament_id: Optional[str] = None) -> List[Official]:
        """
        Get available officials by type
        
        Args:
            official_type: Type of official to get
            tournament_id: Optional tournament ID
            
        Returns:
            List of officials of the specified type
        """
        pool = self._pools.get(tournament_id)
        if not pool:
            return []
        
        return pool.get_by_type(official_type)
    
    def normalize_officials_data(self, raw_data: Any, official_type: OfficialType) -> List[Official]:
        """
        Normalize raw officials data (strings or dicts) into Official objects
        
        This is THE single source of truth for data transformation.
        No UI component should do this transformation.
        
        Args:
            raw_data: Raw data (list of strings or list of dicts)
            official_type: Type of official
            
        Returns:
            List of Official objects
        """
        if not raw_data:
            return []
        
        officials = []
        
        for item in raw_data:
            try:
                if isinstance(item, str):
                    # String format: convert to Official
                    full_name = item.strip()
                    if not full_name:
                        continue
                    
                    # Generate short name from last word
                    short_name = full_name.split()[-1] if ' ' in full_name else full_name
                    
                    official = Official(
                        id=str(uuid.uuid4()),
                        full_name=full_name,
                        short_name=short_name,
                        official_type=official_type
                    )
                    officials.append(official)
                    
                elif isinstance(item, dict):
                    # Dictionary format: use existing data
                    # Handle both new format and old format
                    full_name = item.get('full_name', item.get('name', ''))
                    if not full_name:
                        continue
                    
                    short_name = item.get('short_name', full_name.split()[-1] if ' ' in full_name else full_name)
                    
                    official = Official(
                        id=item.get('id', str(uuid.uuid4())),
                        full_name=full_name,
                        short_name=short_name,
                        official_type=official_type,
                        photo_url=item.get('photo_url', item.get('official_photo')),
                        nationality=item.get('nationality'),
                        experience=item.get('experience'),
                        fifa_qualified=item.get('fifa_qualified', False)
                    )
                    officials.append(official)
                    
            except Exception as e:
                print(f"⚠️  Warning: Failed to normalize official data: {e}")
                continue
        
        return officials
    
    def clear_pool(self, tournament_id: Optional[str] = None) -> bool:
        """
        Clear officials pool
        
        Args:
            tournament_id: Optional tournament ID (None for default pool)
            
        Returns:
            True if pool was cleared, False if pool didn't exist
        """
        if tournament_id in self._pools:
            del self._pools[tournament_id]
            
            # Publish event
            event = OfficialsPoolClearedEvent(tournament_id=tournament_id)
            self.event_bus.publish("officials_pool_cleared", event)
            
            print(f"✅ Officials pool cleared for tournament: {tournament_id}")
            return True
        
        return False
    
    def get_all_pools(self) -> Dict[Optional[str], OfficialsPool]:
        """Get all loaded pools (for debugging/admin)"""
        return self._pools.copy()

