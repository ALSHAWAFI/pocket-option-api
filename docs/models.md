# Models

All data structures are Pydantic v2 models, enums, or type adapters. They are re-exported from the package root:

```python
from pocket_trader import Asset, Deal, Candle, Account, PriceTick, DealAction
from pocket_trader.models import UpdateCloseValueItem, OpenDealRequest
```

> **Runtime note:** event handlers registered with `client.on.*` receive the **parsed JSON payloads** produced by the middleware pipeline (`dict` / `list`), not automatically-instantiated Pydantic models. The models below describe those payload shapes; validate them with the [type adapters](#type-adapters) when you want typed objects.

---

## Enums

### `Asset(str, enum.Enum)`

Trading assets. It is a custom `str`-enum: `Asset("EURUSD")`, `Asset.EURUSD`, and the plain string `"EURUSD"` are interchangeable. Unknown strings are created lazily via `_missing_`, so any symbol works.

**Major pairs:** `AUDCAD, EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`

**Commodities:** `XAUUSD, XAGUSD, UKBrent, USCrude, XNGUSD, XPTUSD, XPDUSD`

**Crypto:** `BTCUSD, ETHUSD, DASH_USD, BTCGBP, BTCJPY, BCHEUR, BCHGBP, BCHJPY, DOTUSD, LNKUSD`

**Indices:** `SP500, NASUSD, DJI30, JPN225, D30EUR, E50EUR, F40EUR, E35EUR, A_100GBP, AUS200, CAC40, AEX25, SMI20, H33HKD`

**Stocks** (values are prefixed `#`): `AAPL, MSFT, TSLA, FB, NFLX, INTC, BA, JPM, JNJ, PFE, XOM, AXP, MCD, CSCO, CITI, TWITTER, BABA`

**OTC:** `CADJPY_otc, EURUSD_otc, GBPUSD_otc, XAUUSD_otc` (more can be created dynamically)

Helpers:

```python
Asset.EURUSD_otc.is_otc()   # True for anything ending in "_otc"
Asset("BTCUSD")              # resolves to the enum member
Asset("SOME_NEW")            # unknown values are created lazily
```

### `AssetType(enum.StrEnum)`

`STOCK`, `COMMODITY`, `CURRENCY`, `CRYPTOCURRENCY`, `INDEX`.

### `Command(enum.IntEnum)`

`PUT = 0`, `CALL = 1` — the numeric trade direction.

### `DealAction(enum.StrEnum)`

`CALL = "call"`, `PUT = "put"` — the string action used when opening a deal.

### `OpenPendingDealRequestOpenType(enum.IntEnum)`

`TIME = 0`, `PRICE = 1` — how a pending deal is triggered.

### `IsDemo`

Type alias `Literal[0, 1]` — `1` = demo, `0` = real account.

---

## Base Models

### `Account`

```python
class Account(BaseModel):
    uid: int
    balance: float
    demo_balance: Optional[float] = None
    currency: str = "USD"
    is_demo: bool = False
```

Property: `available_balance` returns `demo_balance` when `is_demo`, else `balance`.

### `AuthorizationData`

All fields are required; camelCase aliases are used on the wire.

```python
class AuthorizationData(BaseModel):
    session: str
    is_demo: IsDemo                            # alias "isDemo"
    uid: int
    platform: int
    is_fast_history: bool                      # alias "isFastHistory"
    is_optimized: bool                         # alias "isOptimized"
```

`emit.auth(...)` also accepts a plain dict with the camelCase keys (`session`, `isDemo`, `uid`, `platform`, `isFastHistory`, `isOptimized`).

### `Candle`

```python
class Candle(BaseModel):
    asset: Asset
    timestamp: datetime.datetime    # timezone-aware (UTC if none given)
    timeframe: int                  # seconds (60 = 1m)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
```

Convenience properties:

| Property | Meaning |
|----------|---------|
| `is_bullish` / `is_bearish` | Close vs open |
| `body_size` | `abs(close - open)` |
| `upper_shadow` / `lower_shadow` | Wick sizes |
| `range` | `high - low` |
| `body_percentage` | Body size as % of range |

Plus `to_dict() -> dict` for serialization.

> The `timestamp` validator attaches `pytz.UTC` when a naive `datetime` is supplied.

### `Deal`

Parsed from the server; fields map to camelCase aliases.

```python
class Deal(BaseModel):
    id: uuid.UUID
    command: Command
    asset: Asset
    uid: int
    amount: float
    is_demo: IsDemo                          # alias "isDemo"
    profit: float
    percent_profit: float                    # alias "percentProfit"
    percent_loss: float                      # alias "percentLoss"
    open_time: datetime.datetime             # alias "openTime"
    close_time: datetime.datetime            # alias "closeTime"
    open_timestamp: float                    # alias "openTimestamp"
    close_timestamp: Optional[float]         # alias "closeTimestamp"
    refund_time: Optional[datetime.datetime] # alias "refundTime"
    refund_timestamp: Optional[int]          # alias "refundTimestamp"
    open_price: float                        # alias "openPrice"
    close_price: Optional[float]             # alias "closePrice"
    copy_ticket: str                         # alias "copyTicket"
    open_ms: Optional[int]                   # alias "openMs"
    close_ms: Optional[int]                  # alias "closeMs"
    option_type: Optional[int]               # alias "optionType"
    is_rollover: Optional[bool]              # alias "isRollover"
    is_copy_signal: bool                     # alias "isCopySignal"
    is_ai: Optional[bool]                    # alias "isAI"
    currency: str
    amount_usd: Optional[float]              # alias "amountUSD"
    request_id: Optional[int]                # alias "requestId"
```

Properties: `is_open` (`close_price is None`), `is_profitable`, `profit_percentage`.

### `PriceTick`

```python
class PriceTick(BaseModel):
    asset: Asset
    price: float
    timestamp: float
    bid: Optional[float] = None
    ask: Optional[float] = None
```

Properties: `spread` (`ask - bid`, or `None`) and `mid_price` (`(bid + ask) / 2`, or `price`).

### `IndicatorResult`

```python
class IndicatorResult(BaseModel):
    value: float
    signal: str = "neutral"          # "buy" | "sell" | "overbought" | "oversold" | "bullish" | "bearish"
    strength: float = 0.0            # 0..1
    metadata: dict = {}
```

Properties: `is_buy_signal`, `is_sell_signal`, `confidence` (`"very_high"` … `"very_low"` from `strength`).

---

## Event Models

Shapes of the payloads delivered to `@client.on.*` handlers.

### `SuccessAuthEvent`

`id: str`.

### `SuccessUpdateBalanceEvent`

`is_demo: IsDemo` (alias `"isDemo"`), `balance: float`.

### `UpdateHistoryFastEvent`

`asset: Asset`, `period: int`, `history: list[list[float]]` — raw OHLC rows (build `Candle` objects from `history`).

### `UpdateCloseValueItem`

```python
class UpdateCloseValueItem(BaseModel):
    asset: Asset
    timestamp: float
    value: float
```

> The default `FixTypesOnMiddleware` delivers `updateStream` items as `{"asset": str, "timestamp": float, "value": float}` dicts — matching this model.

### `SuccessCloseDealEvent`

`profit: float`, `deals: list[Deal]`.

### `MarketSentimentItem`

`asset: Asset`, `value: int`.

### `AssetItemTimeframe`

`time: int`.

### `UpdateAssetItem`

```python
class UpdateAssetItem(BaseModel):
    id: int
    asset: Asset                              # alias "symbol"
    label: str
    type: AssetType
    precision: int
    payout: int
    min_duration: int
    max_duration: int
    step_duration: int
    volatility_index: int
    spread: int
    leverage: int
    extra_data: list[JsonValue]
    expire_time: int
    is_active: bool
    timeframes: list[AssetItemTimeframe]
    start_time: int
    default_timeframe: int
    status_code: int
```

---

## Request Models

Payloads for `client.emit.*`.

### `OpenDealRequest`

`extra="forbid"`; camelCase aliases accepted.

```python
class OpenDealRequest(BaseModel):
    asset: Asset
    amount: int
    action: DealAction            # CALL / PUT
    is_demo: IsDemo               # alias "isDemo"
    request_id: int               # alias "requestId"
    option_type: int = 100        # alias "optionType"
    time: int                     # duration in seconds (validated 5..43200)
```

`amount` is validated against `API_LIMITS_MIN_ORDER_AMOUNT`/`API_LIMITS_MAX_ORDER_AMOUNT`.

```python
await client.emit.open_deal(OpenDealRequest(
    asset=Asset.EURUSD, amount=10, action=DealAction.CALL, time=60,
    is_demo=1, request_id=123456,
))
```

### `ChangeAssetRequest`

`asset: Asset`, `period: int` — switch the active chart asset/timeframe.

### `CopySignalRequest`

```python
class CopySignalRequest(BaseModel):
    symbol: Asset
    amount: int
    expired_at: int               # alias "expiredAt"
    action: DealAction
    is_demo: IsDemo               # alias "isDemo"
    request_id: int               # alias "requestId"
    created_at: int               # alias "createdAt"
    timeframe: int
    signal_id: str                # alias "signalId"
```

### `OpenPendingDealRequest`

```python
class OpenPendingDealRequest(BaseModel):
    open_type: OpenPendingDealRequestOpenType  # alias "openType"
    amount: int
    asset: Asset
    open_time: str                             # alias "openTime"
    open_price: int                            # alias "openPrice"
    timeframe: int
    min_payout: int                            # alias "minPayout"
    command: Command
```

---

## Type Adapters

Shared Pydantic v2 `TypeAdapter`s for validating raw payload lists:

| Adapter | Validates |
|---------|-----------|
| `UpdateCloseValueListTypeAdapter` | `list[UpdateCloseValueItem]` |
| `UpdateAssetItemListTypeAdapter` | `list[UpdateAssetItem]` |
| `MarketSentimentItemListTypeAdapter` | `list[MarketSentimentItem]` |
| `DealListTypeAdapter` | `list[Deal]` |

```python
from pocket_trader import DealListTypeAdapter

deals = DealListTypeAdapter.validate_python(raw_deals)
```

---

Next: [Client & Connection](client.md) · [Trading](trading.md) · [Types, Utils & Constants](types-utils-constants.md)