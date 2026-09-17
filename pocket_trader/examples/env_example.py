#!/usr/bin/env python3
"""
Pocket Option SDK - Comprehensive example with .env file
Comprehensive example with .env file support
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Add library path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try importing python-dotenv (optional)
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")

from pocket_trader import (
    PocketOptionClient,
    Asset,
    Deal,
    Candle,
    Indicators,
    RiskManager,
    MemoryDealsStorage,
    MemoryCandleStorage,
    StreamProcessor,
    ChaforProcessor,
    Regions,
    OrderType,
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
        logging.FileHandler('trading_bot.log')
    ]
)
logger = logging.getLogger("PocketBot")


class Config:
    """Manage settings from .env file"""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.session: str = ""
        self.uid: int = 0
        self.is_demo: bool = True
        self.region: str = "demo"
        self.initial_balance: float = 1000
        self.max_risk_per_trade: float = 0.02
        self.max_daily_trades: int = 10
        
        self._load_env_file()
        self._load_from_env()
    
    def _load_env_file(self):
        """Load from .env file if it exists"""
        env_path = Path(self.env_file)
        if env_path.exists():
            if HAS_DOTENV:
                load_dotenv(env_path)
                logger.info(f"✅ Loaded .env file: {env_path}")
            else:
                # Manual read of the file
                self._manual_load(env_path)
        else:
            logger.warning(f"⚠️ .env file not found: {env_path}")
    
    def _manual_load(self, env_path: Path):
        """Manually read .env file"""
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"\'')
            logger.info(f"✅ Manually loaded .env file: {env_path}")
        except Exception as e:
            logger.error(f"❌ Error loading .env file: {e}")
    
    def _load_from_env(self):
        """Load values from environment variables"""
        self.session = os.getenv('PO_SESSION', '')
        self.uid = int(os.getenv('PO_UID', '0'))
        
        demo_str = os.getenv('IS_DEMO', 'true').lower()
        self.is_demo = demo_str in ('true', '1', 'yes')
        
        self.region = os.getenv('PO_REGION', 'demo')
        self.initial_balance = float(os.getenv('INITIAL_BALANCE', '1000'))
        self.max_risk_per_trade = float(os.getenv('MAX_RISK_PER_TRADE', '0.02'))
        self.max_daily_trades = int(os.getenv('MAX_DAILY_TRADES', '10'))
        
        # Validate data
        self._validate()
    
    def _validate(self):
        """Validate the data"""
        if not self.session:
            logger.warning("⚠️ PO_SESSION is empty! Authentication will fail.")
        
        if self.uid <= 0:
            logger.warning(f"⚠️ Invalid PO_UID: {self.uid}")
    
    def display(self):
        """Display settings"""
        logger.info("📋 Configuration:")
        logger.info(f"   Session: {self.session[:10]}...{self.session[-5:] if len(self.session) > 15 else ''}")
        logger.info(f"   UID: {self.uid}")
        logger.info(f"   Demo Mode: {self.is_demo}")
        logger.info(f"   Region: {self.region}")
        logger.info(f"   Initial Balance: ${self.initial_balance}")
        logger.info(f"   Max Risk/Trade: {self.max_risk_per_trade*100}%")
        logger.info(f"   Max Daily Trades: {self.max_daily_trades}")


class PocketTradingBot:
    """
    Integrated trading bot with settings from .env
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        self.stats = {
            'trades_opened': 0,
            'trades_closed': 0,
            'total_profit': 0.0,
            'start_time': datetime.now()
        }
        
        # 1️⃣ Main client
        self.client = PocketOptionClient(
            timeout=30,
            auto_reconnect=True
        )
        
        # 2️⃣ Risk management
        self.risk = RiskManager(initial_balance=config.initial_balance)
        self.risk.max_risk_per_trade = config.max_risk_per_trade
        self.risk.max_daily_trades = config.max_daily_trades
        
        # 3️⃣ Storage
        self.deals_storage = MemoryDealsStorage(self.client)
        self.candle_storage = MemoryCandleStorage(self.client)
        
        # 4️⃣ Processors
        self.stream = StreamProcessor()
        self.chafor = ChaforProcessor()
        self.indicators = Indicators()
        
        # 5️⃣ Trading data
        self.assets = [
            Asset.EURUSD,
            Asset.GBPUSD,
            Asset.XAUUSD,
            Asset.BTCUSD,
        ]
        self.prices: Dict[Asset, float] = {}
        self.price_history: Dict[Asset, list] = {a: [] for a in self.assets}
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info("✅ Trading bot initialized")
    
    def _setup_handlers(self):
        """Setup event handlers"""
        
        @self.client.on.connect
        async def on_connect():
            logger.info("🔌 Connected to server")
        
        @self.client.on.disconnect
        async def on_disconnect():
            logger.warning("🔌 Disconnected from server")
        
        @self.client.on.success_auth
        async def on_auth(data):
            logger.info(f"✅ Authentication successful: {data.id}")
        
        @self.client.on.update_balance
        async def on_balance(data):
            if data.is_demo == self.config.is_demo:
                logger.info(f"💰 Balance: {data.balance}")
                self.risk.current_balance = data.balance
        
        @self.client.on.update_close_value
        async def on_price(items):
            for item in items:
                self.prices[item.asset] = item.value
                if item.asset in self.price_history:
                    self.price_history[item.asset].append(item.value)
                    if len(self.price_history[item.asset]) > 100:
                        self.price_history[item.asset] = self.price_history[item.asset][-100:]
        
        @self.client.on.success_open_deal
        async def on_open(deal):
            logger.info(f"✅ Deal opened: {deal.asset} {deal.command} amount={deal.amount}")
            await self.deals_storage.add_or_update_deal(deal)
            self.risk.add_trade(str(deal.id))
            self.stats['trades_opened'] += 1
        
        @self.client.on.success_close_deal
        async def on_close(event):
            logger.info(f"✅ Deal closed profit: {event.profit}")
            self.stats['trades_closed'] += len(event.deals)
            self.stats['total_profit'] += event.profit
            
            for deal in event.deals:
                await self.deals_storage.add_or_update_deal(deal)
                self.risk.update_trade_result(deal.profit or 0)
                self.risk.remove_trade(str(deal.id))
        
        @self.client.on.change_market_sentiment
        async def on_sentiment(items):
            for item in items:
                logger.debug(f"📊 Sentiment {item.asset}: {item.value}%")
    
    async def connect(self) -> bool:
        """Connect to the server"""
        try:
            url = Regions.get_url(self.config.region)
            logger.info(f"Connecting to {url}...")
            await self.client.connect(url)
            
            # Authentication
            auth_data = {
                "session": self.config.session,
                "isDemo": 1 if self.config.is_demo else 0,
                "uid": self.config.uid,
                "platform": 2,
                "isFastHistory": True,
                "isOptimized": True
            }
            await self.client.emit.auth(auth_data)
            
            # Wait for confirmation
            await asyncio.sleep(2)
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
    
    async def subscribe_all(self):
        """Subscribe to all assets"""
        for asset in self.assets:
            try:
                await self.client.emit.subscribe_to_asset(asset)
                await self.client.emit.subscribe_for_market_sentiment(asset)
                logger.info(f"✅ Subscribed to {asset}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {asset}: {e}")
    
    async def analyze(self, asset: Asset) -> Dict[str, Any]:
        """Analyze a specific asset"""
        if asset not in self.price_history or len(self.price_history[asset]) < 30:
            return {'signal': 'NEUTRAL', 'confidence': 0}
        
        prices = self.price_history[asset]
        
        # Calculate indicators
        rsi = self.indicators.rsi(prices, 14)
        macd = self.indicators.macd(prices)
        bb = self.indicators.bollinger_bands(prices)
        
        # Aggregate signals
        signals = []
        
        if rsi.get('signal') in ['oversold', 'bullish']:
            signals.append(('BUY', 0.7))
        elif rsi.get('signal') in ['overbought', 'bearish']:
            signals.append(('SELL', 0.7))
        
        if macd.get('signal_type') == 'bullish':
            signals.append(('BUY', 0.6))
        elif macd.get('signal_type') == 'bearish':
            signals.append(('SELL', 0.6))
        
        if bb.get('signal') == 'oversold':
            signals.append(('BUY', 0.8))
        elif bb.get('signal') == 'overbought':
            signals.append(('SELL', 0.8))
        
        # Determine final signal
        buy_count = len([s for s in signals if s[0] == 'BUY'])
        sell_count = len([s for s in signals if s[0] == 'SELL'])
        
        if buy_count > sell_count:
            confidence = buy_count / max(len(signals), 1)
            return {'signal': 'BUY', 'confidence': confidence}
        elif sell_count > buy_count:
            confidence = sell_count / max(len(signals), 1)
            return {'signal': 'SELL', 'confidence': confidence}
        
        return {'signal': 'NEUTRAL', 'confidence': 0}
    
    async def trade(self, asset: Asset, signal: str, confidence: float):
        """Execute a trade"""
        # Check risk
        can_trade, reason = self.risk.can_trade()
        if not can_trade:
            logger.warning(f"Cannot trade {asset}: {reason}")
            return
        
        # Calculate position size
        amount = self.risk.calculate_position_size(confidence=confidence)
        if amount < 1:
            logger.debug(f"Position size too small: {amount}")
            return
        
        # Execute
        action = OrderType.CALL if signal == 'BUY' else OrderType.PUT
        try:
            await self.client.emit.open_deal({
                'asset': asset,
                'amount': int(amount),
                'action': action,
                'time': 60,
                'isDemo': 1 if self.config.is_demo else 0,
                'requestId': int(datetime.now().timestamp() * 1000),
                'optionType': 100
            })
            logger.info(f"🚀 Trade signal: {asset} {action} amount={int(amount)}")
            
        except Exception as e:
            logger.error(f"❌ Trade failed: {e}")
    
    async def run(self):
        """Run the bot"""
        self.running = True
        logger.info("🚀 Starting trading bot...")
        
        # Connect
        if not await self.connect():
            logger.error("Failed to connect. Exiting.")
            return
        
        # Subscribe
        await self.subscribe_all()
        
        # Wait for data
        logger.info("Waiting for market data...")
        await asyncio.sleep(5)
        
        # Trading loop
        cycle = 0
        while self.running:
            try:
                cycle += 1
                logger.info(f"🔄 Analysis cycle #{cycle}")
                
                for asset in self.assets:
                    # Analyze
                    result = await self.analyze(asset)
                    
                    if result['signal'] != 'NEUTRAL' and result['confidence'] > 0.5:
                        logger.info(f"🎯 Signal for {asset}: {result['signal']} "
                                   f"(confidence: {result['confidence']:.2f})")
                        
                        await self.trade(asset, result['signal'], result['confidence'])
                    
                    await asyncio.sleep(2)
                
                # Show stats every 10 cycles
                if cycle % 10 == 0:
                    await self.show_stats()
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)
    
    async def show_stats(self):
        """Show statistics"""
        elapsed = datetime.now() - self.stats['start_time']
        minutes = elapsed.total_seconds() / 60
        
        logger.info("📊 " + "=" * 40)
        logger.info(f"📊 Statistics after {minutes:.1f} minutes:")
        logger.info(f"   Trades Opened: {self.stats['trades_opened']}")
        logger.info(f"   Trades Closed: {self.stats['trades_closed']}")
        logger.info(f"   Total Profit: ${self.stats['total_profit']:.2f}")
        
        risk_stats = self.risk.get_metrics()
        logger.info(f"   Current Balance: ${risk_stats.get('balance', 0):.2f}")
        logger.info(f"   Win Rate: {risk_stats.get('win_rate', 0)}%")
        logger.info(f"   Consecutive Losses: {risk_stats.get('consecutive_losses', 0)}")
        logger.info("📊 " + "=" * 40)
    
    async def stop(self):
        """Stop the bot"""
        logger.info("🛑 Stopping bot...")
        self.running = False
        
        # Show final statistics
        await self.show_stats()
        
        # Disconnect
        try:
            await self.client.disconnect()
        except:
            pass
        
        logger.info("👋 Bot stopped")


