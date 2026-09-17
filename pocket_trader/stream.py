"""
Real-time stream data handling (39-byte updates)
"""

import struct
import time
from typing import Optional, Dict, List, Callable, Awaitable, Any
from datetime import datetime
from collections import deque
import asyncio

from .models import Asset
from .utils import setup_logger, fix_timestamp
from .constants import MESSAGE_SIZES


class StreamUpdate:
    """
    39-byte stream update structure from platform
    """
    
    STRUCT_FORMAT = '<IdIfffff'  # < little-endian, I=uint32, d=double, I=uint32, f=float...
    
    def __init__(self, data: bytes):
        self.raw_data = data
        self.parsed = False
        self.asset_id: Optional[int] = None
        self.asset: Optional[Asset] = None
        self.price: float = 0.0
        self.timestamp: int = 0
        self.volume: int = 0
        self.change_24h: float = 0.0
        self.bid: float = 0.0
        self.ask: float = 0.0
        self.spread: float = 0.0
        self.flags: str = ""
        self._logger = setup_logger("StreamUpdate")
        
        self._parse()
    
    def _parse(self):
        """Parse 39-byte binary data"""
        try:
            if len(self.raw_data) < 36:
                self._logger.warning(f"Invalid stream data length: {len(self.raw_data)}")
                return
            
            # Unpack first 36 bytes
            (self.asset_id, self.price, self.timestamp, self.volume,
             self.change_24h, self.bid, self.ask, self.spread) = struct.unpack(
                '<IdIfffff', self.raw_data[:36]
            )
            
            # Fix timestamp
            self.timestamp = int(fix_timestamp(self.timestamp))
            
            # Remaining 3 bytes as flags
            if len(self.raw_data) >= 39:
                self.flags = self.raw_data[36:39].hex()
            
            self.parsed = True
            
        except struct.error as e:
            self._logger.error(f"Stream parse error: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
    
    @property
    def datetime(self) -> datetime:
        """Get datetime from timestamp"""
        return datetime.fromtimestamp(self.timestamp)
    
    @property
    def change_percent(self) -> float:
        """Get 24h change as percentage"""
        return self.change_24h * 100
    
    @property
    def mid_price(self) -> float:
        """Get mid price (average of bid and ask)"""
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.price
    
    def __repr__(self) -> str:
        if not self.parsed:
            return f"StreamUpdate(raw={self.raw_data.hex()})"
        return (f"StreamUpdate(asset_id={self.asset_id}, price={self.price:.5f}, "
                f"bid={self.bid:.5f}, ask={self.ask:.5f}, spread={self.spread:.5f})")


class StreamProcessor:
    """
    Process real-time stream updates with callbacks and history
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._updates: Dict[Asset, deque] = {}
        self._callbacks: List[Callable[[Asset, StreamUpdate], Awaitable[None]]] = []
        self._batch_callbacks: List[Callable[[Dict[Asset, List[StreamUpdate]]], Awaitable[None]]] = []
        self._last_price: Dict[Asset, float] = {}
        self._last_update: Dict[Asset, float] = {}
        self._price_history: Dict[Asset, deque] = {}
        self._logger = setup_logger("StreamProcessor")
        self._batch_mode = False
        self._batch_buffer: Dict[Asset, List[StreamUpdate]] = {}
        self._batch_task: Optional[asyncio.Task] = None
    
    def add_callback(self, callback: Callable[[Asset, StreamUpdate], Awaitable[None]]):
        """Add callback for individual stream updates"""
        self._callbacks.append(callback)
        self._logger.debug(f"Added callback, total: {len(self._callbacks)}")
    
    def add_batch_callback(self, callback: Callable[[Dict[Asset, List[StreamUpdate]]], Awaitable[None]]):
        """Add callback for batch updates (processed every 100ms)"""
        self._batch_callbacks.append(callback)
        self._logger.debug(f"Added batch callback, total: {len(self._batch_callbacks)}")
    
    def enable_batch_mode(self, interval_ms: int = 100):
        """Enable batch processing mode"""
        if self._batch_task:
            return
        
        self._batch_mode = True
        self._batch_buffer.clear()
        self._batch_task = asyncio.create_task(self._batch_processor(interval_ms / 1000))
        self._logger.info(f"✅ Batch mode enabled (interval: {interval_ms}ms)")
    
    def disable_batch_mode(self):
        """Disable batch processing mode"""
        if self._batch_task:
            self._batch_task.cancel()
            self._batch_task = None
        
        self._batch_mode = False
        self._batch_buffer.clear()
        self._logger.info("Batch mode disabled")
    
    async def _batch_processor(self, interval: float):
        """Process updates in batches"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                if not self._batch_buffer:
                    continue
                
                # Create a copy and clear buffer
                batch = dict(self._batch_buffer)
                self._batch_buffer.clear()
                
                # Call batch callbacks
                for callback in self._batch_callbacks:
                    try:
                        await callback(batch)
                    except Exception as e:
                        self._logger.error(f"Batch callback error: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Batch processor error: {e}")
    
    async def process(self, asset: Asset, update: StreamUpdate):
        """Process a stream update"""
        try:
            # Store in history
            if asset not in self._updates:
                self._updates[asset] = deque(maxlen=self.max_history)
                self._price_history[asset] = deque(maxlen=self.max_history)
            
            self._updates[asset].append(update)
            self._price_history[asset].append(update.price)
            self._last_price[asset] = update.price
            self._last_update[asset] = time.time()
            
            # Batch mode handling
            if self._batch_mode:
                if asset not in self._batch_buffer:
                    self._batch_buffer[asset] = []
                self._batch_buffer[asset].append(update)
            else:
                # Individual callbacks
                for callback in self._callbacks:
                    try:
                        await callback(asset, update)
                    except Exception as e:
                        self._logger.error(f"Callback error: {e}")
                        
        except Exception as e:
            self._logger.error(f"Error processing update: {e}")
    
    def get_last_price(self, asset: Asset) -> Optional[float]:
        """Get last price for asset"""
        return self._last_price.get(asset)
    
    def get_last_update_time(self, asset: Asset) -> Optional[float]:
        """Get last update time for asset"""
        return self._last_update.get(asset)
    
    def get_price_history(self, asset: Asset, count: Optional[int] = None) -> List[float]:
        """Get price history for asset"""
        if asset not in self._price_history:
            return []
        
        prices = list(self._price_history[asset])
        if count:
            return prices[-count:]
        return prices
    
    def get_update_history(self, asset: Asset, count: Optional[int] = None) -> List[StreamUpdate]:
        """Get full update history"""
        if asset not in self._updates:
            return []
        
        updates = list(self._updates[asset])
        if count:
            return updates[-count:]
        return updates
    
    def get_price_at_time(self, asset: Asset, timestamp: float) -> Optional[float]:
        """Get price closest to given timestamp"""
        if asset not in self._updates:
            return None
        
        best_update = None
        best_diff = float('inf')
        
        for update in self._updates[asset]:
            diff = abs(update.timestamp - timestamp)
            if diff < best_diff:
                best_diff = diff
                best_update = update
        
        return best_update.price if best_update else None
    
    def get_ohlc(self, asset: Asset, period_seconds: int = 60) -> Optional[Dict[str, float]]:
        """
        Get OHLC (Open, High, Low, Close) for a period
        """
        if asset not in self._price_history or len(self._price_history[asset]) < 2:
            return None
        
        now = time.time()
        start_time = now - period_seconds
        
        prices = []
        for update in reversed(self._updates[asset]):
            if update.timestamp >= start_time:
                prices.append(update.price)
            else:
                break
        
        if len(prices) < 2:
            return None
        
        return {
            'open': prices[-1],  # Oldest
            'high': max(prices),
            'low': min(prices),
            'close': prices[0],  # Newest
            'volume': len(prices)
        }
    
    def is_stale(self, asset: Asset, max_age: float = 5.0) -> bool:
        """Check if asset data is stale"""
        if asset not in self._last_update:
            return True
        return (time.time() - self._last_update[asset]) > max_age
    
    def get_all_assets(self) -> List[Asset]:
        """Get all assets with data"""
        return list(self._updates.keys())
    
    def get_active_assets(self, max_age: float = 5.0) -> List[Asset]:
        """Get assets with recent updates"""
        now = time.time()
        return [
            asset for asset in self._updates
            if asset in self._last_update and (now - self._last_update[asset]) <= max_age
        ]
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get summary of all assets"""
        summary = {}
        
        for asset in self.get_all_assets():
            last_price = self.get_last_price(asset)
            if last_price:
                prices = self.get_price_history(asset, 20)
                if len(prices) >= 2:
                    change = ((prices[-1] - prices[0]) / prices[0]) * 100
                else:
                    change = 0.0
                
                summary[asset.value] = {
                    'price': last_price,
                    'change_20': round(change, 2),
                    'stale': self.is_stale(asset),
                    'last_update': self.get_last_update_time(asset)
                }
        
        return summary
    
    def clear_asset(self, asset: Asset):
        """Clear data for specific asset"""
        if asset in self._updates:
            self._updates[asset].clear()
            self._price_history[asset].clear()
            self._last_price.pop(asset, None)
            self._last_update.pop(asset, None)
            
            if asset in self._batch_buffer:
                self._batch_buffer[asset].clear()
            
            self._logger.info(f"Cleared data for {asset}")
    
    def clear_all(self):
        """Clear all data"""
        self._updates.clear()
        self._price_history.clear()
        self._last_price.clear()
        self._last_update.clear()
        self._batch_buffer.clear()
        self._logger.info("Cleared all stream data")