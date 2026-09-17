# test_time_sync.py
import asyncio
from pocket_trader import PocketOptionClient

async def main():
    client = PocketOptionClient()
    
    success = await client.connect_and_auth(
        url="wss://demo-api-eu.po.market",
        session="your_session_id_here",
        uid=0,
        is_demo=1,
        sync_time=False  # تعطيل التزامن التلقائي
    )
    
    if success:
        print("✅ Connected and authenticated!")
        
        # يمكنك الحصول على الوقت الحالي من التيكات بدلاً من ذلك
        @client.on.update_close_value
        async def on_price(items):
            if items:
                item = items[0]
                if isinstance(item, dict):
                    timestamp = item.get('timestamp', 0)
                    print(f"💹 {item.get('asset')}: {item.get('value'):.5f} @ {timestamp}")
                    print(f"   Server time from tick: {timestamp}")
        
        await asyncio.sleep(30)
        await client.close()

asyncio.run(main())