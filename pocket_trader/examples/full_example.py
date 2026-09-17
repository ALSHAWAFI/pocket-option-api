#!/usr/bin/env python3
"""
Pocket Option SDK - Comprehensive usage example
Comprehensive example demonstrating all library features
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

# Add library path (if working locally)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pocket_trader import (
    # Core
    PocketOptionClient,
    Asset,
    Deal,
    Candle,
    
    # Indicators
    Indicators,
    
    # Risk Management
    RiskManager,
    
    # Storage
    CandleBuilder,
    MemoryCandleStorage,
    MemoryDealsStorage,
    
    # Stream & Chafor
    StreamUpdate,
    StreamProcessor,
    ChaforMessage,
    ChaforProcessor,
    
    # Constants
    Regions,
    OrderType,
    
    # Exceptions
    PocketTraderError,
    ConnectionError,
    AuthError,
    TradingError,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pocket_trader.log')
    ]
)
logger = logging.getLogger("PocketTrader-Example")


class TradingBot:
    """
    Integrated trading bot using all library features
    """
    
    def __init__(
        self,
        session_id: str,
        region: str = "demo",
        demo_mode: bool = True,
        initial_balance: float = 1000
    ):
        """
        Initialize the trading bot
        
        Args:
            session_id: Session ID from browser
            region: Server region (eu, us, asia, demo)
            demo_mode: Use a demo account
            initial_balance: Initial balance for risk management
        """
        self.session_id = session_id
        self.region = region
        self.demo_mode = demo_mode
        self.running = False
        
        # 1️⃣ **Main client**
        self.client = PocketOptionClient(
            timeout=30,
            auto_reconnect=True
        )
        
        # 2️⃣ **Risk management**
        self.risk_manager = RiskManager(initial_balance=initial_balance)
        self.risk_manager.max_risk_per_trade = 0.02  # 2% risk
        self.risk_manager.max_daily_trades = 10
        
        # 3️⃣ **Candle storage**
        self.candle_storage = MemoryCandleStorage(self.client)
        
        # 4️⃣ **Deals storage**
        self.deals_storage = MemoryDealsStorage(self.client)
        
        # 5️⃣ **Stream processing**
        self.stream_processor = StreamProcessor(max_history=1000)
        
        # 6️⃣ **Chafor processing (signals)**
        self.chafor_processor = ChaforProcessor()
        
        # 7️⃣ **Technical indicators**
        self.indicators = Indicators()
        
        # Trading data
        self.assets_to_trade = [
            Asset.EURUSD,
            Asset.GBPUSD,
            Asset.XAUUSD,
            Asset.BTCUSD,
        ]
        self.current_prices: Dict[Asset, float] = {}
        self.price_history: Dict[Asset, list] = {asset: [] for asset in self.assets_to_trade}
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info(f"✅ Trading bot initialized for region: {region}")
    
    def _setup_handlers(self):
        """Setup all event handlers"""
        
        # 1️⃣ Connection handler
        @self.client.on.connect
        async def on_connect(Data=None):
            logger.info("🔌 Connected to server")
        
        # 2️⃣ Disconnection handler
        @self.client.on.disconnect
        async def on_disconnect(Data=None):
            logger.warning("🔌 Disconnected from server")
            if self.running:
                logger.info("Attempting to reconnect...")
        
        # 3️⃣ Balance update handler
        @self.client.on.update_balance
        async def on_balance_update(data):
            if data.is_demo == self.demo_mode:
                logger.info(f"💰 Balance updated: {data.balance}")
                self.risk_manager.current_balance = data.balance
        
        # 4️⃣ Price update handler (Stream)
        @self.client.on.update_close_value
        async def on_price_update(items):
            for item in items:
                asset = item.asset
                price = item.value
                timestamp = item.timestamp
                
                # Store current price
                self.current_prices[asset] = price
                
                # Add to history
                if asset in self.price_history:
                    self.price_history[asset].append(price)
                    # Keep last 100 prices
                    if len(self.price_history[asset]) > 100:
                        self.price_history[asset] = self.price_history[asset][-100:]
                
                # Process the Stream
                # In practice, you may need to convert data to StreamUpdate
                logger.debug(f"📊 {asset}: {price:.5f}")
        
        # 5️⃣ Open deals update handler
        @self.client.on.update_opened_deals
        async def on_opened_deals(deals):
            for deal in deals:
                logger.info(f"📈 Deal opened: {deal.asset} {deal.command} amount={deal.amount}")
                await self.deals_storage.add_or_update_deal(deal)
        
        # 6️⃣ Closed deals update handler
        @self.client.on.update_closed_deals
        async def on_closed_deals(deals):
            for deal in deals:
                profit = deal.profit or 0
                logger.info(f"📉 Deal closed: {deal.asset} profit={profit:.2f}")
                await self.deals_storage.add_or_update_deal(deal)
                
                # Update risk management
                self.risk_manager.update_trade_result(profit)
                self.risk_manager.remove_trade(str(deal.id))
        
        # 7️⃣ Successful deal open handler
        @self.client.on.success_open_deal
        async def on_success_open(deal):
            logger.info(f"✅ Deal opened successfully: {deal.id}")
            await self.deals_storage.add_or_update_deal(deal)
            self.risk_manager.add_trade(str(deal.id))
        
        # 8️⃣ Successful deal close handler
        @self.client.on.success_close_deal
        async def on_success_close(event):
            logger.info(f"✅ Deal closed with profit: {event.profit}")
            for deal in event.deals:
                await self.deals_storage.add_or_update_deal(deal)
        
        # 9️⃣ Market sentiment change handler (Chafor)
        @self.client.on.change_market_sentiment
        async def on_market_sentiment(items):
            for item in items:
                logger.info(f"📊 Market sentiment {item.asset}: {item.value}% bullish")
        
        # 🔟 Asset update handler
        @self.client.on.update_assets
        async def on_assets_update(assets):
            logger.info(f"📋 Assets updated: {len(assets)} assets")
        
        # 1️⃣1️⃣ Authentication success handler
        @self.client.on.success_auth
        async def on_auth_success(data):
            logger.info(f"✅ Authentication successful: {data.id}")
        
        logger.info("✅ Event handlers configured")
    
    async def connect_and_auth(self) -> bool:
        """
        Connect and authenticate with the server
        
        Returns:
            bool: Connection success
        """
        try:
            # 1️⃣ Connect
            logger.info(f"Connecting to {self.region}...")
            url = Regions.get_url(self.region)
            await self.client.connect(url)
            
            # 2️⃣ Authenticate
            logger.info("Authenticating...")
            await self.client.emit.auth({
                "session": self.session_id,
                "isDemo": 1 if self.demo_mode else 0,
                "uid": 0,
                "platform": 2,
                "isFastHistory": True,
                "isOptimized": True
            })
            
            # Wait for authentication
            await asyncio.sleep(2)
            
            logger.info("✅ Connected and authenticated successfully")
            return True
            
        except ConnectionError as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
        except AuthError as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    async def subscribe_to_assets(self):
        """Subscribe to assets for trading"""
        for asset in self.assets_to_trade:
            try:
                # Subscribe to price updates
                await self.client.emit.subscribe_to_asset(asset)
                logger.info(f"✅ Subscribed to {asset}")
                
                # Subscribe to market sentiment
                await self.client.emit.subscribe_for_market_sentiment(asset)
                
                # Short wait between subscriptions
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {asset}: {e}")
    
    async def get_historical_candles(self, asset: Asset, timeframe: int = 60, count: int = 100):
        """
        Get historical candles
        
        Args:
            asset: The asset
            timeframe: Period in seconds
            count: Number of candles
        """
        logger.info(f"📊 Getting historical candles for {asset}...")
        
        # Temporarily change asset to fetch history
        await self.client.emit.change_asset({
            "asset": asset,
            "period": timeframe
        })
        
        # Wait for data to load
        await asyncio.sleep(3)
        
        # Use CandleBuilder to build candles
        builder = CandleBuilder(asset, timeframe, max_candles=count)
        
        # In practice, data comes from the updateHistoryNewFast event
        logger.info(f"✅ Historical data requested for {asset}")
    
    async def analyze_market(self, asset: Asset) -> Dict[str, Any]:
        """
        Analyze the market using technical indicators
        
        Args:
            asset: The asset to analyze
            
        Returns:
            dict: Analysis results
        """
        if asset not in self.price_history or len(self.price_history[asset]) < 50:
            return {"signal": "neutral", "confidence": 0}
        
        prices = self.price_history[asset]
        
        # Calculate indicators
        rsi_result = self.indicators.rsi(prices, period=14)
        macd_result = self.indicators.macd(prices)
        bb_result = self.indicators.bollinger_bands(prices)
        
        # Analyze signals
        buy_signals = 0
        sell_signals = 0
        total_signals = 0
        
        # RSI
        if rsi_result["signal"] == "oversold":
            buy_signals += 2
        elif rsi_result["signal"] == "overbought":
            sell_signals += 2
        elif rsi_result["signal"] == "bullish":
            buy_signals += 1
        elif rsi_result["signal"] == "bearish":
            sell_signals += 1
        total_signals += 1
        
        # MACD
        if macd_result.get("signal_type") == "bullish":
            buy_signals += 1
        elif macd_result.get("signal_type") == "bearish":
            sell_signals += 1
        total_signals += 1
        
        # Bollinger Bands
        if bb_result.get("signal") == "oversold":
            buy_signals += 1
        elif bb_result.get("signal") == "overbought":
            sell_signals += 1
        total_signals += 1
        
        # Determine final signal
        if buy_signals > sell_signals:
            signal = "BUY"
            confidence = buy_signals / total_signals
        elif sell_signals > buy_signals:
            signal = "SELL"
            confidence = sell_signals / total_signals
        else:
            signal = "NEUTRAL"
            confidence = 0
        
        return {
            "asset": asset,
            "signal": signal,
            "confidence": confidence,
            "current_price": self.current_prices.get(asset, 0),
            "indicators": {
                "rsi": rsi_result,
                "macd": macd_result,
                "bollinger": bb_result,
            }
        }
    
    async def execute_trade(self, asset: Asset, signal: str, confidence: float):
        """
        Execute a trade based on the signal
        
        Args:
            asset: The asset
            signal: Trading signal (BUY/SELL)
            confidence: Confidence in the signal
        """
        # Check if trading is possible
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            logger.warning(f"Cannot trade: {reason}")
            return
        
        # Calculate position size
        amount = self.risk_manager.calculate_position_size(confidence=confidence)
        
        # Determine order type
        action = OrderType.CALL if signal == "BUY" else OrderType.PUT
        
        try:
            logger.info(f"🚀 Executing {action} for {asset} amount={amount:.2f}")
            
            # Open the deal
            deal = await self.deals_storage.open_deal(
                asset=asset,
                amount=int(amount),
                action=action,
                time=60,  # 60 seconds
                is_demo=1 if self.demo_mode else 0,
                check_limits=True
            )
            
            logger.info(f"✅ Deal opened: {deal.id}")
            
            # You can wait for the result
            # result = await self.deals_storage.check_deal_result(deal=deal, wait_time=120)
            # logger.info(f"💰 Deal result: profit={result.profit}")
            
        except TradingError as e:
            logger.error(f"❌ Trading error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("🔄 Starting trading loop...")
        
        while self.running:
            try:
                for asset in self.assets_to_trade:
                    # Analyze market
                    analysis = await self.analyze_market(asset)
                    
                    if analysis["signal"] != "NEUTRAL" and analysis["confidence"] > 0.5:
                        logger.info(f"🎯 Signal for {asset}: {analysis['signal']} "
                                   f"(confidence: {analysis['confidence']:.2f})")
                        
                        # Execute the trade
                        await self.execute_trade(
                            asset=asset,
                            signal=analysis["signal"],
                            confidence=analysis["confidence"]
                        )
                    
                    # Wait between assets
                    await asyncio.sleep(1)
                
                # Show risk statistics every minute
                if int(datetime.now().timestamp()) % 60 == 0:
                    metrics = self.risk_manager.get_metrics()
                    logger.info(f"📊 Risk Metrics: {metrics}")
                
                # Wait before next cycle
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    async def run(self):
        """Run the bot"""
        self.running = True
        
        try:
            # 1️⃣ Connect and authenticate
            if not await self.connect_and_auth():
                logger.error("Failed to connect. Exiting.")
                return
            
            # 2️⃣ Subscribe to assets
            await self.subscribe_to_assets()
            
            # 3️⃣ Get historical data
            for asset in self.assets_to_trade[:1]:  # first asset only
                await self.get_historical_candles(asset)
            
            # 4️⃣ Start trading loop
            await self.trading_loop()
            
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources before exiting"""
        logger.info("🧹 Cleaning up...")
        self.running = False
        
        # Unsubscribe
        for asset in self.assets_to_trade:
            try:
                await self.client.emit.unsubscribe_for_market_sentiment(asset)
            except:
                pass
        
        # Disconnect
        try:
            await self.client.disconnect()
        except:
            pass
        
        # Show final statistics
        metrics = self.risk_manager.get_metrics()
        logger.info("📊 Final Statistics:")
        for key, value in metrics.items():
            logger.info(f"   {key}: {value}")
        
        logger.info("👋 Goodbye!")


