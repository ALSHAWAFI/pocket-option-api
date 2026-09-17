# test.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset

async def main():
    client = PocketOptionClient()
    
    # اتصال ومصادقة مبسطة
    success = await client.connect_and_auth(
        url="wss://demo-api-eu.po.market",
        session="your_session",
        uid=0,
        is_demo=1
    )
    
    if success:
        print("✅ Connected and authenticated!")
        
        # جلب الشموع
        candles = await client.get_candles(Asset.EURUSD_otc, timeframe=60, limit=20)
        print(f"Got {len(candles)} candles")
        
        await asyncio.sleep(5)
        await client.close()

asyncio.run(main())