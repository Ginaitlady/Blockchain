import ccxt
import os
import math
import time
import pandas as pd
import requests
import json
import sqlite3
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from datetime import datetime

# Binance Settings
api_key = os.getenv("BINANCE_API_KEY")
secret = os.getenv("BINANCE_SECRET_KEY")
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    }
})
symbol = "BTC/USDT"
client = OpenAI()

# SERP API Settings
serp_api_key = os.getenv("SERP_API_KEY")  # SERP_API_KEY needs to be added to the .env file

# SQLite Database Settings
DB_FILE = "bitcoin_trading.db"

def setup_database():
    """Create the database and necessary tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Trades table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        entry_price REAL NOT NULL,
        amount REAL NOT NULL,
        leverage INTEGER NOT NULL,
        sl_price REAL NOT NULL,
        tp_price REAL NOT NULL,
        sl_percentage REAL NOT NULL,
        tp_percentage REAL NOT NULL,
        position_size_percentage REAL NOT NULL,
        investment_amount REAL NOT NULL,
        status TEXT DEFAULT 'OPEN',
        exit_price REAL,
        exit_timestamp TEXT,
        profit_loss REAL,
        profit_loss_percentage REAL
    )
    ''')
    
    # AI Analysis results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        current_price REAL NOT NULL,
        direction TEXT NOT NULL,
        recommended_position_size REAL NOT NULL,
        recommended_leverage INTEGER NOT NULL,
        stop_loss_percentage REAL NOT NULL,
        take_profit_percentage REAL NOT NULL,
        reasoning TEXT NOT NULL,
        trade_id INTEGER,
        FOREIGN KEY (trade_id) REFERENCES trades (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup complete")

def save_ai_analysis(analysis_data, trade_id=None):
    """Save AI analysis results to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO ai_analysis (
        timestamp, 
        current_price, 
        direction, 
        recommended_position_size, 
        recommended_leverage, 
        stop_loss_percentage, 
        take_profit_percentage, 
        reasoning,
        trade_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        analysis_data.get('current_price', 0),
        analysis_data.get('direction', 'NO_POSITION'),
        analysis_data.get('recommended_position_size', 0),
        analysis_data.get('recommended_leverage', 0),
        analysis_data.get('stop_loss_percentage', 0),
        analysis_data.get('take_profit_percentage', 0),
        analysis_data.get('reasoning', ''),
        trade_id
    ))
    
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id

def save_trade(trade_data):
    """Save trade information to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO trades (
        timestamp,
        action,
        entry_price,
        amount,
        leverage,
        sl_price,
        tp_price,
        sl_percentage,
        tp_percentage,
        position_size_percentage,
        investment_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        trade_data.get('action', ''),
        trade_data.get('entry_price', 0),
        trade_data.get('amount', 0),
        trade_data.get('leverage', 0),
        trade_data.get('sl_price', 0),
        trade_data.get('tp_price', 0),
        trade_data.get('sl_percentage', 0),
        trade_data.get('tp_percentage', 0),
        trade_data.get('position_size_percentage', 0),
        trade_data.get('investment_amount', 0)
    ))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def update_trade_status(trade_id, status, exit_price=None, exit_timestamp=None, profit_loss=None, profit_loss_percentage=None):
    """Update trade status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    update_fields = ["status = ?"]
    update_values = [status]
    
    if exit_price is not None:
        update_fields.append("exit_price = ?")
        update_values.append(exit_price)
    
    if exit_timestamp is not None:
        update_fields.append("exit_timestamp = ?")
        update_values.append(exit_timestamp)
    
    if profit_loss is not None:
        update_fields.append("profit_loss = ?")
        update_values.append(profit_loss)
    
    if profit_loss_percentage is not None:
        update_fields.append("profit_loss_percentage = ?")
        update_values.append(profit_loss_percentage)
    
    update_sql = f"UPDATE trades SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(trade_id)
    
    cursor.execute(update_sql, update_values)
    conn.commit()
    conn.close()