async def simple_example():
    """
    Simple example for basic usage
    """
    logger.info("=" * 50)
    logger.info("🔰 Simple Usage Example")
    logger.info("=" * 50)
    
    # 1️⃣ Create client
    client = PocketOptionClient(timeout=30)
    
    try:
        # 2️⃣ Connect
        await client.connect(Regions.DEMO)
        logger.info("✅ Connected to demo server")
        
        # 3️⃣ Authenticate
        auth_data = {
            "session": "your_session_id_here",
            "isDemo": 1,
            "uid": 0,
            "platform": 2,
            "isFastHistory": True,
            "isOptimized": True
        }
        await client.emit.auth(auth_data)
        logger.info("✅ Authentication sent")
        
        # 4️⃣ Subscribe to a pair
        await client.emit.subscribe_to_asset(Asset.EURUSD)
        logger.info(f"✅ Subscribed to {Asset.EURUSD}")
        
        # 5️⃣ Wait for some updates
        logger.info("Waiting for updates (10 seconds)...")
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        await client.disconnect()
        logger.info("👋 Disconnected")


async def indicators_example():
    """
    Example of using technical indicators
    """
    logger.info("=" * 50)
    logger.info("📊 Indicators Example")
    logger.info("=" * 50)
    
    # Sample data
    prices = [1.1050, 1.1060, 1.1040, 1.1070, 1.1080, 1.1075, 1.1090,
              1.1085, 1.1100, 1.1095, 1.1110, 1.1105, 1.1120, 1.1115,
              1.1130, 1.1125, 1.1140, 1.1135, 1.1150, 1.1145]
    
    highs = [p + 0.001 for p in prices]
    lows = [p - 0.001 for p in prices]
    
    # Calculate indicators
    indicators = Indicators()
    
    rsi = indicators.rsi(prices, period=14)
    logger.info(f"RSI: {rsi}")
    
    macd = indicators.macd(prices)
    logger.info(f"MACD: {macd}")
    
    bb = indicators.bollinger_bands(prices)
    logger.info(f"Bollinger Bands: {bb}")
    
    stoch = indicators.stochastic(highs, lows, prices)
    logger.info(f"Stochastic: {stoch}")
    
    williams = indicators.williams_r(highs, lows, prices)
    logger.info(f"Williams %R: {williams}")
    
    cci = indicators.cci(highs, lows, prices)
    logger.info(f"CCI: {cci}")
    
    adx = indicators.adx(highs, lows, prices)
    logger.info(f"ADX: {adx}")


