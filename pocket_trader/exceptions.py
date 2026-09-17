"""
Custom exceptions for PocketTrader
Merged: exceptions.py + errors.py
"""

from typing import Optional, Dict, Any, Literal


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class PocketTraderError(Exception):
    """Base exception for all PocketTrader errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'details': self.details
        }


# ============================================================================
# DEAL ERRORS (from errors.py)
# ============================================================================

DealErrorCode = Literal[
    "min_amount", "max_amount", "min_duration", "max_duration",
    "max_orders", "timeout", "not_found", "send_failed",
    "invalid_action", "insufficient_balance",
]


class DealError(ValueError):
    """Exception raised for deal/trade errors"""
    
    def __init__(self, code: DealErrorCode, message: str, extras: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extras = extras or {}

    def __str__(self) -> str:
        extras_str = f" {self.extras}" if self.extras else ""
        return f"[{self.code}] {self.message}{extras_str}"
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "extras": self.extras,
        }


# ============================================================================
# CONNECTION ERRORS
# ============================================================================

class ConnectionError(PocketTraderError):
    """Raised when connection fails"""
    pass


class AuthError(PocketTraderError):
    """Raised when authentication fails"""
    pass


class SubscriptionError(PocketTraderError):
    """Raised when subscription fails"""
    pass


# ============================================================================
# TRADE ERRORS
# ============================================================================

class TradeError(PocketTraderError):
    """Raised when trade operation fails"""
    pass


class InsufficientBalanceError(TradeError):
    """Raised when balance is insufficient for trade"""
    pass


# ============================================================================
# STORAGE ERRORS
# ============================================================================

class StorageError(PocketTraderError):
    """Raised when storage operation fails"""
    pass


# ============================================================================
# INDICATOR ERRORS
# ============================================================================

class IndicatorError(PocketTraderError):
    """Raised when indicator calculation fails"""
    pass


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(PocketTraderError):
    """Raised when data validation fails"""
    pass


class InvalidAssetError(ValidationError):
    """Raised when asset is invalid"""
    pass


# ============================================================================
# TIMEOUT ERRORS
# ============================================================================

class TimeoutError(PocketTraderError):
    """Raised when operation times out"""
    pass


# ============================================================================
# RATE LIMIT ERRORS
# ============================================================================

class RateLimitError(PocketTraderError):
    """Raised when rate limit is exceeded"""
    pass


# ============================================================================
# PARSE ERRORS
# ============================================================================

class ParseError(PocketTraderError):
    """Raised when data parsing fails"""
    pass


# ============================================================================
# ERROR CODES
# ============================================================================

class ErrorCode:
    """Error codes for common situations"""
    
    # Connection errors
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    DISCONNECTED = "disconnected"
    
    # Auth errors
    AUTH_FAILED = "auth_failed"
    INVALID_CREDENTIALS = "invalid_credentials"
    SESSION_EXPIRED = "session_expired"
    
    # Trade errors
    MIN_AMOUNT = "min_amount"
    MAX_AMOUNT = "max_amount"
    MIN_DURATION = "min_duration"
    MAX_DURATION = "max_duration"
    MAX_ORDERS = "max_orders"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    
    # Validation errors
    INVALID_ASSET = "invalid_asset"
    INVALID_ACTION = "invalid_action"
    INVALID_DATA = "invalid_data"
    
    # Rate limits
    RATE_LIMIT = "rate_limit"
    
    # Timeout
    TIMEOUT = "timeout"
    DEAL_TIMEOUT = "deal_timeout"