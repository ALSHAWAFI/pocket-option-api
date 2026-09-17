# trading.py
"""
Trading module - Unified candle, deal, and trade management
Merged: candles.py + deals.py + storage.py
With support for advanced features: LFU Cache, Pattern Cache, Genetic Optimization
"""

import abc
import asyncio
import sqlite3
import json
import uuid
import datetime
import math
import time
import hashlib
import typing
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple, TYPE_CHECKING
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field

import pytz

from .models import Asset, Candle, Deal, UpdateCloseValueItem
from .utils import setup_logger, append_or_replace, generate_request_id
from .exceptions import DealError
from .constants import (
    API_LIMITS_MIN_ORDER_AMOUNT, API_LIMITS_MAX_ORDER_AMOUNT,
    API_LIMITS_MIN_DURATION, API_LIMITS_MAX_DURATION,
    API_LIMITS_MAX_CONCURRENT_ORDERS
)

if TYPE_CHECKING:
    from .client import PocketOptionClient


# ============================================================================
# 1. CANDLE BUILDER - building candles from ticks
# ============================================================================

class CandleBuilder:
    """Build complete candles from real-time price ticks"""
    
    def __init__(self, asset: Asset, timeframe_seconds: int = 60, max_candles: int = 100):
        self.asset = asset
        self.timeframe = timeframe_seconds
        self.max_candles = max_candles
        self.current_candle: Optional[Candle] = None
        self.completed_candles: List[Candle] = []
        self._tick_count = 0
        self._on_new_candle_callback: Optional[Callable[[Candle], Awaitable[None]]] = None
        self._logger = setup_logger(f"CandleBuilder.{asset}")
    
    def add_tick(self, timestamp: float, price: float) -> bool:
        """Add a new price tick and update current candle"""
        try:
            candle_time = int(timestamp / self.timeframe) * self.timeframe
            candle_dt = datetime.datetime.fromtimestamp(candle_time, tz=pytz.UTC)
            
            if self.current_candle is None:
                self.current_candle = Candle(
                    asset=self.asset,
                    timestamp=candle_dt,
                    timeframe=self.timeframe,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                )
                self._tick_count = 1
                return False
            
            if self.current_candle.timestamp.timestamp() != candle_time:
                self.completed_candles.append(self.current_candle)
                if len(self.completed_candles) > self.max_candles:
                    self.completed_candles = self.completed_candles[-self.max_candles:]
                
                if self._on_new_candle_callback:
                    try:
                        asyncio.create_task(self._on_new_candle_callback(self.current_candle))
                    except Exception as e:
                        self._logger.error(f"Callback error: {e}")
                
                self.current_candle = Candle(
                    asset=self.asset,
                    timestamp=candle_dt,
                    timeframe=self.timeframe,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                )
                self._tick_count = 1
                return True
            else:
                self.current_candle.high = max(self.current_candle.high, price)
                self.current_candle.low = min(self.current_candle.low, price)
                self.current_candle.close = price
                self._tick_count += 1
                return False
                
        except Exception as e:
            self._logger.error(f"Error adding tick: {e}")
            return False
    
    def get_completed_candles(self, count: Optional[int] = None) -> List[Candle]:
        return self.completed_candles[-count:] if count else self.completed_candles.copy()
    
    def get_current_candle(self) -> Optional[Candle]:
        return self.current_candle
    
    def get_all_candles(self) -> List[Candle]:
        candles = self.completed_candles.copy()
        if self.current_candle:
            candles.append(self.current_candle)
        return candles
    
    def get_candle_count(self) -> int:
        return len(self.completed_candles)
    
    def get_tick_count(self) -> int:
        return self._tick_count
    
    def set_on_new_candle(self, callback: Callable[[Candle], Awaitable[None]]):
        self._on_new_candle_callback = callback


# ============================================================================
# 2. CANDLE STORAGE - candle storage
# ============================================================================

