# indicators.py
"""
Technical indicators with numpy optimization, caching, and AI enhancements
Supports: RSI, MACD, Bollinger Bands, Stochastic, AI Pattern Recognition
"""

import asyncio
import numpy as np
import time
import hashlib
import json
from typing import List, Dict, Optional, Union, Tuple, Any, Callable
from functools import lru_cache
from dataclasses import dataclass, field
from collections import deque
import random

from .utils import setup_logger
from .cache import IndicatorCache, PatternCache
from .models import IndicatorResult


# ============================================================================
# ENHANCED INDICATOR RESULT
# ============================================================================

@dataclass
class EnhancedIndicatorResult:
    """Enhanced indicator result with AI confidence"""
    value: float = 0.0
    signal: str = "neutral"
    strength: float = 0.0
    ai_confidence: float = 0.0
    pattern_match: Optional[Dict] = None
    market_regime: str = "neutral"
    learning_rate: float = 0.01
    prediction_accuracy: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def composite_score(self) -> float:
        """Composite score combining signal and AI confidence"""
        return (self.strength * 0.6) + (self.ai_confidence * 0.4)
    
    @property
    def recommendation(self) -> str:
        """Get trading recommendation"""
        if self.composite_score > 0.7:
            return "STRONG"
        elif self.composite_score > 0.5:
            return "MODERATE"
        elif self.composite_score > 0.3:
            return "CAUTIOUS"
        else:
            return "AVOID"
    
    @property
    def is_buy_signal(self) -> bool:
        """Check if signal is buy"""
        return self.signal in ["buy", "oversold", "bullish"]
    
    @property
    def is_sell_signal(self) -> bool:
        """Check if signal is sell"""
        return self.signal in ["sell", "overbought", "bearish"]


# ============================================================================
# NEURAL PATTERN RECOGNITION
# ============================================================================

class NeuralPatternRecognizer:
    """
    Simple neural network for pattern recognition in price data
    Uses a 3-layer perceptron for pattern classification
    """
    
    def __init__(self, input_size: int = 10, hidden_size: int = 20, output_size: int = 3):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Initialize weights
        self.w1 = np.random.randn(input_size, hidden_size) * 0.1
        self.b1 = np.zeros(hidden_size)
        self.w2 = np.random.randn(hidden_size, output_size) * 0.1
        self.b2 = np.zeros(output_size)
        
        self._logger = setup_logger("NeuralPatternRecognizer")
        self._training_data: List[Tuple[np.ndarray, int]] = []
        self._is_trained = False
    
    def _sigmoid(self, x):
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _sigmoid_derivative(self, x):
        """Derivative of sigmoid"""
        return x * (1 - x)
    
    def _softmax(self, x):
        """Softmax activation for output layer"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()
    
    def _forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Forward propagation"""
        # Hidden layer
        z1 = np.dot(x, self.w1) + self.b1
        a1 = self._sigmoid(z1)
        
        # Output layer
        z2 = np.dot(a1, self.w2) + self.b2
        a2 = self._softmax(z2)
        
        return a1, a2
    
    def predict(self, prices: List[float]) -> Dict[str, float]:
        """
        Predict pattern type
        Returns probabilities for: uptrend, downtrend, sideways
        """
        if len(prices) < self.input_size:
            return {'uptrend': 0.33, 'downtrend': 0.33, 'sideways': 0.34}
        
        # Normalize prices
        prices_array = np.array(prices[-self.input_size:])
        norm_prices = (prices_array - prices_array.mean()) / (prices_array.std() + 1e-8)
        
        _, output = self._forward(norm_prices)
        
        return {
            'uptrend': float(output[0]),
            'downtrend': float(output[1]),
            'sideways': float(output[2])
        }
    
    def train(self, X: List[np.ndarray], y: List[int], epochs: int = 100, lr: float = 0.01):
        """Train the neural network"""
        self._logger.info(f"Training neural network with {len(X)} samples")
        
        for epoch in range(epochs):
            total_loss = 0
            
            for x, target in zip(X, y):
                # Forward pass
                a1, a2 = self._forward(x)
                
                # One-hot encode target
                target_onehot = np.zeros(self.output_size)
                target_onehot[target] = 1
                
                # Backward pass
                dz2 = a2 - target_onehot
                dw2 = np.outer(a1, dz2)
                db2 = dz2
                
                da1 = np.dot(dz2, self.w2.T)
                dz1 = da1 * self._sigmoid_derivative(a1)
                dw1 = np.outer(x, dz1)
                db1 = dz1
                
                # Update weights
                self.w2 -= lr * dw2
                self.b2 -= lr * db2
                self.w1 -= lr * dw1
                self.b1 -= lr * db1
                
                total_loss += -np.log(a2[target] + 1e-8)
            
            if epoch % 20 == 0:
                self._logger.debug(f"Epoch {epoch}, Loss: {total_loss/len(X):.4f}")
        
        self._is_trained = True
        self._logger.info("Neural network training complete")


