# risk.py
"""
Advanced risk management system with position sizing, drawdown control,
and AI-powered risk assessment
"""

import math
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
import asyncio

from .utils import setup_logger


@dataclass
class RiskMetrics:
    """Risk metrics snapshot"""
    current_balance: float
    daily_pnl: float
    daily_trades: int
    open_trades: int
    consecutive_losses: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    risk_per_trade: float
    recommended_position: float
    is_safe_to_trade: bool
    safety_reason: str = "OK"


# ============================================================================
# AI-POWERED RISK ASSESSMENT
# ============================================================================

class AIRiskAssessor:
    """
    AI-powered risk assessment using market volatility and pattern recognition
    """
    
    def __init__(self):
        self._volatility_history: deque = deque(maxlen=100)
        self._market_regimes: deque = deque(maxlen=50)
        self._logger = setup_logger("AIRiskAssessor")
    
    def update(self, volatility: float, market_regime: str):
        """Update market conditions"""
        self._volatility_history.append(volatility)
        self._market_regimes.append(market_regime)
    
    def assess_risk_level(self) -> Dict[str, Any]:
        """
        Assess current risk level using AI
        Returns risk level and suggested position multiplier
        """
        if not self._volatility_history:
            return {'risk_level': 'normal', 'multiplier': 1.0, 'confidence': 0.5}
        
        # Analyze volatility trend
        recent_vol = list(self._volatility_history)[-10:]
        vol_trend = np.polyfit(range(len(recent_vol)), recent_vol, 1)[0] if len(recent_vol) > 1 else 0
        
        # Analyze market regime stability
        regime_counts = {}
        for regime in self._market_regimes:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        most_common_regime = max(regime_counts.items(), key=lambda x: x[1])[0] if regime_counts else 'unknown'
        regime_stability = regime_counts.get(most_common_regime, 0) / len(self._market_regimes) if self._market_regimes else 0.5
        
        # Calculate risk score (0-1, higher = more risk)
        vol_score = min(1.0, np.mean(recent_vol) / 0.03)  # 3% volatility = high risk
        trend_score = max(0, min(1, vol_trend * 100))  # Positive trend = increasing risk
        regime_score = 1 - regime_stability  # Unstable regime = higher risk
        
        risk_score = (vol_score * 0.4 + trend_score * 0.3 + regime_score * 0.3)
        
        # Determine risk level
        if risk_score > 0.7:
            risk_level = 'extreme'
            multiplier = 0.3
        elif risk_score > 0.5:
            risk_level = 'high'
            multiplier = 0.6
        elif risk_score > 0.3:
            risk_level = 'moderate'
            multiplier = 0.8
        elif risk_score > 0.15:
            risk_level = 'normal'
            multiplier = 1.0
        else:
            risk_level = 'low'
            multiplier = 1.2
        
        return {
            'risk_level': risk_level,
            'multiplier': multiplier,
            'confidence': 1.0 - risk_score,
            'risk_score': risk_score,
            'volatility_score': vol_score,
            'trend_score': trend_score,
            'regime_stability': regime_stability
        }


# ============================================================================
# PORTFOLIO MANAGER (Multi-Asset)
# ============================================================================