class CandleStorage(abc.ABC):
    """Abstract base class for candle storage"""
    
    def __init__(self, client: 'PocketOptionClient'):
        self.client = client
        self.logger = setup_logger("CandleStorage")
        self.client.on.update_close_value(self._on_update_close_value)
    
    async def _on_update_close_value(self, items: List[UpdateCloseValueItem]):
        try:
            await self.add_item_bulk(items)
        except Exception as e:
            self.logger.error(f"Error handling price updates: {e}")
    
    async def add_candle(self, candle: Candle) -> None:
        """Add a complete candle"""
        try:
            await self.add_item_bulk([
                UpdateCloseValueItem(asset=candle.asset, timestamp=candle.timestamp.timestamp(), value=candle.open),
                UpdateCloseValueItem(asset=candle.asset, timestamp=candle.timestamp.timestamp() + 0.01, value=candle.low),
                UpdateCloseValueItem(asset=candle.asset, timestamp=candle.timestamp.timestamp() + 0.02, value=candle.high),
                UpdateCloseValueItem(asset=candle.asset, timestamp=candle.timestamp.timestamp() + (candle.timeframe - 0.01), value=candle.close),
            ])
        except Exception as e:
            self.logger.error(f"Error adding candle: {e}")
    
    @abc.abstractmethod
    async def add_item(self, item: UpdateCloseValueItem): ...
    
    @abc.abstractmethod
    async def add_item_bulk(self, items: List[UpdateCloseValueItem]): ...
    
    @abc.abstractmethod
    async def get_items(self, asset: Asset, *, 
                       start: Optional[datetime.datetime] = None,
                       end: Optional[datetime.datetime] = None,
                       count: Optional[int] = None) -> List[UpdateCloseValueItem]: ...
    
    async def get_candles(self, asset: Asset, timeframe: int = 60, *,
                         start: Optional[datetime.datetime] = None,
                         end: Optional[datetime.datetime] = None,
                         count: Optional[int] = None) -> List[Candle]:
        """Get candles from stored price ticks"""
        try:
            items = await self.get_items(asset, start=start, end=end, count=count)
            
            buckets: dict[int, list[UpdateCloseValueItem]] = defaultdict(list)
            for item in items:
                ts_bucket = math.floor(item.timestamp / timeframe) * timeframe
                buckets[ts_bucket].append(item)
            
            candles = []
            for ts_bucket in sorted(buckets):
                group = buckets[ts_bucket]
                values = [i.value for i in group]
                candle = Candle(
                    asset=asset,
                    timestamp=datetime.datetime.fromtimestamp(ts_bucket, tz=pytz.UTC),
                    timeframe=timeframe,
                    open=values[0],
                    close=values[-1],
                    high=max(values),
                    low=min(values),
                )
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            self.logger.error(f"Error getting candles: {e}")
            return []


