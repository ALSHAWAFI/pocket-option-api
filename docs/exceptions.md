# Exceptions

PocketTrader uses a small exception hierarchy rooted at `PocketTraderError`, plus a dedicated `DealError` for deal/trade failures.

All are importable from the package root.

---

## Hierarchy

```
PocketTraderError
├── ConnectionError          connection failed
├── AuthError                authentication failed
├── SubscriptionError        subscribe/unsubscribe failed
├── TradeError               trade operation failed
│   └── InsufficientBalanceError   not enough balance
├── StorageError             storage operation failed
├── IndicatorError           indicator calculation failed
├── ValidationError          data validation failed
│   └── InvalidAssetError    invalid asset name
├── TimeoutError             operation timed out
├── RateLimitError           rate limit exceeded
└── ParseError               data parsing failed

DealError (ValueError)       deal/trade request errors (see below)
```

> **Note:** `ConnectionError` and `TimeoutError` shadow the Python builtins of the same name inside this package. Catch with `except pocket_trader.ConnectionError:` when you mean the library's own types.
>
> **Note:** `DealError` subclasses `ValueError`, **not** `PocketTraderError`, so `except PocketTraderError` will *not* catch it — catch `DealError` (or `ValueError`) explicitly.

---

## `PocketTraderError`

```python
from pocket_trader import PocketTraderError

class PocketTraderError(Exception):
    def __init__(self, message: str, details: Optional[Dict] = None):
        ...
    def to_dict(self) -> Dict:
        # {"type": "AuthError", "message": "...", "details": {...}}
```

- `except PocketTraderError` to handle *any* library error subclass (but **not** `DealError`, see note above).
- `err.message` and `err.details` always available.
- `err.to_dict()` useful for logging or API responses.

---

## `DealError`

Raised by `DealsStorage.open_deal` and related operations. Carries a machine-readable `code`.

```python
from pocket_trader import DealError

try:
    await deals.open_deal(...)
except DealError as e:
    print(e.code)    # e.g. "min_amount"
    print(e.message) # human-readable
    print(e.extras)  # extra context dict, e.g. {"request_id": ...}
```

`DealError` also exposes `to_dict()` → `{"code", "message", "extras"}` and a friendly `str` like `[min_amount] Min amount is 1`.

### `DealErrorCode`

The literal union of allowed codes:

| Code | Raised when |
|------|-------------|
| `min_amount` | amount below `API_LIMITS_MIN_ORDER_AMOUNT` (1) |
| `max_amount` | amount above `API_LIMITS_MAX_ORDER_AMOUNT` (50_000) |
| `min_duration` | duration below `API_LIMITS_MIN_DURATION` (5) |
| `max_duration` | duration above `API_LIMITS_MAX_DURATION` (43_200) |
| `max_orders` | concurrent open orders limit reached |
| `timeout` | no confirmation within the wait window |
| `not_found` | deal not found after confirmation |
| `send_failed` | emitting the deal request failed |
| `invalid_action` | unknown action |
| `insufficient_balance` | not enough funds |
| `pattern_failed` | setup too similar to a previously failed pattern — **raised by `open_deal` but not listed in the `DealErrorCode` Literal** |

---

## `ErrorCode`

String constants for common situations (avoids typos):

```python
from pocket_trader import ErrorCode

ErrorCode.CONNECTION_FAILED      # "connection_failed"
ErrorCode.AUTH_FAILED            # "auth_failed"
ErrorCode.INVALID_CREDENTIALS    # "invalid_credentials"
ErrorCode.SESSION_EXPIRED        # "session_expired"
ErrorCode.MIN_AMOUNT             # "min_amount"
ErrorCode.MAX_AMOUNT             # "max_amount"
ErrorCode.MIN_DURATION           # "min_duration"
ErrorCode.MAX_DURATION           # "max_duration"
ErrorCode.MAX_ORDERS             # "max_orders"
ErrorCode.INSUFFICIENT_BALANCE   # "insufficient_balance"
ErrorCode.INVALID_ASSET          # "invalid_asset"
ErrorCode.INVALID_ACTION         # "invalid_action"
ErrorCode.INVALID_DATA           # "invalid_data"
ErrorCode.RATE_LIMIT             # "rate_limit"
ErrorCode.TIMEOUT                # "timeout"
ErrorCode.DEAL_TIMEOUT           # "deal_timeout"
```

---

## Handling patterns

```python
from pocket_trader import (
    PocketTraderError, DealError, ConnectionError, AuthError,
    RateLimitError, TimeoutError,
)

try:
    await client.emit.auth(payload)
except AuthError as e:
    print("Bad credentials:", e.details)
    if e.details.get("code") == ErrorCode.SESSION_EXPIRED:
        print("Re-fetch session")

try:
    await deals.open_deal(...)
except DealError as e:
    if e.code == "min_amount":
        amount = 1
    elif e.code == "max_orders":
        print("Too many open orders")
except (RateLimitError, TimeoutError):
    print("Slowed down")

# Catch-all for anything the library raises:
except PocketTraderError as e:
    print(e.to_dict())
```

---

Next: [Middleware](middleware.md) · [Types, Utils & Constants](types-utils-constants.md) · [Trading](trading.md)