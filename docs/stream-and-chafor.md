# Stream & Chafor

The Pocket Option protocol carries some messages as **compact binary frames**. PocketTrader parses two of them natively.

| Type | Size | Payload | Class |
|------|------|---------|-------|
| Stream update | 39 bytes | Live price tick | `StreamUpdate` |
| Chafor message | 19 bytes | Signals / candle closes | `ChaforMessage` |

Both are re-exported from the package root, along with their processors.

---

## Stream Update (39 bytes)

### `StreamUpdate`

Parses a 39-byte binary frame:

```
Offset  Type    Field
0       I       asset_id  (uint32)
4       d       price     (double)
12      I       timestamp (uint32)
16      f       volume    (float)
20      f       change_24h
24      f       bid
28      f       ask
32      f       spread
36      3 bytes  flags (hex)
```

Matched by `<IdIfffff` (little-endian). The timestamp is normalized via `fix_timestamp` (handles the platform's `-7200s` offset).

```python
from pocket_trader import StreamUpdate

update = StreamUpdate(raw_bytes)   # bytes of length >= 36

update.asset_id      # int
update.asset         # Asset (id-2-asset mapping resolved elsewhere)
update.price         # float
update.timestamp     # int (fixed epoch seconds)
update.volume        # float
update.change_24h    # float (fraction); use change_percent for %
update.bid / update.ask / update.spread
update.flags         # hex string of last 3 bytes

update.datetime         # datetime
update.change_percent   # change_24h * 100
update.mid_price        # (bid + ask) / 2, or price
update.parsed           # True if successfully parsed
```

If the payload is too short (< 36 bytes), it logs a warning and leaves `parsed=False`.

### `StreamProcessor`

Collects updates per asset with price history, staleness detection, OHLC snapshots, and batch callbacks.

```python
from pocket_trader import StreamProcessor

proc = StreamProcessor(max_history=1000)

async def on_update(asset, update):
    print(asset, update.price)

async def on_batch(batch):                   # {asset: [StreamUpdate, ...]}
    ...

proc.add_callback(on_update)                 # plain registration (returns None)
proc.add_batch_callback(on_batch)

proc.enable_batch_mode(interval_ms=100)      # flushes batches every 100ms
await proc.process(asset, update)            # feed a StreamUpdate
```

Querying:

| Method | Returns |
|--------|---------|
| `get_last_price(asset)` | Latest price or `None` |
| `get_last_update_time(asset)` | `time.time()` of last update |
| `get_price_history(asset, count)` | Last N prices |
| `get_update_history(asset, count)` | Last N `StreamUpdate`s |
| `get_price_at_time(asset, ts)` | Closest price to a timestamp |
| `get_ohlc(asset, period_seconds=60)` | `{open, high, low, close, volume}` |
| `is_stale(asset, max_age=5.0)` | No update recently |
| `get_all_assets()` / `get_active_assets(max_age=5.0)` | Tracked / fresh assets |
| `get_market_summary()` | Per-asset `{price, change_20, stale, last_update}` |
| `clear_asset(asset)` / `clear_all()` | Reset |

Callbacks are added with `add_callback` / `add_batch_callback` (plain registration — they return `None`, so they are **not** decorators).

---

## Chafor Message (19 bytes)

### `ChaforMessage`

Parses a 19-byte frame:

```
Offset  Type     Field
0       uint8    signal_type
1       uint32   asset_id
5       double   price
13      6 bytes   extra
```

```python
from pocket_trader import ChaforMessage

msg = ChaforMessage(raw_bytes)

msg.signal_type      # int
msg.asset_id         # int
msg.asset            # Asset (if resolvable)
msg.price            # float
msg.extra            # remaining bytes
msg.signal_name      # "STRONG_BUY" | ... | "UNKNOWN_n"
msg.is_trading_signal  # STRONG_BUY or STRONG_BREAKOUT
msg.is_candle_close    # CANDLE_CLOSE
msg.is_warning         # WARNING
```

Signal types (see `SIGNAL_TYPES` in `constants`):

| Code | Name | Meaning |
|------|------|---------|
| 1 | `STRONG_BUY` | Strong buy signal |
| 2 | `CANDLE_CLOSE` | A candle has closed |
| 3 | `MEDIUM_INDICATOR` | Medium-strength indicator |
| 4 | `WARNING` | Warning |
| 5 | `STRONG_BREAKOUT` | Strong breakout signal |

### `ChaforProcessor`

Converts chafor messages into candles (on `CANDLE_CLOSE`) and routes signals/warnings to callbacks.

```python
from pocket_trader import ChaforProcessor, ChaforMessage

proc = ChaforProcessor(max_candles=100)

async def on_signal(msg: ChaforMessage):
    print("Signal:", msg.signal_name, msg.asset_id)

async def on_candle(asset, candle):
    print("Candle closed:", asset, candle.close)

async def on_warning(msg):
    print("Careful:", msg)

proc.add_signal_callback(on_signal)
proc.add_candle_callback(on_candle)
proc.add_warning_callback(on_warning)

await proc.process(ChaforMessage(raw_bytes))   # feed a message
```

Querying:

| Method | Returns |
|--------|---------|
| `get_last_candle(asset)` | Most recent candle |
| `get_candles(asset, count=None)` | Last N candles |
| `get_last_signal(asset)` | Last trading signal |
| `get_signals(asset=None, signal_type=None, count=100)` | Filtered signals |
| `get_signal_stats()` | Totals by type + per-asset candle counts |
| `clear()` | Reset everything |

---

## Wiring into the client

The client itself does **not** auto-parse binary frames into `StreamUpdate`/`ChaforMessage` — these are standalone parsers for raw binary data. You wire them yourself.

The client's `update_close_value` event delivers price updates as **dict items**, which is usually all you need:

```python
@client.on.update_close_value
async def on_price(items):
    for item in items:
        # item is a dict: {"asset": "EURUSD", "timestamp": 123.4, "value": 1.2345}
        latest[item["asset"]] = item["value"]
```

To use the binary parsers, feed them raw 39/19-byte frames from a binary source:

```python
from pocket_trader import StreamUpdate, StreamProcessor, ChaforMessage, ChaforProcessor

processor = StreamProcessor()
await processor.process(asset, StreamUpdate(raw_39_bytes))

cp = ChaforProcessor()
await cp.process(ChaforMessage(raw_19_bytes))
```

> The generated `client.on.*` surface has **no** `stream_update`, `stream_update_raw`, `chafor_message`, or `chafor_message_raw` handlers. If your endpoint emits raw binary frames through the socket, route them by subclassing `PocketOptionClient` and overriding `_on_any_event` (see [Client](client.md)).

---

Next: [Middleware](middleware.md) · [Caching](caching.md) · [Client & Connection](client.md)