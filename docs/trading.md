# Trading

PocketTrader's trading subsystem builds candles from ticks, stores deals, and executes trades — with built-in pattern learning that avoids repeating failed setups.

---

## Overview

```
                    ┌─────────────────────────────────────────────┐
 price ticks ──▶ CandleBuilder    builds OHLCV candles from ticks
                    CandleStorage  abstract candle storage
                    MemoryCandleStorage  in-memory + pattern cache
                    ┌─────────────────────────────────────────────┐
 deals ────────▶ DealsStorage      abstract deal storage
                    MemoryDealsStorage  in-memory + pattern learning
                    ┌─────────────────────────────────────────────┐
 trades ───────▶ TradeStorage      persistent SQLite trade log
                    Trade / TradeStatus
                    ┌─────────────────────────────────────────────┐
 history ──────▶ FastCandleCollector  cached multi-asset collection
```

---

## Candle Building

### `CandleBuilder`

Builds complete `Candle` objects from real-time price ticks for a single asset.

```python
from pocket_trader import CandleBuilder, Asset

builder = CandleBuilder(
    asset=Asset.EURUSD,
    timeframe_seconds=60,   # 1-minute candles
    max_candles=100,        # keep the last 100 completed
)
```

Feed ticks as they arrive (from an `update_close_value` handler):

```python
completed = builder.add_tick(timestamp=time.time(), price=1.0945)
# -> True when a tick closes the current candle and starts a new one
```

Querying:

```python
builder.get_completed_candles(count=50)   # last N completed candles
builder.get_current_candle()               # candle still forming (or None)
builder.get_all_candles()                  # completed + current
builder.get_candle_count()                 # number of completed candles
builder.get_tick_count()                   # ticks in the current candle
```

Hook a callback for each newly completed candle (async, fired via `asyncio.create_task`):

```python
async def on_new_candle(candle):
    print("New candle:", candle.asset, candle.close)

builder.set_on_new_candle(on_new_candle)
```

---

## Candle Storage

### `CandleStorage` (abstract)

Binding of a client to candle storage, auto-registering with `client.on.update_close_value`:

```python
class CandleStorage(abc.ABC):
    def __init__(self, client: 'PocketOptionClient'):
```

### `MemoryCandleStorage`

In-memory candle store with automatic candle building per (asset, timeframe) and a pattern cache for AI analysis.

```python
from pocket_trader import MemoryCandleStorage

storage = MemoryCandleStorage(client, max_size=10000)
```

| Method | Purpose |
|--------|---------|
| `get_candle_builder(asset, timeframe=60)` | Returns/reuses the `CandleBuilder` for that key |
| `get_built_candles(asset, timeframe, count)` | Candles already built from live ticks |
| `get_similar_patterns(asset, timeframe, current_candle, limit=10)` | Similar historical candle patterns (AI) |
| `wait_for_candles(...)` | Blocks until N candles are available (with timeout) |

It listens to the client's `update_close_value` internally, so once attached it keeps building candles automatically.

---

## Deals

### `DealsStorage` (abstract)

Tracks open/close events, learns successful vs failed patterns, and validates trades against API limits.

```python
class DealsStorage(abc.ABC):
    def __init__(self, client: 'PocketOptionClient'):
        self.client.on.success_open_deal(self._on_success_open_deal)
        self.client.on.success_close_deal(self._on_success_close_deal)
        self.client.on.update_opened_deals(...)
        self.client.on.update_closed_deals(...)
```

Constructing a storage automatically wires the client's deal events into it — remember to **create the storage after the client but before opening deals**.

### Opening a deal

```python
deal = await storage.open_deal(
    asset=Asset.EURUSD,
    amount=10,
    action=DealAction.CALL,   # or "call"
    time=60,                  # duration in seconds
    is_demo=1,
    request_id=None,          # auto-generated if not given
    option_type=100,          # standard option
    check_limits=True,        # enforce API limits
)
```

`open_deal` will:

1. Validate the amount/duration against API limits (`DealError` if out of range).
2. Enforce the max concurrent orders limit (default 10 open orders).
3. **Avoid repeating failed patterns** — raises `DealError("pattern_failed", ...)` if a setup resembling a previously failed trade is detected.
4. Emit the `openDeal` request with a unique `request_id`.
5. Block until `success_open_deal` arrives (30s timeout → `DealError("timeout")`).
6. Return the confirmed `Deal`.

