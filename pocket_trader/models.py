# models.py
"""
Pydantic models for Pocket Option data structures
"""

import datetime
import enum
import typing
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union

import pydantic
import pytz

# ============================================================================
# TYPE ALIASES
# ============================================================================

IsDemo = typing.Literal[0, 1]


# ============================================================================
# ENUMS
# ============================================================================

class Asset(str, enum.Enum):
    """Trading assets available on Pocket Option"""
    
    # Major pairs
    AUDCAD = "AUDCAD"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"
    USDJPY = "USDJPY"
    USDCHF = "USDCHF"
    USDCAD = "USDCAD"
    AUDUSD = "AUDUSD"
    NZDUSD = "NZDUSD"
    
    # Commodities
    XAUUSD = "XAUUSD"
    XAGUSD = "XAGUSD"
    UKBrent = "UKBrent"
    USCrude = "USCrude"
    XNGUSD = "XNGUSD"
    XPTUSD = "XPTUSD"
    XPDUSD = "XPDUSD"
    
    # Crypto
    BTCUSD = "BTCUSD"
    ETHUSD = "ETHUSD"
    DASH_USD = "DASH_USD"
    BTCGBP = "BTCGBP"
    BTCJPY = "BTCJPY"
    BCHEUR = "BCHEUR"
    BCHGBP = "BCHGBP"
    BCHJPY = "BCHJPY"
    DOTUSD = "DOTUSD"
    LNKUSD = "LNKUSD"
    
    # Indices
    SP500 = "SP500"
    NASUSD = "NASUSD"
    DJI30 = "DJI30"
    JPN225 = "JPN225"
    D30EUR = "D30EUR"
    E50EUR = "E50EUR"
    F40EUR = "F40EUR"
    E35EUR = "E35EUR"
    A_100GBP = "100GBP"
    AUS200 = "AUS200"
    CAC40 = "CAC40"
    AEX25 = "AEX25"
    SMI20 = "SMI20"
    H33HKD = "H33HKD"
    
    # Stocks
    AAPL = "#AAPL"
    MSFT = "#MSFT"
    TSLA = "#TSLA"
    FB = "#FB"
    NFLX = "#NFLX"
    INTC = "#INTC"
    BA = "#BA"
    JPM = "#JPM"
    JNJ = "#JNJ"
    PFE = "#PFE"
    XOM = "#XOM"
    AXP = "#AXP"
    MCD = "#MCD"
    CSCO = "#CSCO"
    CITI = "#CITI"
    TWITTER = "#TWITTER"
    BABA = "#BABA"
    
    # OTC pairs
    CADJPY_otc = "CADJPY_otc"
    EURUSD_otc = "EURUSD_otc"
    GBPUSD_otc = "GBPUSD_otc"
    XAUUSD_otc = "XAUUSD_otc"
    # ... more assets can be added as needed
    
    def is_otc(self) -> bool:
        """Check if asset is OTC"""
        return self.value.endswith("_otc")
    
    def __new__(cls, value: str) -> "Asset":
        for member in cls:
            if member.value == value:
                return member
        obj = str.__new__(cls, value)
        obj._name_ = value
        obj._value_ = value
        return obj
    
    @classmethod
    def _missing_(cls, value: str) -> "Asset":
        obj = str.__new__(cls, value)
        obj._name_ = value
        obj._value_ = value
        cls._value2member_map_[value] = obj
        return obj
    
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())


class AssetType(enum.StrEnum):
    """Asset type"""
    STOCK = "stock"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CRYPTOCURRENCY = "cryptocurrency"
    INDEX = "index"


class Command(enum.IntEnum):
    """Trade command (PUT/CALL)"""
    PUT = 0
    CALL = 1


class DealAction(enum.StrEnum):
    """Deal action (CALL/PUT)"""
    CALL = "call"
    PUT = "put"


class OpenPendingDealRequestOpenType(enum.IntEnum):
    """Open type for pending deals"""
    TIME = 0
    PRICE = 1


# ============================================================================
# BASE MODELS
# ============================================================================

class Account(pydantic.BaseModel):
    """Account information"""
    uid: int
    balance: float
    demo_balance: Optional[float] = None
    currency: str = "USD"
    is_demo: bool = False
    
    @property
    def available_balance(self) -> float:
        """Get available balance"""
        return self.demo_balance if self.is_demo else self.balance


class AuthorizationData(pydantic.BaseModel):
    """Authentication data for login"""
    session: str
    is_demo: typing.Annotated[IsDemo, pydantic.Field(..., alias="isDemo")]
    uid: int
    platform: int
    is_fast_history: typing.Annotated[bool, pydantic.Field(..., alias="isFastHistory")]
    is_optimized: typing.Annotated[bool, pydantic.Field(..., alias="isOptimized")]


