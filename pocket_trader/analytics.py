# analytics.py
"""
Advanced trading performance analytics with machine learning insights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import asyncio
from collections import deque

from .utils import setup_logger
from .trading import TradeStorage
from .models import Deal


@dataclass
class TradeMetrics:
    """Comprehensive trade metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percentage: float = 0.0
    average_r_multiple: float = 0.0
    average_trade_duration: float = 0.0
    best_asset: str = ""
    worst_asset: str = ""
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    recovery_factor: float = 0.0
    var_95: float = 0.0
    expected_shortfall: float = 0.0
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items()}
    
    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.to_dict()])


# ============================================================================
# MACHINE LEARNING PREDICTOR
# ============================================================================

class MLPredictor:
    """
    Machine Learning based performance predictor
    Uses historical patterns to predict future performance
    """
    
    def __init__(self):
        self._model = None
        self._features_history: List[Dict] = []
        self._targets_history: List[float] = []
        self._logger = setup_logger("MLPredictor")
    
    def add_training_data(self, features: Dict[str, float], future_profit: float):
        """Add training data point"""
        self._features_history.append(features)
        self._targets_history.append(future_profit)
        
        # Keep only last 1000
        if len(self._features_history) > 1000:
            self._features_history = self._features_history[-1000:]
            self._targets_history = self._targets_history[-1000:]
    
    def train(self):
        """Train the prediction model"""
        if len(self._features_history) < 50:
            self._logger.warning("Insufficient data for training")
            return
        
        # Convert to numpy arrays
        X = []
        for features in self._features_history:
            # Extract feature vector
            vector = [
                features.get('win_rate', 0),
                features.get('profit_factor', 0),
                features.get('sharpe_ratio', 0),
                features.get('volatility', 0),
                features.get('consecutive_losses', 0),
                features.get('avg_win', 0),
                features.get('avg_loss', 0)
            ]
            X.append(vector)
        
        y = np.array(self._targets_history)
        
        # Simple linear regression model
        X = np.array(X)
        X_with_bias = np.c_[np.ones(X.shape[0]), X]
        
        # Least squares solution
        try:
            theta = np.linalg.lstsq(X_with_bias, y, rcond=None)[0]
            self._model = theta
            self._logger.info("ML model trained successfully")
        except Exception as e:
            self._logger.error(f"Training failed: {e}")
    
    def predict(self, features: Dict[str, float]) -> float:
        """Predict future performance"""
        if self._model is None:
            return 0.0
        
        vector = np.array([
            1,  # bias
            features.get('win_rate', 0),
            features.get('profit_factor', 0),
            features.get('sharpe_ratio', 0),
            features.get('volatility', 0),
            features.get('consecutive_losses', 0),
            features.get('avg_win', 0),
            features.get('avg_loss', 0)
        ])
        
        prediction = np.dot(vector, self._model)
        return float(prediction)
    
    def get_accuracy(self) -> float:
        """Calculate prediction accuracy"""
        if len(self._features_history) < 50 or self._model is None:
            return 0.0
        
        # Simple backtesting
        correct = 0
        total = min(50, len(self._features_history))
        
        for i in range(-total, 0):
            features = self._features_history[i]
            actual = self._targets_history[i]
            predicted = self.predict(features)
            
            if (actual > 0 and predicted > 0) or (actual < 0 and predicted < 0):
                correct += 1
        
        return (correct / total) * 100 if total > 0 else 0


# ============================================================================
# PERFORMANCE ANALYZER
# ============================================================================

