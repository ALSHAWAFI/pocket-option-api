# bot_rsi.py
import asyncio
from pocket_trader import PocketOptionClient
from pocket_trader.models import Asset
from pocket_trader.indicators import Indicators

async def main():
    client = PocketOptionClient()
    bot_started = False
    
    @client.on.connect
    async def on_connect(data):
        print("✅ Connected!")
        await client.emit.auth({
            "session": "your_session_id_here",
            "isDemo": 1,
            "uid": 0,
            "platform": 2
        })
    
    @client.on.update_balance
    async def on_balance(data):
        nonlocal bot_started
        if not bot_started:
            bot_started = True
            print(f"💰 Balance: ${data.get('balance', 0):.2f}")
            asyncio.create_task(trading_loop(client))
    
    @client.on.success_close_deal
    async def on_close(data):
        profit = data.get('profit', 0) if isinstance(data, dict) else getattr(data, 'profit', 0)
        if profit > 0:
            print(f"🎉 WIN! +${profit:.2f}")
        else:
            print(f"💔 LOSS: ${profit:.2f}")
    
    await client.connect("wss://demo-api-eu.po.market")
    await client.wait()

async def trading_loop(client):
    """حلقة التداول الرئيسية"""
    await asyncio.sleep(3)
    
    while True:
        try:
            # جلب الشموع
            candles = await client.get_candles(Asset.EURUSD_otc, timeframe=60, limit=20)
            
            if len(candles) >= 20:
                prices = [c.close for c in candles]
                
                # حساب RSI
                rsi_result = await Indicators.rsi(prices, period=14)
                rsi = rsi_result.value
                
                print(f"📊 RSI: {rsi:.1f}")
                
                # استراتيجية RSI
                if rsi < 30:  # منطقة تشبع بيعي
                    print("📈 RSI oversold -> Opening CALL")
                    await client.emit.open_deal({
                        "asset": Asset.EURUSD_otc,
                        "amount": 1,
                        "action": "call",
                        "isDemo": 1,
                        "requestId": int(asyncio.get_event_loop().time() * 1000),
                        "optionType": 100,
                        "time": 60
                    })
                    await asyncio.sleep(65)  # انتظر انتهاء الصفقة
                
                elif rsi > 70:  # منطقة تشبع شرائي
                    print("📉 RSI overbought -> Opening PUT")
                    await client.emit.open_deal({
                        "asset": Asset.EURUSD_otc,
                        "amount": 1,
                        "action": "put",
                        "isDemo": 1,
                        "requestId": int(asyncio.get_event_loop().time() * 1000),
                        "optionType": 100,
                        "time": 60
                    })
                    await asyncio.sleep(65)
            
            await asyncio.sleep(5)  # انتظر قبل التحليل التالي
            
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

asyncio.run(main())