# Client & Connection

The client is the heart of PocketTrader. It is built as a typed layer over `python-socketio`'s async client and handles connection lifecycle, authentication, event dispatch, rate limiting, reconnection, and heartbeat/watchdog monitoring.

---

## Classes

| Class | Purpose |
|-------|---------|
| `BasePocketOptionClient` | Socket.IO connection management (connect, disconnect, event routing, weight/health handling) |
| `PocketOptionClient` | Public API client: wiring, lifecycle helpers, retry, rate limiting, reconnection |
| `RateLimiter` | Token-bucket rate limiter (default 100 req/s) |
| `RetryManager` | Smart retry of transient operations |
| `ConnectionManager` | Tracks connection state and URL selection |

Import:

```python
from pocket_trader import PocketOptionClient, Regions, Asset
from pocket_trader.client import RateLimiter, RetryManager, ConnectionManager
```

---

## Constructing the Client

```python
from pocket_trader import PocketOptionClient

client = PocketOptionClient(
    middlewares=None,             # list of Middleware; defaults to
                                  #  [MakeJsonOnMiddleware(), FixTypesOnMiddleware()]
    # --- socket.IO options ---
    reconnection=True,            # socket-level reconnection
    reconnection_attempts=0,      # 0 = unlimited
    reconnection_delay=1.0,
    reconnection_delay_max=5.0,
    randomization_factor=0.5,
    logger=False,                 # enable socket.IO logging
    engineio_logger=False,
    json=None,                    # JSON module (json/ujson/orjson)
    handle_sigint=True,           # graceful Ctrl+C shutdown
    request_timeout=5,            # seconds for socket requests
    http_session=None,            # optional aiohttp session
    ssl_verify=True,
    websocket_extra_options=None,
    timestamp_requests=False,
    # --- PocketTrader extras ---
    rate_limit=100,               # requests per second budget
    rate_limit_per_seconds=1,
    max_retries=3,                # RetryManager retries
)
```

Key attributes set in the constructor:

| Attribute | Meaning |
|-----------|---------|
| `authorization_data` | `models.AuthorizationData` or `None` until auth |
| `middlewares` | ordered inbound/outbound pipeline |
| `json` | active JSON module |
| `_rate_limiter` | `RateLimiter` instance |
| `_retry_manager` | `RetryManager` instance |
| `sio` | underlying `socketio.AsyncClient` |
| `conn_manager` | `ConnectionManager` for state/heartbeat |
| `on` / `emit` | typed event/emit facades |

---

## Connecting

Pass the WebSocket URL (a `Regions` value or a raw URL string). The default `Origin` and `User-Agent` headers are set automatically.

```python
await client.connect(Regions.DEMO)                    # by region enum value (a URL string)
await client.connect("wss://api-eu.po.market")        # by raw URL
await client.connect(Regions.get_url("demo"))         # by name lookup
```

Signature:

```python
async def connect(
    url: str,                                # WebSocket URL
    headers: Optional[Dict[str, str]] = None,
    auth: Optional[models.AuthorizationData] = None,  # optional socket.IO auth
    wait: bool = True,                       # block until connected (or timeout)
    wait_timeout: float = 30,                # seconds to wait
    retry: bool = False,                     # retry connect attempts
) -> None:
```

Disconnecting:

```python
await client.disconnect()
```

Connection state is exposed through the connection manager:

```python
from pocket_trader.client import ConnectionState

client.conn_manager.state      # ConnectionState.CONNECTED / ...
```

The public `PocketOptionClient` uses the built-in `ConnectionManager` created in `__init__`; to customize monitoring, replace `client.conn_manager` with your own `ConnectionManager(client, ConnectionConfig(...))`.

---

## Authentication

After connecting, send credentials with `emit.auth`:

```python
await client.emit.auth({
    "session": "<your-session-id>",
    "isDemo": 1,                      # 1 = demo, 0 = real
    "uid": 0,                         # your numeric user id
    "platform": 2,
    "isFastHistory": True,
    "isOptimized": True,
})
```

Wait for confirmation:

```python
@client.on.success_auth
async def on_auth(data):
    client.authenticated = True
    print("Authenticated:", data)
```

> `client.emit.auth` expects the raw payload dict; it maps to the `"auth"` socket event.

---

## Events (`client.on.*`)

Register handlers with `@client.on.<event>` (decorator) or `client.on.<event>(handler)` (direct). Handlers are sync or async callables.

