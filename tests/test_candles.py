# test_candles_simple.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset

async def main():
    client = PocketOptionClient()
    
    @client.on.connect
    async def on_connect(data):
        print("✅ Connected!")
        await client.emit.auth({
            "session": "your_session_id_here",
            "isDemo": 1,
            "uid": 0,
            "platform": 2
        })
    
    @client.on.update_balance  # استخدم هذا بدلاً من success_auth
    async def on_balance(data):
        print(f"✅ Authenticated! Balance: {data}")
        
        # جلب الشموع
        print("\n📊 Getting historical candles...")
        candles = await client.get_candles(
            Asset.EURUSD_otc,
            timeframe=60,
            limit=20,
            timeout=10
        )
        
        print(f"Got {len(candles)} candles")
        for i, candle in enumerate(candles[-5:]):
            print(f"  {i+1}. {candle.timestamp.strftime('%H:%M:%S')} - "
                  f"O:{candle.open:.5f} H:{candle.high:.5f} "
                  f"L:{candle.low:.5f} C:{candle.close:.5f}")
        
        await asyncio.sleep(5)
        await client.close()
    
    await client.connect("wss://demo-api-eu.po.market")
    await asyncio.sleep(60)

asyncio.run(main())