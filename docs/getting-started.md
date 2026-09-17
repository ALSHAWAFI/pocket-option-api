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

Pocket Option authenticates over the WebSocket with the same payload your browser sends. The most reliable way to obtain it is to read it directly from the WebSocket handshake.

> Adapted from the original project **[lordralinc/pocket_option](https://github.com/lordralinc/pocket_option)** — credit to its author for documenting this method.

### Extract from the WebSocket (recommended)

1. Log in to [pocketoption.com](https://pocketoption.com) and open the Developer Tools (**F12**).
2. Switch to the **Network** tab.
3. Click the **WS** filter to show only WebSocket connections.
4. Reload the page, then select the active connection to your region (e.g. `wss://api-eu.po.market/...`).
5. Open its **Messages** tab (in Chrome: **Frames**) and look for an outgoing message that starts with `42["auth",`.
6. Copy the `session`, `uid`, and `isDemo` values from that JSON.

The auth frame looks like this — `42` is the Socket.IO packet prefix, followed by the event name and its JSON payload:

```text
42["auth",{"session":"abcd1234efgh5678","isDemo":1,"uid":1234589,"platform":1}]
```

| Field      | Meaning |
|------------|---------|
| `session`  | Your session token (string) — **treat it like a password** |
| `uid`      | Your numeric user ID |
| `isDemo`   | `1` = demo account, `0` = real account |
| `platform` | Client platform id (e.g. `1` or `2`) |

> **Tip:** In Chrome, enable **Preserve log** and use the message filter box (`auth`) to locate the frame faster. In Firefox the panel is called **Response**/**Messages** and the filter sits at the bottom.

### Alternative: from cookies

1. Open Developer Tools (**F12**) → **Application** (Chrome) or **Storage** (Firefox).
2. Under **Cookies** for `pocketoption.com`, copy:
   - `ssid` → use as `session`
   - `uid` → your numeric user ID
   - `isDemo` → `1` when the session belongs to the demo account

These map directly onto the `auth` payload used in [Step 4](#4-first-connection):

```python
{
    "session": SESSION_ID,   # from the WS frame or the ssid cookie
    "isDemo": 1,             # 1 = demo, 0 = real
    "uid": UID,
    "platform": 1,
    "isFastHistory": True,
    "isOptimized": True,
}
```

> **Security:** Never commit these values. Keep them in `.env` (already excluded by `.gitignore`). If a session is ever exposed, log out of Pocket Option to invalidate it.

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