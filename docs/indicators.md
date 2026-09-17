# Indicators & AI

The indicators subsystem provides classical technical indicators augmented with **AI confidence scoring**, **neural pattern recognition**, **market-regime detection**, and **genetic algorithm optimization**. All methods are async classmethods and return `EnhancedIndicatorResult`.

---

## `EnhancedIndicatorResult`

```python
from pocket_trader import EnhancedIndicatorResult

result = EnhancedIndicatorResult(
    value=1.0952,
    signal="bullish",       # "bullish" | "bearish" | "neutral" | "overbought" | "oversold" | ...
    strength=0.72,          # 0..1 signal strength
    ai_confidence=0.83,     # AI confidence in the signal
    pattern_match={"...": ...},   # optional matched historical pattern
    market_regime="trending",
    learning_rate=0.01,
    prediction_accuracy=0.0,
    metadata={},            # e.g. {"period": 20, "current_price": ...}
)
```

Computed helpers:

| Property | Meaning |
|----------|---------|
| `composite_score` | `strength * 0.6 + ai_confidence * 0.4` |
| `recommendation` | `"STRONG BUY"` / `"STRONG SELL"` / `"BUY"` / `"SELL"` / `"HOLD"` |
| `is_buy_signal()` / `is_sell_signal()` | Boolean helpers on signal + score |

---

## `Indicators`

`Indicators` is a classmethod-only API. Signature pattern:

```python
await Indicators.<name>(prices, ...)
```

All methods accept `prices: List[float]` (closes) and return `EnhancedIndicatorResult`.

### Moving averages

```python
await Indicators.sma(prices, period=20, use_ai=True, use_cache=True)
await Indicators.ema(prices, period=20, smoothing=2.0, use_cache=True)
```

- **SMA** — signal bullish when price > MA×1.02, bearish < MA×0.98, else neutral.
- **EMA** — similar thresholds (±1.5%).

### RSI

```python
await Indicators.rsi(prices, period=14, optimize=False, use_cache=True)
```

- Standard RSI calculation; `>70` gives `"overbought"`, `<30` gives `"oversold"`.
- `optimize=True` runs the genetic optimizer over `period ∈ [5, 25]` when data is long enough.

### MACD

```python
await Indicators.macd(prices, fast=12, slow=26, signal=9, use_cache=True)
```

Returns the MACD `value` plus `"strong_bullish"/"bullish"` signals based on histogram/line position.

### Bollinger Bands

```python
await Indicators.bollinger_bands(prices, period=20, std_dev=2.0, use_cache=True)
```

Value is the middle band; metadata includes `upper`, `lower`, `bandwidth`, `%B`; signals reflect price vs bands.

### Market regime

```python
await Indicators.detect_market_regime(prices, volumes=None)
# -> {"regime": "trending"|"ranging"|"volatile", "volatility": float, ... }
```

Returns a dict, not an `EnhancedIndicatorResult`.

### Comprehensive analysis

```python
result = await Indicators.comprehensive_analysis(
    prices=prices, highs=highs, lows=lows, volumes=volumes
)
# -> EnhancedIndicatorResult with combined signals, regime, and AI confidence

all_indicators = await Indicators.get_all_indicators(
    prices, highs, lows, volumes
)
# -> dict of all indicator results

await Indicators.optimize_rsi(prices)   # GA-optimized RSI period
await Indicators.clear_cache()          # drop cached indicator results
```

Results are cached via `IndicatorCache` (see [Caching](caching.md)).

---

## `NeuralPatternRecognizer`

A small configurable neural network for trend prediction.

```python
from pocket_trader import NeuralPatternRecognizer

model = NeuralPatternRecognizer(
    input_size=10,          # price window length
    hidden_size=20,
    output_size=3,          # up / down / flat probabilities
)
```

```python
prices = [1.09, 1.091, ...]
probs = model.predict(prices)                  # dict of class probabilities

X = [np.array(close_window) for _ in ...]      # training examples
y = [1, 0, 2, ...]                             # labels (0=down, 1=up, 2=flat)
model.train(X, y, epochs=100, lr=0.01)
```

`predict` returns a dict like `{"up": 0.4, "down": 0.1, "flat": 0.5}` and a direction/confidence.

---

## `GeneticIndicatorOptimizer`

Optimizes indicator parameters with a population-based genetic algorithm.

```python
from pocket_trader import GeneticIndicatorOptimizer
import numpy as np

optimizer = GeneticIndicatorOptimizer(population_size=50, mutation_rate=0.1)
optimizer.initialize_population({"period": (5, 25)})

async def rsi_func(prices, **params):
    return await Indicators.rsi(prices, params["period"], optimize=False)

best = await optimizer.evolve(
    prices[-100:], rsi_func, {"period": (5, 25)}, generations=20
)
optimizer.get_best_parameters()   # -> {"period": 17, ...}
```

Built into `Indicators.rsi(..., optimize=True)` automatically.

---

## End-to-end: signal from live candles

Candle data arrives asynchronously via the `update_history_new_fast` event (see [Trading — FastCandleCollector](trading.md#fastcandlecollector)). A compact pattern:

```python
import asyncio
from pocket_trader import Indicators, PocketOptionClient, Regions, Asset

async def main():
    client = PocketOptionClient()
    await client.connect(Regions.DEMO)
    await client.emit.auth({"session": "<session>", "isDemo": 1, "uid": 0,
                            "platform": 2, "isFastHistory": True})

    closes = []

    @client.on.update_history_new_fast
    async def on_history(data):
        # data provides candles for the subscribed asset
        nonlocal closes
        candles = getattr(data, "candles", None)
        if not candles and isinstance(data, (list, tuple)):
            candles = data
        if candles:
            closes = [c.close for c in candles[-100:] if hasattr(c, "close")]

    await client.emit.get_candles({"asset": Asset.EURUSD.value, "timeframe": 60, "count": 100})

    await asyncio.sleep(5)  # give the server time to push history

    if closes:
        rsi = await Indicators.rsi(closes, period=14)
        macd = await Indicators.macd(closes)
        print("RSI:", rsi.value, rsi.signal, "strength:", rsi.strength)
        print("MACD:", macd.value, macd.signal)
        print("Recommendation:", macd.recommendation)

    await client.disconnect()

asyncio.run(main())
```

> **Note:** `emit.get_candles(...)` is fire-and-forget — it emits the request and returns immediately. Candle data must be collected from the `update_history_new_fast` event. For a ready-made collector, prefer `FastCandleCollector` ([trading.md](trading.md#fastcandlecollector)).

---

Next: [Risk Management](risk-management.md) · [Analytics & ML](analytics.md) · [Caching](caching.md)