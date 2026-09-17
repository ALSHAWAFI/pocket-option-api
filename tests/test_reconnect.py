# test_reconnect.py
"""اختبار إعادة الاتصال التلقائي"""

import asyncio
from pocket_trader import PocketOptionClient, PocketTraderConfig
from pocket_trader.constants import Regions


async def test_reconnect():
    config = PocketTraderConfig.from_env()
    client = PocketOptionClient()
    
    @client.on.disconnect
    async def on_disconnect(data):
        print("⚠️ Disconnected! Auto-reconnect should start...")
    
    @client.on.reconnect
    async def on_reconnect(data):
        print("✅ Reconnected successfully!")
    
    # Connect
    await client.connect(Regions.get_url(config.region), auth=config.to_auth_data())
    print("✅ Connected")
    
    # Get connection status
    status = client.get_connection_status()
    print(f"Status: {status}")
    
    # Test getting candles
    from pocket_trader.models import Asset
    candles = await client.get_candles_safe(Asset.EURUSD, timeframe=60, count=20)
    print(f"Got {len(candles)} candles for EURUSD")
    
    # Keep running to test reconnection
    print("Monitoring connection... (Ctrl+C to exit)")
    
    try:
        while True:
            await asyncio.sleep(10)
            status = client.get_connection_status()
            print(f"💓 Heartbeat: connected={status['connected']}, reconnects={status['reconnect_attempts']}")
    except KeyboardInterrupt:
        pass
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_reconnect())