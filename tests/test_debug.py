# test_debug.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset

async def main():
    client = PocketOptionClient()
    
    # استمع لكل الأحداث واطبعها
    @client.on.connect
    async def on_connect(data):
        print("📡 Event: connect")
    
    @client.on.disconnect
    async def on_disconnect(data):
        print("📡 Event: disconnect")
    
    # استمع لكل شيء
    original_on_any = client._on_any_event
    
    async def debug_on_any(event, data):
        print(f"📡 Event received: '{event}'")
        print(f"   Data: {data}")
        await original_on_any(event, data)
    
    client._on_any_event = debug_on_any
    
    # الاتصال
    await client.connect("wss://demo-api-eu.po.market")
    
    # انتظر قليلاً
    await asyncio.sleep(2)
    
    # إرسال auth
    await client.send("auth", {
        "session": "your_session_id_here",
        "isDemo": 1,
        "uid": 0,
        "platform": 2
    })
    
    # انتظر
    await asyncio.sleep(10)
    
    await client.close()

asyncio.run(main())