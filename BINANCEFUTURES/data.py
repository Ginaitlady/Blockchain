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

client = OpenAI()
exchange.load_markets()
symbol = "BTC/USDT"

# Collect chart data and AI analysis
ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe="15m", limit=96)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
print(df.to_json())

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a crypto trading expert. Analyze the market data and respond with only 'long' or 'short'."},
        {"role": "user", "content": df.to_json()}
    ]
)
action = response.choices[0].message.content.lower().strip()
print(f"AI Decision: {action.upper()}")