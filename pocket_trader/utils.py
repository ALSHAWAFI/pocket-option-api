"""
Utility functions for PocketTrader
"""

import contextlib
import inspect
import random
import time
import logging
import struct
import asyncio
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Union, List, Callable, TypeVar, cast
from pathlib import Path

import pytz

from .constants import TIMESTAMP_OFFSET

# Type aliases
T = TypeVar('T')
JsonValue = Union[int, float, str, bool, None, Dict[str, Any], List[Any]]


# ============== Random Generator ==============
_rnd = random.SystemRandom()


# ============== Logging ==============

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Setup a logger with consistent formatting
    """
    logger = logging.getLogger(f"pocket_trader.{name}")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False
    
    return logger


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup global logging configuration
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        Path(log_file).parent.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )


# ============== Function Helpers ==============

def get_function_full_name(fn: Callable) -> str:
    """
    Get full qualified name of a function
    """
    if inspect.isclass(fn):
        return fn.__name__ + ".__init__"
    if hasattr(fn, '__module__') and fn.__module__:
        return f"{fn.__module__}.{fn.__qualname__}"
    return fn.__qualname__


# ============== JSON Helpers ==============

class JsonFunction:
    """Protocol for JSON functions"""
    
    def dumps(self, value: JsonValue, **kwargs) -> str:
        """Serialize to JSON string"""
        raise NotImplementedError
    
    def loads(self, value: Union[str, bytes]) -> JsonValue:
        """Deserialize from JSON string/bytes"""
        raise NotImplementedError


def get_json_function() -> JsonFunction:
    """
    Get the best available JSON function (ujson > orjson > json)
    """
    
    # Try ujson first (fastest)
    with contextlib.suppress(ImportError):
        import ujson
        
        class _UJson(JsonFunction):
            def loads(self, value: Union[str, bytes]) -> JsonValue:
                return cast(JsonValue, ujson.loads(value))
            
            def dumps(self, value: JsonValue, **kwargs) -> str:
                return ujson.dumps(value, ensure_ascii=False, **kwargs)
        
        return _UJson()
    
    # Try orjson next
    with contextlib.suppress(ImportError):
        import orjson
        
        class _ORJson(JsonFunction):
            def loads(self, value: Union[str, bytes]) -> JsonValue:
                return cast(JsonValue, orjson.loads(value))
            
            def dumps(self, value: JsonValue, **kwargs) -> str:
                return orjson.dumps(value).decode()
        
        return _ORJson()
    
    # Fallback to standard json
    import json
    
    class _Json(JsonFunction):
        def loads(self, value: Union[str, bytes]) -> JsonValue:
            return cast(JsonValue, json.loads(value))
        
        def dumps(self, value: JsonValue, **kwargs) -> str:
            return json.dumps(value, ensure_ascii=False, **kwargs)
    
    return _Json()


# ============== Time Helpers ==============

def fix_timestamp(ts: float) -> float:
    """
    Fix timestamp offset for Pocket Option
    """
    return ts + TIMESTAMP_OFFSET


def format_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format datetime for API (ISO format with timezone)
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt.isoformat()


def timestamp_now() -> int:
    """
    Get current timestamp with offset
    """
    return int(time.time()) + TIMESTAMP_OFFSET


def parse_timestamp(ts: Union[int, float, str]) -> datetime:
    """
    Parse timestamp to datetime
    """
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return datetime.fromtimestamp(float(ts), tz=pytz.UTC)


# ============== ID Generation ==============

def generate_request_id() -> int:
    """
    Generate unique request ID
    """
    return int(time.time() * 1000) + _rnd.randint(1, 1000)


def generate_uuid() -> str:
    """
    Generate UUID string
    """
    import uuid
    return str(uuid.uuid4())


# ============== Binary Parsing ==============

class BinaryParser:
    """
    High-performance binary data parser
    """
    
    _STREAM_STRUCT = struct.Struct('<IdIfffff')
    _CHAFOR_STRUCT = struct.Struct('<BId')
    
    @classmethod
    def parse_stream(cls, data: bytes) -> Dict[str, Any]:
        """
        Parse 39-byte stream data
        """
        if len(data) < 36:
            raise ValueError(f"Invalid stream data length: {len(data)}")
        
        values = cls._STREAM_STRUCT.unpack(data[:36])
        
        return {
            'asset_id': values[0],
            'price': values[1],
            'timestamp': fix_timestamp(values[2]),
            'volume': values[3],
            'change_24h': values[4],
            'bid': values[5],
            'ask': values[6],
            'spread': values[6] - values[5] if values[5] and values[6] else 0,
            'flags': data[36:39].hex() if len(data) >= 39 else ''
        }
    
    @classmethod
    def parse_chafor(cls, data: bytes) -> Dict[str, Any]:
        """
        Parse 19-byte chafor data
        """
        if len(data) < 13:
            raise ValueError(f"Invalid chafor data length: {len(data)}")
        
        values = cls._CHAFOR_STRUCT.unpack(data[:13])
        
        return {
            'signal_type': values[0],
            'asset_id': values[1],
            'price': values[2],
            'extra': data[13:19].hex() if len(data) >= 19 else ''
        }


# ============== Backward compatibility functions ==============

def parse_stream_data(data: bytes) -> Dict[str, Any]:
    """
    Compatibility function - calls BinaryParser.parse_stream
    """
    return BinaryParser.parse_stream(data)


def parse_chafor_data(data: bytes) -> Dict[str, Any]:
    """
    Compatibility function - calls BinaryParser.parse_chafor
    """
    return BinaryParser.parse_chafor(data)


# ============== Number Helpers ==============

def decimal_to_float(d: Union[Decimal, float, str]) -> float:
    """
    Convert Decimal to float safely
    """
    if isinstance(d, Decimal):
        return float(d)
    if isinstance(d, str):
        return float(d)
    return float(d)


def truncate_decimal(value: float, decimals: int = 2) -> float:
    """
    Truncate decimal without rounding
    """
    return float(int(value * 10**decimals) / 10**decimals)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """
    Safe division with zero check
    """
    if b == 0:
        return default
    return a / b


def round_to_step(value: float, step: float) -> float:
    """
    Round value to nearest step
    """
    return round(value / step) * step


# ============== Collection Helpers ==============

def append_or_replace(
    array: Union[List[T], deque],
    item: T,
    eq_by_keys: List[str],
    get_key_method: Callable[[T, str], Any] = getattr,
) -> Union[List[T], deque]:
    """
    Append item or replace if exists with same keys
    """
    for i, it in enumerate(array):
        if all(get_key_method(it, key) == get_key_method(item, key) for key in eq_by_keys):
            array[i] = item
            return array
    array.append(item)
    return array


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_by_key(items: List[Dict], key: str) -> List[Dict]:
    """
    Remove duplicates from list of dicts by key
    """
    seen = set()
    result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


# ============== Async Helpers ==============

async def run_in_executor(func: Callable, *args):
    """
    Run blocking function in executor
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