### Waiting for the result

```python
result = await storage.check_deal_result(
    wait_time=600,            # seconds to wait for the close event
    deal=deal,                # ...or deal_id / request_id
)
# returns the closed Deal — profit is set on success
```

### Querying deals

```python
deals = await storage.get_deals(
    asset=Asset.EURUSD,
    uid=0,
    closed=True,        # only closed deals
    win=True,           # only winning deals
    count=50,           # last 50
)
one = await storage.get_deal(deal_id=..., request_id=...)
```

### Pattern learning

```python
await storage.learn_from_trade(deal, was_win=True, market_data={"rsi": 70.0})
```

- Winning patterns are stored (last 1000); similar setups are boosted via `get_similar_successful_pattern`.
- Losing patterns become *blocklisted* — trades ≥ 80% similar to a failed pattern are rejected.

---

## Persistent Trade Storage

### `Trade` and `TradeStatus`

```python
from pocket_trader import Trade, TradeStatus

trade = Trade(
    id="tx-1",
    asset="EURUSD",
    direction="CALL",
    amount=10.0,
    entry_price=1.0945,
    status=TradeStatus.OPEN,
)
trade.to_dict()                      # JSON-serializable dict
Trade.from_dict(data)                # rebuild from dict
```

`TradeStatus` enum: `OPEN`, `CLOSED`, `WIN`, `LOSS`, `PENDING`.

### `TradeStorage`

Persistent SQLite-backed trade history with an LRU cache in front.

```python
storage = TradeStorage(db_path="trading_data.db", cache_size=1000)
```

| Method | Purpose |
|--------|---------|
| `save_trade(trade)` | Insert/update a trade |
| `get_trade(trade_id)` | Fetch one trade |
| `list_trades(limit=100, status=None)` | Query recent trades |
| `update_status(trade_id, status, profit)` | Mark won/lost/closed |
| `get_statistics()` | Win rate, P&L, totals |
| `close()` | Close DB connection |

Trades stored here survive process restarts and feed the analytics subsystem.

---

## Fast Candle Collection

### `FastCandleCollector`

Collects candles quickly using in-memory caching and parallel collection; a convenience wrapper around `MemoryCandleStorage`.

```python
from pocket_trader import FastCandleCollector

collector = FastCandleCollector(client)
```

| Method | Purpose |
|--------|---------|
| `collect_candles(asset, timeframe=60, count=100, use_cache=True)` | Candles from live-built history, falling back to `wait_for_candles` (30s) |
| `collect_multiple_assets([...], timeframe=60, count=100)` | Parallel collection → `{asset: [Candle]}` |
| `get_live_candle(asset, timeframe=60)` | Current forming candle (waits up to 10s) |
| `clear_cache()` | Drop the cached results |
| `get_cache_stats()` | `{cache_size, cache_keys}` |

Cached results are reused for 30 seconds.

---

## End-to-end example

```python
import asyncio
from pocket_trader import (
    PocketOptionClient, Asset, Regions, DealAction,
    MemoryDealsStorage, FastCandleCollector,
)
from pocket_trader.utils import generate_request_id

async def main():
    client = PocketOptionClient()
    deals = MemoryDealsStorage(client)          # wire deal events
    candles = FastCandleCollector(client)       # wire price events

    await client.connect(Regions.DEMO)
    await client.emit.auth({
        "session": "<session>", "isDemo": 1, "uid": 0,
        "platform": 2, "isFastHistory": True,
    })

    # Collect candles for the asset
    built = await candles.collect_candles(Asset.EURUSD, timeframe=60, count=100)
    print("Candles collected:", len(built))

    deal = await deals.open_deal(
        asset=Asset.EURUSD,
        amount=10,
        action=DealAction.CALL,
        time=60,
        request_id=generate_request_id(),
    )
    result = await deals.check_deal_result(deal=deal)
    print("Result:", result.profit)
    await client.disconnect()

asyncio.run(main())
```

---

Next: [Models](models.md) · [Indicators & AI](indicators.md) · [Client & Connection](client.md)