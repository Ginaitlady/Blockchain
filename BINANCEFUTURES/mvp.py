import ccxt
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
import math
from openai import OpenAI
import time
from datetime import datetime

api_key = os.getenv("COINBASE_API_KEY")
secret = os.getenv("COINBASE_SECRET_KEY")
exchange = ccxt.coinbase({
    'apikey' : api_key,
    'secret' : secret,
    'enableRateLimit' : True,
    'options' : {
        'defaultType' : 'spot',
        'adjustForTimeDifference' : True
    }
})

symbol = "BTC/USD"
client = OpenAI()
exchange.load_markets()

print("\n=== Bitcoin Trading Bot Started ===")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Trading Pair:", symbol)
print("Leverage: 5x")
print("SL/TP: ±0.5%")
print("===================================\n")

while True:
    try:
        # Get current time and price
        current_time = datetime.now().strftime('%H:%M:%S')
        current_price = exchange.fetch_ticker(symbol)['last']
        print(f"\n[{current_time}] Current BTC Price: ${current_price:,.2f}")

        # Check position
        current_side = None
        amount = 0
        positions = exchange.fetch_positions([symbol])
        for position in positions:
            if position['symbol'] == 'BTC/USDT:USDT':
                amt = float(position['info']['positionAmt'])
                if amt > 0:
                    current_side = 'long'
                    amount = amt
                elif amt < 0:
                    current_side = 'short'
                    amount = abs(amt)
        if current_side:
            print(f"Current Position: {current_side.upper()} {amount} BTC")
        else:
            # If no position, cancel remaining open orders
            try:
                open_orders = exchange.fetch_open_orders(symbol)
                if open_orders:
                    for order in open_orders:
                        exchange.cancel_order(order['id'], symbol)
                    print("Cancelled remaining open orders for", symbol)
                else:
                    print("No remaining open orders to cancel.")
            except Exception as e:
                print("Error cancelling orders:", e)
            time.sleep(5)
            print("No position. Analyzing market...")

            # Collect chart data and AI analysis
            ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe="15m", limit=96)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a crypto trading expert. Analyze the market data and respond with only 'long' or 'short'."},
                    {"role": "user", "content": df.to_json()}
                ]
            )
            action = response.choices[0].message.content.lower().strip()
            print(f"AI Decision: {action.upper()}")

            # Calculate order amount (minimum 100 USDT order)
            amount = math.ceil((100 / current_price) * 1000) / 1000
            print(f"Order Amount: {amount} BTC")

            # Set leverage
            exchange.set_leverage(5, symbol)

            # Enter position and place SL/TP orders (0.5% buffer applied)
            if action == "long":
                order = exchange.create_market_buy_order(symbol, amount)
                entry_price = current_price
                sl_price = round(entry_price * 0.995, 2)   # 0.5% decline
                tp_price = round(entry_price * 1.005, 2)   # 0.5% rise
                
                # Create SL/TP orders
                exchange.create_order(symbol, 'STOP_MARKET', 'sell', amount, None, {'stopPrice': sl_price})
                exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', amount, None, {'stopPrice': tp_price})
                
                print(f"\n=== LONG Position Opened ===")
                print(f"Entry: ${entry_price:,.2f}")
                print(f"Stop Loss: ${sl_price:,.2f} (-0.5%)")
                print(f"Take Profit: ${tp_price:,.2f} (+0.5%)")
                print("===========================")

            elif action == "short":
                order = exchange.create_market_sell_order(symbol, amount)
                entry_price = current_price
                sl_price = round(entry_price * 1.005, 2)   # 0.5% rise
                tp_price = round(entry_price * 0.995, 2)   # 0.5% decline
                
                # Create SL/TP orders
                exchange.create_order(symbol, 'STOP_MARKET', 'buy', amount, None, {'stopPrice': sl_price})
                exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'buy', amount, None, {'stopPrice': tp_price})
                
                print(f"\n=== SHORT Position Opened ===")
                print(f"Entry: ${entry_price:,.2f}")
                print(f"Stop Loss: ${sl_price:,.2f} (+0.5%)")
                print(f"Take Profit: ${tp_price:,.2f} (-0.5%)")
                print("============================")
            else:
                print("Action is neither 'long' nor 'short', so no orders executed.")

        time.sleep(1)

    except Exception as e:
        print(f"\n Error: {e}")
        time.sleep(5)