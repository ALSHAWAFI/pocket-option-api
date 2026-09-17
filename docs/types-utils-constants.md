# Types, Utils & Constants

Reference for the supporting modules: type aliases/protocols (`types.py`), helpers (`utils.py`), and configuration constants (`constants.py`).

---

## Types (`pocket_trader.types`)

### JSON types

```python
from pocket_trader import JsonValue
from pocket_trader.types import JsonFunction

# JsonValue: Any JSON-serializable value:
#   int | float | str | bool | None | Dict[str, Any] | List[Any]
```

`JsonFunction` is a typing **Protocol** describing any JSON module exposing `dumps(value, *, separators=None)` and `loads(value)`. `json`, `ujson`, and `orjson` all satisfy it. (Note: `JsonFunction` lives in `pocket_trader.types` — only `JsonValue` is re-exported from the package root.)

### Callback types

```python
from pocket_trader import EmitCallback, SIOEventListener, TypedEventListener

EmitCallback       # Callable[[str, int, JsonValue], Awaitable|None]
SIOEventListener   # Callable[..., Awaitable|None]
TypedEventListener # Callable[[T], Awaitable|None]
```

Used by the client to type event/emit handlers.

### Trading constants

```python
from pocket_trader import PriceType, IndicatorType, CandlePeriod

PriceType.OPEN / HIGH / LOW / CLOSE / HL2 / HLC3 / OHLC4
IndicatorType.TREND / MOMENTUM / VOLATILITY / VOLUME / OSCILLATOR

CandlePeriod.M1 / M5 / M15 / M30 / H1 / H4 / D1 / W1
CandlePeriod.from_string("1m")   # 60
```

---

## Utils (`pocket_trader.utils`)

### Logging

```python
from pocket_trader import setup_logger, setup_logging

setup_logging(level="INFO", log_file="trader.log")
logger = setup_logger("MyBot", level="DEBUG")
```

- `setup_logging(level, log_file=None)` — global `basicConfig`.
- `setup_logger(name, level="INFO")` — child logger `pocket_trader.<name>`.

### Timestamps

```python
from pocket_trader import fix_timestamp, format_datetime

fix_timestamp(1726760000)      # + TIMESTAMP_OFFSET (-7200)
format_datetime()              # ISO-8601 UTC string of now
```

- `fix_timestamp(ts)` adds the platform offset so server timestamps align with real epoch.
- `format_datetime(dt=None)` → ISO string (UTC if naive).

### IDs & parsing

```python
from pocket_trader import generate_request_id, parse_stream_data, parse_chafor_data

request_id = generate_request_id()        # unique increasing int
stream = parse_stream_data(raw_bytes)     # 39-byte → dict
chafor = parse_chafor_data(raw_bytes)     # 19-byte → dict
```

These mirror the `StreamUpdate` / `ChaforMessage` objects but return plain dicts (see [Stream & Chafor](stream-and-chafor.md)).

### Formatting

```python
from pocket_trader import format_price, format_percentage, format_duration

format_price(1.094556, "EURUSD")  # "1.09456" (5 dp for 6-letter pairs)
format_price(0.00000123, "BTCUSD")# "0.00" for crypto, high precision for small prices
format_percentage(2.5)            # "+2.50%"
format_duration(3661)             # "1h"
```

### Validation

```python
from pocket_trader import validate_asset, validate_amount, validate_duration

validate_asset("EURUSD_otc")   # True
validate_amount(10)            # True  (1..50_000)
validate_duration(60)          # True  (5..43_200)
```

### Collection & async helpers

```python
from pocket_trader.utils import (
    append_or_replace, chunk_list, deduplicate_by_key,
    run_in_executor, create_task_safe, wait_for_with_progress,
    safe_divide, round_to_step, truncate_decimal, decimal_to_float,
)
```

---

## Constants (`pocket_trader.constants`)

### Version

```python
from pocket_trader import VERSION, __version__

VERSION          # "2.0.0"
__version__      # "2.0.0"
__version_info__ # (2, 0, 0)
```

### Trading limits

| Constant | Value | Meaning |
|----------|-------|---------|
| `API_LIMITS_MIN_ORDER_AMOUNT` | `1` | Minimum trade amount |
| `API_LIMITS_MAX_ORDER_AMOUNT` | `50_000` | Maximum trade amount |
| `API_LIMITS_MIN_DURATION` | `5` | Minimum duration (s) |
| `API_LIMITS_MAX_DURATION` | `43_200` | Maximum duration (12h) |
| `API_LIMITS_MAX_CONCURRENT_ORDERS` | `10` | Max open orders |
| `API_LIMITS_RATE_LIMIT` | `100` | Max requests/second |

### Network

```python
from pocket_trader import DEFAULT_ORIGIN, DEFAULT_USER_AGENT
DEFAULT_ORIGIN       # "https://m.pocketoption.com"
DEFAULT_USER_AGENT   # Firefox UA string
```

### Connection settings

| Constant | Value | Used by |
|----------|-------|---------|
| `DEFAULT_RECONNECTION_ATTEMPTS` | `50` | reconnect tries |
| `DEFAULT_RECONNECTION_DELAY` | `2` | initial backoff |
| `DEFAULT_RECONNECTION_DELAY_MAX` | `30` | max backoff |
| `MAX_RECONNECT_BACKOFF` | `60` | backoff ceiling |
| `HEARTBEAT_INTERVAL` | `15` | seconds between pings |
| `WATCHDOG_INTERVAL` | `10` | seconds between liveness checks |
| `DATA_TIMEOUT` | `30` | no-data threshold |
| `PONG_TIMEOUT` | `20` | missing-pong threshold |

### Message sizes

```python
from pocket_trader import MESSAGE_SIZES

MESSAGE_SIZES.STREAM     # 39 bytes
MESSAGE_SIZES.CHAFOR     # 19 bytes
MESSAGE_SIZES.HEARTBEAT  # 1 byte
```

### Signal types

```python
from pocket_trader import SIGNAL_TYPES

SIGNAL_TYPES.STRONG_BUY      # 1
SIGNAL_TYPES.CANDLE_CLOSE    # 2
SIGNAL_TYPES.MEDIUM_INDICATOR# 3
SIGNAL_TYPES.WARNING         # 4
SIGNAL_TYPES.STRONG_BREAKOUT # 5
SIGNAL_TYPES.NAMES           # {1: "STRONG_BUY", ...}
```

### Regions

```python
from pocket_trader import Regions

Regions.DEMO          # "wss://demo-api-eu.po.market"
Regions.EUROPA        # "wss://api-eu.po.market"
Regions.get_url("demo")  # friendly lookup
```

See [Getting Started](getting-started.md) for the full table.

### Asset categories

```python
from pocket_trader import AssetCategory

AssetCategory.FOREX / COMMODITIES / CRYPTO / INDICES / STOCKS
AssetCategory.OTC_FOREX / OTC_COMMODITIES / OTC_INDICES / OTC_STOCKS
AssetCategory.get_category("EURUSD_otc")   # "forex"
```

### Timeframes

```python
from pocket_trader import TIMEFRAMES
TIMEFRAMES  # {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
            #  "4h": 14400, "1d": 86400, "1w": 604800}
```

---

Next: [Getting Started](getting-started.md) · [Exceptions](exceptions.md) · [README](../README.md)