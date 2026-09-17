"""
Chafor message handling (19-byte signals/candles)
"""

import struct
from typing import Optional, Dict, List, Callable, Awaitable, Any
from datetime import datetime
import asyncio

from .models import Asset, Candle
from .utils import setup_logger
from .constants import SIGNAL_TYPES


class ChaforMessage:
    """
    19-byte chafor message - mysterious signals/candles
    Structure based on analysis:
    - Byte 0: signal_type (uint8)
    - Bytes 1-4: asset_id (uint32)
    - Bytes 5-12: price (double)
    - Bytes 13-18: extra data (6 bytes)
    """
    
    def __init__(self, data: bytes):
        self.raw_data = data
        self.parsed = False
        self.signal_type: Optional[int] = None
        self.asset_id: Optional[int] = None
        self.asset: Optional[Asset] = None
        self.price: Optional[float] = None
        self.extra: bytes = b''
        self._logger = setup_logger("ChaforMessage")
        
        self._parse()
    
    def _parse(self):
        """Parse 19-byte binary data"""
        try:
            if len(self.raw_data) >= 13:
                self.signal_type = self.raw_data[0]
                self.asset_id = struct.unpack('<I', self.raw_data[1:5])[0]
                self.price = struct.unpack('<d', self.raw_data[5:13])[0]
                self.extra = self.raw_data[13:19] if len(self.raw_data) >= 19 else b''
                self.parsed = True
            else:
                self._logger.warning(f"Invalid chafor data length: {len(self.raw_data)}")
                
        except struct.error as e:
            self._logger.error(f"Chafor parse error: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}")
    
    @property
    def signal_name(self) -> str:
        """Get signal type name"""
        return SIGNAL_TYPES.NAMES.get(self.signal_type, f"UNKNOWN_{self.signal_type}")
    
    @property
    def is_trading_signal(self) -> bool:
        """Check if this is a trading signal"""
        return self.signal_type in [SIGNAL_TYPES.STRONG_BUY, SIGNAL_TYPES.STRONG_BREAKOUT]
    
    @property
    def is_candle_close(self) -> bool:
        """Check if this is a candle close"""
        return self.signal_type == SIGNAL_TYPES.CANDLE_CLOSE
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning"""
        return self.signal_type == SIGNAL_TYPES.WARNING
    
    def __repr__(self) -> str:
        if not self.parsed:
            return f"ChaforMessage(raw={self.raw_data.hex()})"
        return (f"ChaforMessage(type={self.signal_name}, "
                f"asset_id={self.asset_id}, price={self.price:.5f})")


class ChaforProcessor:
    """
    Process chafor messages and convert to candles/signals
    """
    
    def __init__(self, max_candles: int = 100):
        self.max_candles = max_candles
        self._messages: List[ChaforMessage] = []
        self._candles: Dict[Asset, List[Candle]] = {}
        self._signals: Dict[Asset, List[ChaforMessage]] = {}
        self._signal_callbacks: List[Callable[[ChaforMessage], Awaitable[None]]] = []
        self._candle_callbacks: List[Callable[[Asset, Candle], Awaitable[None]]] = []
        self._warning_callbacks: List[Callable[[ChaforMessage], Awaitable[None]]] = []
        self._last_candle: Dict[Asset, Candle] = {}
        self._last_signal: Dict[Asset, ChaforMessage] = {}
        self._logger = setup_logger("ChaforProcessor")
    
    def add_signal_callback(self, callback: Callable[[ChaforMessage], Awaitable[None]]):
        """Add callback for trading signals"""
        self._signal_callbacks.append(callback)
    
    def add_candle_callback(self, callback: Callable[[Asset, Candle], Awaitable[None]]):
        """Add callback for candle closes"""
        self._candle_callbacks.append(callback)
    
    def add_warning_callback(self, callback: Callable[[ChaforMessage], Awaitable[None]]):
        """Add callback for warnings"""
        self._warning_callbacks.append(callback)
    
    async def process(self, message: ChaforMessage):
        """Process a chafor message"""
        try:
            # Store message
            self._messages.append(message)
            if len(self._messages) > 1000:
                self._messages = self._messages[-1000:]
            
            # Handle by type
            if message.is_trading_signal:
                await self._handle_signal(message)
            elif message.is_candle_close:
                await self._handle_candle_close(message)
            elif message.is_warning:
                await self._handle_warning(message)
            
            # Store by asset
            if message.asset:
                if message.asset not in self._signals:
                    self._signals[message.asset] = []
                
                self._signals[message.asset].append(message)
                if len(self._signals[message.asset]) > 100:
                    self._signals[message.asset] = self._signals[message.asset][-100:]
                
                if message.is_trading_signal:
                    self._last_signal[message.asset] = message
                    
        except Exception as e:
            self._logger.error(f"Error processing chafor: {e}")
    
    async def _handle_signal(self, message: ChaforMessage):
        """Handle trading signal"""
        self._logger.info(f"📊 Trading signal: {message.signal_name} for asset {message.asset_id}")
        
        for callback in self._signal_callbacks:
            try:
                await callback(message)
            except Exception as e:
                self._logger.error(f"Signal callback error: {e}")
    
    async def _handle_candle_close(self, message: ChaforMessage):
        """Handle candle close and create candle"""
        if not message.asset or not message.price:
            return
        
        # Create candle
        candle = Candle(
            asset=message.asset,
            timestamp=datetime.now(),
            timeframe=60,  # Default 1-minute
            open=message.price,
            high=message.price,
            low=message.price,
            close=message.price
        )
        
        # Store candle
        if message.asset not in self._candles:
            self._candles[message.asset] = []
        
        self._candles[message.asset].append(candle)
        self._last_candle[message.asset] = candle
        
        # Keep only max_candles
        if len(self._candles[message.asset]) > self.max_candles:
            self._candles[message.asset] = self._candles[message.asset][-self.max_candles:]
        
        self._logger.debug(f"🕯️ Candle closed for {message.asset} at {message.price:.5f}")
        
        # Call callbacks
        for callback in self._candle_callbacks:
            try:
                await callback(message.asset, candle)
            except Exception as e:
                self._logger.error(f"Candle callback error: {e}")
    
    async def _handle_warning(self, message: ChaforMessage):
        """Handle warning message"""
        self._logger.warning(f"⚠️ Warning signal: {message}")
        
        for callback in self._warning_callbacks:
            try:
                await callback(message)
            except Exception as e:
                self._logger.error(f"Warning callback error: {e}")
    
    def get_last_candle(self, asset: Asset) -> Optional[Candle]:
        """Get last candle for asset"""
        return self._last_candle.get(asset)
    
    def get_candles(self, asset: Asset, count: Optional[int] = None) -> List[Candle]:
        """Get candles for asset"""
        candles = self._candles.get(asset, [])
        if count:
            return candles[-count:]
        return candles
    
    def get_last_signal(self, asset: Asset) -> Optional[ChaforMessage]:
        """Get last signal for asset"""
        return self._last_signal.get(asset)
    
    def get_signals(self, asset: Optional[Asset] = None, 
                   signal_type: Optional[int] = None,
                   count: int = 100) -> List[ChaforMessage]:
        """Get recent signals"""
        messages = self._messages
        
        if asset:
            messages = [m for m in messages if m.asset == asset]
        if signal_type is not None:
            messages = [m for m in messages if m.signal_type == signal_type]
        
        return messages[-count:]
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal statistics"""
        stats = {
            'total_messages': len(self._messages),
            'signals_by_type': {},
            'assets_with_signals': len(self._signals),
            'candles_by_asset': {str(a): len(c) for a, c in self._candles.items()}
        }
        
        # Count by signal type
        for msg in self._messages:
            if msg.signal_type:
                name = msg.signal_name
                stats['signals_by_type'][name] = stats['signals_by_type'].get(name, 0) + 1
        
        return stats
    
    def clear(self):
        """Clear all stored data"""
        self._messages.clear()
        self._candles.clear()
        self._signals.clear()
        self._last_candle.clear()
        self._last_signal.clear()
        self._logger.info("🧹 Processor cleared")