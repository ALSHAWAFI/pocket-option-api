# __init__.py
"""
PocketTrader - Unofficial Python client for Pocket Option trading platform
Version: 2.0.0

Advanced features:
- AI-powered pattern recognition
- Genetic algorithm optimization
- Multi-asset portfolio management
- Real-time performance monitoring
- Smart caching (LFU, Predictive, Pattern)
"""

__version__ = "2.0.0"
__author__ = "PocketTrader Team"
__license__ = "MIT"
import typing
from typing import Optional, List, Dict, Any, Union, Callable, Awaitable
import logging
from .utils import setup_logging

# Setup default logging (WARNING level only)
setup_logging(level="WARNING")

# ============================================================================
# CORE CLIENT
# ============================================================================
from .client import PocketOptionClient

# ============================================================================
# MODELS - All data structures
# ============================================================================
from .models import (
    # Enums
    Asset, AssetType, Command, DealAction, IsDemo, OpenPendingDealRequestOpenType,
    
    # Base Models
    Account, AuthorizationData, Candle, Deal, PriceTick, IndicatorResult,
    
    # Events
    SuccessAuthEvent, SuccessUpdateBalanceEvent, UpdateHistoryFastEvent,
    UpdateCloseValueItem, SuccessCloseDealEvent, MarketSentimentItem,
    UpdateAssetItem, AssetItemTimeframe,
    
    # Requests
    OpenDealRequest, CopySignalRequest, OpenPendingDealRequest, ChangeAssetRequest,
    
    # Type Adapters
    UpdateCloseValueListTypeAdapter, UpdateAssetItemListTypeAdapter,
    MarketSentimentItemListTypeAdapter, DealListTypeAdapter,
)

# ============================================================================
# TRADING - Unified (candles + deals + storage)
# ============================================================================
from .trading import (
    # Candles
    CandleBuilder, CandleStorage, MemoryCandleStorage,
    # Deals
    DealsStorage, MemoryDealsStorage,
    # Trades
    TradeStorage, Trade, TradeStatus, FastCandleCollector,
)

# ============================================================================
# CACHE - Advanced caching systems
# ============================================================================
from .cache import (
    TTLCache,
    LFUCache,
    PredictiveCache,
    IndicatorCache,
    PatternCache,
)

# ============================================================================
# INDICATORS - Technical indicators with AI and genetic optimization
# ============================================================================
from .indicators import (
    Indicators,
    EnhancedIndicatorResult,
    NeuralPatternRecognizer,
    GeneticIndicatorOptimizer,
)

# ============================================================================
# RISK MANAGEMENT - Advanced risk with AI and portfolio management
# ============================================================================
from .risk import (
    RiskManager,
    RiskMetrics,
    PortfolioManager,
    AIRiskAssessor,
)

# ============================================================================
# ANALYTICS - Performance analysis with machine learning
# ============================================================================
from .analytics import (
    PerformanceAnalyzer,
    TradeMetrics,
    PerformanceMonitor,
    MLPredictor,
)

# ============================================================================
# STREAM - Real-time 39-byte updates
# ============================================================================
from .stream import StreamUpdate, StreamProcessor

# ============================================================================
# CHAFOR - 19-byte signals
# ============================================================================
from .chafor import ChaforMessage, ChaforProcessor

# ============================================================================
# MIDDLEWARES - Unified middleware system
# ============================================================================
from .middleware import (
    Middleware,
    LoggingMiddleware,
    MakeJsonOnMiddleware,
    FixTypesOnMiddleware,
    StatsMiddleware,
    ThrottleMiddleware,
)

# ============================================================================
# EXCEPTIONS - Unified exceptions
# ============================================================================
from .exceptions import (
    PocketTraderError,
    ConnectionError,
    AuthError,
    SubscriptionError,
    TradeError,
    StorageError,
    IndicatorError,
    ValidationError,
    TimeoutError,
    RateLimitError,
    InsufficientBalanceError,
    InvalidAssetError,
    ParseError,
    DealError,
    ErrorCode,
)

# ============================================================================
# CONSTANTS
# ============================================================================
from .constants import (
    VERSION,
    Regions,
    MESSAGE_SIZES,
    SIGNAL_TYPES,
    AssetCategory,
    TIMEFRAMES,
    API_LIMITS_MIN_ORDER_AMOUNT,
    API_LIMITS_MAX_ORDER_AMOUNT,
    API_LIMITS_MIN_DURATION,
    API_LIMITS_MAX_DURATION,
    API_LIMITS_MAX_CONCURRENT_ORDERS,
    API_LIMITS_RATE_LIMIT,
    DEFAULT_ORIGIN,
    DEFAULT_USER_AGENT,
    HEARTBEAT_INTERVAL,
    WATCHDOG_INTERVAL,
    DATA_TIMEOUT,
    PONG_TIMEOUT,
)