def create_task_safe(coro):
    """
    Create asyncio task safely
    """
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        # No running loop
        return asyncio.create_task(coro)


async def wait_for_with_progress(coro, timeout: float, check_interval: float = 0.1):
    """
    Wait for coroutine with progress checking
    """
    task = asyncio.create_task(coro)
    elapsed = 0.0
    
    while elapsed < timeout:
        if task.done():
            return task.result()
        
        await asyncio.sleep(check_interval)
        elapsed += check_interval
    
    task.cancel()
    raise TimeoutError(f"Timeout after {timeout}s")


# ============== Validation ==============

def validate_asset(asset: str) -> bool:
    """
    Validate asset symbol format
    """
    if not asset or not isinstance(asset, str):
        return False
    
    if len(asset) > 20:
        return False
    
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.#')
    return all(c in valid_chars for c in asset)


def validate_amount(amount: float, min_amount: float = 1, max_amount: float = 50000) -> bool:
    """
    Validate trade amount
    """
    return min_amount <= amount <= max_amount


def validate_duration(duration: int, min_duration: int = 5, max_duration: int = 43200) -> bool:
    """
    Validate trade duration
    """
    return min_duration <= duration <= max_duration


# ============== Formatting ==============

def format_price(price: float, asset: Optional[str] = None) -> str:
    """
    Format price with appropriate decimal places
    """
    if asset:
        if any(c in asset.upper() for c in ['BTC', 'ETH', 'DASH']):
            return f"{price:.2f}"
        elif len(asset) == 6 and asset.isalpha():
            return f"{price:.5f}"
    
    if price < 0.01:
        return f"{price:.6f}"
    elif price < 1:
        return f"{price:.4f}"
    elif price < 100:
        return f"{price:.2f}"
    else:
        return f"{price:.1f}"


def format_percentage(value: float) -> str:
    """
    Format percentage
    """
    return f"{value:+.2f}%" if value != 0 else "0.00%"


def format_duration(seconds: int) -> str:
    """
    Format duration in human readable form
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"