async def risk_management_example():
    """
    Example of risk management
    """
    logger.info("=" * 50)
    logger.info("🎯 Risk Management Example")
    logger.info("=" * 50)
    
    # Create risk manager
    risk = RiskManager(initial_balance=1000)
    
    # Adjust settings
    risk.max_risk_per_trade = 0.02  # 2%
    risk.max_daily_trades = 5
    risk.max_consecutive_losses = 2
    
    logger.info(f"Initial balance: ${risk.current_balance}")
    
    # Simulate trades
    trades = [
        {"profit": 20, "win": True},
        {"profit": -10, "win": False},
        {"profit": -15, "win": False},
        {"profit": 25, "win": True},
        {"profit": 30, "win": True},
        {"profit": -20, "win": False},
    ]
    
    for i, trade in enumerate(trades, 1):
        # Check if trading is possible
        can_trade, reason = risk.can_trade()
        if not can_trade:
            logger.warning(f"Trade {i} blocked: {reason}")
            continue
        
        # Calculate position size
        position = risk.calculate_position_size(confidence=0.8)
        logger.info(f"Trade {i}: Position size = ${position:.2f}")
        
        # Update result
        risk.update_trade_result(trade["profit"])
        logger.info(f"   Result: {'✅' if trade['win'] else '❌'} Profit: {trade['profit']}")
    
    # Show statistics
    metrics = risk.get_metrics()
    logger.info("\n📊 Final Metrics:")
    for key, value in metrics.items():
        logger.info(f"   {key}: {value}")


