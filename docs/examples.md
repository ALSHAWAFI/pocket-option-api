# Examples

The package ships two examples under `pocket_trader/examples/`.

> **⚠️ Outdated imports:** both examples import `OrderType` and `TradingError` from `pocket_trader`, but the current API exports `DealAction` (not `OrderType`) and the error is `TradeError` (not `TradingError`). Treat the examples as *architecture references*, not verbatim runnable code. All identifiers below are corrected.

---

## `env_example.py` — configuration-driven bot

Shows how to drive the bot from a `.env` file.

### Required env vars

```env
PO_SESSION=<browser session>
PO_UID=<uid>
IS_DEMO=true            # or false
PO_REGION=demo          # demo | eu | us | asia
SYMBOLS=EURUSD_otc,GBPUSD_otc,BTCUSD_otc
BASE_AMOUNT=10
TRADE_DURATION=60
```

### Flow

1. Loads `.env` with `python-dotenv`.
2. Builds a `PocketOptionClient`, connects to `Regions.get_url(PO_REGION)`.
3. Authenticates with `emit.auth({...})`.
4. Subscribes to each symbol.
5. On `update_close_value`, builds candles via `CandleBuilder`.
6. Runs a trading loop that opens deals when the strategy produces a signal.

```python
from pocket_trader import PocketOptionClient, Asset, Regions, DealAction

client = PocketOptionClient()
await client.connect(Regions.get_url(region))
await client.emit.auth({
    "session": session, "isDemo": 1 if is_demo else 0,
    "uid": uid, "platform": 2, "isFastHistory": True,
})
```

---

## `full_example.py` — full trading bot

A single-file bot wiring every subsystem:

| Subsystem | Usage |
|-----------|-------|
| Client | `PocketOptionClient`, `Regions` |
| Storage | `MemoryCandleStorage`, `MemoryDealsStorage` |
| Candles | `CandleBuilder` per asset |
| Risk | `RiskManager` with `update_trade_result()` |
| Indicators | `Indicators.rsi()` etc. for signals |
| Analytics | `TradeStorage` for persistence |

Key handlers (with corrected imports):

```python
from pocket_trader import (
    PocketOptionClient, Asset, Regions, DealAction,
    MemoryDealsStorage, RiskManager, CandleBuilder,
)

@client.on.connect
async def on_connect(data=None):
    await client.emit.auth({...})

@client.on.update_balance
async def on_balance(data):
    risk_manager.current_balance = data["balance"]

@client.on.update_close_value
async def on_price(items):
    for item in items:
        builder.add_tick(timestamp=item["timestamp"], price=item["value"])

@client.on.success_open_deal
async def on_opened(deal):
    await deals_storage.add_or_update_deal(deal)   # storage accepts dicts
    risk_manager.add_trade(str(deal["id"]), amount=deal["amount"])

@client.on.success_close_deal
async def on_closed(event):
    for deal in event["deals"]:
        await deals_storage.add_or_update_deal(deal)
        risk_manager.update_trade_result(deal["profit"] or 0)
        risk_manager.remove_trade(str(deal["id"]))
```

Opening a trade:

```python
action = DealAction.CALL if signal == "BUY" else DealAction.PUT
await deals_storage.open_deal(
    asset=Asset(symbol),
    amount=amount,
    action=action,
    time=duration,
)
```

---

## Converting the examples

If you want to run them as-is, patch the stale names first:

```diff
-from pocket_trader import OrderType, TradingError
+from pocket_trader import DealAction, TradeError

-action = OrderType.CALL if ... else OrderType.PUT
+action = DealAction.CALL if ... else DealAction.PUT

-except TradingError as e:
+except TradeError as e:
```

---

## Your own minimal bot

See [Trading](trading.md) for a canonical end-to-end example that uses the **current** API (including `generate_request_id()` and `check_deal_result()`).

---

Next: [Code Generator](generator.md) · [Getting Started](getting-started.md) · [README](../README.md)