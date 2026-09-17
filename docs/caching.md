# Caching

PocketTrader ships several caching layers to make indicators, price history, and AI patterns fast. All caches are `async` and thread-safe via `asyncio.Lock`.

| Cache | Strategy | Use |
|-------|----------|-----|
| `TTLCache` | Time-to-live + LRU eviction | General purpose cache |
| `LFUCache` | Least-frequently-used eviction | Hot, repeatedly accessed data |
| `PredictiveCache` | ML-style prefetch on top of a `TTLCache` | Ahead-of-time warmup |
| `IndicatorCache` | Domain-aware indicator results keyed by `(indicator, asset, timeframe, args)` | Indicator computation |
| `PatternCache` | Successful/failed trade patterns | Avoid repeating failures |

All are exported from the package root.

---

## `TTLCache`

```python
from pocket_trader import TTLCache

cache = TTLCache(
    max_size=1000,          # max entries (LRU eviction beyond this)
    default_ttl=60.0,       # seconds
    cleanup_interval=10.0,  # background sweep interval
)
await cache.start()         # start the background cleanup task
```

```python
await cache.set("eurusd:price", 1.0945, ttl=30)      # custom ttl
value = await cache.get("eurusd:price", default=None)

cached = await cache.get_or_set(
    "rsi:14", lambda: 55.3, ttl=60
)                       # compute only on miss

await cache.delete("key")
await cache.clear()
```

Stats:

```python
stats = cache.get_stats()
# {"hits": 10, "misses": 2, "evictions": 0, "expirations": 1,
#  "size": 3, "max_size": 1000, "hit_rate": 83.33, "usage_percent": 0.3}
```

Remember to `await cache.stop()` on shutdown.

---

## `LFUCache`

```python
from pocket_trader import LFUCache

cache = LFUCache[str, float](max_size=1000, ttl=None)
await cache.set("key", 42.0)
await cache.get("key")        # increments access count
await cache.delete("key")
await cache.clear()
stats = await cache.get_stats()
```

Eviction removes the least frequently used entries when full.

---

## `PredictiveCache`

Wraps a `TTLCache` and prefetches *likely-needed* keys using a moving window.

```python
from pocket_trader import PredictiveCache, TTLCache

base = TTLCache(max_size=1000)
pcache = PredictiveCache(cache=base, window_size=100)

await pcache.set("asset:1", {"price": 1.09})
await pcache.get("asset:1")
```

### Prefetching

`PredictiveCache` learns the sequence of key accesses and, when a key is hit, predicts the next likely key and requests it. To actually load it, override `_on_prefetch`:

```python
class MyPredictiveCache(PredictiveCache):
    async def _on_prefetch(self, key: str):
        value = await expensive_lookup(key)
        await self.set(key, value)
```

`PredictiveCache.get_stats()` returns `{"patterns": N, "history_size": N, "cache_stats": {...}}`.

---

## `IndicatorCache`

Caches indicator results so repeated calls with the same parameters are instant.

```python
from pocket_trader import IndicatorCache

ic = IndicatorCache(max_size=500, use_lfu=True)
await ic.set(value=0.72, indicator="rsi", asset="EURUSD", timeframe=60, period=14)
v = await ic.get(indicator="rsi", asset="EURUSD", timeframe=60, period=14)

await ic.get_or_compute(indicator="macd", asset="EURUSD", timeframe=60,
                        compute_func=lambda: compute_macd(...))
await ic.invalidate_asset("EURUSD")
await ic.clear()
stats = await ic.get_stats()
```

Argument order is flexible — keys are built from `(indicator, asset, timeframe, *args)`. TTLs are derived from the timeframe (longer timeframes cache longer).

Used automatically by `Indicators.*` methods.

---

## `PatternCache`

Learns which trading patterns work and which fail.

```python
from pocket_trader import PatternCache

pc = PatternCache(max_patterns=1000)
await pc.add_successful("EURUSD_CALL_60", {"rsi": 65})
await pc.add_failed("EURUSD_PUT_60", {"rsi": 35})

similar = await pc.get_similar("EURUSD_CALL_60", threshold=0.8)
# -> most similar stored pattern (or None)
stats = await pc.get_stats()
await pc.clear()
```

---

## Gluing it together

```python
import asyncio
from pocket_trader import TTLCache, IndicatorCache

async def main():
    price = TTLCache(max_size=10_000, default_ttl=5)
    indicators = IndicatorCache()

    await price.start()
    await price.set("XAUUSD", 2380.5)
    print(await price.get("XAUUSD"))

    result = await indicators.get_or_compute("sma20", "XAUUSD", 60,
        compute_func=lambda: 2390.0)
    print(result, await indicators.get_stats())
    await price.stop()

asyncio.run(main())
```

---

Next: [Indicators & AI](indicators.md) · [Stream & Chafor](stream-and-chafor.md) · [Trading](trading.md)