def get_latest_open_trade():
    """Get the latest open trade information"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, action, entry_price, amount, leverage, sl_price, tp_price
    FROM trades
    WHERE status = 'OPEN'
    ORDER BY timestamp DESC
    LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'action': result[1],
            'entry_price': result[2],
            'amount': result[3],
            'leverage': result[4],
            'sl_price': result[5],
            'tp_price': result[6]
        }
    return None

def get_trade_summary(days=7):
    """Get recent trade summary information"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss_percentage) as avg_profit_loss_percentage
    FROM trades
    WHERE exit_timestamp IS NOT NULL
    AND timestamp >= datetime('now', ?)
    ''', (f'-{days} days',))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'total_trades': result[0] or 0,
            'winning_trades': result[1] or 0,
            'losing_trades': result[2] or 0,
            'total_profit_loss': result[3] or 0,
            'avg_profit_loss_percentage': result[4] or 0
        }
    return None

# New function: Get historical trading data and AI analysis results
def get_historical_trading_data(limit=10):
    """Get historical trading data and related AI analysis results"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Set row_factory to access by column name
    cursor = conn.cursor()
    
    # Get completed trades along with related AI analysis
    cursor.execute('''
    SELECT 
        t.id as trade_id,
        t.timestamp as trade_timestamp,
        t.action,
        t.entry_price,
        t.exit_price,
        t.amount,
        t.leverage,
        t.sl_price,
        t.tp_price,
        t.sl_percentage,
        t.tp_percentage,
        t.position_size_percentage,
        t.status,
        t.profit_loss,
        t.profit_loss_percentage,
        a.id as analysis_id,
        a.reasoning,
        a.direction,
        a.recommended_leverage,
        a.recommended_position_size,
        a.stop_loss_percentage,
        a.take_profit_percentage
    FROM 
        trades t
    LEFT JOIN 
        ai_analysis a ON t.id = a.trade_id
    WHERE 
        t.status = 'CLOSED'
    ORDER BY 
        t.timestamp DESC
    LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    
    # Convert to a list of dictionaries
    historical_data = []
    for row in results:
        historical_data.append({k: row[k] for k in row.keys()})
    
    conn.close()
    return historical_data