async def candle_builder_example():
    """
    Example of building candles
    """
    logger.info("=" * 50)
    logger.info("🕯️ Candle Builder Example")
    logger.info("=" * 50)
    
    # Create builder
    builder = CandleBuilder(Asset.EURUSD, timeframe_seconds=60, max_candles=10)
    
    # Simulate ticks
    ticks = [
        (1000, 1.1050),
        (1010, 1.1060),
        (1020, 1.1040),
        (1030, 1.1070),
        (1040, 1.1080),
        (1050, 1.1075),
        (2000, 1.1090),  # new candle
        (2010, 1.1085),
        (2020, 1.1100),
    ]
    
    for timestamp, price in ticks:
        completed = builder.add_tick(timestamp, price)
        if completed:
            logger.info(f"✅ Candle completed at {timestamp}")
    
    # Show candles
    candles = builder.get_all_candles()
    for i, candle in enumerate(candles):
        logger.info(f"Candle {i+1}: O={candle.open:.4f} H={candle.high:.4f} "
                   f"L={candle.low:.4f} C={candle.close:.4f}")


async def main():
    """
    Main function - run all examples
    """
    logger.info("🚀 Pocket Option SDK - Full Example")
    logger.info("=" * 60)
    
    # Choose the appropriate example
    
    # 1️⃣ Simple example
    # await simple_example()
    
    # 2️⃣ Indicators example
    await indicators_example()
    
    # 3️⃣ Risk management example
    await risk_management_example()
    
    # 4️⃣ Candle builder example
    await candle_builder_example()
    
    # 5️⃣ Complete bot example (requires real session_id)
    # session_id = "your_session_id_here"
    # bot = TradingBot(session_id=session_id, region="demo", demo_mode=True)
    # await bot.run()
    
    logger.info("=" * 60)
    logger.info("✅ All examples completed")