class PerformanceAnalyzer:
    """Advanced trading performance analysis with machine learning"""
    
    def __init__(self, storage: TradeStorage):
        self.storage = storage
        self._logger = setup_logger("PerformanceAnalyzer")
        self._cache: Dict[str, Any] = {}
        self._ml_predictor = MLPredictor()
    
    async def analyze_period(self, 
                            days: int = 30,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> TradeMetrics:
        """Analyze trading performance over period"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=days)
        if end_date is None:
            end_date = datetime.now()
        
        trades = await self.storage.get_trades(
            start_time=start_date,
            end_time=end_date
        )
        
        if not trades:
            return TradeMetrics()
        
        df = self._trades_to_dataframe(trades)
        
        if df.empty:
            return TradeMetrics()
        
        metrics = TradeMetrics()
        metrics.total_trades = len(df)
        
        # Win/Loss analysis
        winners = df[df['profit'] > 0]
        losers = df[df['profit'] < 0]
        
        metrics.winning_trades = len(winners)
        metrics.losing_trades = len(losers)
        metrics.gross_profit = winners['profit'].sum() if not winners.empty else 0
        metrics.gross_loss = abs(losers['profit'].sum()) if not losers.empty else 0
        metrics.total_profit = metrics.gross_profit - metrics.gross_loss
        
        # Win/Loss rates
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
            metrics.loss_rate = (metrics.losing_trades / metrics.total_trades) * 100
        
        # Profit factor
        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        else:
            metrics.profit_factor = float('inf') if metrics.gross_profit > 0 else 0
        
        # Averages
        metrics.average_win = winners['profit'].mean() if not winners.empty else 0
        metrics.average_loss = abs(losers['profit'].mean()) if not losers.empty else 0
        metrics.largest_win = winners['profit'].max() if not winners.empty else 0
        metrics.largest_loss = abs(losers['profit'].min()) if not losers.empty else 0
        
        # R-multiple
        if metrics.average_loss > 0:
            metrics.average_r_multiple = metrics.average_win / metrics.average_loss
        
        # Expectancy
        if metrics.average_loss > 0:
            metrics.expectancy = (
                (metrics.win_rate / 100) * metrics.average_win -
                (metrics.loss_rate / 100) * metrics.average_loss
            )
        
        # Consecutive wins/losses
        metrics.consecutive_wins = self._max_consecutive(df, lambda x: x > 0)
        metrics.consecutive_losses = self._max_consecutive(df, lambda x: x < 0)
        
        # Equity curve and drawdown
        df = df.sort_values('close_time')
        df['cumulative_profit'] = df['profit'].cumsum()
        df['peak'] = df['cumulative_profit'].cummax()
        df['drawdown'] = df['peak'] - df['cumulative_profit']
        df['drawdown_pct'] = (df['drawdown'] / df['peak'].replace(0, np.nan)) * 100
        
        metrics.max_drawdown = df['drawdown'].max()
        metrics.max_drawdown_percentage = df['drawdown_pct'].max()
        
        # Recovery factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.total_profit / metrics.max_drawdown
        
        # Trade duration
        if 'duration' in df.columns:
            metrics.average_trade_duration = df['duration'].mean()
        
        # Risk-adjusted returns
        if len(df) > 1:
            returns = df['profit'].values
            
            # Sharpe ratio
            if returns.std() > 0:
                metrics.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
            
            # Sortino ratio
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0 and downside_returns.std() > 0:
                metrics.sortino_ratio = (returns.mean() / downside_returns.std()) * np.sqrt(252)
            
            # Calmar ratio
            if metrics.max_drawdown_percentage > 0:
                annual_return = returns.mean() * 252
                metrics.calmar_ratio = annual_return / (metrics.max_drawdown_percentage / 100)
            
            # VaR and Expected Shortfall
            metrics.var_95 = np.percentile(returns, 5)
            metrics.expected_shortfall = returns[returns <= metrics.var_95].mean() if len(returns[returns <= metrics.var_95]) > 0 else metrics.var_95
        
        # Best/Worst assets
        asset_performance = df.groupby('asset')['profit'].agg(['sum', 'count'])
        if not asset_performance.empty:
            best_idx = asset_performance['sum'].idxmax()
            worst_idx = asset_performance['sum'].idxmin()
            metrics.best_asset = str(best_idx) if best_idx else ""
            metrics.worst_asset = str(worst_idx) if worst_idx else ""
        
        # Train ML predictor
        features = {
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'sharpe_ratio': metrics.sharpe_ratio,
            'volatility': returns.std() if len(df) > 1 else 0,
            'consecutive_losses': metrics.consecutive_losses,
            'avg_win': metrics.average_win,
            'avg_loss': metrics.average_loss
        }
        
        self._ml_predictor.add_training_data(features, metrics.total_profit)
        self._ml_predictor.train()
        
        return metrics

    def _trades_to_dataframe(self, trades: List) -> pd.DataFrame:
        """
        Convert trades list to DataFrame
        Handles both Deal (from models) and Trade (from trading)
        """
        data = []
        for t in trades:
            # Check that close_time and profit exist
            if not hasattr(t, 'close_time') or not hasattr(t, 'profit'):
                continue

            if t.close_time and t.profit is not None:
                # Extract direction (direction/command)
                direction = 'unknown'
                if hasattr(t, 'command'):
                    # Deal object from models.py
                    if hasattr(t.command, 'name'):
                        direction = t.command.name
                    else:
                        direction = str(t.command)
                elif hasattr(t, 'direction'):
                    # Trade object from trading.py
                    direction = t.direction

                # Extract asset name
                asset_name = ''
                if hasattr(t, 'asset'):
                    if hasattr(t.asset, 'value'):
                        asset_name = t.asset.value
                    else:
                        asset_name = str(t.asset)

                trade_data = {
                    'profit': t.profit,
                    'amount': getattr(t, 'amount', 0),
                    'asset': asset_name,
                    'direction': direction,
                    'open_time': t.open_time,
                    'close_time': t.close_time,
                }

                # Calculate duration if available
                if t.close_time and t.open_time:
                    trade_data['duration'] = (t.close_time - t.open_time).total_seconds()

                data.append(trade_data)

        return pd.DataFrame(data) if data else pd.DataFrame()
    
    def _max_consecutive(self, df: pd.DataFrame, condition) -> int:
        """Calculate maximum consecutive occurrences"""
        if df.empty:
            return 0
        
        mask = condition(df['profit']).astype(int)
        max_consecutive = 0
        current = 0
        
        for val in mask:
            if val:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0
        
        return max_consecutive

    async def best_assets(self, days: int = 30, min_trades: int = 5, top_n: int = 5) -> pd.DataFrame:
        """Find best performing assets"""
        trades = await self.storage.get_trades(
            start_time=datetime.now() - timedelta(days=days)
        )

        if not trades:
            return pd.DataFrame()

        df = self._trades_to_dataframe(trades)

        if df.empty:
            return pd.DataFrame()

        # Group by asset
        grouped = df.groupby('asset').agg({
            'profit': ['sum', 'count', 'mean'],
            'amount': 'sum'
        }).round(2)

        grouped.columns = ['total_profit', 'trades', 'avg_profit', 'total_volume']
        grouped = grouped[grouped['trades'] >= min_trades]

        # Add win rate
        win_rates = []
        for asset in grouped.index:
            asset_trades = df[df['asset'] == asset]
            win_rate = (asset_trades[asset_trades['profit'] > 0].shape[0] / len(asset_trades)) * 100
            win_rates.append(round(win_rate, 2))

        grouped['win_rate'] = win_rates
        grouped = grouped.sort_values('total_profit', ascending=False)

        return grouped.head(top_n)
    
    async def time_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Analyze performance by time (hour of day, day of week)"""
        trades = await self.storage.get_trades(
            start_time=datetime.now() - timedelta(days=days)
        )
        
        if not trades:
            return {}
        
        df = self._trades_to_dataframe(trades)
        
        if df.empty:
            return {}
        
        df['hour'] = df['close_time'].dt.hour
        df['day'] = df['close_time'].dt.day_name()
        df['week'] = df['close_time'].dt.isocalendar().week
        
        hourly = df.groupby('hour').agg({
            'profit': ['sum', 'count', 'mean']
        }).round(2)
        hourly.columns = ['total_profit', 'trades', 'avg_profit']
        
        daily = df.groupby('day').agg({
            'profit': ['sum', 'count', 'mean']
        }).round(2)
        daily.columns = ['total_profit', 'trades', 'avg_profit']
        
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily = daily.reindex([d for d in day_order if d in daily.index])
        
        best_hour = hourly['total_profit'].idxmax() if not hourly.empty else None
        worst_hour = hourly['total_profit'].idxmin() if not hourly.empty else None
        
        return {
            'hourly': hourly.to_dict() if not hourly.empty else {},
            'daily': daily.to_dict() if not daily.empty else {},
            'best_hour': int(best_hour) if best_hour is not None else None,
            'worst_hour': int(worst_hour) if worst_hour is not None else None,
            'best_day': daily['total_profit'].idxmax() if not daily.empty else None,
            'worst_day': daily['total_profit'].idxmin() if not daily.empty else None,
        }
    
    async def generate_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive performance report with ML insights"""
        self._logger.info(f"Generating report for last {days} days")
        
        metrics = await self.analyze_period(days)
        best_assets = await self.best_assets(days)
        time_analysis = await self.time_analysis(days)
        
        trades = await self.storage.get_trades(
            start_time=datetime.now() - timedelta(days=days)
        )
        
        df = self._trades_to_dataframe(trades)
        equity_curve = []
        
        if not df.empty:
            df = df.sort_values('close_time')
            df['cumulative'] = df['profit'].cumsum()
            equity_curve = [
                {'date': row['close_time'].isoformat(), 'equity': row['cumulative']}
                for _, row in df.iterrows()
            ]
        
        # ML predictions
        features = {
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'sharpe_ratio': metrics.sharpe_ratio,
            'volatility': df['profit'].std() if not df.empty else 0,
            'consecutive_losses': metrics.consecutive_losses,
            'avg_win': metrics.average_win,
            'avg_loss': metrics.average_loss
        }
        
        future_prediction = self._ml_predictor.predict(features)
        ml_accuracy = self._ml_predictor.get_accuracy()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'metrics': metrics.to_dict(),
            'best_assets': best_assets.to_dict() if not best_assets.empty else {},
            'time_analysis': time_analysis,
            'equity_curve': equity_curve,
            'summary': self._generate_summary(metrics),
            'recommendations': self._generate_recommendations(metrics, time_analysis),
            'ml_predictions': {
                'next_period_profit': round(future_prediction, 2),
                'model_accuracy': round(ml_accuracy, 2)
            }
        }
        
        return report
    
    def _generate_summary(self, metrics: TradeMetrics) -> str:
        """Generate human-readable summary"""
        lines = [
            f"📊 Performance Summary",
            f"====================",
            f"Total Trades: {metrics.total_trades}",
            f"Win Rate: {metrics.win_rate:.1f}% ({metrics.winning_trades}W / {metrics.losing_trades}L)",
            f"Profit Factor: {metrics.profit_factor:.2f}",
            f"Net Profit: ${metrics.total_profit:.2f}",
            f"Average Win: ${metrics.average_win:.2f} | Average Loss: ${metrics.average_loss:.2f}",
            f"Largest Win: ${metrics.largest_win:.2f} | Largest Loss: ${metrics.largest_loss:.2f}",
            f"Max Drawdown: {metrics.max_drawdown_percentage:.1f}% (${metrics.max_drawdown:.2f})",
            f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
            f"Sortino Ratio: {metrics.sortino_ratio:.2f}",
            f"VaR 95%: ${metrics.var_95:.2f}",
            f"Expected Shortfall: ${metrics.expected_shortfall:.2f}",
            f"Expectancy: ${metrics.expectancy:.2f} per trade",
            f"Best Asset: {metrics.best_asset} | Worst: {metrics.worst_asset}",
        ]
        return "\n".join(lines)
    
    def _generate_recommendations(self, metrics: TradeMetrics, time_analysis: Dict) -> List[str]:
        """Generate trading recommendations"""
        recommendations = []
        
        if metrics.win_rate < 40:
            recommendations.append("⚠️ Low win rate - Consider reviewing entry strategy")
        
        if metrics.profit_factor < 1.5:
            recommendations.append("⚠️ Profit factor below 1.5 - Risk management needs improvement")
        
        if metrics.max_drawdown_percentage > 20:
            recommendations.append("⚠️ High drawdown - Consider reducing position sizes")
        
        if metrics.consecutive_losses > 3:
            recommendations.append(f"⚠️ {metrics.consecutive_losses} consecutive losses - Consider taking a break")
        
        if metrics.sharpe_ratio < 0.5:
            recommendations.append("⚠️ Low risk-adjusted returns - Review strategy efficiency")
        
        if time_analysis.get('best_hour') is not None:
            recommendations.append(f"💡 Best trading hour: {time_analysis['best_hour']}:00")
        
        if time_analysis.get('best_day') is not None:
            recommendations.append(f"💡 Best trading day: {time_analysis['best_day']}")
        
        if not recommendations:
            recommendations.append("✅ All metrics look good - Keep up the good work!")
        
        return recommendations
    
    async def save_report(self, filepath: str, days: int = 30):
        """Save report to file"""
        report = await self.generate_report(days)
        
        path = Path(filepath)
        path.parent.mkdir(exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self._logger.info(f"📄 Report saved to {filepath}")
        
        text_path = path.with_suffix('.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(report['summary'])
            f.write("\n\nML Predictions:\n")
            f.write(f"Next Period Profit: ${report['ml_predictions']['next_period_profit']:.2f}\n")
            f.write(f"Model Accuracy: {report['ml_predictions']['model_accuracy']:.1f}%\n")
        
        self._logger.info(f"📄 Summary saved to {text_path}")
    
    async def get_ml_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get machine learning insights about trading performance"""
        metrics = await self.analyze_period(days)
        
        features = {
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'sharpe_ratio': metrics.sharpe_ratio,
            'volatility': 0,  # Will be calculated
            'consecutive_losses': metrics.consecutive_losses,
            'avg_win': metrics.average_win,
            'avg_loss': metrics.average_loss
        }
        
        prediction = self._ml_predictor.predict(features)
        accuracy = self._ml_predictor.get_accuracy()
        
        return {
            'next_period_profit_prediction': round(prediction, 2),
            'model_confidence': round(accuracy, 2),
            'is_reliable': accuracy > 60,
            'features_used': list(features.keys())
        }


# ============================================================================
# PERFORMANCE MONITOR
# ============================================================================

class PerformanceMonitor:
    """Real-time performance monitoring with alerts"""
    
    def __init__(self, storage: TradeStorage, alert_callback: Optional[Callable] = None):
        self.storage = storage
        self.alert_callback = alert_callback
        self.metrics_history: Dict[str, deque] = {}
        self.alerts: List[Dict] = []
        self._monitoring = False
        self._task = None
        self._logger = setup_logger("PerformanceMonitor")
    
    async def start(self, interval: float = 60.0):
        """Start monitoring"""
        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop(interval))
        self._logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    async def stop(self):
        """Stop monitoring"""
        self._monitoring = False
        if self._task:
            self._task.cancel()
            self._task = None
        self._logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                await asyncio.sleep(interval)
                await self._check_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Monitor error: {e}")
    
    async def _check_metrics(self):
        """Check current metrics and trigger alerts"""
        trades = await self.storage.get_trades(
            start_time=datetime.now() - timedelta(hours=1),
            limit=100
        )
        
        if not trades:
            return
        
        total = len(trades)
        wins = len([t for t in trades if t.profit and t.profit > 0])
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Store metrics
        if 'win_rate' not in self.metrics_history:
            self.metrics_history['win_rate'] = deque(maxlen=100)
        self.metrics_history['win_rate'].append(win_rate)
        
        # Check for anomalies
        if win_rate < 30 and len(self.metrics_history['win_rate']) > 10:
            await self._trigger_alert(
                "LOW_WIN_RATE",
                f"Win rate dropped to {win_rate:.1f}%",
                {'win_rate': win_rate, 'trades': total}
            )
        
        # Check for high frequency
        if total > 50 and 'win_rate' in self.metrics_history:
            avg_freq = sum(self.metrics_history['win_rate']) / len(self.metrics_history['win_rate'])
            if total > avg_freq * 2:
                await self._trigger_alert(
                    "HIGH_TRADE_FREQUENCY",
                    f"Trade frequency spiked: {total} trades in last hour",
                    {'trades': total, 'avg': avg_freq}
                )
    
    async def _trigger_alert(self, code: str, message: str, data: Dict):
        """Trigger an alert"""
        alert = {
            'code': code,
            'message': message,
            'data': data,
            'timestamp': time.time()
        }
        self.alerts.append(alert)
        
        if self.alert_callback:
            try:
                await self.alert_callback(alert)
            except Exception as e:
                self._logger.error(f"Alert callback error: {e}")
        
        self._logger.warning(f"⚠️ ALERT: {code} - {message}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            'monitoring': self._monitoring,
            'alerts_count': len(self.alerts),
            'recent_alerts': self.alerts[-5:],
            'metrics': {k: list(v) for k, v in self.metrics_history.items()}
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "PerformanceAnalyzer",
    "TradeMetrics",
    "PerformanceMonitor",
    "MLPredictor",
]