# Added function to calculate trade performance metrics
def get_performance_metrics():
    """Calculate trade performance metrics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Overall trade performance
    cursor.execute('''
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss_percentage) as avg_profit_loss_percentage,
        MAX(profit_loss_percentage) as max_profit_percentage,
        MIN(profit_loss_percentage) as max_loss_percentage,
        AVG(CASE WHEN profit_loss > 0 THEN profit_loss_percentage ELSE NULL END) as avg_win_percentage,
        AVG(CASE WHEN profit_loss < 0 THEN profit_loss_percentage ELSE NULL END) as avg_loss_percentage
    FROM trades
    WHERE status = 'CLOSED'
    ''')
    
    overall_metrics = cursor.fetchone()
    
    # Performance by direction (long/short)
    cursor.execute('''
    SELECT 
        action,
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss_percentage) as avg_profit_loss_percentage
    FROM trades
    WHERE status = 'CLOSED'
    GROUP BY action
    ''')
    
    directional_metrics = cursor.fetchall()
    
    conn.close()
    
    # Construct results
    metrics = {
        "overall": {
            "total_trades": overall_metrics[0] or 0,
            "winning_trades": overall_metrics[1] or 0,
            "losing_trades": overall_metrics[2] or 0,
            "total_profit_loss": overall_metrics[3] or 0,
            "avg_profit_loss_percentage": overall_metrics[4] or 0,
            "max_profit_percentage": overall_metrics[5] or 0,
            "max_loss_percentage": overall_metrics[6] or 0,
            "avg_win_percentage": overall_metrics[7] or 0,
            "avg_loss_percentage": overall_metrics[8] or 0
        },
        "directional": {}
    }
    
    # Calculate win rate
    if metrics["overall"]["total_trades"] > 0:
        metrics["overall"]["win_rate"] = (metrics["overall"]["winning_trades"] / metrics["overall"]["total_trades"]) * 100
    else:
        metrics["overall"]["win_rate"] = 0
    
    # Add directional metrics
    for row in directional_metrics:
        action = row[0]
        total = row[1] or 0
        winning = row[2] or 0
        
        direction_metrics = {
            "total_trades": total,
            "winning_trades": winning,
            "losing_trades": row[3] or 0,
            "total_profit_loss": row[4] or 0,
            "avg_profit_loss_percentage": row[5] or 0,
            "win_rate": (winning / total * 100) if total > 0 else 0
        }
        
        metrics["directional"][action] = direction_metrics
    
    return metrics

print("\n=== Bitcoin Trading Bot Started ===")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Trading Pair:", symbol)
print("Dynamic Leverage: AI Optimized")
print("Dynamic SL/TP: AI Optimized")
print("Multi Timeframe Analysis: 15m, 1h, 4h")
print("News Sentiment Analysis: Enabled")
print("Historical Performance Learning: Enabled")
print("Database Logging: Enabled")
print("===================================\n")

# Database setup
setup_database()

# Multi-timeframe data collection function
def fetch_multi_timeframe_data():
    # Collect data by timeframe
    timeframes = {
        "15m": {"timeframe": "15m", "limit": 96},  # 24 hours (15m * 96)
        "1h": {"timeframe": "1h", "limit": 48},   # 48 hours (1h * 48)
        "4h": {"timeframe": "4h", "limit": 30}    # 5 days (4h * 30)
    }
    multi_tf_data = {}
    for tf_name, tf_params in timeframes.items():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_params["timeframe"], limit=tf_params["limit"])
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            multi_tf_data[tf_name] = df
            print(f"Collected {tf_name} data: {len(df)} candles")
        except Exception as e:
            print(f"Error fetching {tf_name} data: {e}")
    return multi_tf_data

# Function to fetch latest Bitcoin news
def fetch_bitcoin_news():
    try:
        # Use SERP API to get latest news related to Bitcoin
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_news",
            "q": "bitcoin",
            "gl": "us",
            "hl": "en",
            "api_key": serp_api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            news_results = data.get("news_results", [])
            
            # Extract only the 10 latest news items, including only title and date
            recent_news = []
            for i, news in enumerate(news_results[:10]):
                news_item = {
                    "title": news.get("title", ""),
                    "date": news.get("date", "")
                }
                recent_news.append(news_item)
            
            print(f"Collected {len(recent_news)} recent news articles (title and date only)")
            return recent_news
        else:
            print(f"Error fetching news: Status code {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# Function to handle position closure
def handle_position_closure(current_price, side, amount, current_trade_id=None):
    """Update database upon position closure"""
    if current_trade_id is None:
        latest_trade = get_latest_open_trade()
        if latest_trade:
            current_trade_id = latest_trade['id']
    
    if current_trade_id:
        # Get the latest open trade
        latest_trade = get_latest_open_trade()
        if latest_trade:
            entry_price = latest_trade['entry_price']
            action = latest_trade['action']
            
            # Calculate Profit/Loss
            if action == 'long':
                profit_loss = (current_price - entry_price) * amount
                profit_loss_percentage = (current_price / entry_price - 1) * 100
            else:  # 'short'
                profit_loss = (entry_price - current_price) * amount
                profit_loss_percentage = (1 - current_price / entry_price) * 100
                
            # Update database
            update_trade_status(
                current_trade_id,
                'CLOSED',
                exit_price=current_price,
                exit_timestamp=datetime.now().isoformat(),
                profit_loss=profit_loss,
                profit_loss_percentage=profit_loss_percentage
            )
            
            print(f"\n=== Position Closed ===")
            print(f"Entry: ${entry_price:,.2f}")
            print(f"Exit: ${current_price:,.2f}")
            print(f"P/L: ${profit_loss:,.2f} ({profit_loss_percentage:.2f}%)")
            print("=======================")
            
            # Display recent trade summary
            summary = get_trade_summary(days=7)
            if summary:
                print("\n=== 7-Day Trading Summary ===")
                print(f"Total Trades: {summary['total_trades']}")
                print(f"Win/Loss: {summary['winning_trades']}/{summary['losing_trades']}")
                if summary['total_trades'] > 0:
                    win_rate = (summary['winning_trades'] / summary['total_trades']) * 100
                    print(f"Win Rate: {win_rate:.2f}%")
                print(f"Total P/L: ${summary['total_profit_loss']:,.2f}")
                print(f"Avg P/L %: {summary['avg_profit_loss_percentage']:.2f}%")
                print("=============================")

while True:
    try:
        # Check current time and price
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
        
        # Check for open trades
        current_trade = get_latest_open_trade()
        current_trade_id = current_trade['id'] if current_trade else None
        
        if current_side:
            print(f"Current Position: {current_side.upper()} {amount} BTC")
            
            # Case: Position exists but no record in DB (e.g., program restart)
            if not current_trade:
                # Create temporary trade information
                temp_trade_data = {
                    'action': current_side,
                    'entry_price': current_price,  # Temporarily set to current price
                    'amount': amount,
                    'leverage': 1,  # default value
                    'sl_price': 0,
                    'tp_price': 0,
                    'sl_percentage': 0,
                    'tp_percentage': 0,
                    'position_size_percentage': 0,
                    'investment_amount': 0
                }
                current_trade_id = save_trade(temp_trade_data)
                print("Created new trade record (for existing position)")
        else:
            # Case: No position now, but an open trade exists in DB (position was closed)
            if current_trade:
                handle_position_closure(current_price, current_trade['action'], current_trade['amount'], current_trade_id)
            
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

            # Collect multi-timeframe chart data
            multi_tf_data = fetch_multi_timeframe_data()
            
            # Collect latest Bitcoin news
            recent_news = fetch_bitcoin_news()
            
            # Get historical trading data and AI analysis results
            historical_trading_data = get_historical_trading_data(limit=10)  # latest 10 trades
            
            # Calculate overall performance metrics
            performance_metrics = get_performance_metrics()
            
            # Prepare data for AI analysis
            market_analysis = {
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "timeframes": {},
                "recent_news": recent_news,
                "historical_trading_data": historical_trading_data,  # Add historical trading data
                "performance_metrics": performance_metrics  # Add trade performance metrics
            }
            
            # Convert and save each timeframe's data as a dict
            for tf_name, df in multi_tf_data.items():
                market_analysis["timeframes"][tf_name] = df.to_dict(orient="records")
            
            # Updated system_prompt (includes historical trade analysis)
            system_prompt = """
