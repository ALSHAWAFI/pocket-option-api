"""
Constants used throughout the library
"""

import enum
from typing import Dict, Final, List


# ============== Version ==============
VERSION: Final[str] = "2.0.0"


# ============== Trading Limits ==============
API_LIMITS_MIN_ORDER_AMOUNT: Final[int] = 1
API_LIMITS_MAX_ORDER_AMOUNT: Final[int] = 50_000
API_LIMITS_MIN_DURATION: Final[int] = 5
API_LIMITS_MAX_DURATION: Final[int] = 43_200  # 12 hours
API_LIMITS_MAX_CONCURRENT_ORDERS: Final[int] = 10
API_LIMITS_RATE_LIMIT: Final[int] = 100  # requests per second


# ============== Technical Constants ==============
MAX_INT_32: Final[int] = 2_147_483_647
TIMESTAMP_OFFSET: Final[int] = -7200  # Platform timestamp offset


# ============== Network Constants ==============
DEFAULT_ORIGIN: Final[str] = "https://m.pocketoption.com"
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) "
    "Gecko/20100101 Firefox/143.0"
)


# ============== Connection Settings ==============
DEFAULT_RECONNECTION_ATTEMPTS = 50
DEFAULT_RECONNECTION_DELAY = 2
DEFAULT_RECONNECTION_DELAY_MAX = 30
MAX_RECONNECT_BACKOFF = 60
HEARTBEAT_INTERVAL = 15
WATCHDOG_INTERVAL = 10
DATA_TIMEOUT = 30
PONG_TIMEOUT = 20


# ============== Message Sizes ==============
class MESSAGE_SIZES:
    """Message sizes in bytes"""
    STREAM: int = 39  # Live price updates
    CHAFOR: int = 19  # Signal and candle messages
    HEARTBEAT: int = 1  # Heartbeat


# ============== Signal Types ==============
class SIGNAL_TYPES:
    """Chafor signal types"""
    STRONG_BUY: int = 1
    CANDLE_CLOSE: int = 2
    MEDIUM_INDICATOR: int = 3
    WARNING: int = 4
    STRONG_BREAKOUT: int = 5
    
    # Signal names
    NAMES: Dict[int, str] = {
        1: "STRONG_BUY",
        2: "CANDLE_CLOSE",
        3: "MEDIUM_INDICATOR",
        4: "WARNING",
        5: "STRONG_BREAKOUT",
    }


# ============== Server Regions ==============
class Regions(enum.StrEnum):
    """Available server regions for connection"""
    UNITED_STATES_NORTH = "wss://api-us-north.po.market"
    UNITED_STATES_SOUTH = "wss://api-us-south.po.market"
    EUROPA = "wss://api-eu.po.market"
    ASIA = "wss://api-asia.po.market"
    UNITED_STATES_2 = "wss://api-us2.po.market"
    UNITED_STATES_3 = "wss://api-us3.po.market"
    UNITED_STATES_4 = "wss://api-us4.po.market"
    FRANCE_1 = "wss://api-fr.po.market"
    FRANCE_2 = "wss://api-fr2.po.market"
    RUSSIA = "wss://api-msk.po.market"
    INDIA = "wss://api-in.po.market"
    FINLAND = "wss://api-fin.po.market"
    SEYCHELLES = "wss://api-sc.po.market"
    HONGKONG = "wss://api-hk.po.market"
    SERVER_1 = "wss://api-spb.po.market"
    SERVER_2 = "wss://api-l.po.market"
    SERVER_3 = "wss://api-c.po.market"
    DEMO = "wss://demo-api-eu.po.market"
    DEMO_2 = "wss://try-demo-eu.po.market"
    
    @classmethod
    def get_url(cls, region: str) -> str:
        """Get URL for region"""
        try:
            return cls[region.upper()].value
        except KeyError:
            # Try to find close region
            if region.lower() in ['us', 'usa', 'united states']:
                return cls.UNITED_STATES_NORTH.value
            if region.lower() in ['eu', 'europe']:
                return cls.EUROPA.value
            if region.lower() in ['asia', 'as']:
                return cls.ASIA.value
            if region.lower() in ['demo', 'test']:
                return cls.DEMO.value
            return cls.EUROPA.value  # Default


# ============== Asset Categories ==============
class AssetCategory:
    """Asset categories for grouping"""
    
    FOREX = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
        "AUDUSD", "NZDUSD", "AUDCAD", "AUDJPY", "EURGBP"
    ]
    
    COMMODITIES = [
        "XAUUSD", "XAGUSD", "UKBrent", "USCrude",
        "XNGUSD", "XPTUSD", "XPDUSD"
    ]
    
    CRYPTO = [
        "BTCUSD", "ETHUSD", "DASH_USD", "BTCGBP",
        "BTCJPY", "BCHEUR", "BCHGBP", "DOTUSD", "LNKUSD"
    ]
    
    INDICES = [
        "SP500", "NASUSD", "DJI30", "JPN225",
        "D30EUR", "E50EUR", "F40EUR", "CAC40",
        "AUS200", "SMI20", "H33HKD"
    ]
    
    STOCKS = [
        "#AAPL", "#MSFT", "#TSLA", "#FB", "#NFLX",
        "#INTC", "#BA", "#JPM", "#JNJ", "#PFE"
    ]
    
    # OTC versions
    OTC_FOREX = [f"{pair}_otc" for pair in FOREX]
    OTC_COMMODITIES = [f"{comm}_otc" for comm in COMMODITIES]
    OTC_INDICES = [f"{idx}_otc" for idx in INDICES]
    OTC_STOCKS = [f"{stock}_otc" for stock in STOCKS]
    
    @classmethod
    def get_category(cls, asset: str) -> str:
        """Get category of an asset"""
        asset = asset.upper()
        
        if asset in cls.FOREX or asset in cls.OTC_FOREX:
            return "forex"
        elif asset in cls.COMMODITIES or asset in cls.OTC_COMMODITIES:
            return "commodity"
        elif asset in cls.CRYPTO:
            return "crypto"
        elif asset in cls.INDICES or asset in cls.OTC_INDICES:
            return "index"
        elif asset in cls.STOCKS or asset in cls.OTC_STOCKS:
            return "stock"
        else:
            return "unknown"


# ============== Update Items Field Names ==============
UPDATE_ITEMS_NAMES = [
    "id", "symbol", "label", "type", "precision", "payout",
    "min_duration", "max_duration", "step_duration", "volatility_index",
    "spread", "leverage", "extra_data", "expire_time", "is_active",
    "timeframes", "start_time", "default_timeframe", "status_code"
]


# ============== Timeframes ==============
TIMEFRAMES = {
    '1m': 60,
    '5m': 300,
    '15m': 900,
    '30m': 1800,
    '1h': 3600,
    '4h': 14400,
    '1d': 86400,
    '1w': 604800,
}


# ============== Default Values ==============
DEFAULT_TIMEFRAME = 60  # 1 minute
DEFAULT_CANDLE_COUNT = 100
DEFAULT_HISTORY_DAYS = 30