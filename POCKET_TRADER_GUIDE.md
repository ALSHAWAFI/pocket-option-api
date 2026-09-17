# POCKET_TRADER Integration Guide
## دليل ربط أي بوت تداول مع مكتبة pocket_trader

---

## 1. Installation

```bash
pip install pocket_trader
pip install python-dotenv pandas pandas_ta numpy
```

---

## 2. .env File (Required)

```env
# Connection
PO_SESSION=your_session_id_here
PO_UID=your_uid_here
IS_DEMO=true

# Server (comma-separated for fallback)
SERVERS=wss://demo-api-eu.po.market

# Trading Pairs (comma-separated)
SYMBOLS=EURUSD_otc,GBPUSD_otc,BTCUSD_otc

# Trade Settings
BASE_AMOUNT=10
TRADE_DURATION=60
MIN_TRADE_INTERVAL=120

# Risk Management
MAX_DAILY_TRADES=30
DAILY_LOSS_LIMIT=50
MAX_CONSECUTIVE_LOSSES=3

# Signal Quality
MIN_CANDLES_REQUIRED=210
MIN_CONFIDENCE=65
```

---

## 3. Core Architecture

```
Bot
 ├── data_fetcher.py    ← Wrapper around pocket_trader (YOU WRITE THIS)
 │    ├── PocketOptionClient    ← pocket_trader handles WebSocket
 │    ├── MemoryDealsStorage    ← pocket_trader handles trade execution
 │    └── CandleStorage         ← YOUR code builds candles from ticks
 │
 ├── strategy.py        ← YOUR trading strategy (YOU WRITE THIS)
 │    └── generate_signals(df, asset) → (pre_signal, confirmed_signal)
 │
 ├── ai_learning.py     ← Optional: track wins/losses (YOU WRITE THIS)
 └── q_learning.py      ← Optional: Q-Learning (YOU WRITE THIS)
```

---

## 4. data_fetcher.py — The Wrapper (CRITICAL)

This is the ONLY file that talks to pocket_trader. Copy this pattern:

### 4.1 Imports

```python
from pocket_trader import (
    PocketOptionClient, Asset, Deal, MemoryDealsStorage
)
from pocket_trader.models import DealAction
from pocket_trader.utils import generate_request_id
```

### 4.2 PocketOptionDataFetcher Class

```python
class PocketOptionDataFetcher:
    def __init__(self, session_id: str, uid: int = None, is_demo: bool = True):
        self.session_id = session_id
        self.uid = uid
        self.is_demo = is_demo
        self.client = None
        self.deals = None
        self.connected = False
        self.authenticated = False
        self._subscribed_assets = set()

        # Callbacks
        self._tick_callbacks = []
        self._candle_callbacks = []
        self._balance_callbacks = []
        self._deal_close_callbacks = []

    def on_tick(self, callback):
        self._tick_callbacks.append(callback)

    def on_candle_complete(self, callback):
        self._candle_callbacks.append(callback)

    def on_balance_update(self, callback):
        self._balance_callbacks.append(callback)

    def on_deal_close(self, callback):
        self._deal_close_callbacks.append(callback)
```

### 4.3 Event Handlers Setup

