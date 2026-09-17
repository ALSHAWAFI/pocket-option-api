# Middleware

Middleware run in the client's inbound/outbound pipeline, letting you log, transform, fix, throttle, or measure every event without touching core code.

All middleware extend the base `Middleware` class and are re-exported from the package root.

---

## Pipeline hooks

Each middleware may implement any of these async hooks:

| Hook | In/Out | Signature | Purpose |
|------|--------|-----------|---------|
| `on_raw` | inbound | `(event: str, data: bytes) -> Optional[bytes]` | Operate on raw bytes before parsing |
| `on` | inbound | `(event: str, data: Any) -> Optional[Any]` | Transform parsed/JSON data |
| `on_emit` | outbound | `(event: str, data) -> Tuple[str, Optional[Any]]` | Transform outgoing emits |
| `on_error` | error | `(event: str, error: Exception, data=None)` | Observe handler errors |

Returning `None` from `on` **drops** the event from further processing (used by throttling).

---

## Base class

```python
from pocket_trader import Middleware

class MyMiddleware(Middleware):
    async def on(self, event: str, data: Any) -> Optional[Any]:
        # `event` is the *socket* event name, e.g. "updateStream"
        if event == "updateStream":
            # transform data...
            data = ...
        return data
```

---

## Built-in middlewares

### `LoggingMiddleware`

```python
from pocket_trader import LoggingMiddleware

LoggingMiddleware(log_raw=False, log_parsed=True)
```

- `log_raw=True` — logs inbound raw byte sizes.
- `log_parsed=True` — logs parsed inbound events (list events are summarized by length).

### `MakeJsonOnMiddleware`

Parses `str`/`bytes` payloads into JSON objects on the `on` hook.

```python
from pocket_trader import MakeJsonOnMiddleware
MakeJsonOnMiddleware()
```

### `FixTypesOnMiddleware`

Normalizes specific event payloads:

- `pong` / `ping-server` → calls `conn_manager.update_last_pong()` when a client is attached.
- `updateStream` → converts `[asset, timestamp, value, ...]` tuples into `{"asset", "timestamp", "value"}` dicts, with timestamps fixed via `fix_timestamp`.

```python
from pocket_trader import FixTypesOnMiddleware
FixTypesOnMiddleware()
```

### `StatsMiddleware`

Collects per-event counters for diagnostics.

```python
from pocket_trader import StatsMiddleware

mw = StatsMiddleware()
mw.get_stats()
# {"uptime": 12.4, "total_events": 500, "events_per_second": 40.3,
#  "by_event": {"updateStream": {"count": 400, "first_seen": ..., "last_seen": ...}}}
mw.reset()
```

### `ThrottleMiddleware`

Drops events exceeding a rate (default: `updateStream` and `chafor`, 100ms apart).

```python
from pocket_trader import ThrottleMiddleware

ThrottleMiddleware(throttle_ms=100, events=["updateStream", "chafor"])
```

---

## Usage

Pass a list of middlewares to the client constructor; they run in order.

```python
from pocket_trader import (
    PocketOptionClient, LoggingMiddleware, MakeJsonOnMiddleware,
    FixTypesOnMiddleware, StatsMiddleware, ThrottleMiddleware,
)

client = PocketOptionClient(middlewares=[
    ThrottleMiddleware(throttle_ms=200),   # 1. throttle
    MakeJsonOnMiddleware(),                # 2. parse JSON
    FixTypesOnMiddleware(),                # 3. fix types
    LoggingMiddleware(log_parsed=True),    # 4. log
    StatsMiddleware(),
])
```

> **Default pipeline:** when `middlewares=None`, the client uses `[MakeJsonOnMiddleware(), FixTypesOnMiddleware()]` (see `client.py:363`). The middleware instances are stored on `client.middlewares`.

Typical order: **throttle → parse → fix types → log**.

---

## Writing a custom transformer

```python
from pocket_trader import Middleware

class RoundPricesMiddleware(Middleware):
    async def on(self, event, data):
        if event == "updateStream" and isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "value" in item:
                    item["value"] = round(item["value"], 3)
        return data
```

---

Next: [Exceptions](exceptions.md) · [Client & Connection](client.md) · [Stream & Chafor](stream-and-chafor.md)