class MemoryCandleStorage(CandleStorage):
    """In-memory candle storage with candle building and pattern caching"""
    
    def __init__(self, client: 'PocketOptionClient', max_size: int = 10000):
        super().__init__(client)
        self._max_size = max_size
        self._storage: Dict[Asset, deque] = defaultdict(lambda: deque([], max_size))
        self._candle_builders: Dict[tuple, CandleBuilder] = {}
        self._candles: Dict[Asset, List[Candle]] = defaultdict(list)
        self._pattern_cache: Dict[str, List[Dict]] = {}  # Pattern cache for candles
        self.logger = setup_logger("MemoryCandleStorage")
    
    def get_candle_builder(self, asset: Asset, timeframe: int = 60) -> CandleBuilder:
        key = (asset, timeframe)
        if key not in self._candle_builders:
            builder = CandleBuilder(asset, timeframe, self._max_size)
            
            async def on_new_candle(candle: Candle):
                try:
                    self._candles[asset].append(candle)
                    if len(self._candles[asset]) > self._max_size:
                        self._candles[asset] = self._candles[asset][-self._max_size:]
                    
                    # Store pattern for AI analysis
                    await self._store_candle_pattern(candle)
                    
                except Exception as e:
                    self.logger.error(f"Error in new candle callback: {e}")
            
            builder.set_on_new_candle(on_new_candle)
            self._candle_builders[key] = builder
            self.logger.debug(f"Created candle builder for {asset} timeframe {timeframe}")
        
        return self._candle_builders[key]
    
    async def _store_candle_pattern(self, candle: Candle):
        """Store candle pattern for AI learning"""
        pattern_key = f"{candle.asset}_{candle.timeframe}"
        
        pattern_data = {
            'timestamp': candle.timestamp.timestamp(),
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
            'volume': candle.volume,
            'is_bullish': candle.is_bullish,
            'body_size': candle.body_size,
            'upper_shadow': candle.upper_shadow,
            'lower_shadow': candle.lower_shadow,
            'range': candle.range
        }
        
        if pattern_key not in self._pattern_cache:
            self._pattern_cache[pattern_key] = []
        
        self._pattern_cache[pattern_key].append(pattern_data)
        
        # Keep only last 1000 patterns
        if len(self._pattern_cache[pattern_key]) > 1000:
            self._pattern_cache[pattern_key] = self._pattern_cache[pattern_key][-1000:]
    
    async def get_similar_patterns(self, asset: Asset, timeframe: int, 
                                   current_candle: Candle, limit: int = 10) -> List[Dict]:
        """Find similar candle patterns from history"""
        pattern_key = f"{asset}_{timeframe}"
        
        if pattern_key not in self._pattern_cache:
            return []
        
        # Calculate pattern similarity
        similar = []
        for pattern in self._pattern_cache[pattern_key]:
            similarity = self._calculate_similarity(current_candle, pattern)
            similar.append((similarity, pattern))
        
        similar.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in similar[:limit]]
    
    def _calculate_similarity(self, candle: Candle, pattern: Dict) -> float:
        """Calculate similarity between two candles"""
        score = 0.0
        
        # Body size similarity
        body_diff = abs(candle.body_size - pattern['body_size']) / (candle.range + 1e-8)
        score += (1 - min(1, body_diff)) * 0.3
        
        # Direction match
        if candle.is_bullish == pattern['is_bullish']:
            score += 0.3
        
        # Range similarity
        range_diff = abs(candle.range - pattern['range']) / (candle.range + 1e-8)
        score += (1 - min(1, range_diff)) * 0.2
        
        # Shadow similarity
        upper_diff = abs(candle.upper_shadow - pattern['upper_shadow']) / (candle.range + 1e-8)
        lower_diff = abs(candle.lower_shadow - pattern['lower_shadow']) / (candle.range + 1e-8)
        score += (1 - min(1, (upper_diff + lower_diff) / 2)) * 0.2
        
        return score

    # In trading.py, find the add_item function in MemoryCandleStorage and replace it with this:

    async def add_item(self, item: UpdateCloseValueItem):
        """Add a price tick"""
        try:
            # ✅ Handle dict if item is of type dict
            if isinstance(item, dict):
                from .models import UpdateCloseValueItem as UpdateItem
                try:
                    asset = item.get('asset')
                    # Convert asset to Asset enum if it's a string
                    if isinstance(asset, str):
                        try:
                            asset = Asset(asset)
                        except:
                            pass
                    item = UpdateItem(
                        asset=asset,
                        timestamp=item.get('timestamp', time.time()),
                        value=item.get('value', 0)
                    )
                except Exception as e:
                    self.logger.error(f"Error converting dict to UpdateCloseValueItem: {e}")
                    return

            self._storage[item.asset] = append_or_replace(
                self._storage[item.asset], item, ["asset", "timestamp"]
            )
            builder = self.get_candle_builder(item.asset, 60)
            builder.add_tick(item.timestamp, item.value)
        except Exception as e:
            self.logger.error(f"Error adding item: {e}")

    # And also add_item_bulk:

    async def add_item_bulk(self, items: List[UpdateCloseValueItem]):
        """Add multiple price ticks"""
        for item in items:
            # ✅ Handle dict
            if isinstance(item, dict):
                from .models import UpdateCloseValueItem as UpdateItem
                try:
                    asset = item.get('asset')
                    if isinstance(asset, str):
                        try:
                            asset = Asset(asset)
                        except:
                            pass
                    item = UpdateItem(
                        asset=asset,
                        timestamp=item.get('timestamp', time.time()),
                        value=item.get('value', 0)
                    )
                except Exception as e:
                    self.logger.error(f"Error converting dict: {e}")
                    continue
            await self.add_item(item)
    
    async def get_items(self, asset: Asset, *,
                       start: Optional[datetime.datetime] = None,
                       end: Optional[datetime.datetime] = None,
                       count: Optional[int] = None) -> List[UpdateCloseValueItem]:
        try:
            items = list(self._storage.get(asset, []))
            if start:
                items = [i for i in items if i.timestamp >= start.timestamp()]
            if end:
                items = [i for i in items if i.timestamp <= end.timestamp()]
            items.sort(key=lambda i: i.timestamp)
            if count is not None:
                items = items[-count:]
            return items
        except Exception as e:
            self.logger.error(f"Error getting items: {e}")
            return []
    
    async def get_built_candles(self, asset: Asset, timeframe: int = 60,
                               count: Optional[int] = None) -> List[Candle]:
        try:
            builder = self.get_candle_builder(asset, timeframe)
            candles = builder.get_completed_candles(count)
            return candles
        except Exception as e:
            self.logger.error(f"Error getting built candles: {e}")
            return []
    
    async def wait_for_candles(self, asset: Asset, timeframe: int = 60,
                              required_count: int = 20, timeout: int = 1200) -> List[Candle]:
        start_time = asyncio.get_event_loop().time()
        while True:
            candles = await self.get_built_candles(asset, timeframe)
            if len(candles) >= required_count:
                self.logger.info(f"Got {required_count} candles for {asset}")
                return candles[-required_count:]
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {required_count} candles for {asset}")
            await asyncio.sleep(5)


# ============================================================================
# 3. DEALS STORAGE - storing and managing deals
# ============================================================================

