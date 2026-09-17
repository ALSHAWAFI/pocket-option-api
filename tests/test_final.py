# test_final.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset

async def main():
    client = PocketOptionClient()
    
    @client.on.update_balance
    async def on_balance(data):
        print(f"💰 Balance: {data}")
    
    @client.on.update_close_value
    async def on_price(items):
        if items:
            item = items[0]
            if isinstance(item, dict):
                print(f"💹 {item.get('asset')}: {item.get('value'):.5f}")
            elif hasattr(item, 'asset'):
                print(f"💹 {item.asset}: {item.value:.5f}")
    
    # استخدام connect_and_auth
    success = await client.connect_and_auth(
        url="wss://demo-api-eu.po.market",
        session="your_session_id_here",
        uid=0,
        is_demo=1
    )
    
    if success:
        print("✅ Connected and authenticated!")
        
        # اشترك في أصل
        await client.emit.subscribe_to_asset(Asset.EURUSD_otc)
        print(f"📡 Subscribed to EURUSD_otc")
        
        # انتظر التيكات
        await asyncio.sleep(30)
    else:
        print("❌ Failed to connect/authenticate")
    
    await client.close()

asyncio.run(main())