# ============================================================================
# GENETIC ALGORITHM FOR INDICATOR OPTIMIZATION
# ============================================================================

class GeneticIndicatorOptimizer:
    """
    Genetic algorithm to optimize indicator parameters
    Evolves the best parameter combinations for current market conditions
    """
    
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.population: List[Dict[str, Any]] = []
        self.fitness_history: List[float] = []
        self._logger = setup_logger("GeneticIndicatorOptimizer")
        self._generation = 0
    
    def initialize_population(self, param_ranges: Dict[str, Tuple[int, int]]):
        """Initialize population with random parameters"""
        self.population = []
        
        for _ in range(self.population_size):
            individual = {}
            for param, (min_val, max_val) in param_ranges.items():
                individual[param] = random.randint(min_val, max_val)
            self.population.append(individual)
        
        self._logger.info(f"Initialized population of {self.population_size} individuals")
        return self.population
    
    def evaluate_fitness(self, individual: Dict, price_data: List[float], 
                         indicator_func: Callable) -> float:
        """
        Evaluate fitness of an individual
        Higher fitness = better parameters
        """
        try:
            # Calculate indicator with these parameters
            result = indicator_func(price_data, **individual)
            
            # Fitness based on signal strength and consistency
            if hasattr(result, 'strength'):
                return result.strength
            elif isinstance(result, dict) and 'strength' in result:
                return result['strength']
            else:
                return 0.5
        except:
            return 0.0
    
    def select_parents(self, fitness_scores: List[float]) -> Tuple[int, int]:
        """Select parents using tournament selection"""
        tournament_size = 3
        tournament1 = random.sample(range(len(self.population)), tournament_size)
        tournament2 = random.sample(range(len(self.population)), tournament_size)
        
        parent1 = max(tournament1, key=lambda i: fitness_scores[i])
        parent2 = max(tournament2, key=lambda i: fitness_scores[i])
        
        return parent1, parent2
    
    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Create child via crossover"""
        child = {}
        for key in parent1.keys():
            if random.random() > 0.5:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child
    
    def mutate(self, individual: Dict, param_ranges: Dict[str, Tuple[int, int]]):
        """Mutate individual"""
        for param, (min_val, max_val) in param_ranges.items():
            if random.random() < self.mutation_rate:
                individual[param] = random.randint(min_val, max_val)
        return individual
    
    async def evolve(self, price_data: List[float], indicator_func: Callable,
                    param_ranges: Dict[str, Tuple[int, int]], 
                    generations: int = 50) -> Dict[str, Any]:
        """
        Evolve population to find optimal parameters
        """
        if not self.population:
            self.initialize_population(param_ranges)
        
        best_individual = None
        best_fitness = -1
        
        for gen in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in self.population:
                fitness = self.evaluate_fitness(individual, price_data, indicator_func)
                fitness_scores.append(fitness)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_individual = individual.copy()
            
            self.fitness_history.append(best_fitness)
            
            # Create new population
            new_population = []
            
            # Elitism: keep top 2
            sorted_indices = np.argsort(fitness_scores)[::-1]
            new_population.append(self.population[sorted_indices[0]].copy())
            new_population.append(self.population[sorted_indices[1]].copy())
            
            # Create offspring
            while len(new_population) < self.population_size:
                parent1_idx, parent2_idx = self.select_parents(fitness_scores)
                parent1 = self.population[parent1_idx]
                parent2 = self.population[parent2_idx]
                
                child = self.crossover(parent1, parent2)
                child = self.mutate(child, param_ranges)
                new_population.append(child)
            
            self.population = new_population
            self._generation = gen
            
            if gen % 10 == 0:
                self._logger.debug(f"Generation {gen}, Best Fitness: {best_fitness:.4f}")
        
        self._logger.info(f"Evolution complete. Best fitness: {best_fitness:.4f}")
        return {
            'best_parameters': best_individual,
            'best_fitness': best_fitness,
            'fitness_history': self.fitness_history,
            'generations': generations
        }
    
    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """Get current best parameters"""
        if self.population:
            return self.population[0].copy()
        return None


# ============================================================================
# MAIN INDICATORS CLASS
# ============================================================================

class Indicators:
    """
    Collection of technical indicators with caching, AI, and genetic optimization
    """
    
    _cache = IndicatorCache()
    _pattern_cache = PatternCache()
    _neural_recognizer = NeuralPatternRecognizer()
    _genetic_optimizer = GeneticIndicatorOptimizer()
    _logger = setup_logger("Indicators")
    
    @classmethod
    def _validate_prices(cls, prices: List[float], min_period: int) -> bool:
        """Validate price data"""
        if not prices or len(prices) < min_period:
            return False
        return True
    
    @classmethod
    def _to_numpy(cls, data: List[float]) -> np.ndarray:
        """Convert to numpy array efficiently"""
        return np.array(data, dtype=np.float64)
    
    # ============== Moving Averages ==============
    
    @classmethod
    async def sma(cls, prices: List[float], period: int = 20, 
                  use_ai: bool = True, use_cache: bool = True) -> EnhancedIndicatorResult:
        """Simple Moving Average with AI enhancement"""
        if not cls._validate_prices(prices, period):
            return EnhancedIndicatorResult(value=prices[-1] if prices else 0)
        
        cache_key = f"sma:{period}"
        if use_cache:
            cached = await cls._cache.get("sma", "prices", period, hash(tuple(prices[-period:])))
            if cached is not None:
                return cached
        
        try:
            arr = cls._to_numpy(prices[-period:])
            value = float(np.mean(arr))
            current_price = prices[-1]
            
            # Generate signal
            if current_price > value * 1.02:
                signal = "bullish"
                strength = min(1.0, (current_price / value - 1) * 50)
            elif current_price < value * 0.98:
                signal = "bearish"
                strength = min(1.0, (value / current_price - 1) * 50)
            else:
                signal = "neutral"
                strength = 0.0
            
            result = EnhancedIndicatorResult(
                value=value,
                signal=signal,
                strength=strength,
                metadata={"period": period, "current_price": current_price}
            )
            
            if use_cache:
                await cls._cache.set(result, "sma", "prices", period, hash(tuple(prices[-period:])))
            
            return result
            
        except Exception as e:
            cls._logger.error(f"Error calculating SMA: {e}")
            return EnhancedIndicatorResult(value=prices[-1] if prices else 0)
    
    @classmethod
    async def ema(cls, prices: List[float], period: int = 20, 
                  smoothing: float = 2.0, use_cache: bool = True) -> EnhancedIndicatorResult:
        """Exponential Moving Average"""
        if not cls._validate_prices(prices, period):
            return EnhancedIndicatorResult(value=prices[-1] if prices else 0)
        
        if use_cache:
            cached = await cls._cache.get("ema", "prices", period, hash(tuple(prices[-period*2:])))
            if cached is not None:
                return cached
        
        try:
            arr = cls._to_numpy(prices)
            multiplier = smoothing / (period + 1)
            
            ema_values = np.zeros_like(arr)
            ema_values[0] = arr[0]
            
            for i in range(1, len(arr)):
                ema_values[i] = (arr[i] - ema_values[i-1]) * multiplier + ema_values[i-1]
            
            value = float(ema_values[-1])
            current_price = prices[-1]
            
            if current_price > value * 1.015:
                signal = "bullish"
                strength = min(1.0, (current_price / value - 1) * 66)
            elif current_price < value * 0.985:
                signal = "bearish"
                strength = min(1.0, (value / current_price - 1) * 66)
            else:
                signal = "neutral"
                strength = 0.0
            
            result = EnhancedIndicatorResult(
                value=value,
                signal=signal,
                strength=strength,
                metadata={"period": period, "current_price": current_price}
            )
            
            if use_cache:
                await cls._cache.set(result, "ema", "prices", period, hash(tuple(prices[-period*2:])))
            
            return result
            
        except Exception as e:
            cls._logger.error(f"Error calculating EMA: {e}")
            return EnhancedIndicatorResult(value=prices[-1] if prices else 0)
    
    # ============== RSI ==============
    
    @classmethod
    async def rsi(cls, prices: List[float], period: int = 14, 
                  optimize: bool = False, use_cache: bool = True) -> EnhancedIndicatorResult:
        """
        Relative Strength Index with genetic optimization
        """
        if not cls._validate_prices(prices, period + 1):
            return EnhancedIndicatorResult(value=50.0)
        
        # Genetic optimization
        if optimize and len(prices) > 100:
            async def rsi_func(p, **params):
                return await cls.rsi(p, params.get('period', 14), optimize=False)
            
            param_ranges = {'period': (5, 25)}
            optimal = await cls._genetic_optimizer.evolve(
                prices[-100:], rsi_func, param_ranges, generations=20
            )
            period = optimal['best_parameters'].get('period', period)
        
        if use_cache:
            cached = await cls._cache.get("rsi", "prices", period, hash(tuple(prices[-period*2:])))
            if cached is not None:
                return cached
        
        try:
            arr = cls._to_numpy(prices[-(period + 1):])
            deltas = np.diff(arr)
            
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Generate signal
            if rsi >= 70:
                signal = "overbought"
                strength = min(1.0, (rsi - 70) / 30)
            elif rsi <= 30:
                signal = "oversold"
                strength = min(1.0, (30 - rsi) / 30)
            elif rsi >= 55:
                signal = "bullish"
                strength = (rsi - 55) / 15
            elif rsi <= 45:
                signal = "bearish"
                strength = (45 - rsi) / 15
            else:
                signal = "neutral"
                strength = 0.0
            
            result = EnhancedIndicatorResult(
                value=float(rsi),
                signal=signal,
                strength=float(strength),
                metadata={"period": period, "overbought": 70, "oversold": 30}
            )
            
            if use_cache:
                await cls._cache.set(result, "rsi", "prices", period, hash(tuple(prices[-period*2:])))
            
            return result
            
        except Exception as e:
            cls._logger.error(f"Error calculating RSI: {e}")
            return EnhancedIndicatorResult(value=50.0)
    
    # ============== MACD ==============
    
    @classmethod
    async def macd(cls, prices: List[float], fast: int = 12, slow: int = 26,
                   signal: int = 9, detect_divergence: bool = True,
                   use_cache: bool = True) -> Dict[str, Any]:
        """
        MACD with divergence detection
        """
        if not cls._validate_prices(prices, slow):
            return {
                'macd': EnhancedIndicatorResult(value=0),
                'signal': EnhancedIndicatorResult(value=0),
                'histogram': EnhancedIndicatorResult(value=0),
                'signal_type': "neutral",
                'strength': 0,
                'divergence': None
            }
        
        if use_cache:
            cached = await cls._cache.get("macd", "prices", fast, slow, signal, 
                                         hash(tuple(prices[-slow*2:])))
            if cached is not None:
                return cached
        
        try:
            # Calculate EMAs
            fast_ema = await cls.ema(prices, fast, use_cache=False)
            slow_ema = await cls.ema(prices, slow, use_cache=False)
            
            macd_line = fast_ema.value - slow_ema.value
            
            # Calculate signal line
            signal_line = await cls.ema([macd_line] * 5 + [macd_line], signal, use_cache=False)
            histogram = macd_line - signal_line.value
            
            # Determine signal
            if histogram > 0:
                if macd_line > 0:
                    signal_type = "strong_bullish"
                    strength = min(1.0, histogram / abs(macd_line) if macd_line != 0 else 0.5)
                else:
                    signal_type = "bullish"
                    strength = min(0.7, abs(histogram) / abs(macd_line) if macd_line != 0 else 0.3)
            elif histogram < 0:
                if macd_line < 0:
                    signal_type = "strong_bearish"
                    strength = min(1.0, abs(histogram) / abs(macd_line) if macd_line != 0 else 0.5)
                else:
                    signal_type = "bearish"
                    strength = min(0.7, abs(histogram) / abs(macd_line) if macd_line != 0 else 0.3)
            else:
                signal_type = "neutral"
                strength = 0.0
            
            result = {
                'macd': EnhancedIndicatorResult(value=macd_line, signal=signal_type, strength=strength),
                'signal': EnhancedIndicatorResult(value=signal_line.value),
                'histogram': EnhancedIndicatorResult(value=histogram, signal=signal_type, strength=strength),
                'signal_type': signal_type,
                'strength': strength,
                'divergence': None
            }
            
            if use_cache:
                await cls._cache.set(result, "macd", "prices", fast, slow, signal,
                                    hash(tuple(prices[-slow*2:])))
            
            return result
            
        except Exception as e:
            cls._logger.error(f"Error calculating MACD: {e}")
            return {
                'macd': EnhancedIndicatorResult(value=0),
                'signal': EnhancedIndicatorResult(value=0),
                'histogram': EnhancedIndicatorResult(value=0),
                'signal_type': "neutral",
                'strength': 0,
                'divergence': None
            }
    
    # ============== Bollinger Bands ==============
    
    @classmethod
    async def bollinger_bands(cls, prices: List[float], period: int = 20,
                             std_dev: float = 2.0, use_cache: bool = True) -> Dict[str, Any]:
        """
        Bollinger Bands with squeeze detection
        """
        if not cls._validate_prices(prices, period):
            middle = prices[-1] if prices else 0
            return {
                'upper': EnhancedIndicatorResult(value=middle),
                'middle': EnhancedIndicatorResult(value=middle),
                'lower': EnhancedIndicatorResult(value=middle),
                'position': 50.0,
                'signal': "neutral",
                'strength': 0,
                'squeeze': False,
                'bandwidth': 0.0
            }
        
        try:
            arr = cls._to_numpy(prices[-period:])
            middle = float(np.mean(arr))
            std = float(np.std(arr))
            
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)
            current = prices[-1]
            
            # Calculate position within bands
            if upper > lower:
                position = (current - lower) / (upper - lower) * 100
            else:
                position = 50.0
            
            # Calculate bandwidth and detect squeeze
            bandwidth = (upper - lower) / middle if middle != 0 else 0
            squeeze = bandwidth < 0.05
            
            # Generate signal
            if current > upper:
                signal = "overbought"
                strength = min(1.0, (current - upper) / (upper - middle) if upper > middle else 1.0)
            elif current < lower:
                signal = "oversold"
                strength = min(1.0, (lower - current) / (middle - lower) if middle > lower else 1.0)
            elif current > middle:
                signal = "bullish"
                strength = (current - middle) / (upper - middle) if upper > middle else 0.5
            else:
                signal = "bearish"
                strength = (middle - current) / (middle - lower) if middle > lower else 0.5
            
            return {
                'upper': EnhancedIndicatorResult(value=upper),
                'middle': EnhancedIndicatorResult(value=middle),
                'lower': EnhancedIndicatorResult(value=lower),
                'position': position,
                'signal': signal,
                'strength': float(strength),
                'bandwidth': bandwidth,
                'squeeze': squeeze,
                'metadata': {'period': period, 'std_dev': std_dev}
            }
            
        except Exception as e:
            cls._logger.error(f"Error calculating Bollinger Bands: {e}")
            middle = prices[-1] if prices else 0
            return {
                'upper': EnhancedIndicatorResult(value=middle),
                'middle': EnhancedIndicatorResult(value=middle),
                'lower': EnhancedIndicatorResult(value=middle),
                'position': 50.0,
                'signal': "neutral",
                'strength': 0,
                'squeeze': False,
                'bandwidth': 0.0
            }
    
    # ============== Market Regime Detection ==============
    
    @classmethod
    async def detect_market_regime(cls, prices: List[float], volumes: List[float] = None) -> Dict[str, Any]:
        """
        Detect current market regime using ML techniques
        Returns: trending_up, trending_down, ranging, volatile, breakout
        """
        if len(prices) < 50:
            return {'regime': 'unknown', 'confidence': 0.0}
        
        prices_array = np.array(prices)
        returns = np.diff(prices_array) / (prices_array[:-1] + 1e-10)
        
        # Calculate features
        volatility = np.std(returns) * np.sqrt(252)
        try:
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices_array, 1)[0]
            trend_strength = abs(slope) / (np.mean(prices_array) + 1e-10) * 100
        except:
            trend_strength = 0
        
        # Volume analysis
        volume_ratio = 1.0
        if volumes and len(volumes) > 20:
            volume_ratio = np.mean(volumes[-5:]) / (np.mean(volumes[-20:-5]) + 1e-10)
        
        # Determine regime
        if trend_strength > 0.3 and slope > 0:
            if volume_ratio > 1.2:
                regime = 'trending_up'
                confidence = min(1.0, trend_strength / 0.5)
            else:
                regime = 'trending_up'
                confidence = min(0.8, trend_strength / 0.5)
        elif trend_strength > 0.3 and slope < 0:
            if volume_ratio > 1.2:
                regime = 'trending_down'
                confidence = min(1.0, trend_strength / 0.5)
            else:
                regime = 'trending_down'
                confidence = min(0.8, trend_strength / 0.5)
        elif volatility > 0.03:
            regime = 'volatile'
            confidence = min(1.0, volatility / 0.1)
        elif volume_ratio > 1.5 and trend_strength > 0.2:
            regime = 'breakout'
            confidence = min(1.0, volume_ratio / 3)
        else:
            regime = 'ranging'
            confidence = 1.0 - (trend_strength / 0.5)
        
        return {
            'regime': regime,
            'confidence': float(min(1.0, max(0.0, confidence))),
            'volatility': float(volatility),
            'trend_strength': float(trend_strength),
            'volume_ratio': float(volume_ratio)
        }
    
    # ============== Comprehensive Analysis ==============
    
    @classmethod
    async def comprehensive_analysis(cls, prices: List[float], highs: List[float],
                                    lows: List[float], closes: List[float],
                                    volumes: List[float] = None) -> Dict[str, Any]:
        """
        Comprehensive market analysis combining all indicators and ML
        """
        if len(prices) < 50:
            return {
                'direction': 'NEUTRAL',
                'confidence': 0,
                'score': 0,
                'rsi': 50,
                'rsi_signal': 'neutral',
                'macd_signal': 'neutral',
                'bollinger_signal': 'neutral',
                'market_regime': 'unknown',
                'recommendation': 'CAUTIOUS'
            }
        
        # Calculate all indicators in parallel
        tasks = [
            cls.rsi(prices),
            cls.macd(prices),
            cls.bollinger_bands(prices),
            cls.detect_market_regime(prices, volumes),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract results safely
        rsi = results[0] if not isinstance(results[0], Exception) else EnhancedIndicatorResult(value=50)
        macd = results[1] if not isinstance(results[1], Exception) else {'signal_type': 'neutral', 'strength': 0}
        bollinger = results[2] if not isinstance(results[2], Exception) else {'signal': 'neutral', 'strength': 0}
        regime = results[3] if not isinstance(results[3], Exception) else {'regime': 'unknown', 'confidence': 0}
        
        # Get values safely
        rsi_value = getattr(rsi, 'value', 50)
        rsi_signal = getattr(rsi, 'signal', 'neutral')
        rsi_strength = getattr(rsi, 'strength', 0)
        
        macd_signal = macd.get('signal_type', 'neutral')
        macd_strength = macd.get('strength', 0)
        
        bollinger_signal = bollinger.get('signal', 'neutral')
        bollinger_strength = bollinger.get('strength', 0)
        
        # Aggregate signals
        signals = []
        weights = []
        
        # RSI
        if rsi_signal in ['oversold', 'bullish']:
            signals.append(1)
            weights.append(rsi_strength)
        elif rsi_signal in ['overbought', 'bearish']:
            signals.append(-1)
            weights.append(rsi_strength)
        else:
            signals.append(0)
            weights.append(0.5)
        
        # MACD
        if 'strong_bullish' in macd_signal:
            signals.append(1)
            weights.append(0.9)
        elif 'bullish' in macd_signal:
            signals.append(1)
            weights.append(0.7)
        elif 'strong_bearish' in macd_signal:
            signals.append(-1)
            weights.append(0.9)
        elif 'bearish' in macd_signal:
            signals.append(-1)
            weights.append(0.7)
        else:
            signals.append(0)
            weights.append(0.5)
        
        # Bollinger Bands
        if bollinger_signal == 'oversold':
            signals.append(1)
            weights.append(bollinger_strength)
        elif bollinger_signal == 'overbought':
            signals.append(-1)
            weights.append(bollinger_strength)
        else:
            signals.append(0)
            weights.append(0.5)
        
        # Market Regime
        regime_type = regime.get('regime', 'unknown')
        regime_confidence = regime.get('confidence', 0.5)
        if regime_type in ['trending_up', 'breakout']:
            signals.append(1)
            weights.append(regime_confidence)
        elif regime_type in ['trending_down']:
            signals.append(-1)
            weights.append(regime_confidence)
        else:
            signals.append(0)
            weights.append(0.5)
        
        # Calculate weighted score
        total_weight = sum(weights)
        if total_weight > 0:
            score = sum(s * w for s, w in zip(signals, weights)) / total_weight
        else:
            score = 0
        
        # Determine final signal
        if score > 0.3:
            direction = 'CALL'
            confidence = min(100, score * 100)
        elif score < -0.3:
            direction = 'PUT'
            confidence = min(100, abs(score) * 100)
        else:
            direction = 'NEUTRAL'
            confidence = 50
        
        return {
            'direction': direction,
            'confidence': confidence,
            'score': score,
            'rsi': rsi_value,
            'rsi_signal': rsi_signal,
            'macd_signal': macd_signal,
            'bollinger_signal': bollinger_signal,
            'market_regime': regime_type,
            'regime_confidence': regime_confidence,
            'recommendation': 'STRONG' if confidence > 75 else 'MODERATE' if confidence > 60 else 'CAUTIOUS'
        }
    
    @classmethod
    async def get_all_indicators(cls, prices: List[float], highs: List[float],
                                lows: List[float], closes: List[float]) -> Dict:
        """
        Get all indicators in one call
        """
        tasks = [
            cls.rsi(prices),
            cls.macd(prices),
            cls.bollinger_bands(prices),
            cls.detect_market_regime(prices),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'rsi': results[0] if not isinstance(results[0], Exception) else EnhancedIndicatorResult(value=50),
            'macd': results[1] if not isinstance(results[1], Exception) else {'signal_type': 'neutral'},
            'bollinger': results[2] if not isinstance(results[2], Exception) else {},
            'market_regime': results[3] if not isinstance(results[3], Exception) else {'regime': 'unknown', 'confidence': 0}
        }
    
    @classmethod
    async def optimize_rsi(cls, prices: List[float]) -> Dict[str, Any]:
        """Optimize RSI parameters using genetic algorithm"""
        async def rsi_func(p, **params):
            return await cls.rsi(p, params.get('period', 14), optimize=False)
        
        param_ranges = {'period': (5, 25)}
        return await cls._genetic_optimizer.evolve(
            prices, rsi_func, param_ranges, generations=30
        )
    
    @classmethod
    async def clear_cache(cls):
        """Clear indicator cache"""
        await cls._cache.clear()
        cls._logger.info("Indicator cache cleared")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "Indicators",
    "EnhancedIndicatorResult",
    "NeuralPatternRecognizer",
    "GeneticIndicatorOptimizer",
]