class Candle(pydantic.BaseModel):
    """Candlestick data model"""
    asset: Asset
    timestamp: datetime.datetime
    timeframe: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    @pydantic.field_validator('timestamp', mode='before')
    @classmethod
    def ensure_timezone(cls, v):
        """Ensure timestamp has timezone"""
        if isinstance(v, datetime.datetime) and v.tzinfo is None:
            return v.replace(tzinfo=pytz.UTC)
        return v
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def body_percentage(self) -> float:
        if self.range == 0:
            return 100.0
        return (self.body_size / self.range) * 100
    
    def to_dict(self) -> dict:
        return {
            'asset': self.asset.value if isinstance(self.asset, Asset) else self.asset,
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
        }


class Deal(pydantic.BaseModel):
    """Deal/trade information"""
    model_config = pydantic.ConfigDict(populate_by_name=True)
    
    id: uuid.UUID
    command: Command
    asset: Asset
    
    uid: int
    amount: float
    is_demo: typing.Annotated[IsDemo, pydantic.Field(..., alias="isDemo")]
    
    profit: float
    percent_profit: typing.Annotated[float, pydantic.Field(..., alias="percentProfit")]
    percent_loss: typing.Annotated[float, pydantic.Field(..., alias="percentLoss")]
    
    open_time: typing.Annotated[datetime.datetime, pydantic.Field(..., alias="openTime")]
    close_time: typing.Annotated[datetime.datetime, pydantic.Field(..., alias="closeTime")]
    open_timestamp: typing.Annotated[float, pydantic.Field(..., alias="openTimestamp")]
    close_timestamp: typing.Annotated[Optional[float], pydantic.Field(None, alias="closeTimestamp")]
    refund_time: typing.Annotated[Optional[datetime.datetime], pydantic.Field(None, alias="refundTime")]
    refund_timestamp: typing.Annotated[Optional[int], pydantic.Field(None, alias="refundTimestamp")]
    
    open_price: typing.Annotated[float, pydantic.Field(..., alias="openPrice")]
    close_price: typing.Annotated[Optional[float], pydantic.Field(None, alias="closePrice")]
    
    copy_ticket: typing.Annotated[str, pydantic.Field(..., alias="copyTicket")]
    open_ms: typing.Annotated[Optional[int], pydantic.Field(None, alias="openMs")]
    close_ms: typing.Annotated[Optional[int], pydantic.Field(None, alias="closeMs")]
    option_type: typing.Annotated[Optional[int], pydantic.Field(None, alias="optionType")]
    is_rollover: typing.Annotated[Optional[bool], pydantic.Field(None, alias="isRollover")]
    is_copy_signal: typing.Annotated[bool, pydantic.Field(..., alias="isCopySignal")]
    is_ai: typing.Annotated[Optional[bool], pydantic.Field(None, alias="isAI")]
    currency: str
    amount_usd: typing.Annotated[Optional[float], pydantic.Field(None, alias="amountUSD")]
    request_id: typing.Annotated[Optional[int], pydantic.Field(None, alias="requestId")]
    
    @property
    def is_open(self) -> bool:
        return self.close_price is None
    
    @property
    def is_profitable(self) -> Optional[bool]:
        if self.profit is None:
            return None
        return self.profit > 0
    
    @property
    def profit_percentage(self) -> float:
        if self.amount == 0:
            return 0.0
        return (self.profit / self.amount) * 100 if self.profit else 0.0


