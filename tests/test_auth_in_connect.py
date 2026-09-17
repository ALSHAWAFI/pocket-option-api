# test_auth_in_connect.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import AuthorizationData

async def main():
    client = PocketOptionClient()
    
    # استمع لكل الأحداث
    async def on_any(event, data):
        print(f"📡 Event: {event}")
        print(f"   Data: {data}")
    
    client._on_any_event = on_any
    
    # المصادقة عبر connect مباشرة
    auth_data = AuthorizationData(
        session="your_session_id_here",
        is_demo=1,
        uid=0,
        platform=2
    )
    
    await client.connect(
        "wss://demo-api-eu.po.market",
        auth=auth_data
    )
    
    await asyncio.sleep(10)
    await client.close()

asyncio.run(main())