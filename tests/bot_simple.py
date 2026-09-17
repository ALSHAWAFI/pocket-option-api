# bot_simple.py - نسخة تعمل بالتأكيد
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset

async def main():
    client = PocketOptionClient()
    
    # متغير للتأكد من تنفيذ الكود مرة واحدة
    bot_started = False
    
    @client.on.connect
    async def on_connect(data):
        print("✅ Connected! Sending auth...")
        await client.emit.auth({
            "session": "your_session_id_here",
            "isDemo": 1,
            "uid": 0,
            "platform": 2
        })
    
    @client.on.update_balance  # ← استخدم هذا بدلاً من success_auth
    async def on_balance(data):
        nonlocal bot_started
        if not bot_started:
            bot_started = True
            print(f"✅ Authenticated! Balance: {data.get('balance', 0):.2f}")
            print("✅ Bot is ready to trade!")
            
            # كل كود البوت هنا
            print("\n📊 Getting candles...")
            candles = await client.get_candles(Asset.EURUSD_otc, timeframe=60, limit=10)
            print(f"Got {len(candles)} candles")
            
            if candles:
                print(f"Latest price: {candles[-1].close:.5f}")
            
            # فتح صفقة تجريبية
            print("\n📈 Opening test trade...")
            await client.emit.open_deal({
                "asset": Asset.EURUSD_otc,
                "amount": 1,
                "action": "call",
                "isDemo": 1,
                "requestId": int(asyncio.get_event_loop().time() * 1000),
                "optionType": 100,
                "time": 60
            })
            print("✅ Trade sent!")
    
    @client.on.success_open_deal
    async def on_open(data):
        print(f"✅ Trade opened successfully!")
    
    @client.on.success_close_deal
    async def on_close(data):
        if isinstance(data, dict):
            profit = data.get('profit', 0)
        else:
            profit = getattr(data, 'profit', 0)
        
        if profit > 0:
            print(f"🎉 WIN! +${profit:.2f}")
        else:
            print(f"💔 LOSS: ${profit:.2f}")
    
    @client.on.update_close_value
    async def on_price(items):
        if items:
            item = items[0]
            if isinstance(item, dict):
                print(f"💹 {item.get('asset')}: {item.get('value'):.5f}")
    
    await client.connect("wss://demo-api-eu.po.market")
    
    try:
        await asyncio.sleep(120)
    except KeyboardInterrupt:
        print("\n⚠️ Stopping...")
    finally:
        await client.close()

asyncio.run(main())