```python
def _setup_handlers(self):

    @self.client.on.connect
    async def on_connect(data=None):
        self.connected = True
        # MUST authenticate after connect
        await self.client.emit.auth({
            "session": self.session_id,
            "isDemo": 1 if self.is_demo else 0,
            "uid": self.uid or 0,
            "platform": 2,
            "isFastHistory": True
        })

    @self.client.on.disconnect
    async def on_disconnect(data=None):
        self.connected = False
        self.authenticated = False
        self._subscribed_assets.clear()

    @self.client.on.success_auth
    async def on_auth(data):
        self.authenticated = True

    @self.client.on.update_balance
    async def on_balance(data):
        balance = getattr(data, 'balance', 0)
        if balance:
            for cb in self._balance_callbacks:
                await cb(float(balance))

    @self.client.on.update_close_value
    async def on_price(items):
        if not self.authenticated:
            return
        if not isinstance(items, list):
            items = [items]
        for item in items:
            # item can be dict or object
            if isinstance(item, dict):
                asset_name = item.get('asset', '')
                price = item.get('value', 0)
                timestamp = item.get('timestamp', time.time())
            elif hasattr(item, 'asset'):
                asset_name = item.asset.value if hasattr(item.asset, 'value') else str(item.asset)
                price = float(item.value)
                timestamp = getattr(item, 'timestamp', time.time())
            else:
                continue

            for cb in self._tick_callbacks:
                await cb(asset_name, price, timestamp)

    @self.client.on.update_history_new_fast
    async def on_history(data):
        asset = data.asset if hasattr(data, 'asset') else data.get('asset', '')
        candles_data = data.candles if hasattr(data, 'candles') else data.get('candles', [])

        candles_list = []
        for candle in candles_data:
            if isinstance(candle, (list, tuple)) and len(candle) >= 5:
                candles_list.append({
                    'timestamp': float(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4])
                })

        if candles_list:
            for cb in self._candle_callbacks:
                await cb(asset, candles_list)

    @self.client.on.success_close_deal
    async def on_close_deal(event):
        deals = []
        if hasattr(event, 'deals'):
            deals = event.deals
        elif hasattr(event, 'profit'):
            deals = [event]
        elif isinstance(event, list):
            deals = event

        for deal in deals:
            for cb in self._deal_close_callbacks:
                await cb(deal)
```

### 4.4 Connect

```python
async def connect(self, servers: list) -> bool:
    for server in servers:
        try:
            self.client = PocketOptionClient(reconnection=True)
            self.deals = MemoryDealsStorage(self.client)
            self._setup_handlers()
            await self.client.connect(url=server, wait=True, wait_timeout=30)

            # Wait for auth (up to 15 seconds)
            for _ in range(30):
                if self.authenticated:
                    return True
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Connection failed: {e}")
    return False
```

### 4.5 Subscribe to Asset

```python
async def subscribe(self, symbol: str) -> bool:
    try:
        if symbol in self._subscribed_assets:
            return True
        await self.client.emit.subscribe_to_asset(Asset(symbol))
        self._subscribed_assets.add(symbol)
        await asyncio.sleep(1.5)
        await self.client.emit.change_asset({"asset": symbol, "period": 60})
        await asyncio.sleep(1.0)
        return True
    except Exception as e:
        logger.error(f"Subscribe failed: {e}")
        return False
```

### 4.6 Execute Trade

```python
async def execute_trade(self, symbol: str, direction: str,
                        amount: float, duration: int) -> str:
    action = DealAction.CALL if direction.upper() == "CALL" else DealAction.PUT

    deal = await self.deals.open_deal(
        asset=Asset(symbol),
        amount=amount,
        action=action,
        time=duration,
        request_id=generate_request_id()
    )

    if deal:
        return str(getattr(deal, 'id', time.time()))
    return None
```

### 4.7 Disconnect

```python
async def disconnect(self):
    if self.client:
        await self.client.disconnect()
    self.connected = False
    self.authenticated = False
```

---

## 5. CandleStorage — Build Candles from Ticks

pocket_trader sends individual ticks (price + timestamp). YOU must build 1-minute candles:

```python
class CandleStorage:
    def __init__(self, symbol: str, max_candles: int = 500):
        self.symbol = symbol
        self.max_candles = max_candles
        self.candles = []
        self.current_candle = None
        self._current_bucket = 0

    def add_tick(self, price: float, timestamp: float) -> dict:
        """Add tick, return completed candle if minute changed"""
        if timestamp > 1e12:
            timestamp = timestamp / 1000

        bucket = int(timestamp // 60) * 60  # 1-minute bucket

        if self.current_candle is None:
            self._start_candle(bucket, price)
            return None

        if bucket != self._current_bucket:
            completed = self._finalize_candle()
            self._start_candle(bucket, price)
            return completed

        # Update current candle
        self.current_candle['high'] = max(self.current_candle['high'], price)
        self.current_candle['low'] = min(self.current_candle['low'], price)
        self.current_candle['close'] = price
        return None

    def _start_candle(self, bucket, price):
        self.current_candle = {
            'timestamp': bucket,
            'open': price, 'high': price,
            'low': price, 'close': price
        }
        self._current_bucket = bucket

    def _finalize_candle(self):
        if self.current_candle is None:
            return None
        completed = self.current_candle.copy()
        self.candles.append(completed)
        if len(self.candles) > self.max_candles:
            self.candles = self.candles[-self.max_candles:]
        self.current_candle = None
        return completed

    def add_candles_history(self, candles: list):
        """Merge historical candles (from on_history event)"""
        existing = {c['timestamp'] for c in self.candles}
        new = [c for c in candles if c['timestamp'] not in existing]
        if new:
            self.candles.extend(new)
            self.candles.sort(key=lambda x: x['timestamp'])
            if len(self.candles) > self.max_candles:
                self.candles = self.candles[-self.max_candles:]

    def get_dataframe(self):
        """Convert to pandas DataFrame"""
        if len(self.candles) < 200:
            return None
        df = pd.DataFrame(self.candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        return df

    def is_ready(self, min_candles=200):
        return len(self.candles) >= min_candles
```

---

## 6. Trading Loop (in main.py or gui.py)

```python
from data_fetcher import PocketOptionDataFetcher, CandleStorage
from strategy import generate_signals

async def run_bot(session_id, uid, is_demo, symbols, servers):
    fetcher = PocketOptionDataFetcher(session_id, uid, is_demo)
    storages = {s: CandleStorage(s) for s in symbols}
    open_assets = set()
    last_signal_time = {}

    # 1. Connect
    connected = await fetcher.connect(servers)
    if not connected:
        return

    # 2. Subscribe to all pairs
    for sym in symbols:
        await fetcher.subscribe(sym)

    # 3. Register callbacks
    @fetcher.on_tick
    async def on_tick(asset, price, ts):
        if asset in storages:
            done = storages[asset].add_tick(price, ts)
            if done:
                # Candle completed → check for signals
                await check_signal(asset)

    @fetcher.on_candle_complete
    async def on_history(asset, candles):
        if asset in storages:
            storages[asset].add_candles_history(candles)

    @fetcher.on_balance_update
    async def on_balance(balance):
        print(f"Balance: ${balance:.2f}")

    @fetcher.on_deal_close
    async def on_deal(deal):
        asset = deal.asset.value if hasattr(deal.asset, 'value') else str(deal.asset)
        profit = deal.profit or 0
        is_win = profit > 0
        open_assets.discard(asset)
        print(f"{'WIN' if is_win else 'LOSS'}: {asset} ${profit:.2f}")

    # 4. Signal checking
    async def check_signal(asset):
        storage = storages.get(asset)
        if not storage or not storage.is_ready(min_candles=210):
            return
        if asset in open_assets:
            return
        if time.time() - last_signal_time.get(asset, 0) < 120:
            return

        df = storage.get_dataframe()
        if df is None:
            return

        _, signal = generate_signals(df.copy(), asset)
        if not signal:
            return

        direction = signal['direction']
        confidence = signal.get('confidence', 75)

        # Execute trade
        open_assets.add(asset)
        last_signal_time[asset] = time.time()

        deal_id = await fetcher.execute_trade(asset, direction, 10, 60)
        if not deal_id:
            open_assets.discard(asset)

    # 5. Keep running
    while True:
        await asyncio.sleep(30)

# Run
asyncio.run(run_bot(SESSION_ID, UID, IS_DEMO, SYMBOLS, SERVERS))
```