class DealsStorage(abc.ABC):
    """Abstract base class for deals storage with pattern learning"""
    
    def __init__(self, client: 'PocketOptionClient'):
        self.client = client
        self._open_deal_events: Dict[int, asyncio.Event] = {}
        self._close_deal_events: Dict[uuid.UUID, asyncio.Event] = {}
        self._successful_patterns: List[Dict] = []
        self._failed_patterns: List[Dict] = []
        self.logger = setup_logger("DealsStorage")
        
        self.client.on.success_open_deal(self._on_success_open_deal)
        self.client.on.success_close_deal(self._on_success_close_deal)
        self.client.on.update_opened_deals(self.add_or_update_deal_bulk)
        self.client.on.update_closed_deals(self.add_or_update_deal_bulk)

    async def _on_success_open_deal(self, deal):
        """Handle successful deal opening"""
        try:
            # Convert dict to Deal object if necessary
            if isinstance(deal, dict):
                from .models import Deal as DealModel
                try:
                    # Try to create a Deal object from the dict
                    deal_obj = DealModel(**deal)
                    deal = deal_obj
                except Exception as e:
                    self.logger.error(f"Error converting dict to Deal: {e}")
                    return

            await self.add_or_update_deal(deal)
            if deal.request_id and self._open_deal_events.get(deal.request_id):
                self._open_deal_events[deal.request_id].set()
                self.logger.debug(f"Deal open event set for request {deal.request_id}")
        except Exception as e:
            self.logger.error(f"Error in success_open_deal handler: {e}")

    async def _on_success_close_deal(self, close_deal):
        try:
            if isinstance(close_deal, dict):
                deals = close_deal.get('deals', [])
                if not deals and 'id' in close_deal:
                    deals = [close_deal]
            elif hasattr(close_deal, 'deals'):
                deals = close_deal.deals
            else:
                deals = [close_deal] if hasattr(close_deal, 'id') else []

            if deals:
                await self.add_or_update_deal_bulk(deals)
                for deal in deals:
                    if isinstance(deal, dict):
                        deal_id = deal.get('id')
                    else:
                        deal_id = getattr(deal, 'id', None)

                    if deal_id and deal_id in self._close_deal_events:
                        event = self._close_deal_events.pop(deal_id)
                        event.set()
        except Exception as e:
            self.logger.error(f"Error in success_close_deal handler: {e}")
    
    async def open_deal(self, asset: Asset, amount: int, action: str, time: int,
                        is_demo: int = 1, request_id: Optional[int] = None,
                        option_type: int = 100, check_limits: bool = True) -> Deal:
        """Open a new deal with validation and pattern matching"""
        if check_limits:
            self._validate_limits(amount, time)
            await self._check_concurrent_orders()
        
        # Check against failed patterns before trading
        pattern_key = f"{asset}_{action}_{time}"
        failed_pattern = await self._check_failed_pattern(pattern_key)
        if failed_pattern and failed_pattern.get('similarity', 0) > 0.8:
            self.logger.warning(f"⚠️ Failed pattern detected for {asset} {action} - avoiding trade")
            raise DealError("pattern_failed", f"Failed pattern detected with {failed_pattern['similarity']*100:.0f}% similarity")
        
        request_id = request_id or generate_request_id()
        self._open_deal_events[request_id] = asyncio.Event()
        
        self.logger.info(f"Opening deal: {asset} {action} amount={amount} duration={time}")
        
        try:
            await self.client.emit.open_deal({
                "asset": asset,
                "amount": amount,
                "action": action,
                "isDemo": is_demo,
                "requestId": request_id,
                "optionType": option_type,
                "time": time
            })
        except Exception as e:
            self._open_deal_events.pop(request_id, None)
            raise DealError("send_failed", f"Failed to send deal request: {e}")
        
        try:
            await asyncio.wait_for(self._open_deal_events[request_id].wait(), 30)
        except TimeoutError:
            self._open_deal_events.pop(request_id, None)
            raise DealError("timeout", "Timeout waiting for deal")
        finally:
            self._open_deal_events.pop(request_id, None)
        
        deal = await self.get_deal(request_id=request_id)
        if deal:
            self.logger.info(f"Deal opened successfully: {deal.id}")
            return deal
        
        raise DealError("not_found", "Failed to find deal", extras={"request_id": request_id})
    
    def _validate_limits(self, amount: int, time: int):
        if amount < API_LIMITS_MIN_ORDER_AMOUNT:
            raise DealError("min_amount", f"Min amount is {API_LIMITS_MIN_ORDER_AMOUNT}")
        if amount > API_LIMITS_MAX_ORDER_AMOUNT:
            raise DealError("max_amount", f"Max amount is {API_LIMITS_MAX_ORDER_AMOUNT}")
        if time < API_LIMITS_MIN_DURATION:
            raise DealError("min_duration", f"Min duration is {API_LIMITS_MIN_DURATION}")
        if time > API_LIMITS_MAX_DURATION:
            raise DealError("max_duration", f"Max duration is {API_LIMITS_MAX_DURATION}")
    
    async def _check_concurrent_orders(self):
        if not self.client.authorization_data:
            return
        uid = self.client.authorization_data.get("uid") if isinstance(self.client.authorization_data, dict) else getattr(self.client.authorization_data, "uid", None)
        if uid:
            orders = await self.get_deals(uid=uid, closed=False)
            orders_list = list(orders)
            if len(orders_list) >= API_LIMITS_MAX_CONCURRENT_ORDERS:
                raise DealError("max_orders", f"Max concurrent orders ({API_LIMITS_MAX_CONCURRENT_ORDERS}) reached")
    
    async def _check_failed_pattern(self, pattern_key: str) -> Optional[Dict]:
        """Check if pattern has failed before"""
        for pattern in self._failed_patterns:
            if pattern.get('key') == pattern_key:
                return pattern
        return None
    
    async def learn_from_trade(self, deal: Deal, was_win: bool, market_data: Optional[Dict] = None):
        """Learn from trade result for pattern recognition"""
        pattern = {
            'key': f"{deal.asset}_{deal.command.name}_{deal.option_type}",
            'asset': deal.asset,
            'direction': deal.command.name,
            'duration': deal.close_timestamp - deal.open_timestamp if deal.close_timestamp else 0,
            'profit': deal.profit,
            'timestamp': time.time(),
            'market_data': market_data or {}
        }
        
        if was_win:
            self._successful_patterns.append(pattern)
            self._successful_patterns = self._successful_patterns[-1000:]
        else:
            pattern['similarity'] = 1.0
            self._failed_patterns.append(pattern)
            self._failed_patterns = self._failed_patterns[-1000:]
    
    async def get_similar_successful_pattern(self, current: Dict) -> Optional[Dict]:
        """Find similar successful pattern"""
        best_match = None
        best_similarity = 0
        
        for pattern in self._successful_patterns:
            similarity = self._calculate_pattern_similarity(current, pattern)
            if similarity > best_similarity and similarity > 0.7:
                best_similarity = similarity
                best_match = pattern
        
        if best_match:
            best_match['similarity'] = best_similarity
        
        return best_match
    
    def _calculate_pattern_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between two patterns"""
        similarity = 0.0
        
        if pattern1.get('asset') == pattern2.get('asset'):
            similarity += 0.3
        
        if pattern1.get('direction') == pattern2.get('direction'):
            similarity += 0.3
        
        duration_diff = abs(pattern1.get('duration', 0) - pattern2.get('duration', 0))
        if duration_diff < 60:
            similarity += 0.2
        
        return similarity
    
    @typing.overload
    async def check_deal_result(self, wait_time: int = 600, *,
                                deal_id: uuid.UUID = ..., request_id: None = ...,
                                deal: None = ...) -> Deal: ...
    
    @typing.overload
    async def check_deal_result(self, wait_time: int = 600, *,
                                deal_id: None = ..., request_id: int = ...,
                                deal: None = ...) -> Deal: ...
    
    @typing.overload
    async def check_deal_result(self, wait_time: int = 600, *,
                                deal_id: None = ..., request_id: None = ...,
                                deal: Deal = ...) -> Deal: ...
    
    async def check_deal_result(self, wait_time: int = 600, *,
                                deal_id: Optional[uuid.UUID] = None,
                                request_id: Optional[int] = None,
                                deal: Optional[Deal] = None) -> Deal:
        """Wait for deal result and return completed deal"""
        if not deal and (deal_id or request_id):
            deal = await self.get_deal(deal_id=deal_id, request_id=request_id)
        
        if not deal:
            raise RuntimeError("Failed to find deal")
        
        self.logger.info(f"Waiting for result of deal {deal.id}")
        self._close_deal_events[deal.id] = asyncio.Event()
        
        try:
            await asyncio.wait_for(self._close_deal_events[deal.id].wait(), wait_time)
        except TimeoutError:
            self._close_deal_events.pop(deal.id, None)
            raise TimeoutError(f"Timeout waiting for deal {deal.id}")
        finally:
            self._close_deal_events.pop(deal.id, None)
        
        deal = await self.get_deal(deal_id=deal.id)
        if deal:
            profit = deal.profit or 0
            self.logger.info(f"Deal {deal.id} closed with profit: {profit}")
            return deal
        
        raise RuntimeError(f"Failed to find deal {deal.id} after closing")
    
    @abc.abstractmethod
    async def add_or_update_deal(self, deal: Deal): ...
    
    @abc.abstractmethod
    async def add_or_update_deal_bulk(self, deals: List[Deal]): ...
    
    @typing.overload
    async def get_deal(self, *, deal_id: uuid.UUID = ..., request_id: None = ...) -> Optional[Deal]: ...
    
    @typing.overload
    async def get_deal(self, *, deal_id: Optional[uuid.UUID] = ..., request_id: int = ...) -> Optional[Deal]: ...
    
    @abc.abstractmethod
    async def get_deal(self, *, deal_id: Optional[uuid.UUID] = None,
                      request_id: Optional[int] = None) -> Optional[Deal]: ...
    
    @abc.abstractmethod
    async def get_deals(self, **filters) -> List[Deal]: ...


class MemoryDealsStorage(DealsStorage):
    """In-memory deals storage with pattern learning"""
    
    def __init__(self, client: 'PocketOptionClient'):
        super().__init__(client)
        self._deals: List[Deal] = []
        self.logger = setup_logger("MemoryDealsStorage")
    
    async def add_or_update_deal(self, deal: Deal) -> None:
        try:
            if isinstance(deal, dict):
                from .models import Deal as DealModel
                try:
                    deal = DealModel(**deal)
                except Exception as e:
                    self.logger.error(f"Error converting dict to Deal: {e}")
                    return
            
            old_len = len(self._deals)
            self._deals = append_or_replace(self._deals, deal, eq_by_keys=["id"])
            
            if len(self._deals) > old_len:
                self.logger.debug(f"Added new deal: {deal.id}")
            else:
                self.logger.debug(f"Updated deal: {deal.id}")
                
        except Exception as e:
            self.logger.error(f"Error adding/updating deal: {e}")
    
    async def add_or_update_deal_bulk(self, deals: List[Deal]) -> None:
        for deal in deals:
            await self.add_or_update_deal(deal)
        
        if deals:
            self.logger.debug(f"Bulk updated {len(deals)} deals")
    
    async def get_deal(self, *, deal_id: Optional[uuid.UUID] = None,
                      request_id: Optional[int] = None) -> Optional[Deal]:
        try:
            if deal_id:
                for deal in self._deals:
                    if deal.id == deal_id:
                        return deal
            
            if request_id:
                for deal in self._deals:
                    if deal.request_id == request_id:
                        return deal
                        
        except Exception as e:
            self.logger.error(f"Error getting deal: {e}")
        
        return None
    
    async def get_deals(self, **filters) -> List[Deal]:
        try:
            data = self._deals.copy()
            
            for key, value in filters.items():
                if value is not None:
                    if key == 'asset':
                        data = [d for d in data if d.asset == value]
                    elif key == 'uid':
                        data = [d for d in data if d.uid == value]
                    elif key == 'closed':
                        if value:
                            data = [d for d in data if d.close_price is not None]
                        else:
                            data = [d for d in data if d.close_price is None]
                    elif key == 'win':
                        if value:
                            data = [d for d in data if d.profit and d.profit > 0]
                        else:
                            data = [d for d in data if d.profit and d.profit <= 0]
            
            data.sort(key=lambda d: d.open_time)
            
            if count := filters.get('count'):
                data = data[-count:]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error filtering deals: {e}")
            return []


# ============================================================================
# 4. TRADE STORAGE - storing trades in SQLite with advanced caching
# ============================================================================

class TradeStatus(Enum):
    """Trade status"""
    OPEN = "open"
    CLOSED = "closed"
    WIN = "win"
    LOSS = "loss"
    PENDING = "pending"


@dataclass
class Trade:
    """Trade model for persistent storage"""
    id: str
    asset: str
    direction: str
    amount: float
    entry_price: float
    status: TradeStatus = TradeStatus.PENDING
    open_time: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(pytz.UTC))
    close_time: Optional[datetime.datetime] = None
    exit_price: Optional[float] = None
    profit: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'asset': self.asset,
            'direction': self.direction,
            'amount': self.amount,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'status': self.status.value,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'profit': self.profit,
            'metadata': json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Trade':
        return cls(
            id=data['id'],
            asset=data['asset'],
            direction=data['direction'],
            amount=data['amount'],
            entry_price=data['entry_price'],
            exit_price=data.get('exit_price'),
            status=TradeStatus(data['status']),
            open_time=datetime.datetime.fromisoformat(data['open_time']),
            close_time=datetime.datetime.fromisoformat(data['close_time']) if data.get('close_time') else None,
            profit=data.get('profit'),
            metadata=json.loads(data['metadata']) if data.get('metadata') else {}
        )


class TradeStorage:
    """Persistent trade storage with SQLite and LRU caching"""
    
    def __init__(self, db_path: str = "trading_data.db", cache_size: int = 1000):
        self.db_path = db_path
        self.cache_size = cache_size
        self._cache: Dict[str, Trade] = {}
        self._cache_order: List[str] = []
        self._lock = asyncio.Lock()
        self.logger = setup_logger("TradeStorage")
        self._init_db()
    
    def _init_db(self):
        try:
            Path(self.db_path).parent.mkdir(exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id TEXT PRIMARY KEY,
                        asset TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        amount REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        status TEXT NOT NULL,
                        open_time TIMESTAMP NOT NULL,
                        close_time TIMESTAMP,
                        profit REAL,
                        metadata TEXT
                    )
                """)
                
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_asset ON trades(asset)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_profit ON trades(profit)")
                
            self.logger.info(f"✅ Database initialized: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Database init error: {e}")
            raise
    
    def _add_to_cache(self, trade: Trade):
        """Add trade to LRU cache"""
        if trade.id in self._cache:
            self._cache_order.remove(trade.id)
        elif len(self._cache) >= self.cache_size:
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]
        
        self._cache[trade.id] = trade
        self._cache_order.append(trade.id)
    
    async def save_trade(self, trade: Trade) -> bool:
        try:
            async with self._lock:
                self._add_to_cache(trade)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trades 
                    (id, asset, direction, amount, entry_price, exit_price, 
                     status, open_time, close_time, profit, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.id, trade.asset, trade.direction, trade.amount,
                    trade.entry_price, trade.exit_price, trade.status.value,
                    trade.open_time.isoformat(),
                    trade.close_time.isoformat() if trade.close_time else None,
                    trade.profit, json.dumps(trade.metadata)
                ))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trade: {e}")
            return False
    
    async def save_trades_bulk(self, trades: List[Trade]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for trade in trades:
                    cursor.execute("""
                        INSERT OR REPLACE INTO trades 
                        (id, asset, direction, amount, entry_price, exit_price, 
                         status, open_time, close_time, profit, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.id, trade.asset, trade.direction, trade.amount,
                        trade.entry_price, trade.exit_price, trade.status.value,
                        trade.open_time.isoformat(),
                        trade.close_time.isoformat() if trade.close_time else None,
                        trade.profit, json.dumps(trade.metadata)
                    ))
                    
                    async with self._lock:
                        self._add_to_cache(trade)
                
                conn.commit()
            
            self.logger.debug(f"Saved {len(trades)} trades")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trades bulk: {e}")
            return False
    
    async def get_trade(self, trade_id: str) -> Optional[Trade]:
        async with self._lock:
            if trade_id in self._cache:
                return self._cache[trade_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
                row = cursor.fetchone()
                
                if row:
                    trade = self._row_to_trade(row)
                    async with self._lock:
                        self._add_to_cache(trade)
                    return trade
                    
        except Exception as e:
            self.logger.error(f"Error getting trade: {e}")
        
        return None
    
    async def get_trades(self, 
                        asset: Optional[str] = None,
                        status: Optional[TradeStatus] = None,
                        start_time: Optional[datetime.datetime] = None,
                        end_time: Optional[datetime.datetime] = None,
                        min_profit: Optional[float] = None,
                        max_profit: Optional[float] = None,
                        limit: int = 1000,
                        offset: int = 0,
                        sort_by: str = "open_time",
                        sort_desc: bool = True) -> List[Trade]:
        try:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if asset:
                query += " AND asset = ?"
                params.append(asset)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            if start_time:
                query += " AND open_time >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND open_time <= ?"
                params.append(end_time.isoformat())
            
            if min_profit is not None:
                query += " AND profit >= ?"
                params.append(min_profit)
            
            if max_profit is not None:
                query += " AND profit <= ?"
                params.append(max_profit)
            
            order = "DESC" if sort_desc else "ASC"
            query += f" ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                trades = [self._row_to_trade(row) for row in rows]
                
                async with self._lock:
                    for trade in trades:
                        self._add_to_cache(trade)
                
                return trades
                
        except Exception as e:
            self.logger.error(f"Error getting trades: {e}")
            return []
    
    async def get_trades_by_date_range(self, start_date: datetime.datetime, 
                                       end_date: datetime.datetime) -> List[Trade]:
        return await self.get_trades(start_time=start_date, end_time=end_date)
    
    async def get_winning_trades(self, min_profit: float = 0) -> List[Trade]:
        return await self.get_trades(status=TradeStatus.WIN, min_profit=min_profit)
    
    async def get_losing_trades(self, max_loss: float = 0) -> List[Trade]:
        return await self.get_trades(status=TradeStatus.LOSS, max_profit=max_loss)
    
    async def delete_trade(self, trade_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
                
                async with self._lock:
                    if trade_id in self._cache:
                        del self._cache[trade_id]
                        if trade_id in self._cache_order:
                            self._cache_order.remove(trade_id)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Error deleting trade: {e}")
            return False
    
    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        try:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM trades WHERE open_time >= ?",
                    (start_date,)
                ).fetchone()['count']
                
                wins = conn.execute(
                    "SELECT COUNT(*) as count FROM trades WHERE status = ? AND open_time >= ?",
                    (TradeStatus.WIN.value, start_date)
                ).fetchone()['count']
                
                losses = conn.execute(
                    "SELECT COUNT(*) as count FROM trades WHERE status = ? AND open_time >= ?",
                    (TradeStatus.LOSS.value, start_date)
                ).fetchone()['count']
                
                profit = conn.execute(
                    "SELECT SUM(profit) as total FROM trades WHERE open_time >= ? AND profit IS NOT NULL",
                    (start_date,)
                ).fetchone()['total'] or 0
                
                avg_profit = conn.execute(
                    "SELECT AVG(profit) as avg FROM trades WHERE open_time >= ? AND profit IS NOT NULL",
                    (start_date,)
                ).fetchone()['avg'] or 0
                
                best_asset = conn.execute("""
                    SELECT asset, SUM(profit) as total 
                    FROM trades 
                    WHERE open_time >= ? 
                    GROUP BY asset 
                    ORDER BY total DESC 
                    LIMIT 1
                """, (start_date,)).fetchone()
                
                worst_asset = conn.execute("""
                    SELECT asset, SUM(profit) as total 
                    FROM trades 
                    WHERE open_time >= ? 
                    GROUP BY asset 
                    ORDER BY total ASC 
                    LIMIT 1
                """, (start_date,)).fetchone()
                
                return {
                    'period_days': days,
                    'total_trades': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'total_profit': profit,
                    'average_profit': avg_profit,
                    'best_asset': best_asset['asset'] if best_asset else None,
                    'best_asset_profit': best_asset['total'] if best_asset else 0,
                    'worst_asset': worst_asset['asset'] if worst_asset else None,
                    'worst_asset_profit': worst_asset['total'] if worst_asset else 0,
                }
                
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}
    
    async def clear(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM trades")
            
            async with self._lock:
                self._cache.clear()
                self._cache_order.clear()
            
            self.logger.info("Trade storage cleared")
            
        except Exception as e:
            self.logger.error(f"Error clearing storage: {e}")
    
    async def vacuum(self):
        """Optimize database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            self.logger.info("Database vacuumed")
        except Exception as e:
            self.logger.error(f"Error vacuuming database: {e}")
    
    async def close(self):
        self._cache.clear()
        self._cache_order.clear()
        self.logger.info("Trade storage closed")
    
    def _row_to_trade(self, row) -> Trade:
        return Trade(
            id=row['id'],
            asset=row['asset'],
            direction=row['direction'],
            amount=row['amount'],
            entry_price=row['entry_price'],
            exit_price=row['exit_price'],
            status=TradeStatus(row['status']),
            open_time=datetime.datetime.fromisoformat(row['open_time']),
            close_time=datetime.datetime.fromisoformat(row['close_time']) if row['close_time'] else None,
            profit=row['profit'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )


# ============================================================================
# FAST CANDLE COLLECTOR - fast candle collection
# ============================================================================

class FastCandleCollector:
    """
    Fast candle collector using caching
    Stores candles in memory to avoid repeated calculations
    """

    def __init__(self, client: 'PocketOptionClient'):
        self.client = client
        self.storage = MemoryCandleStorage(client)
        self._cache: Dict[str, tuple] = {}
        self._logger = setup_logger("FastCandleCollector")

    async def collect_candles(self, asset: Asset, timeframe: int = 60,
                              count: int = 100, use_cache: bool = True) -> List[Candle]:
        """
        Quickly collect candles using caching

        Args:
            asset: The requested asset
            timeframe: The time period in seconds (60 = 1 minute)
            count: Number of candles requested
            use_cache: Whether to use caching

        Returns:
            List of candles
        """
        cache_key = f"{asset}_{timeframe}_{count}"

        # Use cache if available
        if use_cache and cache_key in self._cache:
            cache_time, candles = self._cache[cache_key]
            if time.time() - cache_time < 30:  # cache for 30 seconds
                self._logger.debug(f"📦 Using cached candles for {asset}")
                return candles

        # Try to get built candles first
        built_candles = await self.storage.get_built_candles(asset, timeframe, count)

        if len(built_candles) >= count:
            self._logger.debug(f"✅ Got {len(built_candles)} built candles for {asset}")
            if use_cache:
                self._cache[cache_key] = (time.time(), built_candles)
            return built_candles[-count:]

        # If not enough, wait for more
        try:
            candles = await self.storage.wait_for_candles(
                asset=asset,
                timeframe=timeframe,
                required_count=count,
                timeout=30
            )
            if use_cache:
                self._cache[cache_key] = (time.time(), candles)
            return candles
        except TimeoutError:
            self._logger.warning(f"⚠️ Timeout waiting for {count} candles for {asset}")
            return built_candles

    async def collect_multiple_assets(self, assets: List[Asset],
                                      timeframe: int = 60,
                                      count: int = 100) -> Dict[Asset, List[Candle]]:
        """
        Collect candles for multiple assets in parallel (very fast)

        Args:
            assets: List of requested assets
            timeframe: The time period in seconds
            count: Number of candles per asset

        Returns:
            Dictionary containing assets and candle lists
        """
        tasks = []
        for asset in assets:
            tasks.append(self.collect_candles(asset, timeframe, count, use_cache=True))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        candles_by_asset = {}
        for asset, result in zip(assets, results):
            if isinstance(result, Exception):
                self._logger.error(f"Error collecting candles for {asset}: {result}")
                candles_by_asset[asset] = []
            else:
                candles_by_asset[asset] = result

        return candles_by_asset

    async def get_live_candle(self, asset: Asset, timeframe: int = 60) -> Optional[Candle]:
        """
        Get the current candle (still forming)

        Args:
            asset: The requested asset
            timeframe: The time period in seconds

        Returns:
            The current candle or None if not available
        """
        builder = self.storage.get_candle_builder(asset, timeframe)
        current = builder.get_current_candle()

        if current:
            return current

        # Wait for a new candle
        start_time = time.time()
        while time.time() - start_time < 10:
            current = builder.get_current_candle()
            if current:
                return current
            await asyncio.sleep(0.5)

        return None

    async def clear_cache(self):
        """Clear the cache"""
        self._cache.clear()
        self._logger.info("🧹 FastCandleCollector cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys())
        }
    
# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Candle
    "CandleBuilder",
    "CandleStorage",
    "MemoryCandleStorage",
    # Deals
    "DealsStorage",
    "MemoryDealsStorage",
    # Trades
    "TradeStorage",
    "Trade",
    "TradeStatus",
    # Fast Collector
    "FastCandleCollector",  # ✅ add this
]