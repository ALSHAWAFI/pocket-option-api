# client.py
"""
Main Pocket Option client with advanced features
Supports: Rate Limiting, Retry Logic, Connection Management
"""

import asyncio
import time
import logging
import functools
from typing import Optional, Callable, Awaitable, List, Dict, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass

import aiohttp
import socketio
import pydantic

from .constants import DEFAULT_ORIGIN, DEFAULT_USER_AGENT
from .utils import setup_logger, get_json_function, fix_timestamp
from .middleware import Middleware, MakeJsonOnMiddleware, FixTypesOnMiddleware
from . import models
from .exceptions import ConnectionError as PocketConnectionError, RateLimitError


# ============================================================================
# RATE LIMITER - Token Bucket Algorithm
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter
    Prevents API rate limit violations
    """
    
    def __init__(self, rate: int = 100, per_seconds: int = 1):
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = rate
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        self._logger = setup_logger("RateLimiter")
        self.stats = {
            'total_requests': 0,
            'limited_requests': 0,
            'waits': 0
        }
    
    async def acquire(self) -> bool:
        """Acquire a token for request"""
        async with self._lock:
            self._refill()
            
            if self.tokens >= 1:
                self.tokens -= 1
                self.stats['total_requests'] += 1
                return True
            
            self.stats['limited_requests'] += 1
            self.stats['waits'] += 1
            
            # Wait for token with timeout
            start = time.time()
            while self.tokens < 1 and (time.time() - start) < 5:
                await asyncio.sleep(0.1)
                self._refill()
            
            if self.tokens >= 1:
                self.tokens -= 1
                self.stats['total_requests'] += 1
                return True
            
            return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.rate / self.per_seconds)
        
        if new_tokens > 0:
            self.tokens = min(self.rate, self.tokens + new_tokens)
            self.last_refill = now
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            **self.stats,
            'current_tokens': self.tokens,
            'rate': f"{self.rate}/{self.per_seconds}s"
        }
    
    def reset(self):
        """Reset rate limiter"""
        self.tokens = self.rate
        self.last_refill = time.time()
        self.stats = {'total_requests': 0, 'limited_requests': 0, 'waits': 0}


# ============================================================================
# RETRY MANAGER - Smart Retry with Exponential Backoff
# ============================================================================

class RetryManager:
    """
    Smart retry mechanism with exponential backoff
    Only retries on retryable errors
    """
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 10.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._logger = setup_logger("RetryManager")
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff"""
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def _is_retryable(self, error: Exception) -> bool:
        """Check if error is retryable"""
        retryable = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            RateLimitError,
            PocketConnectionError
        )
        return isinstance(error, retryable)
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self._is_retryable(e) or attempt == self.max_retries:
                    raise
                
                delay = self._calculate_delay(attempt)
                self._logger.debug(f"Retry {attempt}/{self.max_retries} after {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        raise last_error or Exception("All retry attempts failed")


# ============================================================================
# CONNECTION STATE
# ============================================================================

class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

@dataclass
class ConnectionConfig:
    """Connection configuration"""
    heartbeat_interval: float = 30.0      # ✅ increased from 15 to 30 seconds
    watchdog_interval: float = 15.0       # ✅ increased from 10 to 15 seconds
    data_timeout: float = 60.0            # ✅ increased from 30 to 60 seconds
    pong_timeout: float = 90.0            # ✅ increased from 20 to 45 seconds
    max_reconnect_attempts: int = 20      # ✅ increased
    initial_reconnect_delay: float = 3.0  # ✅ increased
    max_reconnect_delay: float = 60.0
    reconnect_backoff_multiplier: float = 1.5


class ConnectionManager:
    """Manages WebSocket connection with stability features"""
    
    def __init__(self, client: 'BasePocketOptionClient', config: Optional[ConnectionConfig] = None):
        self.client = client
        self.config = config or ConnectionConfig()
        self.state = ConnectionState.DISCONNECTED
        self._last_data = 0.0
        self._last_pong = 0.0
        self._reconnect_attempts = 0
        self._tasks: set[asyncio.Task] = set()
        self._logger = setup_logger("ConnectionManager")
        self._state_listeners: List[Callable[[ConnectionState], Awaitable[None]]] = []
        self._lock = asyncio.Lock()
    
    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED
    
    async def start_monitoring(self):
        """Start heartbeat and watchdog tasks"""
        self._last_data = time.time()
        self._last_pong = time.time()
        
        heartbeat = asyncio.create_task(self._heartbeat_loop())
        watchdog = asyncio.create_task(self._watchdog_loop())
        
        self._tasks.update({heartbeat, watchdog})
        self._logger.info("Connection monitoring started")

    async def _heartbeat_loop(self):
        while self.state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)

                if self.state != ConnectionState.CONNECTED:
                    break

                await self.client.emit.ps()
                await asyncio.sleep(5)

                time_since_pong = time.time() - self._last_pong
                if time_since_pong > self.config.pong_timeout:
                    # ✅ changed from warning to debug
                    self._logger.debug(f"No pong received for {time_since_pong:.0f}s")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Heartbeat error: {e}")

    async def _watchdog_loop(self):
        """Watchdog to detect silent disconnections"""
        while self.state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.config.watchdog_interval)

                if self.state != ConnectionState.CONNECTED:
                    break

                time_since_data = time.time() - self._last_data
                if time_since_data > self.config.data_timeout:
                    self._logger.warning(f"⚠️ No data for {time_since_data:.0f}s")
                    # ✅ Don't disconnect immediately in a quiet market
                    # Only if too much time has passed
                    if time_since_data > self.config.data_timeout * 2:
                        await self._handle_timeout("data_timeout")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Watchdog error: {e}")
    
    async def _handle_timeout(self, reason: str):
        """Handle connection timeout"""
        async with self._lock:
            if self.state != ConnectionState.CONNECTED:
                return
            
            self._logger.warning(f"🔄 Connection timeout: {reason}")
            self.state = ConnectionState.RECONNECTING
            await self._notify_state_change()
            asyncio.create_task(self._reconnect())
    
    def update_last_data(self):
        """Update last data timestamp"""
        self._last_data = time.time()
    
    def update_last_pong(self):
        """Update last pong timestamp"""
        self._last_pong = time.time()
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        async with self._lock:
            self._reconnect_attempts += 1
        
        try:
            delay = min(
                self.config.initial_reconnect_delay * 
                (self.config.reconnect_backoff_multiplier ** (self._reconnect_attempts - 1)),
                self.config.max_reconnect_delay
            )
            
            self._logger.info(f"⏳ Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts})")
            await asyncio.sleep(delay)
            
            if self._reconnect_attempts > self.config.max_reconnect_attempts:
                self._logger.error("❌ Max reconnection attempts reached")
                async with self._lock:
                    self.state = ConnectionState.FAILED
                    await self._notify_state_change()
                return
            
            success = await self.client._reconnect()
            
            async with self._lock:
                if success:
                    self.state = ConnectionState.CONNECTED
                    self._reconnect_attempts = 0
                    self._logger.info("✅ Reconnected successfully")
                else:
                    self.state = ConnectionState.RECONNECTING
                    asyncio.create_task(self._reconnect())
                
                await self._notify_state_change()
                
        except Exception as e:
            self._logger.error(f"Reconnection error: {e}")
            async with self._lock:
                self.state = ConnectionState.RECONNECTING
                asyncio.create_task(self._reconnect())
    
    def stop_monitoring(self):
        """Stop all monitoring tasks"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        self._logger.info("Connection monitoring stopped")
    
    async def _notify_state_change(self):
        """Notify listeners of state change"""
        for callback in self._state_listeners:
            try:
                await callback(self.state)
            except Exception as e:
                self._logger.error(f"State change callback error: {e}")
    
    def add_state_listener(self, callback: Callable[[ConnectionState], Awaitable[None]]):
        """Add state change listener"""
        self._state_listeners.append(callback)


# ============================================================================
# BASE CLIENT
# ============================================================================

class BasePocketOptionClient:
    """Base Socket.IO client with middleware, rate limiting, and retry logic"""
    
    def __init__(
        self,
        middlewares: Optional[List[Middleware]] = None,
        *,
        reconnection: bool = True,
        reconnection_attempts: int = 0,
        reconnection_delay: float = 1.0,
        reconnection_delay_max: float = 5.0,
        randomization_factor: float = 0.5,
        logger: Union[bool, logging.Logger] = False,
        engineio_logger: bool = False,
        json: Optional[Any] = None,
        handle_sigint: bool = True,
        request_timeout: float = 5,
        http_session: Optional[aiohttp.ClientSession] = None,
        ssl_verify: bool = True,
        websocket_extra_options: Optional[dict] = None,
        timestamp_requests: bool = False,
        rate_limit: int = 100,
        rate_limit_per_seconds: int = 1,
        max_retries: int = 3,
    ):
        self.authorization_data: Optional[models.AuthorizationData] = None
        self.middlewares = middlewares or [MakeJsonOnMiddleware(), FixTypesOnMiddleware()]
        self.json = json or get_json_function()
        self._logger = setup_logger("client") if logger is False else logger
        
        # Rate limiting
        self._rate_limiter = RateLimiter(rate=rate_limit, per_seconds=rate_limit_per_seconds)
        self._retry_manager = RetryManager(max_retries=max_retries)
        
        # Socket.IO client
        self.sio = socketio.AsyncClient(
            reconnection=reconnection,
            reconnection_attempts=reconnection_attempts,
            reconnection_delay=reconnection_delay,
            reconnection_delay_max=reconnection_delay_max,
            randomization_factor=randomization_factor,
            logger=logger is not False,
            serializer="default",
            json=self.json,
            handle_sigint=handle_sigint,
            request_timeout=request_timeout,
            http_session=http_session,
            ssl_verify=ssl_verify,
            websocket_extra_options=websocket_extra_options,
            timestamp_requests=timestamp_requests,
            engineio_logger=engineio_logger,
        )
        
        # Connection manager
        self.conn_manager = ConnectionManager(self)
        self.conn_manager.add_state_listener(self._on_connection_state_change)
        
        # Handlers
        self._handlers: List[dict] = []
        self._setup_handlers()
        
        # Connection URL
        self._connect_url: Optional[str] = None
    
    def _setup_handlers(self):
        """Setup default event handlers"""
        self.sio.on("connect", handler=self._on_connect)
        self.sio.on("disconnect", handler=self._on_disconnect)
        self.sio.on("*", handler=self._on_any_event)
    
    async def _on_connect(self):
        """Handle connect event"""
        self.conn_manager.state = ConnectionState.CONNECTED
        self.conn_manager.update_last_data()
        self.conn_manager.update_last_pong()
        await self.conn_manager.start_monitoring()
        self._logger.info("✅ Connected to server")
        await self._handle_event("connect")
    
    async def _on_disconnect(self):
        """Handle disconnect event"""
        self.conn_manager.state = ConnectionState.DISCONNECTED
        self.conn_manager.stop_monitoring()
        self._logger.warning("🔌 Disconnected from server")
        await self._handle_event("disconnect")

    async def _on_any_event(self, event: str, data: Optional[bytes] = None):
        """Handle any incoming event"""
        self.conn_manager.update_last_data()

        # ✅ Handle new connection events
        if event in ["pong", "ping-server"]:
            self.conn_manager.update_last_pong()
            self._logger.debug(f"📡 {event} received")
            return

        # ✅ Handle reconnection events
        if event in ["reconnect", "reconnecting", "reconnect_attempt", "reconnect_error", "reconnect_failed"]:
            self._logger.info(f"🔄 {event}: {data}")
            # Don't pass them to regular handlers
            return

        # ✅ Handle connection errors
        if event in ["error", "connect_error"]:
            self._logger.error(f"❌ {event}: {data}")
            # Don't pass them to regular handlers
            return

        # ✅ Handle new data events
        if event in ["updateCharts", "updateIndicators", "updateFavorites", "updatePriceAlerts"]:
            self._logger.debug(f"📊 {event}: {type(data)}")

        # Process through middlewares
        if data is not None:
            for middleware in self.middlewares:
                try:
                    data = await middleware.on(event, data)
                except Exception as e:
                    self._logger.error(f"Middleware error: {e}")

        await self._handle_event(event, data)
    
    async def _handle_event(self, event: str, data: Optional[Any] = None):
        """Internal event handler"""
        for handler in filter(lambda x: x["event"] == event, self._handlers):
            try:
                result = handler["callback"](data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.error(f"Handler error for {event}: {e}")
    
    async def _on_connection_state_change(self, state: ConnectionState):
        """Handle connection state change"""
        self._logger.debug(f"Connection state changed to {state.value}")
    
    async def _reconnect(self) -> bool:
        """Internal reconnect method"""
        if not self._connect_url:
            self._logger.error("No connection URL available")
            return False
        
        try:
            await self.disconnect()
            await asyncio.sleep(2)
            await self.connect(self._connect_url)
            return True
        except Exception as e:
            self._logger.error(f"Reconnect failed: {e}")
            return False
    
    def add_on(self, event: str, handler: Callable, model: Optional[Any] = None):
        """Add event handler"""
        self._handlers.append({
            "event": event,
            "callback": handler,
            "model": model
        })
        return handler
    
    async def send(self, event: str, data: Optional[Any] = None, 
                   callback: Optional[Callable] = None, 
                   use_retry: bool = True) -> None:
        """Send event with rate limiting and optional retry"""
        # Rate limiting
        if not await self._rate_limiter.acquire():
            raise RateLimitError("Rate limit exceeded")
        
        async def _send():
            return await self.sio.emit(event=event, data=data, callback=callback)
        
        if use_retry:
            return await self._retry_manager.execute(_send)
        else:
            return await _send()
    
    async def connect(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            auth: Optional[models.AuthorizationData] = None,
            wait: bool = True,
            wait_timeout: float = 30,
            retry: bool = False,
    ):
        """Connect to server"""
        headers = headers or {}
        headers.setdefault("Origin", DEFAULT_ORIGIN)
        headers.setdefault("User-Agent", DEFAULT_USER_AGENT)
        
        self._connect_url = url
        self.conn_manager.state = ConnectionState.CONNECTING
        
        self._logger.info(f"🔌 Connecting to {url}")
        
        sio_auth = None
        if auth:
            if isinstance(auth, dict):
                sio_auth = auth
            else:
                sio_auth = {
                    "session": auth.session,
                    "isDemo": auth.is_demo,
                    "uid": auth.uid,
                    "platform": auth.platform,
                }
        
        result = await self.sio.connect(
            url,
            headers=headers,
            auth=sio_auth,
            transports=["websocket"],
            namespaces=["/"],
            socketio_path="socket.io",
            wait=wait,
            wait_timeout=wait_timeout,
            retry=retry,
        )
        
        return result
    
    async def disconnect(self):
        """Disconnect from server"""
        self.conn_manager.stop_monitoring()
        self.conn_manager.state = ConnectionState.DISCONNECTED
        self._logger.info("🔌 Disconnecting")
        await self.sio.disconnect()
    
    async def wait(self):
        """Wait until connection is closed"""
        await self.sio.wait()
    
    async def shutdown(self):
        """Shutdown client"""
        await self.disconnect()
        await self.sio.shutdown()
    
    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return self._rate_limiter.get_stats()


# ============================================================================
# MAIN CLIENT
# ============================================================================

from .generated_client import PocketOptionClientEmit, PocketOptionClientOn


class PocketOptionClient(BasePocketOptionClient):
    """Complete Pocket Option client with all advanced features"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on = PocketOptionClientOn(self)
        self._emit = PocketOptionClientEmit(self)
    
    @property
    def on(self):
        """Event handlers"""
        return self._on
    
    @property
    def emit(self):
        """Emit methods"""
        return self._emit


def apply_connection_patches():
    """Apply connection patches (for backward compatibility)"""
    pass