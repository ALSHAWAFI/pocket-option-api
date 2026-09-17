# Analytics & ML

The analytics subsystem turns your `TradeStorage` history into actionable insight: performance metrics, best/worst assets, time-of-day analysis, machine-learning profit predictions, and a real-time monitor.

---

## Components

| Class | Purpose |
|-------|---------|
| `TradeMetrics` | Full performance metrics dataclass |
| `PerformanceAnalyzer` | Period analysis, reports, ML insights |
| `MLPredictor` | Small neural model predicting future profit |
| `PerformanceMonitor` | Loop that alerts when metrics degrade |

---

## `TradeMetrics`

```python
from pocket_trader import TradeMetrics

metrics = TradeMetrics()
metrics.to_dict()                        # JSON-serializable
metrics.to_dataframe()                   # pandas DataFrame
```

Fields:

| Group | Fields |
|-------|--------|
| Counts | `total_trades`, `winning_trades`, `losing_trades` |
| P&L | `total_profit`, `total_loss`, `gross_profit`, `gross_loss` |
| Averages | `average_win`, `average_loss`, `largest_win`, `largest_loss` |
| Ratios | `win_rate`, `loss_rate`, `profit_factor`, `expectancy`, `average_r_multiple` |
| Risk-adjusted | `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `recovery_factor` |
| Drawdown | `max_drawdown`, `max_drawdown_percentage` |
| Streaks | `consecutive_wins`, `consecutive_losses` |
| Misc | `average_trade_duration`, `best_asset`, `worst_asset`, `var_95`, `expected_shortfall` |

> `to_dataframe()` returns a single-row DataFrame; for per-trade analysis use `PerformanceAnalyzer` internals via `_trades_to_dataframe` (built from the same schema).

---

## `PerformanceAnalyzer`

```python
from pocket_trader import PerformanceAnalyzer
from pocket_trader import TradeStorage

storage = TradeStorage(db_path="trading_data.db")
analyzer = PerformanceAnalyzer(storage)
```

### Period metrics

```python
metrics = await analyzer.analyze_period(
    days=30,
    start_date=None,     # defaults to now - days
    end_date=None,       # defaults to now
)
```

Every call also feeds the internal `MLPredictor` with the latest period's features and future profit.

### Best/worst assets

```python
top = await analyzer.best_assets(days=30, min_trades=5, top_n=5)
# -> DataFrame with per-asset aggregate performance
```

### Time analysis

```python
time_stats = await analyzer.time_analysis(days=30)
# -> dict: profit/win-rate per hour-of-day (and per day-of-week)
```

### Reports

```python
report = await analyzer.generate_report(days=30)
# dict: {'metrics': TradeMetrics, 'summary': str, 'recommendations': [...], 'best_assets': df, ...}

await analyzer.save_report("report.json", days=30)
ml = await analyzer.get_ml_insights(days=30)
# dict with {next_period_forecast, confidence, feature_importances, ...}
```

The report generator builds a human summary and 3–5 concrete recommendations (e.g. "avoid trading during hours X", "reduce stake after 2 consecutive losses").

---

## `MLPredictor`

```python
from pocket_trader import MLPredictor

ml = MLPredictor()
ml.add_training_data(
    features={"win_rate": 55.0, "profit_factor": 1.4, "sharpe_ratio": 1.1,
              "volatility": 0.02, "consecutive_losses": 1,
              "avg_win": 8.0, "avg_loss": 5.0},
    future_profit=120.0,
)
ml.train()
prediction = ml.predict({"win_rate": 58.0, ...})
accuracy = ml.get_accuracy()
```

- A neural model trained on period-level features → next-period profit forecast.
- Used automatically by `PerformanceAnalyzer.analyze_period`.

---

## `PerformanceMonitor`

Live monitoring loop that alerts when key metrics degrade.

```python
async def on_alert(code: str, message: str, data: dict):
    print(f"[{code}] {message}")

monitor = PerformanceMonitor(storage, alert_callback=on_alert)
await monitor.start(interval=60.0)    # check every 60s (background task)
     ...
await monitor.stop()
```

### Alerts

| Code | Condition |
|------|-----------|
| `WIN_RATE_DROP` | Win rate below threshold |
| `DRAWDOWN_LIMIT` | Drawdown beyond configured % |
| `CONSECUTIVE_LOSSES` | Loss streak exceeded |
| `DAILY_LOSS_LIMIT` | Daily loss beyond limit |
| `LOW_PROFIT_FACTOR` | Profit factor < 1.0 |
| `RISK_LEVEL` | AI risk assessment elevated |

```python
status = monitor.get_status()   # current snapshot + last check time
```

---

## Integration example

```python
import asyncio
from pocket_trader import PerformanceAnalyzer, TradeStorage

async def main():
    storage = TradeStorage("trading_data.db")
    analyzer = PerformanceAnalyzer(storage)

    metrics = await analyzer.analyze_period(days=30)
    print(f"Trades: {metrics.total_trades}, Win rate: {metrics.win_rate:.1f}%")
    print(f"Profit factor: {metrics.profit_factor:.2f}")
    print(f"Sharpe: {metrics.sharpe_ratio:.2f}, Max DD: {metrics.max_drawdown_percentage:.1f}%")
    print(f"Best asset: {metrics.best_asset}")

    report = await analyzer.generate_report(days=30)
    print(report["summary"])
    for rec in report["recommendations"]:
        print("-", rec)

    ml = await analyzer.get_ml_insights(days=30)
    print("Forecast:", ml.get("next_period_forecast"))

    await storage.close()

asyncio.run(main())
```

---

Next: [Risk Management](risk-management.md) · [Caching](caching.md) · [Trading](trading.md)