if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import logging
from datetime import datetime

from pocket_option import (
    PocketOptionClient,
    Indicators,
    RiskManager,
    StreamProcessor,
    ChaforProcessor,
    MemoryCandleStorage,
    MemoryDealsStorage,
    Asset,
    DealAction,
    AuthorizationData,
)
from pocket_option.middlewares import StreamMiddleware, ChaforMiddleware

logging.basicConfig(level=logging.INFO)


class TradingBot:
    """
    Advanced trading bot using all library features
    """
    
    def __init__(self, session: str, uid: int):
        self.session = session
        self.uid = uid
        self.client = None
        self.indicators = Indicators()
        self.risk = RiskManager(initial_balance=1000)
        
        # Processors
        self.stream_processor = StreamProcessor()
        self.chafor_processor = ChaforProcessor()
        
        # Storage
        self.candle_storage = None
        self.deals_storage = None
        
        # Settings
        self.enabled = True
        self.preferred_assets = [
            Asset.EURUSD_otc,
            Asset.GBPUSD_otc,
            Asset.XAUUSD_otc,
            Asset.BTCUSD
        ]
    
    async def setup(self):
        """Setup client and handlers"""
        
        # Create client with middlewares
        self.client = PocketOptionClient(
            middlewares=[
                StreamMiddleware(),    # Handle 39-byte binary
                ChaforMiddleware(),     # Handle 19-byte binary
            ]
        )
        
        # Setup storage
        self.candle_storage = MemoryCandleStorage(self.client)
        self.deals_storage = MemoryDealsStorage(self.client)
        
        # Register handlers
        self.client.on.connect(self.on_connect)
        self.client.on.disconnect(self.on_disconnect)
        self.client.on.success_auth(self.on_auth)
        self.client.on.update_close_value(self.on_price_update)
        self.client.on.change_market_sentiment(self.on_market_sentiment)
        
        # Register stream processor
        self.stream_processor.add_callback(self.on_stream_update)
        self.chafor_processor.add_signal_callback(self.on_trading_signal)
        self.chafor_processor.add_candle_callback(self.on_candle_close)
    
    async def on_connect(self):
        """Handle connection"""
        logging.info("✅ Connected to platform")
        
        # Authenticate
        auth = AuthorizationData(
            session=self.session,
            is_demo=1,
            uid=self.uid,
            platform=2,
            is_fast_history=True,
            is_optimized=True
        )
        await self.client.emit.auth(auth)
    
    async def on_auth(self, data):
        """Handle successful auth"""
        logging.info(f"✅ Authenticated: {data}")
        
        # Load initial data
        await self.client.emit.indicator_load()
        await self.client.emit.favorite_load()
        await self.client.emit.price_alert_load()
        
        # Subscribe to assets
        for asset in self.preferred_assets:
            await self.client.emit.subscribe_to_asset(asset)
            logging.info(f"📡 Subscribed to {asset}")
    
    async def on_disconnect(self):
        """Handle disconnect"""
        logging.warning("⚠️ Disconnected from platform")
    
    async def on_price_update(self, items):
        """Handle price updates (from generated client)"""
        for item in items:
            # Store in candle storage
            await self.candle_storage.add_item(item)
    
    async def on_stream_update(self, asset: Asset, update):
        """Handle 39-byte stream updates"""
        # Get price history
        prices = self.stream_processor.get_price_history(asset, 20)
        
        if len(prices) >= 14:
            # Calculate indicators
            rsi = self.indicators.rsi(prices)
            sma20 = self.indicators.sma(prices, 20)
            
            current = update.price
            
            # Simple strategy
            if rsi < 30 and current > sma20:
                logging.info(f"📈 BUY signal: {asset} @ {current}")
                await self.execute_trade(asset, DealAction.CALL, 10)
            
            elif rsi > 70 and current < sma20:
                logging.info(f"📉 SELL signal: {asset} @ {current}")
                await self.execute_trade(asset, DealAction.PUT, 10)
    
    async def on_market_sentiment(self, items):
        """Handle market sentiment updates (chafor)"""
        for item in items:
            logging.debug(f"📊 Sentiment: {item}")
    
    async def on_trading_signal(self, message):
        """Handle trading signals from chafor"""
        if message.asset in self.preferred_assets:
            current = self.stream_processor.get_last_price(message.asset)
            if current:
                direction = DealAction.CALL if message.price > current else DealAction.PUT
                logging.info(f"🔮 Signal: {direction.upper()} {message.asset} @ {message.price}")
                
                # Execute with higher confidence
                await self.execute_trade(message.asset, direction, 20)
    
    async def on_candle_close(self, asset: Asset, candle):
        """Handle candle closes"""
        logging.info(f"🕯️ Candle closed: {asset} - O:{candle.open} C:{candle.close}")
    
    async def execute_trade(self, asset: Asset, action: DealAction, amount: float):
        """Execute a trade with risk management"""
        
        # Check risk
        can_trade, reason = self.risk.can_trade()
        if not can_trade:
            logging.warning(f"⛔ Risk check failed: {reason}")
            return
        
        try:
            # Open deal
            deal = await self.deals_storage.open_deal(
                asset=asset,
                amount=amount,
                action=action,
                time=60,  # 1 minute
                is_demo=1
            )
            
            logging.info(f"🚀 Deal opened: {deal.id}")
            
            # Wait for result
            result = await self.deals_storage.check_deal_result(deal=deal, wait_time=70)
            
            # Update risk
            self.risk.update_trade_result(result.profit)
            
            logging.info(f"💰 Deal result: {result.status} P/L: {result.profit}")
            
        except Exception as e:
            logging.error(f"❌ Trade failed: {e}")
    
    async def run(self):
        """Run the bot"""
        await self.setup()
        
        # Connect to demo server
        await self.client.connect(
            url="wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket",
            headers={
                "Origin": "https://pocketoption.com",
                "User-Agent": "Mozilla/5.0"
            }
        )
        
        # Keep running
        try:
            while self.enabled:
                await asyncio.sleep(1)
                
                # Show stats every minute
                if datetime.now().second == 0:
                    stats = self.risk.get_metrics()
                    logging.info(f"📊 Balance: ${stats['balance']} | "
                               f"Win rate: {stats['win_rate']}% | "
                               f"Today: ${stats['daily_pnl']:+.2f}")
        
        except KeyboardInterrupt:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the bot"""
        self.enabled = False
        if self.client:
            await self.client.disconnect()
        logging.info("👋 Bot stopped")


async def main():
    """Main function"""
    # Your credentials
    bot = TradingBot(
        session="your_session_id_here",
        uid=0
    )
    
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())