class PortfolioManager:
    """
    Multi-asset portfolio management with dynamic allocation
    """
    
    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        self.allocations: Dict[str, float] = {}
        self.performance: Dict[str, Dict] = {}
        self._correlation_matrix: Optional[np.ndarray] = None
        self._assets_list: List[str] = []
        self._logger = setup_logger("PortfolioManager")
    
    def add_asset(self, asset: str, allocation_percent: float):
        """Add asset with allocation percentage"""
        self.allocations[asset] = allocation_percent
        self.performance[asset] = {
            'trades': 0,
            'wins': 0,
            'profit': 0.0,
            'allocation': allocation_percent,
            'returns': []
        }
        self._assets_list.append(asset)
        self._logger.info(f"Added {asset} with {allocation_percent:.1f}% allocation")
    
    def update_performance(self, asset: str, profit: float, was_win: bool):
        """Update performance metrics for an asset"""
        if asset not in self.performance:
            self.performance[asset] = {'trades': 0, 'wins': 0, 'profit': 0.0, 'returns': []}
        
        self.performance[asset]['trades'] += 1
        self.performance[asset]['profit'] += profit
        self.performance[asset]['returns'].append(profit)
        
        if was_win:
            self.performance[asset]['wins'] += 1
        
        # Keep last 100 returns
        if len(self.performance[asset]['returns']) > 100:
            self.performance[asset]['returns'] = self.performance[asset]['returns'][-100:]
    
    def calculate_correlation(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlation between assets"""
        if len(self._assets_list) < 2:
            return {}
        
        returns_matrix = []
        valid_assets = []
        
        for asset in self._assets_list:
            returns = self.performance[asset]['returns']
            if len(returns) > 20:
                returns_matrix.append(returns[-20:])
                valid_assets.append(asset)
        
        if len(valid_assets) < 2:
            return {}
        
        returns_array = np.array(returns_matrix).T
        correlation = np.corrcoef(returns_array.T)
        
        result = {}
        for i, asset1 in enumerate(valid_assets):
            result[asset1] = {}
            for j, asset2 in enumerate(valid_assets):
                result[asset1][asset2] = float(correlation[i, j])
        
        return result
    
    def rebalance(self, use_correlation: bool = True):
        """Rebalance allocations based on performance and correlation"""
        total_profit = sum(p['profit'] for p in self.performance.values())
        
        if total_profit == 0:
            return
        
        # Calculate new allocations based on performance
        for asset, perf in self.performance.items():
            if perf['trades'] > 0:
                profit_ratio = perf['profit'] / total_profit if total_profit != 0 else 0
                performance_factor = 1 + profit_ratio * 0.5
                new_allocation = self.allocations.get(asset, 0) * performance_factor
                self.allocations[asset] = min(50, max(5, new_allocation))
        
        # Adjust for correlation (reduce allocation for correlated assets)
        if use_correlation:
            correlation = self.calculate_correlation()
            for asset1 in self.allocations:
                for asset2 in self.allocations:
                    if asset1 != asset2 and asset1 in correlation and asset2 in correlation[asset1]:
                        corr = abs(correlation[asset1][asset2])
                        if corr > 0.7:
                            # Reduce allocation for highly correlated assets
                            reduction = 1 - (corr - 0.7) / 0.3 * 0.5
                            self.allocations[asset1] *= reduction
        
        # Normalize to 100%
        total = sum(self.allocations.values())
        if total > 0:
            for asset in self.allocations:
                self.allocations[asset] = (self.allocations[asset] / total) * 100
        
        self._logger.info("Portfolio rebalanced")
    
    def get_capital_for_asset(self, asset: str) -> float:
        """Get capital allocated to an asset"""
        allocation = self.allocations.get(asset, 0) / 100
        return self.total_capital * allocation
    
    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Get portfolio statistics"""
        total_trades = sum(p['trades'] for p in self.performance.values())
        total_profit = sum(p['profit'] for p in self.performance.values())
        total_wins = sum(p['wins'] for p in self.performance.values())
        
        # Calculate diversification score
        allocation_entropy = 0
        for alloc in self.allocations.values():
            if alloc > 0:
                p = alloc / 100
                allocation_entropy -= p * math.log(p)
        max_entropy = math.log(len(self.allocations)) if self.allocations else 1
        diversification_score = allocation_entropy / max_entropy if max_entropy > 0 else 0
        
        return {
            'total_capital': self.total_capital,
            'total_trades': total_trades,
            'total_profit': total_profit,
            'total_wins': total_wins,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'diversification_score': diversification_score,
            'assets': {
                asset: {
                    'allocation': self.allocations.get(asset, 0),
                    'trades': perf['trades'],
                    'profit': perf['profit'],
                    'win_rate': (perf['wins'] / perf['trades'] * 100) if perf['trades'] > 0 else 0
                }
                for asset, perf in self.performance.items()
            }
        }
    
    def get_best_asset(self) -> Optional[str]:
        """Get best performing asset"""
        if not self.performance:
            return None
        
        return max(self.performance.items(),
                   key=lambda x: x[1]['profit'] if x[1]['trades'] > 0 else -float('inf'))[0]
    
    def get_worst_asset(self) -> Optional[str]:
        """Get worst performing asset"""
        if not self.performance:
            return None
        
        return min(self.performance.items(),
                   key=lambda x: x[1]['profit'] if x[1]['trades'] > 0 else float('inf'))[0]


# ============================================================================
# MAIN RISK MANAGER
# ============================================================================

class RiskManager:
    """
    Advanced risk management system with Kelly Criterion, Martingale control,
    AI risk assessment, and drawdown protection
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.daily_trades = 0
        self.open_trades: List[str] = []
        self.total_wins = 0
        self.total_losses = 0
        
        # Performance tracking
        self.trade_history: deque = deque(maxlen=1000)
        self.equity_curve: deque = deque(maxlen=1000)
        self.drawdown_history: deque = deque(maxlen=100)
        self.daily_returns: List[float] = []
        
        self._last_reset = date.today()
        self._logger = setup_logger("RiskManager")
        
        # AI components
        self._ai_assessor = AIRiskAssessor()
        self._portfolio_manager: Optional[PortfolioManager] = None
        
        # Default limits
        self.max_risk_per_trade = 0.02
        self.max_daily_risk = 0.06
        self.max_consecutive_losses = 3
        self.max_daily_trades = 20
        self.max_open_trades = 5
        self.max_drawdown_percent = 20
        
        # Advanced settings
        self.use_kelly = True
        self.kelly_fraction = 0.25
        self.use_anti_martingale = False
        self.martingale_multiplier = 2.0
        self.use_ai_risk_assessment = True
        self.use_dynamic_stop = True
        
        # Volatility adjustment
        self.volatility_factor = 1.0
        self.volatility_history: deque = deque(maxlen=20)
    
    def set_portfolio_manager(self, portfolio: PortfolioManager):
        """Set portfolio manager for multi-asset support"""
        self._portfolio_manager = portfolio
    
    def _check_daily_reset(self):
        """Reset daily counters if new day"""
        today = date.today()
        if today != self._last_reset:
            self._logger.info(f"📅 Daily reset - Previous PnL: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.consecutive_losses = 0
            self.daily_returns.append(self.daily_pnl)
            if len(self.daily_returns) > 30:
                self.daily_returns = self.daily_returns[-30:]
            self._last_reset = today
    
    def update_peak(self):
        """Update peak balance for drawdown calculation"""
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
    
    def get_current_drawdown(self) -> Tuple[float, float]:
        """Get current drawdown (absolute and percentage)"""
        if self.peak_balance == 0:
            return 0.0, 0.0
        drawdown_abs = self.peak_balance - self.current_balance
        drawdown_pct = (drawdown_abs / self.peak_balance) * 100
        return drawdown_abs, drawdown_pct
    
    def get_max_drawdown(self) -> Tuple[float, float]:
        """Get maximum historical drawdown"""
        if not self.equity_curve:
            return 0.0, 0.0
        
        max_dd_abs = 0.0
        max_dd_pct = 0.0
        peak = self.initial_balance
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            else:
                dd_abs = peak - equity
                dd_pct = (dd_abs / peak) * 100 if peak > 0 else 0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_abs = dd_abs
        
        return max_dd_abs, max_dd_pct
    
    def calculate_var(self, confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if len(self.trade_history) < 30:
            return self.current_balance * 0.05
        
        returns = list(self.trade_history)
        returns_array = np.array(returns)
        var = np.percentile(returns_array, (1 - confidence) * 100)
        return abs(var)
    
    def calculate_expected_shortfall(self, confidence: float = 0.95) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(self.trade_history) < 30:
            return self.current_balance * 0.07
        
        returns = list(self.trade_history)
        returns_array = np.array(returns)
        var_threshold = np.percentile(returns_array, (1 - confidence) * 100)
        tail_returns = returns_array[returns_array <= var_threshold]
        
        if len(tail_returns) == 0:
            return var_threshold
        
        return abs(np.mean(tail_returns))
    
    def can_trade(self, check_limits: bool = True, asset: Optional[str] = None) -> Tuple[bool, str]:
        """Check if trading is allowed based on all risk parameters"""
        self._check_daily_reset()
        self.update_peak()
        
        # Check drawdown limit
        _, dd_pct = self.get_current_drawdown()
        if dd_pct > self.max_drawdown_percent:
            reason = f"Max drawdown reached ({dd_pct:.1f}% > {self.max_drawdown_percent}%)"
            self._logger.warning(f"⚠️ {reason}")
            return False, reason
        
        # Check portfolio allocation if asset specified
        if asset and self._portfolio_manager:
            capital = self._portfolio_manager.get_capital_for_asset(asset)
            if capital < self.min_trade_amount:
                reason = f"Insufficient capital allocated to {asset}"
                return False, reason
        
        if check_limits:
            # Check daily loss limit
            max_daily_loss = self.initial_balance * self.max_daily_risk
            if self.daily_pnl <= -max_daily_loss:
                reason = f"Daily loss limit reached (${self.daily_pnl:.2f} / ${max_daily_loss:.2f})"
                self._logger.warning(f"⚠️ {reason}")
                return False, reason
            
            # Check consecutive losses
            if self.consecutive_losses >= self.max_consecutive_losses:
                reason = f"Max consecutive losses ({self.consecutive_losses})"
                self._logger.warning(f"⚠️ {reason}")
                return False, reason
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                reason = f"Daily trade limit ({self.daily_trades}/{self.max_daily_trades})"
                self._logger.warning(f"⚠️ {reason}")
                return False, reason
            
            # Check open trades limit
            if len(self.open_trades) >= self.max_open_trades:
                reason = f"Max open trades ({len(self.open_trades)}/{self.max_open_trades})"
                self._logger.warning(f"⚠️ {reason}")
                return False, reason
        
        return True, "OK"
    
    def calculate_position_size(self, confidence: float = 1.0, 
                               volatility: Optional[float] = None,
                               asset: Optional[str] = None) -> float:
        """Calculate optimal position size based on multiple factors"""
        
        # Get available capital for asset
        available_capital = self.current_balance
        if asset and self._portfolio_manager:
            available_capital = self._portfolio_manager.get_capital_for_asset(asset)
        
        # Base risk amount
        base_risk = available_capital * self.max_risk_per_trade
        
        # AI risk assessment
        ai_multiplier = 1.0
        if self.use_ai_risk_assessment:
            risk_assessment = self._ai_assessor.assess_risk_level()
            ai_multiplier = risk_assessment['multiplier']
            self._logger.debug(f"🤖 AI Risk Multiplier: {ai_multiplier:.2f}")
        
        # Adjust for consecutive losses
        if self.consecutive_losses > 0:
            reduction = 1 - (self.consecutive_losses * 0.25)
            base_risk *= max(0.25, reduction)
        
        # Adjust for consecutive wins (anti-martingale)
        if self.use_anti_martingale and self.consecutive_wins > 1:
            increase = 1 + (self.consecutive_wins * 0.1)
            base_risk *= min(2.0, increase)
        
        # Kelly Criterion
        if self.use_kelly and len(self.trade_history) >= 20:
            kelly_size = self._calculate_kelly_size()
            if kelly_size > 0:
                base_risk = min(base_risk, kelly_size)
        
        # Volatility adjustment
        if volatility is not None and volatility > 0:
            normal_volatility = 0.01
            vol_factor = normal_volatility / volatility
            base_risk *= vol_factor
        
        # Apply AI multiplier
        base_risk *= ai_multiplier
        
        # Apply confidence factor
        base_risk *= max(0.1, min(1.0, confidence))
        
        # Round appropriately
        if base_risk < 10:
            return round(base_risk, 2)
        elif base_risk < 100:
            return round(base_risk, 1)
        else:
            return round(base_risk)
    
    def _calculate_kelly_size(self) -> float:
        """Calculate position size using Kelly Criterion"""
        if len(self.trade_history) < 20:
            return 0.0
        
        wins = [t for t in self.trade_history if t > 0]
        losses = [t for t in self.trade_history if t < 0]
        
        if not wins or not losses:
            return 0.0
        
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        
        if avg_loss == 0:
            return 0.0
        
        b = avg_win / avg_loss
        kelly = (win_rate * b - (1 - win_rate)) / b
        
        kelly = max(0.0, min(kelly * self.kelly_fraction, self.max_risk_per_trade))
        
        return self.current_balance * kelly
    
    def calculate_martingale_size(self, base_size: float) -> float:
        """Calculate martingale position size after loss"""
        if self.consecutive_losses == 0:
            return base_size
        
        multiplier = self.martingale_multiplier ** self.consecutive_losses
        multiplier = min(multiplier, 5.0)
        
        martingale_size = base_size * multiplier
        
        if martingale_size > self.current_balance * 0.5:
            return base_size
        
        return martingale_size
    
    def add_trade(self, trade_id: str, amount: float, asset: Optional[str] = None):
        """Add trade to open trades"""
        self.open_trades.append(trade_id)
        self.daily_trades += 1
        
        self.volatility_history.append(amount)
        if len(self.volatility_history) > 5:
            self.volatility_factor = np.std(self.volatility_history) / np.mean(self.volatility_history)
    
    def remove_trade(self, trade_id: str):
        """Remove trade from open trades"""
        if trade_id in self.open_trades:
            self.open_trades.remove(trade_id)
    
    def update_trade_result(self, profit: float, trade_id: Optional[str] = None,
                           asset: Optional[str] = None, market_regime: Optional[str] = None):
        """Update metrics with trade result"""
        self._check_daily_reset()
        
        # Update balances
        self.daily_pnl += profit
        self.current_balance += profit
        
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Add to history
        self.trade_history.append(profit)
        self.equity_curve.append(self.current_balance)
        
        # Update drawdown history
        _, dd_pct = self.get_current_drawdown()
        self.drawdown_history.append(dd_pct)
        
        # Update portfolio manager
        if asset and self._portfolio_manager:
            self._portfolio_manager.update_performance(asset, profit, profit > 0)
        
        # Update AI assessor
        if market_regime and self.use_ai_risk_assessment:
            volatility = abs(profit) / self.current_balance if self.current_balance > 0 else 0
            self._ai_assessor.update(volatility, market_regime)
        
        # Update win/loss counters
        if profit > 0:
            self.total_wins += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.total_losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Remove from open trades
        if trade_id:
            self.remove_trade(trade_id)
    
    def get_metrics(self) -> RiskMetrics:
        """Get comprehensive risk metrics"""
        self._check_daily_reset()
        self.update_peak()
        
        total_trades = self.total_wins + self.total_losses
        win_rate = (self.total_wins / total_trades * 100) if total_trades > 0 else 0.0
        
        gross_profit = sum(p for p in self.trade_history if p > 0)
        gross_loss = abs(sum(p for p in self.trade_history if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio
        sharpe = 0.0
        if len(self.trade_history) >= 20:
            returns = list(self.trade_history)
            if np.std(returns) > 0:
                sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        
        # Sortino ratio
        sortino = 0.0
        if len(self.trade_history) >= 20:
            returns = list(self.trade_history)
            downside = [r for r in returns if r < 0]
            if downside and np.std(downside) > 0:
                sortino = (np.mean(returns) / np.std(downside)) * np.sqrt(252)
        
        # Calmar ratio
        _, max_dd_pct = self.get_max_drawdown()
        annual_return = np.mean(self.trade_history) * 252 if self.trade_history else 0
        calmar = annual_return / (max_dd_pct / 100) if max_dd_pct > 0 else 0
        
        # VaR and Expected Shortfall
        var_95 = self.calculate_var(0.95)
        expected_shortfall = self.calculate_expected_shortfall(0.95)
        
        # AI risk assessment
        ai_risk = self._ai_assessor.assess_risk_level() if self.use_ai_risk_assessment else {}
        
        # Recommended position size
        recommended = self.calculate_position_size()
        
        # Safety check
        safe, reason = self.can_trade()
        
        return RiskMetrics(
            current_balance=round(self.current_balance, 2),
            daily_pnl=round(self.daily_pnl, 2),
            daily_trades=self.daily_trades,
            open_trades=len(self.open_trades),
            consecutive_losses=self.consecutive_losses,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            max_drawdown=round(max_dd_pct, 2),
            var_95=round(var_95, 2),
            expected_shortfall=round(expected_shortfall, 2),
            risk_per_trade=round(self.max_risk_per_trade * 100, 1),
            recommended_position=round(recommended, 2),
            is_safe_to_trade=safe,
            safety_reason=reason
        )
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics for analysis"""
        metrics = self.get_metrics()
        
        # Calculate additional stats
        if self.trade_history:
            returns = np.array(self.trade_history)
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            stats = {
                **asdict(metrics),
                'total_profit': round(self.current_balance - self.initial_balance, 2),
                'total_trades': len(self.trade_history),
                'average_win': round(np.mean(positive_returns), 2) if len(positive_returns) > 0 else 0,
                'average_loss': round(abs(np.mean(negative_returns)), 2) if len(negative_returns) > 0 else 0,
                'largest_win': round(np.max(positive_returns), 2) if len(positive_returns) > 0 else 0,
                'largest_loss': round(abs(np.min(negative_returns)), 2) if len(negative_returns) > 0 else 0,
                'win_loss_ratio': round(abs(np.mean(positive_returns) / np.mean(negative_returns)), 2) 
                                  if len(negative_returns) > 0 and np.mean(negative_returns) != 0 else float('inf'),
                'volatility': round(np.std(returns), 2),
                'kelly_percentage': round(self._calculate_kelly_size() / self.current_balance * 100, 2) 
                                   if self.current_balance > 0 else 0,
            }
        else:
            stats = asdict(metrics)
        
        # Add AI risk assessment
        if self.use_ai_risk_assessment:
            stats['ai_risk_assessment'] = self._ai_assessor.assess_risk_level()
        
        return stats
    
    def get_trade_recommendation(self, confidence: float = 1.0, 
                                 asset: Optional[str] = None) -> Dict[str, Any]:
        """Get trading recommendation with position size and reasoning"""
        safe, reason = self.can_trade(asset=asset)
        
        if not safe:
            return {
                'can_trade': False,
                'reason': reason,
                'position_size': 0,
                'risk_level': 'high',
                'suggestion': 'Stop trading until conditions improve'
            }
        
        position_size = self.calculate_position_size(confidence, asset=asset)
        
        # AI risk assessment
        ai_risk = self._ai_assessor.assess_risk_level() if self.use_ai_risk_assessment else {}
        
        # Determine risk level
        if self.consecutive_losses >= 2:
            risk_level = 'high'
            suggestion = 'Reduce position size and be cautious'
        elif self.consecutive_wins >= 3:
            risk_level = 'moderate'
            suggestion = 'Good momentum, consider trailing stops'
        else:
            risk_level = 'normal'
            suggestion = 'Normal trading conditions'
        
        # Adjust for AI risk assessment
        if ai_risk.get('risk_level') == 'extreme':
            risk_level = 'extreme'
            suggestion = 'Extreme market conditions - Consider stopping'
            position_size *= 0.3
        elif ai_risk.get('risk_level') == 'high':
            risk_level = 'high'
            suggestion = 'High market risk - Reduce size'
            position_size *= 0.6
        
        # Adjust for drawdown
        _, dd_pct = self.get_current_drawdown()
        if dd_pct > 10:
            risk_level = 'very_high'
            suggestion = 'Significant drawdown - Consider stopping'
        
        return {
            'can_trade': True,
            'position_size': round(position_size, 2),
            'risk_level': risk_level,
            'suggestion': suggestion,
            'metrics': self.get_metrics(),
            'drawdown_percent': round(dd_pct, 2),
            'ai_risk_assessment': ai_risk
        }
    
    def update_market_conditions(self, volatility: float, market_regime: str):
        """Update market conditions for AI assessment"""
        if self.use_ai_risk_assessment:
            self._ai_assessor.update(volatility, market_regime)
    
    def reset(self):
        """Reset all metrics (for new trading session)"""
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.daily_trades = 0
        self.open_trades.clear()
        self.total_wins = 0
        self.total_losses = 0
        self.trade_history.clear()
        self.equity_curve.clear()
        self.drawdown_history.clear()
        self.volatility_history.clear()
        self._last_reset = date.today()
        self._logger.info("🔄 Risk manager reset")
    
    def set_limits(self, **kwargs):
        """Set risk limits dynamically"""
        valid_keys = [
            'max_risk_per_trade', 'max_daily_risk', 'max_consecutive_losses',
            'max_daily_trades', 'max_open_trades', 'max_drawdown_percent',
            'use_kelly', 'kelly_fraction', 'use_anti_martingale',
            'use_ai_risk_assessment', 'martingale_multiplier'
        ]
        
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
                self._logger.info(f"⚙️ Set {key} = {value}")
            else:
                self._logger.warning(f"⚠️ Unknown limit: {key}")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "RiskManager",
    "RiskMetrics",
    "PortfolioManager",
    "AIRiskAssessor",
]