You are a crypto trading expert specializing in multi-timeframe analysis and news sentiment analysis applying Kelly criterion to determine optimal position sizing, leverage, and risk management.
You adhere strictly to Warren Buffett's investment principles:

**Rule No.1: Never lose money.**
**Rule No.2: Never forget rule No.1.**

Analyze the market data across different timeframes (15m, 1h, 4h), recent news headlines, and historical trading performance to provide your trading decision.

Follow this process:
1. Review historical trading performance:
   - Examine the outcomes of recent trades (profit/loss)
   - Review your previous analysis and trading decisions
   - Identify what worked well and what didn't
   - Learn from past mistakes and successful patterns
   - Compare the performance of LONG vs SHORT positions
   - Evaluate the effectiveness of your stop-loss and take-profit levels
   - Assess which leverage settings performed best

2. Assess the current market condition across all timeframes:
   - Short-term trend (15m): Recent price action and momentum
   - Medium-term trend (1h): Intermediate market direction
   - Long-term trend (4h): Overall market bias
   - Volatility across timeframes
   - Key support/resistance levels
   - News sentiment: Analyze recent news article titles for bullish or bearish sentiment

3. Based on your analysis, determine:
   - Direction: Whether to go LONG or SHORT
   - Conviction: Probability of success (as a percentage between 51-95%)

4. Calculate Kelly position sizing:
   - Use the Kelly formula: f* = (p - q/b)
   - Where:
     * f* = fraction of capital to risk
     * p = probability of success (your conviction level)
     * q = probability of failure (1 - p)
     * b = win/loss ratio (based on stop loss and take profit distances)
   - Adjust based on historical win rates and profit/loss ratios

5. Determine optimal leverage:
   - Based on market volatility across timeframes
   - Consider higher leverage (up to 20x) in low volatility trending markets
   - Use lower leverage (1-3x) in high volatility or uncertain markets
   - Never exceed what is prudent based on your conviction level
   - Learn from past leverage decisions and their outcomes
   - Be more conservative if recent high-leverage trades resulted in losses

6. Set optimal Stop Loss (SL) and Take Profit (TP) levels:
   - Analyze recent price action, support/resistance levels
   - Consider volatility to prevent premature stop-outs
   - Set SL at a technical level that would invalidate your trade thesis
   - Set TP at a realistic target based on technical analysis
   - Both levels should be expressed as percentages from entry price
   - Adapt based on historical SL/TP performance and premature stop-outs
   - Learn from trades that hit SL vs TP and adjust accordingly

