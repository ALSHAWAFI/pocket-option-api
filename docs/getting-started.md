# Getting Started

This guide walks you through setting up PocketTrader, getting credentials, and making your first connection.

---

## 1. Requirements

- Python **3.9+**
- A Pocket Option account (demo account recommended for testing)

### Install

```bash
pip install pocket-trader
```

For locally developing against a checkout:

```bash
pip install -e .
```

Optional speed extras (faster JSON via `ujson`/`orjson`):

```bash
pip install pocket-trader[speed]
```

---

## 2. Getting Your Credentials

PocketTrader authenticates over the WebSocket using credentials from your browser session.

1. Log in to [pocketoption.com](https://pocketoption.com) in your browser.
2. Open the developer tools (**F12**) → **Application/Storage** → **Cookies**.
3. Copy the values of:
   - `ssid` → used as `session`
   - `uid` → a numeric user ID

> **Security:** Never commit these values. Use a `.env` file (and keep it out of git).

---

## 3. Configure `.env`

Copy the provided `.env.example` to `.env` and fill it in:

```env
PO_SESSION=4u9d6kfghfghfghfhgfhgf
PO_UID=1679898790
IS_DEMO=true
PO_REGION=demo
INITIAL_BALANCE=1000
MAX_RISK_PER_TRADE=0.02
MAX_DAILY_TRADES=10
```

| Variable                | Meaning                              | Default      |
|-------------------------|--------------------------------------|--------------|
| `PO_SESSION`            | Session ID from browser cookie       | *(required)* |
| `PO_UID`                | Your user ID                         | *(required)* |
| `IS_DEMO`               | `true` = demo, `false` = real money  | `true`       |
| `PO_REGION`             | Server region: `demo`, `eu`, `us`, `asia` | `demo` |
| `INITIAL_BALANCE`       | Starting balance for risk calc       | `1000`       |
| `MAX_RISK_PER_TRADE`    | Risk fraction per trade (0.02 = 2%)  | `0.02`       |
| `MAX_DAILY_TRADES`      | Daily trade cap                      | `10`         |

Load them with `python-dotenv`:

```python
import os
from dotenv import load_dotenv
load_dotenv()

SESSION_ID = os.getenv("PO_SESSION")
UID = int(os.getenv("PO_UID", "0"))
```

---

## 4. First Connection

```python
import asyncio
from pocket_trader import PocketOptionClient, Asset, Regions

async def main():
    client = PocketOptionClient()

    # Connect to the demo endpoint
    await client.connect(Regions.DEMO)

    # Authenticate
    await client.emit.auth({
        "session": "<your-session-id>",
        "isDemo": 1,
        "uid": 0,
        "platform": 2,
        "isFastHistory": True,
        "isOptimized": True,
    })

    # Register an event handler *before* subscribing
    @client.on.update_close_value
    async def on_price(items):
        for item in items:
            print(item["asset"], "→", item["value"])

    # Subscribe to an asset
    await client.emit.subscribe_to_asset(Asset.EURUSD)

    # Cancel after 30 seconds, then disconnect
    await asyncio.sleep(30)
    await client.disconnect()

asyncio.run(main())
```

> **Important:** register event handlers *before* connecting/subscribing, so no updates are missed.

---

## 5. Lifecycle

1. **Create client** — `PocketOptionClient(...)`
2. **Connect** — `await client.connect(Regions.DEMO)` (or a raw `url`)
3. **Authenticate** — `await client.emit.auth({...})` (listen via `@client.on.success_auth`)
4. **Subscribe** — `await client.emit.subscribe_to_asset(Asset.X)`
5. **Trade** — via `MemoryDealsStorage.open_deal(...)` (see [Trading](trading.md))
6. **Disconnect** — `await client.disconnect()`

### Server regions

`Regions` is a `StrEnum` where each member value is the target WebSocket URL:

| Member               | WebSocket URL                    |
|----------------------|----------------------------------|
| `Regions.DEMO`       | `wss://demo-api-eu.po.market`    |
| `Regions.DEMO_2`     | `wss://try-demo-eu.po.market`    |
| `Regions.EUROPA`     | `wss://api-eu.po.market`         |
| `Regions.UNITED_STATES_NORTH` | `wss://api-us-north.po.market` |
| `Regions.UNITED_STATES_SOUTH` | `wss://api-us-south.po.market` |
| `Regions.ASIA`       | `wss://api-asia.po.market`       |

Full list also includes `UNITED_STATES_2..4`, `FRANCE_1..2`, `RUSSIA`, `INDIA`, `FINLAND`, `SEYCHELLES`, `HONGKONG`, `SERVER_1..3`.

The helper `Regions.get_url(region)` resolves friendly names (`"demo"`, `"eu"`, `"us"`, `"asia"`) to a URL (defaults to `EUROPA`).

---

## 6. What's Next

- [Client & Connection](client.md) — all events, emits, and connection options
- [Trading](trading.md) — making and tracking deals
- [Indicators & AI](indicators.md) — signals and pattern recognition