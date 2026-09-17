import collections.abc
import typing
from typing import TypeVar, Union, Dict, List, Any, Callable, Awaitable, Optional

__all__ = (
    "EmitCallback", 
    "JsonFunction", 
    "JsonValue", 
    "SIOEventListener", 
    "TypedEventListener",
    "PriceType",
    "IndicatorType",
    "CandlePeriod",
)

# ============== JSON Types ==============
JsonValue = Union[int, float, str, bool, None, Dict[str, Any], List[Any]]
"""JSON serializable value type"""


class JsonFunction(typing.Protocol):
    """Protocol for JSON functions (like json, ujson, orjson)"""
    
    def dumps(self, value: JsonValue, *, separators: tuple[str, str] | None = None) -> str:
        """Serialize to JSON string"""
        ...
    
    def loads(self, value: str | bytes) -> JsonValue:
        """Deserialize from JSON string/bytes"""
        ...


# ============== Callback Types ==============
EmitCallback = Union[
    Callable[[str, int, JsonValue], None],
    Callable[[str, int, JsonValue], Awaitable[None]]
]
"""Callback type for emit responses"""

SIOEventListener = Union[
    Callable[..., None],
    Callable[..., Awaitable[None]]
]
"""Socket.IO event listener type"""

T = TypeVar('T')
TypedEventListener = Union[
    Callable[[T], None],
    Callable[[T], Awaitable[None]]
]
"""Typed event listener for specific data type"""


# ============== Trading Types ==============
class PriceType:
    """Price types for indicators"""
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    HL2 = "hl2"  # (high+low)/2
    HLC3 = "hlc3"  # (high+low+close)/3
    OHLC4 = "ohlc4"  # (open+high+low+close)/4


class IndicatorType:
    """Indicator types"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OSCILLATOR = "oscillator"


class CandlePeriod:
    """Common candle periods in seconds"""
    M1 = 60
    M5 = 300
    M15 = 900
    M30 = 1800
    H1 = 3600
    H4 = 14400
    D1 = 86400
    W1 = 604800
    
    @classmethod
    def from_string(cls, period: str) -> int:
        """Convert string period to seconds"""
        mapping = {
            '1m': cls.M1, '5m': cls.M5, '15m': cls.M15, '30m': cls.M30,
            '1h': cls.H1, '4h': cls.H4, '1d': cls.D1, '1w': cls.W1,
        }
        return mapping.get(period.lower(), cls.M1)