# ============================================================================
# UTILS
# ============================================================================
from .utils import (
    setup_logger,
    fix_timestamp,
    format_datetime,
    generate_request_id,
    parse_stream_data,
    parse_chafor_data,
    format_price,
    format_percentage,
    format_duration,
    validate_asset,
    validate_amount,
    validate_duration,
)

# ============================================================================
# TYPES
# ============================================================================
from .types import (
    JsonValue,
    EmitCallback,
    SIOEventListener,
    TypedEventListener,
    PriceType,
    IndicatorType,
    CandlePeriod,
)

# ============================================================================
# PATCHES (for backward compatibility)
# ============================================================================
from . import patches
from .patches import apply_connection_patches

# Version info
__version_info__ = tuple(map(int, __version__.split('.')))


# ============================================================================
# ALL EXPORTS
# ============================================================================
__all__ = [
    # Core
    "PocketOptionClient",
    
    # Models
    "Asset", "AssetType", "Command", "DealAction", "IsDemo",
    "OpenPendingDealRequestOpenType",
    "Account", "AuthorizationData", "Candle", "Deal", "PriceTick",
    "IndicatorResult",
    "SuccessAuthEvent", "SuccessUpdateBalanceEvent", "SuccessCloseDealEvent",
    "UpdateHistoryFastEvent", "UpdateAssetItem", "UpdateCloseValueItem",
    "MarketSentimentItem", "AssetItemTimeframe",
    "OpenDealRequest", "CopySignalRequest", "OpenPendingDealRequest",
    "ChangeAssetRequest",
    "UpdateCloseValueListTypeAdapter", "UpdateAssetItemListTypeAdapter",
    "MarketSentimentItemListTypeAdapter", "DealListTypeAdapter",
    
    # Trading
    "CandleBuilder", "CandleStorage", "MemoryCandleStorage",
    "DealsStorage", "MemoryDealsStorage",
    "TradeStorage", "Trade", "TradeStatus", "FastCandleCollector",
    
    # Cache
    "TTLCache", "LFUCache", "PredictiveCache", "IndicatorCache", "PatternCache",
    
    # Indicators
    "Indicators", "EnhancedIndicatorResult", "NeuralPatternRecognizer",
    "GeneticIndicatorOptimizer",
    
    # Risk
    "RiskManager", "RiskMetrics", "PortfolioManager", "AIRiskAssessor",
    
    # Analytics
    "PerformanceAnalyzer", "TradeMetrics", "PerformanceMonitor", "MLPredictor",
    
    # Stream
    "StreamUpdate", "StreamProcessor",
    
    # Chafor
    "ChaforMessage", "ChaforProcessor",
    
    # Middlewares
    "Middleware", "LoggingMiddleware", "MakeJsonOnMiddleware",
    "FixTypesOnMiddleware", "StatsMiddleware", "ThrottleMiddleware",
    
    # Exceptions
    "PocketTraderError", "ConnectionError", "AuthError",
    "SubscriptionError", "TradeError", "StorageError",
    "IndicatorError", "ValidationError", "TimeoutError",
    "RateLimitError", "InsufficientBalanceError",
    "InvalidAssetError", "ParseError", "DealError", "ErrorCode",
    
    # Constants
    "VERSION", "Regions", "MESSAGE_SIZES", "SIGNAL_TYPES",
    "AssetCategory", "TIMEFRAMES",
    "API_LIMITS_MIN_ORDER_AMOUNT", "API_LIMITS_MAX_ORDER_AMOUNT",
    "API_LIMITS_MIN_DURATION", "API_LIMITS_MAX_DURATION",
    "API_LIMITS_MAX_CONCURRENT_ORDERS", "API_LIMITS_RATE_LIMIT",
    "DEFAULT_ORIGIN", "DEFAULT_USER_AGENT",
    "HEARTBEAT_INTERVAL", "WATCHDOG_INTERVAL",
    "DATA_TIMEOUT", "PONG_TIMEOUT",
    
    # Utils
    "setup_logger", "fix_timestamp", "format_datetime",
    "generate_request_id", "parse_stream_data", "parse_chafor_data",
    "format_price", "format_percentage", "format_duration",
    "validate_asset", "validate_amount", "validate_duration",
    
    # Types
    "JsonValue", "EmitCallback", "SIOEventListener", "TypedEventListener",
    "PriceType", "IndicatorType", "CandlePeriod",
    
    # Deprecated
    "apply_connection_patches",
]