7. Apply risk management:
   - Never recommend betting more than 50% of the Kelly criterion (half-Kelly) to reduce volatility
   - If expected direction has less than 55% conviction, recommend not taking the trade (use "NO_POSITION")
   - Adjust leverage to prevent high risk exposure
   - Be more conservative if recent trades showed losses
   - If overall win rate is below 50%, be more selective with your entries

8. Provide reasoning:
   - Explain the rationale behind your trading direction, leverage, and SL/TP recommendations
   - Highlight key factors from your analysis that influenced your decision
   - Discuss how historical performance informed your current decision
   - If applicable, explain how you're adapting based on recent trade outcomes
   - Mention specific patterns you've observed in successful vs unsuccessful trades

Your response must contain ONLY a valid JSON object with exactly these 6 fields:
{
  "direction": "LONG" or "SHORT" or "NO_POSITION",
  "recommended_position_size": [final recommended position size as decimal between 0.1-1.0],
  "recommended_leverage": [an integer between 1-20],
  "stop_loss_percentage": [percentage distance from entry as decimal, e.g., 0.005 for 0.5%],
  "take_profit_percentage": [percentage distance from entry as decimal, e.g., 0.005 for 0.5%],
  "reasoning": "Your detailed explanation for all recommendations"
}

IMPORTANT: Do not format your response as a code block. Do not include ```json, ```, or any other markdown formatting. Return ONLY the raw JSON object.
"""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(market_analysis)}
                ]
            )

            # Parse AI response
            try:
                response_content = response.choices[0].message.content.strip()
                print(f"Raw AI response: {response_content}")  # Debug print
                
                # Remove code blocks (remove ```json and ``` patterns)
                if response_content.startswith("```"):
                    # Extract content after the first newline and before the last ```
                    content_parts = response_content.split("\n", 1)
                    if len(content_parts) > 1:
                        response_content = content_parts[1]
                    # Remove the last ```
                    if "```" in response_content:
                        response_content = response_content.rsplit("```", 1)[0]
                    response_content = response_content.strip()
                
                trading_decision = json.loads(response_content)
                print(f"AI Trading Decision:")
                print(f"Direction: {trading_decision['direction']}")
                print(f"Recommended Position Size: {trading_decision['recommended_position_size']*100:.1f}%")
                print(f"Recommended Leverage: {trading_decision['recommended_leverage']}x")
                print(f"Stop Loss Level: {trading_decision['stop_loss_percentage']*100:.2f}%")
                print(f"Take Profit Level: {trading_decision['take_profit_percentage']*100:.2f}%")
                print(f"Reasoning: {trading_decision['reasoning']}")
                
                # Save AI analysis results to the database
                analysis_data = {
                    'current_price': current_price,
                    'direction': trading_decision['direction'],
                    'recommended_position_size': trading_decision['recommended_position_size'],
                    'recommended_leverage': trading_decision['recommended_leverage'],
                    'stop_loss_percentage': trading_decision['stop_loss_percentage'],
                    'take_profit_percentage': trading_decision['take_profit_percentage'],
                    'reasoning': trading_decision['reasoning']
                }
                analysis_id = save_ai_analysis(analysis_data)
                
                action = trading_decision['direction'].lower()
                
                # Case: Should not open a position
                if action == "no_position":
                    print("It is best not to open a position in the current market situation.")
                    print(f"Reason: {trading_decision['reasoning']}")
                    time.sleep(60)  # Wait 1 minute when no position
                    continue
                    
                # Calculate investment amount (a percentage of available capital)
                balance = exchange.fetch_balance()
                available_capital = balance['USDT']['free']  # Available USDT balance
                position_size_percentage = trading_decision['recommended_position_size']
                investment_amount = available_capital * position_size_percentage
                
                # Check minimum order amount (min 100 USDT)
                if investment_amount < 100:
                    investment_amount = 100
                    print(f"Adjusted to minimum order amount (100 USDT)")
                
                print(f"Investment Amount: {investment_amount:.2f} USDT")
                
                # Calculate order quantity
                amount = math.ceil((investment_amount / current_price) * 1000) / 1000
                print(f"Order Quantity: {amount} BTC")

                # Set AI-recommended leverage
                recommended_leverage = trading_decision['recommended_leverage']
                exchange.set_leverage(recommended_leverage, symbol)
                print(f"Leverage Set: {recommended_leverage}x")

                # Get AI-recommended SL/TP percentages
                sl_percentage = trading_decision['stop_loss_percentage']
                tp_percentage = trading_decision['take_profit_percentage']

                # Enter position and place SL/TP orders (using AI-recommended percentages)
                if action == "long":
                    order = exchange.create_market_buy_order(symbol, amount)
                    entry_price = current_price
                    sl_price = round(entry_price * (1 - sl_percentage), 2)  # Decrease by AI-recommended percentage
                    tp_price = round(entry_price * (1 + tp_percentage), 2)  # Increase by AI-recommended percentage
                    
                    # Create SL/TP orders
                    exchange.create_order(symbol, 'STOP_MARKET', 'sell', amount, None, {'stopPrice': sl_price})
                    exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', amount, None, {'stopPrice': tp_price})
                    
                    # Save trade data
                    trade_data = {
                        'action': 'long',
                        'entry_price': entry_price,
                        'amount': amount,
                        'leverage': recommended_leverage,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'sl_percentage': sl_percentage,
                        'tp_percentage': tp_percentage,
                        'position_size_percentage': position_size_percentage,
                        'investment_amount': investment_amount
                    }
                    trade_id = save_trade(trade_data)
                    
                    # Link AI analysis result to the trade
                    update_analysis_sql = "UPDATE ai_analysis SET trade_id = ? WHERE id = ?"
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(update_analysis_sql, (trade_id, analysis_id))
                    conn.commit()
                    conn.close()
                    
                    print(f"\n=== LONG Position Opened ===")
                    print(f"Entry: ${entry_price:,.2f}")
                    print(f"Stop Loss: ${sl_price:,.2f} (-{sl_percentage*100:.2f}%)")
                    print(f"Take Profit: ${tp_price:,.2f} (+{tp_percentage*100:.2f}%)")
                    print(f"Leverage: {recommended_leverage}x")
                    print(f"Analysis Reasoning: {trading_decision['reasoning']}")
                    print("===========================")

                elif action == "short":
                    order = exchange.create_market_sell_order(symbol, amount)
                    entry_price = current_price
                    sl_price = round(entry_price * (1 + sl_percentage), 2)  # Increase by AI-recommended percentage
                    tp_price = round(entry_price * (1 - tp_percentage), 2)  # Decrease by AI-recommended percentage
                    
                    # Create SL/TP orders
                    exchange.create_order(symbol, 'STOP_MARKET', 'buy', amount, None, {'stopPrice': sl_price})
                    exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'buy', amount, None, {'stopPrice': tp_price})
                    
                    # Save trade data
                    trade_data = {
                        'action': 'short',
                        'entry_price': entry_price,
                        'amount': amount,
                        'leverage': recommended_leverage,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'sl_percentage': sl_percentage,
                        'tp_percentage': tp_percentage,
                        'position_size_percentage': position_size_percentage,
                        'investment_amount': investment_amount
                    }
                    trade_id = save_trade(trade_data)
                    
                    # Link AI analysis result to the trade
                    update_analysis_sql = "UPDATE ai_analysis SET trade_id = ? WHERE id = ?"
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(update_analysis_sql, (trade_id, analysis_id))
                    conn.commit()
                    conn.close()
                    
                    print(f"\n=== SHORT Position Opened ===")
                    print(f"Entry: ${entry_price:,.2f}")
                    print(f"Stop Loss: ${sl_price:,.2f} (+{sl_percentage*100:.2f}%)")
                    print(f"Take Profit: ${tp_price:,.2f} (-{tp_percentage*100:.2f}%)")
                    print(f"Leverage: {recommended_leverage}x")
                    print(f"Analysis Reasoning: {trading_decision['reasoning']}")
                    print("============================")
                else:
                    print("Action is not 'long' or 'short', so no order is executed.")
                    
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"AI response: {response.choices[0].message.content}")
                time.sleep(30)  # Wait and retry
                continue
            except Exception as e:
                print(f"Other error: {e}")
                time.sleep(10)
                continue

        time.sleep(60)  # Main loop runs every 1 minute

    except Exception as e:
        print(f"\n Error: {e}")
        time.sleep(5)