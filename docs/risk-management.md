# Risk Management

The risk subsystem protects capital with **dynamic position sizing**, **Kelly Criterion**, **anti-martingale & martingale sizing**, **Value at Risk (VaR)**, **Expected Shortfall**, **drawdown limits**, and **AI risk assessment**.

---

## Components

| Class | Purpose |
|-------|---------|
| `RiskManager` | Main risk engine: limits, position sizing, capital protection |
| `RiskMetrics` | Snapshot dataclass of current risk state |
| `PortfolioManager` | Multi-asset allocation, correlation, rebalancing |
| `AIRiskAssessor` | Risk level from volatility/regime history |

---

## `RiskManager`

```python
from pocket_trader import RiskManager

rm = RiskManager(initial_balance=1000.0)
```

### Configuration (attributes)

Defaults are sensible; override after construction:

```python
rm.max_risk_per_trade = 0.02         # 2% of balance per trade
rm.max_daily_risk = 0.06             # 6% total daily loss cap
rm.max_consecutive_losses = 3        # stop after 3 losses in a row
rm.max_daily_trades = 20
rm.max_open_trades = 5
rm.max_drawdown_percent = 20         # hard stop at 20% drawdown

rm.use_kelly = True
rm.kelly_fraction = 0.25             # bet 25% of Kelly size
rm.use_anti_martingale = False
rm.use_ai_risk_assessment = True
rm.use_dynamic_stop = True
rm.martingale_multiplier = 2.0
```

Set any of them with a single call:

```python
rm.set_limits(max_risk_per_trade=0.01, max_daily_trades=10, use_kelly=False)
```

### Can we trade?

```python
ok, reason = rm.can_trade(check_limits=True, asset="EURUSD")
if not ok:
    print("Blocked:", reason)
```

`can_trade` checks (in order): daily reset, balance present, max trades today, daily risk budget, consecutive losses, max open trades, drawdown, and (optionally) portfolio/violation limits.

### Position sizing

```python
amount = rm.calculate_position_size(
    confidence=1.0,          # strategy confidence multiplier
    balance=rm.current_balance,
    max_risk_per_trade=0.02,
)
```

- Uses the **Kelly Criterion** by default (`use_kelly=True`): `f* = win_rate - (1 - win_rate)/payout`, scaled by `kelly_fraction` (0.25).
- `use_anti_martingale=True` splits the bet and `use_ai_risk_assessment=True` applies the AI volatility multiplier.
- Falls back to a fixed risk-per-trade amount otherwise.

Martingale sizing (for recovery strategies):

```python
next_size = rm.calculate_martingale_size(base_size=10.0)
# base * martingale_multiplier ^ consecutive_losses
```

### Tracking trades

```python
rm.add_trade(trade_id="t1", amount=10.0, asset="EURUSD")
rm.update_trade_result(
    profit=+8.0, trade_id="t1",
    was_win=True, asset="EURUSD",
)
rm.remove_trade("t1")
```

State is updated automatically: balance, peak, daily PnL, equity curve, consecutive win/loss streaks, and per-asset stats (via the attached `PortfolioManager`).

### Market conditions

```python
rm.update_market_conditions(volatility=1.4, market_regime="volatile")
```

Feeds the `AIRiskAssessor`, which returns a risk level and a position multiplier:

```python
assessment = rm.get_detailed_stats()["ai_assessment"]
# {'risk_level': 'normal'|'elevated'|'high', 'multiplier': 0.5..1.0, 'confidence': ...}
```

### Metrics & reporting

```python
metrics: RiskMetrics = rm.get_metrics()
print(metrics.is_safe_to_trade, metrics.safety_reason)
print(metrics.var_95, metrics.expected_shortfall)
print(metrics.recommended_position)

details = rm.get_detailed_stats()          # dict with every field
rec = rm.get_trade_recommendation(confidence=0.9)  # (position size, reason)
rm.reset()                                  # back to initial state
```

### `RiskMetrics` fields

`current_balance`, `daily_pnl`, `daily_trades`, `open_trades`, `consecutive_losses`, `win_rate`, `profit_factor`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `max_drawdown`, `var_95`, `expected_shortfall`, `risk_per_trade`, `recommended_position`, `is_safe_to_trade`, `safety_reason`.

---

## Value at Risk

```python
var_95 = rm.calculate_var(confidence=0.95)
es = rm.calculate_expected_shortfall(confidence=0.95)
drawdown_abs, drawdown_pct = rm.get_current_drawdown()
max_abs, max_pct = rm.get_max_drawdown()
```

- VaR: worst expected loss over the daily returns history at the given confidence.
- Expected Shortfall: the *average* loss beyond the VaR threshold.
- Drawdowns are tracked from the peak balance.

---

## `PortfolioManager`

Multi-asset capital allocation with correlation-aware rebalancing.

```python
from pocket_trader import PortfolioManager

pf = PortfolioManager(total_capital=1000.0)
pf.add_asset("EURUSD", allocation_percent=0.5)
pf.add_asset("XAUUSD", allocation_percent=0.5)
```

| Method | Purpose |
|--------|---------|
| `update_performance(asset, profit, was_win)` | Record per-asset results |
| `calculate_correlation()` | `{asset: {other: correlation}}` |
| `rebalance(use_correlation=True)` | Recompute allocations, penalizing correlated assets |
| `get_capital_for_asset(asset)` | Allocated budget for an asset |
| `get_portfolio_stats()` | Per-asset PnL, win rates, allocation, best/worst |
| `get_best_asset()` / `get_worst_asset()` | Performance helpers |

Wire it into the risk manager:

```python
rm.set_portfolio_manager(pf)
```

---

## `AIRiskAssessor`

```python
assessor = AIRiskAssessor()
assessor.update(volatility=1.2, market_regime="volatile")
risk = assessor.assess_risk_level()
# {'risk_level': 'normal'|'elevated'|'high', 'multiplier': <0..1>, 'confidence': ...}
```

- Tracks the last 100 volatility values and 50 regimes.
- Compares recent vs historical volatility, bumps the level on consecutive high-regimes.
- The `multiplier` shrinks recommended position sizes when risk is elevated.

---

## Integration example

```python
import asyncio
from pocket_trader import (
    PocketOptionClient, Asset, DealAction, Regions,
    RiskManager, MemoryDealsStorage,
)
from pocket_trader.utils import generate_request_id

async def main():
    client = PocketOptionClient()
    deals = MemoryDealsStorage(client)
    rm = RiskManager(initial_balance=1000.0)

    await client.connect(Regions.DEMO)
    await client.emit.auth({"session": "<session>", "isDemo": 1, "uid": 0,
                            "platform": 2, "isFastHistory": True})

    async def trade(asset: Asset, direction: DealAction, confidence: float):
        if not rm.can_trade()[0]:
            return None
        size = rm.calculate_position_size(confidence=confidence)
        deal = await deals.open_deal(asset=asset, amount=size,
                                     action=direction, time=60,
                                     request_id=generate_request_id())
        rm.add_trade(str(deal.id), size, asset=asset.value)
        result = await deals.check_deal_result(deal=deal, wait_time=90)
        rm.update_trade_result(
            profit=result.profit or 0, trade_id=str(result.id),
            was_win=(result.profit or 0) > 0, asset=asset.value,
        )
        return result

    # example: one trade with high confidence
    await trade(Asset.EURUSD, DealAction.CALL, confidence=0.9)
    print(rm.get_metrics().recommended_position)
    await client.disconnect()

asyncio.run(main())
```

---

Next: [Analytics & ML](analytics.md) · [Trading](trading.md) · [Indicators & AI](indicators.md)