class PriceTick(pydantic.BaseModel):
    """Real-time price tick"""
    asset: Asset
    price: float
    timestamp: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    @property
    def spread(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    @property
    def mid_price(self) -> float:
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.price


class IndicatorResult(pydantic.BaseModel):
    """Standard indicator result"""
    value: float
    signal: str = "neutral"
    strength: float = 0.0
    metadata: Dict[str, Any] = pydantic.Field(default_factory=dict)
    
    @property
    def is_buy_signal(self) -> bool:
        return self.signal in ["buy", "oversold", "bullish"]
    
    @property
    def is_sell_signal(self) -> bool:
        return self.signal in ["sell", "overbought", "bearish"]
    
    @property
    def confidence(self) -> str:
        if self.strength >= 0.8:
            return "very_high"
        elif self.strength >= 0.6:
            return "high"
        elif self.strength >= 0.4:
            return "medium"
        elif self.strength >= 0.2:
            return "low"
        else:
            return "very_low"


# ============================================================================
# EVENT MODELS
# ============================================================================

class SuccessAuthEvent(pydantic.BaseModel):
    """Successful authentication event"""
    id: str


class SuccessUpdateBalanceEvent(pydantic.BaseModel):
    """Balance update event"""
    is_demo: typing.Annotated[IsDemo, pydantic.Field(..., alias="isDemo")]
    balance: float


class UpdateHistoryFastEvent(pydantic.BaseModel):
    """Historical candles update event"""
    asset: Asset
    period: int
    history: list[list[float]]


class UpdateCloseValueItem(pydantic.BaseModel):
    """Real-time price update item"""
    asset: Asset
    timestamp: float
    value: float


class SuccessCloseDealEvent(pydantic.BaseModel):
    """Successful deal close event"""
    profit: float
    deals: list[Deal]


class MarketSentimentItem(pydantic.BaseModel):
    """Market sentiment item"""
    asset: Asset
    value: int


class AssetItemTimeframe(pydantic.BaseModel):
    """Asset timeframe"""
    time: int


class UpdateAssetItem(pydantic.BaseModel):
    """Asset update item"""
    id: int
    asset: typing.Annotated[Asset, pydantic.Field(..., alias="symbol")]
    label: str
    type: AssetType
    precision: int
    payout: int
    min_duration: int
    max_duration: int
    step_duration: int
    volatility_index: int
    spread: int
    leverage: int
    extra_data: list[pydantic.JsonValue]
    expire_time: int
    is_active: bool
    timeframes: list[AssetItemTimeframe]
    start_time: int
    default_timeframe: int
    status_code: int


# ============================================================================
# REQUEST MODELS
# ============================================================================

class OpenDealRequest(pydantic.BaseModel):
    """Request to open a new deal"""
    model_config = pydantic.ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid"
    )
    
    asset: Asset
    amount: int
    action: DealAction
    is_demo: IsDemo = pydantic.Field(alias="isDemo")
    request_id: int = pydantic.Field(alias="requestId")
    option_type: int = pydantic.Field(100, alias="optionType")
    time: int
    
    @pydantic.field_validator('amount')
    @classmethod
    def validate_amount(cls, v: int) -> int:
        from .constants import API_LIMITS_MIN_ORDER_AMOUNT, API_LIMITS_MAX_ORDER_AMOUNT
        if v < API_LIMITS_MIN_ORDER_AMOUNT:
            raise ValueError(f"Amount must be at least {API_LIMITS_MIN_ORDER_AMOUNT}")
        if v > API_LIMITS_MAX_ORDER_AMOUNT:
            raise ValueError(f"Amount cannot exceed {API_LIMITS_MAX_ORDER_AMOUNT}")
        return v
    
    @pydantic.field_validator('time')
    @classmethod
    def validate_duration(cls, v: int) -> int:
        from .constants import API_LIMITS_MIN_DURATION, API_LIMITS_MAX_DURATION
        if v < API_LIMITS_MIN_DURATION:
            raise ValueError(f"Duration must be at least {API_LIMITS_MIN_DURATION}")
        if v > API_LIMITS_MAX_DURATION:
            raise ValueError(f"Duration cannot exceed {API_LIMITS_MAX_DURATION}")
        return v


class CopySignalRequest(pydantic.BaseModel):
    """Request to copy a signal"""
    symbol: Asset
    amount: int
    expired_at: typing.Annotated[int, pydantic.Field(..., alias="expiredAt")]
    action: DealAction
    is_demo: typing.Annotated[IsDemo, pydantic.Field(..., alias="isDemo")]
    request_id: typing.Annotated[int, pydantic.Field(..., alias="requestId")]
    created_at: typing.Annotated[int, pydantic.Field(..., alias="createdAt")]
    timeframe: int
    signal_id: typing.Annotated[str, pydantic.Field(..., alias="signalId")]


class OpenPendingDealRequest(pydantic.BaseModel):
    """Request to open a pending deal"""
    open_type: typing.Annotated[OpenPendingDealRequestOpenType, pydantic.Field(..., alias="openType")]
    amount: int
    asset: Asset
    open_time: typing.Annotated[str, pydantic.Field(..., alias="openTime")]
    open_price: typing.Annotated[int, pydantic.Field(..., alias="openPrice")]
    timeframe: int
    min_payout: typing.Annotated[int, pydantic.Field(..., alias="minPayout")]
    command: Command


class ChangeAssetRequest(pydantic.BaseModel):
    """Request to change current asset"""
    asset: Asset
    period: int


# ============================================================================
# TYPE ADAPTERS
# ============================================================================

UpdateCloseValueListTypeAdapter = pydantic.TypeAdapter(list[UpdateCloseValueItem])
UpdateAssetItemListTypeAdapter = pydantic.TypeAdapter(list[UpdateAssetItem])
MarketSentimentItemListTypeAdapter = pydantic.TypeAdapter(list[MarketSentimentItem])
DealListTypeAdapter = pydantic.TypeAdapter(list[Deal])


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Enums
    "Asset", "AssetType", "Command", "DealAction", "IsDemo",
    "OpenPendingDealRequestOpenType",
    
    # Base Models
    "Account", "AuthorizationData", "Candle", "Deal", "PriceTick", "IndicatorResult",
    
    # Events
    "SuccessAuthEvent", "SuccessUpdateBalanceEvent", "UpdateHistoryFastEvent",
    "UpdateCloseValueItem", "SuccessCloseDealEvent", "MarketSentimentItem",
    "UpdateAssetItem", "AssetItemTimeframe",
    
    # Requests
    "OpenDealRequest", "CopySignalRequest", "OpenPendingDealRequest", "ChangeAssetRequest",
    
    # Adapters
    "UpdateCloseValueListTypeAdapter", "UpdateAssetItemListTypeAdapter",
    "MarketSentimentItemListTypeAdapter", "DealListTypeAdapter",
]