"""
Patches and improvements for the library - enhanced connection version
"""

import asyncio
import time
import logging
import functools
from .client import BasePocketOptionClient
from .trading import DealError  # ✅ importing from trading instead of errors

logger = logging.getLogger("pocket_trader.patches")

def apply_connection_patches():
    """Apply all connection patches to improve stability"""
    
    logger.info("🔧 Applying connection stability patches...")
    
    # Save original functions
    original_init = BasePocketOptionClient.__init__
    original_connect = BasePocketOptionClient.connect
    original_disconnect = BasePocketOptionClient.disconnect
    original_handle = BasePocketOptionClient.handle_new_event
    
    # ===== 1. Monkey-patch __init__ =====
    @functools.wraps(original_init)
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Add new connection variables
        self._heartbeat_running = False
        self._watchdog_running = False
        self._last_data = time.time()
        self._last_pong = time.time()
        self._connect_url = None
        self._reconnect_lock = asyncio.Lock()
        self._force_reconnecting = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 50
        
        logger.debug("✅ Connection patches initialized")
    
    BasePocketOptionClient.__init__ = patched_init
    
    # ===== 2. Add update_last_data =====
    def update_last_data(self):
        """Update last data timestamp"""
        self._last_data = time.time()
    
    BasePocketOptionClient.update_last_data = update_last_data
    
    # ===== 3. Add _heartbeat_loop =====
    async def heartbeat_loop(self):
        """Heartbeat loop to keep the connection alive"""
        self._heartbeat_running = True
        self._last_pong = time.time()
        
        logger.info("💓 Heartbeat loop started")
        
        while self._heartbeat_running and self.sio.connected and not self._force_reconnecting:
            try:
                await asyncio.sleep(15)  # every 15 seconds
                
                if not self.sio.connected or self._force_reconnecting:
                    break
                
                # Send ping
                ping_time = time.time()
                logger.debug("📡 Sending ping")
                await self.emit.ps()
                
                # Wait for pong
                await asyncio.sleep(2)
                
                # Check response
                if time.time() - self._last_pong > 20:
                    logger.warning("⚠️ No pong received - connection may be stale")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
        
        self._heartbeat_running = False
        logger.debug("💓 Heartbeat loop stopped")
    
    BasePocketOptionClient._heartbeat_loop = heartbeat_loop
    
    # ===== 4. Add _watchdog_loop =====
    async def watchdog_loop(self):
        """Watchdog loop to detect silent disconnections"""
        self._watchdog_running = True
        self._last_data = time.time()
        
        logger.info("👀 Watchdog loop started")
        
        while self._watchdog_running and self.sio.connected and not self._force_reconnecting:
            try:
                await asyncio.sleep(10)  # every 10 seconds
                
                if not self.sio.connected or self._force_reconnecting:
                    break
                
                # If 30 seconds pass without data
                if time.time() - self._last_data > 30:
                    logger.warning("⚠️ No data for 30s - connection may be dead")
                    asyncio.create_task(self._force_reconnect("NO_DATA"))
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                await asyncio.sleep(5)
        
        self._watchdog_running = False
        logger.debug("👀 Watchdog loop stopped")
    
    BasePocketOptionClient._watchdog_loop = watchdog_loop
    
    # ===== 5. Add _force_reconnect =====
    async def force_reconnect(self, reason: str):
        """Force reconnect with debounce"""
        async with self._reconnect_lock:
            if self._force_reconnecting:
                return
            
            self._force_reconnecting = True
            self._reconnect_attempts += 1
            
            logger.warning(f"🔄 Force reconnecting due to: {reason} (attempt {self._reconnect_attempts})")
            
            try:
                # Disconnect current connection
                await self.disconnect()
                
                # Smart delay
                wait_time = min(30, 2 ** min(self._reconnect_attempts, 5))
                logger.info(f"⏳ Waiting {wait_time}s before reconnect...")
                await asyncio.sleep(wait_time)
                
                # Reconnect
                if self._connect_url:
                    logger.info(f"📡 Reconnecting to {self._connect_url}")
                    await self.connect(url=self._connect_url)
                    logger.info("✅ Reconnected successfully")
                    self._reconnect_attempts = 0
                    
            except Exception as e:
                logger.error(f"❌ Force reconnect failed: {e}")
                
                # If it failed, retry after a minute
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    logger.info("⏰ Will retry in 60 seconds...")
                    await asyncio.sleep(60)
                    asyncio.create_task(self._force_reconnect("RETRY"))
            finally:
                self._force_reconnecting = False
    
    BasePocketOptionClient._force_reconnect = force_reconnect
    
    # ===== 6. Monkey-patch connect =====
    @functools.wraps(original_connect)
    async def patched_connect(self, url, *args, **kwargs):
        """Improved version of connect"""
        self._connect_url = url
        self._last_data = time.time()
        self._last_pong = time.time()
        self._force_reconnecting = False
        
        logger.info(f"🔌 Connecting to {url}")
        
        result = await original_connect(self, url, *args, **kwargs)
        
        # Start loops after connection
        if self.sio.connected:
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._watchdog_loop())
            logger.info("✅ Connection monitoring started")
        
        return result
    
    BasePocketOptionClient.connect = patched_connect
    
    # ===== 7. Monkey-patch disconnect =====
    @functools.wraps(original_disconnect)
    async def patched_disconnect(self, *args, **kwargs):
        """Improved version of disconnect"""
        self._heartbeat_running = False
        self._watchdog_running = False
        logger.info("🔌 Disconnecting from server")
        return await original_disconnect(self, *args, **kwargs)
    
    BasePocketOptionClient.disconnect = patched_disconnect
    
    # ===== 8. Monkey-patch handle_new_event =====
    @functools.wraps(original_handle)
    async def patched_handle(self, event_name, data=None):
        """Improved version of handle_new_event"""
        self.update_last_data()
        
        if event_name in ["pong", "ping-server"]:
            self._last_pong = time.time()
            logger.debug("📡 Pong received")
        
        return await original_handle(self, event_name, data)
    
    BasePocketOptionClient.handle_new_event = patched_handle
    
    logger.info("✅ All connection patches applied successfully")
    return True