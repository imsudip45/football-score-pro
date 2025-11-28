"""Event Bus Implementation"""
import logging
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from threading import Lock
from ..services.interfaces import IEventBus


@dataclass
class EventLog:
    """
    Represents an event log entry.
    
    Attributes:
        event_type: Type of event
        data: Event data
        timestamp: When the event was published
        subscriber_count: Number of subscribers that received the event
        errors: Any errors that occurred during event delivery
    """
    event_type: str
    data: Any
    timestamp: datetime
    subscriber_count: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class EventBus(IEventBus):
    """
    Event Bus implementation for publish-subscribe pattern.
    
    Provides thread-safe event publishing and subscription with error handling,
    logging, and debugging capabilities.
    """

    def __init__(self, enable_logging: bool = True):
        """
        Initialize the event bus.
        
        Args:
            enable_logging: Whether to enable event logging
        """
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_logs: List[EventLog] = []
        self._lock = Lock()
        self._enable_logging = enable_logging
        self._logger = logging.getLogger(__name__)
        
        # Configure logging if enabled
        if self._enable_logging and not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
            
        Returns:
            True if subscription was successful, False otherwise
        """
        if not event_type or not callback:
            self._logger.warning("Invalid subscription: event_type and callback are required")
            return False

        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            # Avoid duplicate subscriptions
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                
                if self._enable_logging:
                    self._logger.info(f"Subscribed to event: {event_type}")
                return True
            else:
                self._logger.warning(f"Callback already subscribed to event: {event_type}")
                return False

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        if not event_type or not callback:
            return False

        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    
                    # Clean up empty subscriber lists
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                    
                    if self._enable_logging:
                        self._logger.info(f"Unsubscribed from event: {event_type}")
                    return True
                except ValueError:
                    self._logger.warning(f"Callback not found for event: {event_type}")
                    return False
            return False

    def publish(self, event_type: str, data: Any = None) -> bool:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event to publish
            data: Event data to send to subscribers
            
        Returns:
            True if event was published successfully, False otherwise
        """
        if not event_type:
            self._logger.error("Event type cannot be empty")
            return False

        timestamp = datetime.utcnow()
        errors = []
        subscriber_count = 0

        # Get subscribers (thread-safe copy)
        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        if not subscribers:
            if self._enable_logging:
                self._logger.debug(f"No subscribers for event: {event_type}")
            
            # Always log the event even if no subscribers
            event_log = EventLog(
                event_type=event_type,
                data=data,
                timestamp=timestamp,
                subscriber_count=0
            )
            self._event_logs.append(event_log)
            
            return True

        # Deliver event to all subscribers
        for callback in subscribers:
            try:
                callback(data)
                subscriber_count += 1
            except Exception as e:
                error_msg = f"Error delivering event {event_type} to subscriber: {str(e)}"
                errors.append(error_msg)
                self._logger.error(error_msg)

        # Always log the event
        event_log = EventLog(
            event_type=event_type,
            data=data,
            timestamp=timestamp,
            subscriber_count=subscriber_count,
            errors=errors
        )
        self._event_logs.append(event_log)

        # Log success/failure if logging is enabled
        if self._enable_logging:
            if errors:
                self._logger.warning(
                    f"Published event {event_type} with {len(errors)} errors "
                    f"to {subscriber_count}/{len(subscribers)} subscribers"
                )
            else:
                self._logger.info(
                    f"Published event {event_type} to {subscriber_count} subscribers"
                )

        return len(errors) == 0

    def get_subscribers(self, event_type: Optional[str] = None) -> Dict[str, int]:
        """
        Get subscriber counts for event types.
        
        Args:
            event_type: Specific event type to check, or None for all
            
        Returns:
            Dictionary mapping event types to subscriber counts
        """
        with self._lock:
            if event_type:
                return {event_type: len(self._subscribers.get(event_type, []))}
            else:
                return {
                    event_type: len(subscribers) 
                    for event_type, subscribers in self._subscribers.items()
                }

    def get_event_logs(self, event_type: Optional[str] = None, limit: Optional[int] = None) -> List[EventLog]:
        """
        Get event logs.
        
        Args:
            event_type: Filter by specific event type
            limit: Maximum number of logs to return (most recent first)
            
        Returns:
            List of event logs
        """
        logs = self._event_logs.copy()
        
        # Filter by event type if specified
        if event_type:
            logs = [log for log in logs if log.event_type == event_type]
        
        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit if specified
        if limit:
            logs = logs[:limit]
        
        return logs

    def clear_event_logs(self):
        """Clear all event logs."""
        self._event_logs.clear()
        if self._enable_logging:
            self._logger.info("Event logs cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dictionary with event bus statistics
        """
        with self._lock:
            total_subscribers = sum(len(subs) for subs in self._subscribers.values())
            subscriber_counts = {
                event_type: len(subscribers) 
                for event_type, subscribers in self._subscribers.items()
            }
            
            return {
                "total_event_types": len(self._subscribers),
                "total_subscribers": total_subscribers,
                "total_events_published": len(self._event_logs),
                "event_types": list(self._subscribers.keys()),
                "subscriber_counts": subscriber_counts
            }

    def has_subscribers(self, event_type: str) -> bool:
        """
        Check if an event type has any subscribers.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if event type has subscribers, False otherwise
        """
        with self._lock:
            return event_type in self._subscribers and len(self._subscribers[event_type]) > 0

    def clear_subscribers(self, event_type: Optional[str] = None):
        """
        Clear subscribers for an event type or all event types.
        
        Args:
            event_type: Specific event type to clear, or None for all
        """
        with self._lock:
            if event_type:
                if event_type in self._subscribers:
                    del self._subscribers[event_type]
                    if self._enable_logging:
                        self._logger.info(f"Cleared subscribers for event: {event_type}")
            else:
                self._subscribers.clear()
                if self._enable_logging:
                    self._logger.info("Cleared all subscribers")

    def __str__(self) -> str:
        """String representation of the event bus."""
        stats = self.get_stats()
        return (
            f"EventBus(event_types={stats['total_event_types']}, "
            f"subscribers={stats['total_subscribers']}, "
            f"events_published={stats['total_events_published']})"
        )