async def create_env_file():
    """Create a sample .env file"""
    env_content = """# Pocket Option Configuration
# Copy this file, name it .env, then edit the values

# Required - session ID from browser
PO_SESSION=your_session_id_here

# Required - your User ID
PO_UID=0

# Demo mode (true/false)
IS_DEMO=true

# Server region (demo, eu, us, asia)
PO_REGION=demo

# Risk management settings
INITIAL_BALANCE=1000
MAX_RISK_PER_TRADE=0.02
MAX_DAILY_TRADES=10
"""
    
    env_path = Path(".env.example")
    if not env_path.exists():
        env_path.write_text(env_content)
        logger.info(f"✅ Created {env_path}")
        logger.info("📝 Copy to .env and edit with your credentials")
    else:
        logger.info(f"✅ {env_path} already exists")


async def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🚀 Pocket Option SDK - .env Example")
    logger.info("=" * 60)
    
    # Create a sample .env file
    await create_env_file()
    
    # Load settings
    config = Config(".env")
    config.display()
    
    if not config.session:
        logger.error("❌ No session ID found!")
        logger.info("\n📝 To fix:")
        logger.info("1. Copy .env.example to .env")
        logger.info("2. Edit .env with your session ID from browser")
        logger.info("3. Run again")
        return
    
    # Run the bot
    bot = PocketTradingBot(config)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())