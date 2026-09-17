# Pocket Option API

**An unofficial, community-driven Python API client for the [Pocket Option](https://pocketoption.com) platform.**

Pocket Option API gives Python developers a typed, asynchronous toolkit for building their own applications on top of the Pocket Option WebSocket API — an async client, Pydantic data models, real-time market streams, technical indicators, and optional higher-level utilities for risk and analysis.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-unofficial-orange)

> **Important:** Read the [Risk Disclaimer](#risk-disclaimer) and [Legal Notice](#legal-notice) before using this project.
> This is an **unofficial** project. It is **not** affiliated with, endorsed by, or sponsored by Pocket Option.
> Trading involves a high level of financial risk, and **this software does not guarantee any profit or success**.

---

## Table of Contents

- [Overview](#overview)
- [What "Unofficial" Means](#what-unofficial-means)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Configuration](#configuration)
- [Package Layout](#package-layout)
- [Development](#development)
- [Credits & Attribution](#credits--attribution)
- [Risk Disclaimer](#risk-disclaimer)
- [Legal Notice](#legal-notice)
- [License](#license)

---

## Overview

Pocket Option API is an **API client library**, not a ready-made trading bot. It handles the low-level concerns — WebSocket connectivity, authentication, message framing, request/response modelling, and event dispatch — so you can focus on the logic of your own application.

At its core the library provides:

- A typed, async client over `python-socketio` with reconnection, heartbeats, and rate limiting.
- Pydantic v2 models for every request, response, and event payload.
- Parsers and processors for the platform's compact binary price and signal frames.
- Building blocks (storage, indicators, caching, middleware) for larger applications.

The higher-level AI, genetic-optimization, and risk-management modules are **optional utilities** shipped with the library. They are experimental and must not be treated as investment advice or as a reliable strategy.

---

## What "Unofficial" Means

Pocket Option API is an independent project maintained by the community. It is **not** an official Pocket Option product, and it is not approved, reviewed, or supported by Pocket Option in any way.

The public Pocket Option WebSocket API used here is undocumented and can change without notice. This means:

- Endpoints, message formats, and protocols may break at any time.
- Features may stop working after an update to the platform.
- No guarantee is made regarding correctness, uptime, or fitness for any purpose.

Use it as a learning and development tool, and always test against a **demo account** first.

---

## Features

**Client & connectivity**
- Async WebSocket client built on `python-socketio`
- Automatic reconnection with exponential backoff and jitter
- Heartbeat and watchdog monitoring
- Token-bucket rate limiting (default 100 req/s)
- Configurable retries for transient failures

**Data & models**
- Pydantic v2 models with validation, camelCase aliases, and timezone handling
- Typed event handlers and emit methods (generated from the platform's event schema)
- Type adapters for validating raw event payload lists
- 40+ assets across forex, commodities, crypto, indices, stocks, and OTC

**Real-time streams**
- 39-byte price stream (`StreamUpdate`, `StreamProcessor`)
- 19-byte signal/candle frames (`ChaforMessage`, `ChaforProcessor`)

**Indicators & analysis**
- Common technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, …)
- Market-regime detection and indicator caching
- Experimental AI helpers: pattern recognition, genetic parameter search, ML-based prediction

**Application building blocks**
- Risk-management utilities: Kelly Criterion, anti-martingale, VaR / Expected Shortfall, drawdown control
- Caching: TTL, LFU, predictive, indicator, and pattern caches
- Storage: in-memory candle/deal storage and persistent SQLite trade storage
- Analytics: performance analysis and real-time monitoring
- Middleware pipeline: JSON parsing, type fixing, logging, stats, throttling

> The AI and risk-management components are **experimental** and provided for research and educational purposes only. They are not a guarantee of performance.

---

## Requirements

- Python **3.9+**
- A Pocket Option account (use the **demo** account while developing)

---

## Installation

```bash
pip install pocket-trader
```

Or from a local checkout:

```bash
pip install -e .
```

### Optional extras

| Extra   | Command                              | Adds |
|---------|--------------------------------------|------|
| `speed` | `pip install pocket-trader[speed]`   | `ujson`, `orjson` for faster JSON |
| `db`    | `pip install pocket-trader[db]`      | `sqlalchemy` for persistent storage |
| `ml`    | `pip install pocket-trader[ml]`      | `scikit-learn`, `scipy` for AI/ML modules |
| `full`  | `pip install pocket-trader[full]`    | All of the above |

---

## Quick Start

```python
import asyncio
from pocket_trader import PocketOptionClient, Asset, Regions

async def main():
    # 1. Create the client
    client = PocketOptionClient()

    # 2. Connect (use the demo region while developing)
    await client.connect(Regions.DEMO)  # or Regions.get_url("demo")

    # 3. Subscribe to price updates
    @client.on.update_close_value
    async def on_price(items):
        for item in items:
            print(f"{item['asset']}: {item['value']:.5f} @ {item['timestamp']}")

    # 4. Authenticate (required after connect)
    await client.emit.auth({
        "session": "your_session_id_here",
        "isDemo": 1,
        "uid": 0,
        "platform": 2,
        "isFastHistory": True,
        "isOptimized": True,
    })

    # 5. Subscribe to an asset
    await client.emit.subscribe_to_asset(Asset.EURUSD)

    # 6. Keep running
    await client.wait()

asyncio.run(main())
```

More complete examples:

- [`pocket_trader/examples/full_example.py`](pocket_trader/examples/full_example.py) — a full application using every subsystem
- [`pocket_trader/examples/env_example.py`](pocket_trader/examples/env_example.py) — `.env`-driven configuration

---

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, credentials, and the connection flow |
| [Client & Connection](docs/client.md) | `PocketOptionClient`, events, emits, rate limiting, reconnection |
| [Models](docs/models.md) | All Pydantic models, enums, and type adapters |
| [Trading](docs/trading.md) | Candle building, candle/deal storage, trade storage, fast candle collector |
| [Indicators & AI](docs/indicators.md) | Indicators, neural pattern recognition, genetic optimization |
| [Risk Management](docs/risk-management.md) | `RiskManager`, Kelly, martingale, VaR, portfolio |
| [Analytics & ML](docs/analytics.md) | Performance analysis, ML predictions, monitoring |
| [Caching](docs/caching.md) | TTL / LFU / predictive / indicator / pattern caches |
| [Stream & Chafor](docs/stream-and-chafor.md) | 39-byte price updates and 19-byte signals |
| [Middleware](docs/middleware.md) | Event pipeline customization |
| [Exceptions](docs/exceptions.md) | Error hierarchy and error codes |
| [Types, Utils & Constants](docs/types-utils-constants.md) | Supporting APIs |
| [Examples](docs/examples.md) | Guided walkthroughs |
| [Code Generator](docs/generator.md) | Regenerating the typed client |

---

## Configuration

Copy [`.env.example`](.env.example) to `.env` and fill in your credentials:

```env
PO_SESSION=your_session_id_here        # session ID from your browser
PO_UID=0                               # your user ID
IS_DEMO=true                           # true = demo account, false = real
PO_REGION=demo                         # demo | eu | us | asia
INITIAL_BALANCE=1000                   # starting balance for risk calculations
MAX_RISK_PER_TRADE=0.02                # 2% risk per trade
MAX_DAILY_TRADES=10                    # daily trade cap
```

Load them with `python-dotenv` (see [`env_example.py`](pocket_trader/examples/env_example.py)).

> **Never commit your `.env` file or your session ID.** Treat credentials as secrets.

---

## Package Layout

```
pocket_trader/
├── __init__.py          # Public API exports
├── client.py            # RateLimiter, RetryManager, ConnectionManager, client classes
├── generated_client.py  # Auto-generated typed emit/on interface (DO NOT EDIT)
├── models.py            # Pydantic data models, enums, type adapters
├── trading.py           # CandleBuilder, storage classes, trades
├── indicators.py        # Indicators + AI/GA enhancements
├── risk.py              # RiskManager, RiskMetrics, PortfolioManager, AIRiskAssessor
├── analytics.py         # PerformanceAnalyzer, PerformanceMonitor, MLPredictor
├── cache.py             # TTLCache, LFUCache, PredictiveCache, etc.
├── stream.py            # StreamUpdate / StreamProcessor (39-byte)
├── chafor.py            # ChaforMessage / ChaforProcessor (19-byte)
├── middleware.py        # Middleware pipeline
├── patches.py           # Legacy connection patches
├── constants.py         # Regions, limits, signal types, timeframes
├── exceptions.py        # Exception hierarchy
├── types.py             # Type aliases & protocols
├── utils.py             # Logging, timestamps, parsing, validation helpers
├── examples/            # full_example.py, env_example.py
└── generator/           # Code generator (events.json + Jinja2 templates)
```

---

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Lint, type-check and test
ruff check .
mypy pocket_trader
pytest

# Regenerate the typed client
generate-client
```

---

## Credits & Attribution

Pocket Option API is an independent, community effort. It is developed on top of, and adapts ideas, protocol research, and code from, the work of earlier developers and open-source contributors.

- **Yury "lordralinc" Yushmanov** — original socket/protocol work that this project builds upon.
- The wider open-source community whose public research into the platform's protocol made this library possible.

If your work has been used here and is not credited correctly, please open an issue so it can be updated.

---

## Risk Disclaimer

**Trading binary options and other financial instruments carries a high level of risk and can result in the loss of all of your invested capital.**

Please read and understand the following:

- This software is provided for **educational and development purposes only**. It is **not** financial, investment, or trading advice.
- **No strategy, indicator, AI module, or algorithm in this project guarantees profit or success.** Past performance — real or simulated — does not indicate future results.
- The AI, genetic-optimization, martingale, and risk-management modules are **experimental** and may behave incorrectly or unexpectedly.
- Automated trading can amplify losses. Bugs, connectivity failures, or API changes may cause unintended trades.
- You are solely responsible for your own trading decisions and for any financial outcome.
- **Only trade with money you can afford to lose**, and always test against a demo account first.

By using Pocket Option API you acknowledge and accept these risks.

---

## Legal Notice

- Pocket Option API is an **unofficial** project. It is **not** affiliated with, endorsed by, or sponsored by Pocket Option, its affiliates, or any related entity.
- "Pocket Option" and any related names, marks, and logos are the property of their respective owners and are used here for identification purposes only.
- The authors and contributors of Pocket Option API accept **no liability** for any loss or damage arising from the use of this software.
- You are responsible for complying with the terms of service of any platform you use and with all applicable laws and regulations in your jurisdiction.

---

## License

Released under the [MIT License](./LICENSE).
