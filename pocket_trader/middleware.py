"""
Middleware system - Unified (merged middleware.py + middlewares.py)
"""

import time
import contextlib
from typing import Optional, Any, Dict, List, Tuple

from .utils import setup_logger, fix_timestamp, get_json_function
from .constants import UPDATE_ITEMS_NAMES


class Middleware:
    """Base middleware class"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
    
    async def on_raw(self, event: str, data: bytes) -> Optional[bytes]:
        return data
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        return data
    
    async def on_emit(self, event: str, data: Optional[Any] = None) -> Tuple[str, Optional[Any]]:
        return event, data
    
    async def on_error(self, event: str, error: Exception, data: Optional[Any] = None):
        self.logger.error(f"Error in event {event}: {error}")


class LoggingMiddleware(Middleware):
    """Log all events"""
    
    def __init__(self, log_raw: bool = False, log_parsed: bool = True):
        super().__init__()
        self.log_raw = log_raw
        self.log_parsed = log_parsed
    
    async def on_raw(self, event: str, data: bytes) -> Optional[bytes]:
        if self.log_raw and data:
            self.logger.debug(f"📥 RAW {event}: {len(data)} bytes")
        return data
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        if self.log_parsed and data is not None:
            if isinstance(data, list) and len(data) > 5:
                self.logger.debug(f"📥 {event}: {len(data)} items")
            else:
                self.logger.debug(f"📥 {event}: {data}")
        return data
    
    async def on_emit(self, event: str, data: Optional[Any] = None) -> Tuple[str, Optional[Any]]:
        self.logger.debug(f"📤 {event}")
        return event, data


class MakeJsonOnMiddleware(Middleware):
    """Parse JSON data from bytes"""
    
    def __init__(self):
        super().__init__()
        self.json = get_json_function()
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        if isinstance(data, (str, bytes)):
            try:
                with contextlib.suppress(Exception):
                    return self.json.loads(data)
            except Exception as e:
                self.logger.error(f"Failed to parse JSON for {event}: {e}")
        return data


class FixTypesOnMiddleware(Middleware):
    """Fix data types for specific events"""
    
    def __init__(self):
        super().__init__()
        self.client = None
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        if data is None:
            return None
        
        try:
            if event in ["pong", "ping-server"] and hasattr(self, 'client') and self.client:
                self.client.conn_manager.update_last_pong()
                return data
            
            if event == "updateStream":
                return await self._fix_update_stream(data)
            elif event == "updateAssets":
                return await self._fix_update_assets(data)
            elif event == "chafor":
                return await self._fix_chafor(data)
        except Exception as e:
            self.logger.error(f"Error fixing types for {event}: {e}")
        
        return data
    
    async def _fix_update_stream(self, data: Any) -> Any:
        if not isinstance(data, list):
            return data
        
        result = []
        for item in data:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    result.append({
                        "asset": str(item[0]),
                        "timestamp": fix_timestamp(float(item[1])),
                        "value": float(item[2]),
                    })
                elif isinstance(item, dict):
                    result.append(item)
                else:
                    result.append(item)
            except Exception as e:
                self.logger.error(f"Error processing item: {e}")
                result.append(item)
        return result
    
    async def _fix_update_assets(self, data: Any) -> Any:
        return data
    
    async def _fix_chafor(self, data: Any) -> Any:
        return data


class StatsMiddleware(Middleware):
    """Collect event statistics"""
    
    def __init__(self):
        super().__init__()
        self.stats: Dict[str, Dict] = {}
        self.start_time = time.time()
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        if event not in self.stats:
            self.stats[event] = {'count': 0, 'first_seen': time.time(), 'last_seen': 0}
        
        stats = self.stats[event]
        stats['count'] += 1
        stats['last_seen'] = time.time()
        
        if isinstance(data, bytes):
            stats['bytes_total'] = stats.get('bytes_total', 0) + len(data)
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        total_events = sum(s['count'] for s in self.stats.values())
        return {
            'uptime': uptime,
            'total_events': total_events,
            'events_per_second': total_events / uptime if uptime > 0 else 0,
            'by_event': self.stats
        }
    
    def reset(self):
        self.stats.clear()
        self.start_time = time.time()


class ThrottleMiddleware(Middleware):
    """Throttle high-frequency events"""
    
    def __init__(self, throttle_ms: int = 100, events: Optional[List[str]] = None):
        super().__init__()
        self.throttle_seconds = throttle_ms / 1000
        self.events = events or ['updateStream', 'chafor']
        self._last_time: Dict[str, float] = {}
    
    async def on(self, event: str, data: Any) -> Optional[Any]:
        if event in self.events:
            now = time.time()
            last = self._last_time.get(event, 0)
            if now - last < self.throttle_seconds:
                return None
            self._last_time[event] = now
        return data


__all__ = [
    "Middleware",
    "LoggingMiddleware",
    "MakeJsonOnMiddleware",
    "FixTypesOnMiddleware",
    "StatsMiddleware",
    "ThrottleMiddleware",
]