---

## 7. strategy.py — YOUR Strategy

```python
def generate_signals(df, asset_name=""):
    """
    Returns (pre_signal, confirmed_signal)
    - pre_signal: can be None (we don't use pre-signals)
    - confirmed_signal: dict with direction, confidence, reason, etc.
    """
    # YOUR STRATEGY LOGIC HERE
    # Example: Katie MA + Stochastic

    if signal_found:
        return None, {
            "type": "CONFIRMED",
            "direction": "CALL",  # or "PUT"
            "strength": "STRONG",
            "confidence": 80,
            "reason": "MA cross + Stoch cross",
            "strategy": "katie",
            "ma4": round(ma4, 5),
            "ma50": round(ma50, 5),
            "ma200": round(ma200, 5),
            "stoch_k": round(stoch_k, 1),
            "stoch_d": round(stoch_d, 1),
            "rsi": round(rsi, 1),
        }

    return None, None
```

---

## 8. pocket_trader API Quick Reference

### Connection
```python
client = PocketOptionClient(reconnection=True)
await client.connect(url="wss://demo-api-eu.po.market", wait=True)
```

### Authentication (MUST call after connect)
```python
await client.emit.auth({
    "session": session_id,
    "isDemo": 1,  # 1=demo, 0=real
    "uid": uid,
    "platform": 2,
    "isFastHistory": True
})
```

### Subscribe to Asset
```python
await client.emit.subscribe_to_asset(Asset("EURUSD_otc"))
await asyncio.sleep(1.5)
await client.emit.change_asset({"asset": "EURUSD_otc", "period": 60})
```

### Open Trade
```python
deals = MemoryDealsStorage(client)
deal = await deals.open_deal(
    asset=Asset("EURUSD_otc"),
    amount=10.0,
    action=DealAction.CALL,  # or DealAction.PUT
    time=60,  # duration in seconds
    request_id=generate_request_id()
)
```

### Available Events
```
client.on.connect              → Server connected
client.on.disconnect           → Server disconnected
client.on.success_auth         → Authenticated
client.on.update_balance       → Balance updated
client.on.update_close_value   → Price tick received
client.on.update_history_new_fast → Historical candles
client.on.success_close_deal   → Trade completed
client.on.success_open_deal    → Trade opened
```

### Asset Names (OTC pairs)
```python
Asset("EURUSD_otc")    # Forex OTC
Asset("BTCUSD_otc")    # Crypto OTC
Asset("#NVDA_otc")     # Stock OTC
Asset("XAUUSD_otc")    # Gold OTC
```

---

## 9. Common Mistakes to Avoid

1. **DON'T** call `client.emit.auth()` before `client.on.connect` fires
2. **DON'T** forget `await asyncio.sleep(1.5)` after subscribe
3. **DON'T** use `DealAction.CALL` — it's `DealAction.CALL` (capital)
4. **DON'T** forget `generate_request_id()` in `open_deal()`
5. **DON'T** build candles manually — use the CandleStorage pattern
6. **DON'T** block the event loop — always use `async/await`
7. **DON'T** trade same pair while previous trade is open — use `open_assets` set
8. **DON'T** forget `reconnection=True` in PocketOptionClient

---

## 10. File Structure

```
your_bot/
├── .env                  ← Session, UID, pairs, settings
├── config.py             ← Read .env, define constants
├── data_fetcher.py       ← Wrapper around pocket_trader (COPY FROM GUIDE)
├── strategy.py           ← YOUR strategy
├── ai_learning.py        ← Optional: track wins/losses
├── q_learning.py         ← Optional: Q-Learning
├── main.py               ← CLI entry point
├── gui.py                ← Optional: PySide6 GUI
└── requirements.txt      ← Dependencies
```

---

## 11. requirements.txt

```
pocket_trader>=2.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
pandas_ta>=0.3.14b1
numpy>=1.24.0
PySide6>=6.5.0
```