> **Handler payloads:** the socket is consumed through a catch-all `on("*")` handler, so callbacks receive the **parsed JSON payloads** (usually `dict` / `list`) produced by the middleware pipeline — **not** auto-validated Pydantic models. The `model=` recorded by each generated handler is informational; validate manually with the [type adapters](models.md#type-adapters) or the models in [Models](models.md) when you need typed objects. The "model / shape" column below is the intended shape.

The full set is generated from [`generator/events.json`](generator.md). Current handlers:

| Handler | Socket event | Model / shape |
|---------|--------------|---------------|
| `on.connect` | `connect` | `None` |
| `on.connecting` | `connecting` | `None` |
| `on.connect_error` | `connect_error` | `None` |
| `on.disconnect` | `disconnect` | `None` |
| `on.reconnect` | `reconnect` | `None` |
| `on.reconnecting` | `reconnecting` | `None` |
| `on.reconnect_attempt` | `reconnect_attempt` | `None` |
| `on.reconnect_error` | `reconnect_error` | `None` |
| `on.reconnect_failed` | `reconnect_failed` | `None` |
| `on.error` | `error` | `None` |

### Account & market data

| Handler | Socket event | Model / shape |
|---------|--------------|---------------|
| `on.success_auth` | `successauth` | `SuccessAuthEvent` |
| `on.update_balance` | `successupdateBalance` | `SuccessUpdateBalanceEvent` |
| `on.update_close_value` | `updateStream` | `list[dict]` — `{asset, timestamp, value}` |
| `on.update_history_new_fast` | `updateHistoryNewFast` | `UpdateHistoryFastEvent` |
| `on.update_assets` | `updateAssets` | `list[UpdateAssetItem]` |
| `on.change_market_sentiment` | `changeMarketSentiment` | `list[MarketSentimentItem]` |
| `on.update_charts` | `updateCharts` | `list` |
| `on.update_indicators` | `updateIndicators` | `dict` |
| `on.update_favorites` | `updateFavorites` | `list` |
| `on.update_price_alerts` | `updatePriceAlerts` | `list` |

### Trading

| Handler | Socket event | Model / shape |
|---------|--------------|---------------|
| `on.success_open_deal` | `successopenOrder` | `Deal` |
| `on.success_close_deal` | `successCloseOrder` | `SuccessCloseDealEvent` |
| `on.success_update_pending` | `successupdatePending` | `list` |
| `on.update_opened_deals` | `updateOpenedDeals` | `list[Deal]` |
| `on.update_closed_deals` | `updateClosedDeals` | `list[Deal]` |

### Meta

| Handler | Socket event | Model / shape |
|---------|--------------|---------------|
| `on.ping_server` | `ping-server` | `None` |
| `on.pong` | `pong` | `None` |

Example (dict access, matching runtime):

```python
@client.on.success_auth
async def on_auth(data):
    print("Authenticated", data)

@client.on.update_balance
async def on_balance(data):
    print("Balance:", data["balance"])

@client.on.success_open_deal
async def on_opened(deal):
    print("Opened:", deal["id"])
```

To get typed objects, validate explicitly:

```python
from pocket_trader import DealListTypeAdapter

@client.on.update_opened_deals
async def on_opened_deals(deals):
    typed = DealListTypeAdapter.validate_python(deals)
    for deal in typed:
        print(deal.id, deal.profit)
```

> `update_close_value` handlers receive the parsed `updateStream` list as dicts. The [binary stream](stream-and-chafor.md) objects (`StreamUpdate`, `ChaforMessage`) are separate parsers you can drive yourself (see [Stream & Chafor](stream-and-chafor.md)).

---

## Emits (`client.emit.*`)

Typed emit methods; each calls `client.send(event, data)` (the underlying `socketio` client).

| Method | Socket event | Payload |
|--------|--------------|---------|
| `ps()` | `ps` | — (heartbeat ping) |
| `indicator_load()` | `indicator/load` | — |
| `favorite_load()` | `favorite/load` | — |
| `price_alert_load()` | `price-alert/load` | — |
| `auth(data)` | `auth` | `AuthorizationData` / dict |
| `subscribe_to_asset(asset)` | `subscribeSymbol` | `Asset` |
| `unsubscribe_from_asset(asset)` | `unsubscribeSymbol` | `Asset` |
| `subscribe_for_market_sentiment(asset)` | `subfor` | `Asset` |
| `unsubscribe_for_market_sentiment(asset)` | `unsubfor` | `Asset` |
| `change_asset(data)` | `changeSymbol` | `ChangeAssetRequest` |
| `open_deal(data)` | `openOrder` | `OpenDealRequest` |
| `close_deal(deal_id)` | `closeOrder` | `str` |
| `cancel_pending_deal(deal_id)` | `cancelPendingOrder` | `str` |
| `copy_signal(data)` | `copySignalOrder` | `CopySignalRequest` |
| `get_candles(data)` | `getCandles` | `dict` |
| `get_history(data)` | `getHistory` | `dict` |
| `get_assets()` | `getAssets` | — |
| `get_balance()` | `getBalance` | — |

```python
await client.emit.auth({
    "session": "<session>", "isDemo": 1, "uid": 0,
    "platform": 2, "isFastHistory": True, "isOptimized": True,
})
await client.emit.subscribe_to_asset(Asset.EURUSD)
await client.emit.open_deal(OpenDealRequest(
    asset=Asset.EURUSD, amount=10, action=DealAction.CALL, time=60,
))
```

`send()` raises on connection failure and rate-limits appropriately.

---

## Rate Limiting

`RateLimiter` is a token-bucket limiter:

```python
from pocket_trader import RateLimiter

limiter = RateLimiter(rate=100, per_seconds=1)   # 100 tokens per second
limiter.acquire()                                  # blocks until a token is free
```

- `rate` — tokens added per second
- `per_seconds` — period
- `stats` — dict with `{hits, misses, wait_time}` counters
- `acquire()` → blocking; `try_acquire()` → non-blocking (returns bool)

The default client uses 100 req/s per `API_LIMITS_RATE_LIMIT`.

---

## Retry & Reconnection

### RetryManager

```python
from pocket_trader.client import RetryManager

retry = RetryManager(max_retries=3, base_delay=1, max_delay=5)
async def op():
    ...
await retry.execute(op)   # retries with exponential backoff on failure
```

`RetryManager` decides *whether* an error is retryable (`_is_retryable`) and backs off exponentially (`_calculate_delay`).

### Reconnection & monitoring

Reconnection and liveness are handled by **`ConnectionManager`** (`client.conn_manager`), which runs:

1. A **heartbeat loop** — sends `ping` every `ConnectionConfig.heartbeat_interval` seconds.
2. A **watchdog loop** — every `ConnectionConfig.watchdog_interval` seconds verifies data is flowing (`data_timeout`) and pongs arrive (`pong_timeout`), triggering `_reconnect` otherwise.
3. **Reconnect** — on drop, reconnects with backoff up to `max_reconnect_attempts`.

Defaults (`ConnectionConfig`): heartbeat 30s, watchdog 15s, data timeout 60s, pong timeout 90s, max reconnect attempts 20, initial delay 3s, max delay 60s, backoff multiplier 1.5.

### Connection state

```python
from pocket_trader.client import ConnectionState

state = client.conn_manager.state    # ConnectionState enum
await client.conn_manager.add_state_listener(async_callback)
client.conn_manager.update_last_data()      # mark activity
client.conn_manager.update_last_pong()
client.conn_manager.stop_monitoring()
```

`ConnectionState` enum values include `CONNECTED`, `CONNECTING`, `RECONNECTING`, `DISCONNECTED`, etc. Subscribe to changes via `add_state_listener(cb)`.

> The legacy `patches.apply_connection_patches()` still exists for backward compatibility but is a no-op in v2 (`client.py` and `patches.py`).

---

## Middleware

Pass middleware in the constructor to transform events:

```python
from pocket_trader import PocketOptionClient, LoggingMiddleware

client = PocketOptionClient(middlewares=[
    LoggingMiddleware(log_parsed=True),
])
```

By default the client wires `[MakeJsonOnMiddleware(), FixTypesOnMiddleware()]`. See [Middleware](middleware.md) for the full pipeline.

---

## Raw Socket Access

If you need raw access to the underlying socket.IO client:

```python
underlying = client.client          # python-socketio AsyncClient
underlying.emit("someEvent", data)  # raw emit
```

---

## Recipes

### Full session skeleton

```python
import asyncio
from pocket_trader import PocketOptionClient, Regions, Asset

async def main():
    client = PocketOptionClient()

    @client.on.connect
    async def on_connect(data):
        print("Connected; authenticating...")
        await client.emit.auth({
            "session": "<session>", "isDemo": 1, "uid": 0,
            "platform": 2, "isFastHistory": True,
        })

    @client.on.success_auth
    async def on_auth(data):
        print("Authenticated")
        await client.emit.subscribe_to_asset(Asset.EURUSD_otc)

    @client.on.update_close_value
    async def on_price(items):
        for item in items:
            print(f"{item['asset']}: {item['value']:0.5f}")

    await client.connect(Regions.DEMO, wait=True, wait_timeout=30)
    try:
        await client.wait()   # run forever until interrupted
    except KeyboardInterrupt:
        await client.disconnect()

asyncio.run(main())
```

### Handling failures

```python
@client.on.error
async def on_error(data):
    print("Socket error:", data)

@client.on.connect_error
async def on_conn_error(data):
    print("Connection error:", data)

@client.on.reconnect_failed
async def on_reconnect_failed(data):
    print("Gave up reconnecting:", data)
```

---

Next: [Trading](trading.md) · [Models](models.md) · [Getting Started](getting-started.md)