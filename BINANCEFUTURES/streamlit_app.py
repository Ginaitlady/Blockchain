import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ccxt  # Cryptocurrency exchange API library
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Bitcoin Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Basic styling
st.markdown("""
<style>
    .header {
        font-size: 2.5rem;
        color: #FF9900;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .metrics-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: space-between;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background-color: #262730;
        border-radius: 5px;
        padding: 1rem;
        text-align: center;
        width: calc(25% - 10px);
        box-sizing: border-box;
    }
    
    .metric-title {
        font-size: 1rem;
        color: #888888;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #FFFFFF;
    }
    
    .positive {
        color: #00CC96;
    }
    
    .negative {
        color: #EF553B;
    }
    
    .neutral {
        color: #FFD700;
    }
    
    .subheader {
        font-size: 1.5rem;
        color: #FF9900;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Functions to read data from SQLite database
def get_trades_data():
    # Create a new connection for use in the current thread
    conn = sqlite3.connect("bitcoin_trading.db")
    query = """
    SELECT 
        id, timestamp, action, entry_price, exit_price, amount, leverage, 
        status, profit_loss, profit_loss_percentage, exit_timestamp
    FROM trades
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()  # Close connection
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if 'exit_timestamp' in df.columns:
        df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp'])
    return df

def get_ai_analysis_data():
    # Create a new connection for use in the current thread
    conn = sqlite3.connect("bitcoin_trading.db")
    query = """
    SELECT 
        id, timestamp, current_price, direction, 
        recommended_leverage, reasoning, trade_id
    FROM ai_analysis
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()  # Close connection
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# Get Bitcoin price data
@st.cache_data(ttl=3600)  # 1-hour cache
def get_bitcoin_price_data(timeframe='1d', limit=90):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate trading performance metrics
def calculate_trading_metrics(trades_df):
    if trades_df.empty:
        return {
            'total_return': 0,
            'sharpe_ratio': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'total_trades': 0,
            'avg_profit_loss': 0,
            'avg_holding_time': 0
        }
    
    # Filter only closed trades
    closed_trades = trades_df[trades_df['status'] == 'CLOSED']
    if closed_trades.empty:
        return {
            'total_return': 0,
            'sharpe_ratio': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'total_trades': 0,
            'avg_profit_loss': 0,
            'avg_holding_time': 0
        }
    
    # Total Return (Initial investment is estimated)
    total_profit_loss = closed_trades['profit_loss'].sum()
    # Estimate initial investment
    initial_investment = closed_trades.sort_values('timestamp').head(3)['entry_price'].mean() * \
                         closed_trades.sort_values('timestamp').head(3)['amount'].mean()
    if initial_investment < 100:  # If too small, set to a reasonable value
        initial_investment = 10000
    total_return = (total_profit_loss / initial_investment) * 100
    
    # Win Rate
    winning_trades = len(closed_trades[closed_trades['profit_loss'] > 0])
    total_trades = len(closed_trades)
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    # Profit Factor
    total_profit = closed_trades[closed_trades['profit_loss'] > 0]['profit_loss'].sum()
    total_loss = abs(closed_trades[closed_trades['profit_loss'] < 0]['profit_loss'].sum())
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    
    # Maximum Drawdown
    closed_trades_sorted = closed_trades.sort_values('timestamp')
    if 'profit_loss' in closed_trades_sorted.columns:
        closed_trades_sorted['cumulative_pl'] = closed_trades_sorted['profit_loss'].cumsum()
        closed_trades_sorted['peak'] = closed_trades_sorted['cumulative_pl'].cummax()
        closed_trades_sorted['drawdown'] = (closed_trades_sorted['peak'] - closed_trades_sorted['cumulative_pl']) / closed_trades_sorted['peak'].replace(0, np.nan)
        max_drawdown = closed_trades_sorted['drawdown'].max() * 100  # Convert to percentage
    else:
        max_drawdown = 0
    
    # Sharpe Ratio (based on daily returns)
    if 'profit_loss_percentage' in closed_trades.columns and len(closed_trades) > 1:
        returns = closed_trades['profit_loss_percentage'] / 100  # Convert to ratio
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Average Profit/Loss
    avg_profit_loss = closed_trades['profit_loss'].mean()
    
    # Average Holding Time
    if 'exit_timestamp' in closed_trades.columns and 'timestamp' in closed_trades.columns:
        # Check if both timestamp and exit_timestamp are datetime
        valid_timestamps = closed_trades.dropna(subset=['exit_timestamp'])
        if not valid_timestamps.empty:
            holding_times = (valid_timestamps['exit_timestamp'] - valid_timestamps['timestamp']).dt.total_seconds() / 3600  # in hours
            avg_holding_time = holding_times.mean()
        else:
            avg_holding_time = 0
    else:
        avg_holding_time = 0
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'avg_profit_loss': avg_profit_loss,
        'avg_holding_time': avg_holding_time
    }

try:
    # Load data
    trades_df = get_trades_data()
    ai_analysis_df = get_ai_analysis_data()
    btc_price_df = get_bitcoin_price_data()

    # Time filter
    st.sidebar.title("Bitcoin Trading Bot")
    time_filter = st.sidebar.selectbox(
        "Select Period:", 
        ["All", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
    )

    # Apply time filter
    now = datetime.now()
    if time_filter == "Last 24 Hours":
        filter_time = now - timedelta(days=1)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 1
    elif time_filter == "Last 7 Days":
        filter_time = now - timedelta(days=7)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 7
    elif time_filter == "Last 30 Days":
        filter_time = now - timedelta(days=30)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 30
    elif time_filter == "Last 90 Days":
        filter_time = now - timedelta(days=90)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 90
    else:
        filtered_trades = trades_df
        chart_days = 90

    # Calculate trading metrics
    metrics = calculate_trading_metrics(filtered_trades)

    # Current open positions
    open_trades = trades_df[trades_df['status'] == 'OPEN']
    has_open_position = len(open_trades) > 0
    current_position = open_trades.iloc[0] if has_open_position else None

    # Current BTC price
    current_btc_price = ai_analysis_df.iloc[0]['current_price'] if not ai_analysis_df.empty else btc_price_df.iloc[-1]['close']

    # Dashboard Main
    st.markdown("<h1 class='header'>Bitcoin Trading Dashboard</h1>", unsafe_allow_html=True)

    # Display main trading metrics
    st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-title">Total Return</div>
            <div class="metric-value {'positive' if metrics['total_return'] > 0 else 'negative' if metrics['total_return'] < 0 else ''}">
                {metrics['total_return']:.2f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Sharpe Ratio</div>
            <div class="metric-value {'positive' if metrics['sharpe_ratio'] > 1 else 'negative' if metrics['sharpe_ratio'] < 0 else ''}">
                {metrics['sharpe_ratio']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Win Rate</div>
            <div class="metric-value {'positive' if metrics['win_rate'] >= 50 else 'negative' if metrics['win_rate'] < 40 else ''}">
                {metrics['win_rate']:.1f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Profit Factor</div>
            <div class="metric-value {'positive' if metrics['profit_factor'] > 1 else 'negative' if metrics['profit_factor'] < 1 else ''}">
                {metrics['profit_factor']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Max Drawdown</div>
            <div class="metric-value {'negative' if metrics['max_drawdown'] > 0 else ''}">
                {metrics['max_drawdown']:.2f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Total Trades</div>
            <div class="metric-value">
                {metrics['total_trades']}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Avg Profit/Loss</div>
            <div class="metric-value {'positive' if metrics['avg_profit_loss'] > 0 else 'negative' if metrics['avg_profit_loss'] < 0 else ''}">
                {metrics['avg_profit_loss']:.2f} USDT
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Avg Holding Time</div>
            <div class="metric-value">
                {metrics['avg_holding_time']:.1f}h
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Current BTC Price and Position Info
    position_cols = st.columns(2)
    
    with position_cols[0]:
        st.markdown(f"""
        <div class="metric-card" style="width: 100%">
            <div class="metric-title">Current BTC Price</div>
            <div class="metric-value">${current_btc_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with position_cols[1]:
        position_status = "No Position" if not has_open_position else f"{current_position['action'].upper()}"
        position_color = "" if not has_open_position else ("positive" if current_position['action'] == 'long' else "negative")
        st.markdown(f"""
        <div class="metric-card" style="width: 100%">
            <div class="metric-title">Current Position</div>
            <div class="metric-value {position_color}">{position_status}</div>
        </div>
        """, unsafe_allow_html=True)

    # BTC Price Chart & Trade Entries
    st.markdown("<h2 class='subheader'>Bitcoin Price Chart & Trade Entries</h2>", unsafe_allow_html=True)

    # Filter BTC chart period
    filtered_price_df = btc_price_df[btc_price_df['timestamp'] > (now - timedelta(days=chart_days))]

    # Create Bitcoin chart + trade points chart
    fig = go.Figure()

    # BTC price line
    fig.add_trace(go.Scatter(
        x=filtered_price_df['timestamp'],
        y=filtered_price_df['close'],
        mode='lines',
        name='BTC Price',
        line=dict(color='gray', width=2),
        hovertemplate='<b>Price</b>: $%{y:,.2f}<br>'
    ))

    # Long (buy) points
    long_points = filtered_trades[filtered_trades['action'] == 'long']
    if not long_points.empty:
        fig.add_trace(go.Scatter(
            x=long_points['timestamp'],
            y=long_points['entry_price'],
            mode='markers',
            name='Long Entry',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            hovertemplate='<b>Long Entry</b><br>' +
                          'Price: $%{y:,.2f}<br>' +
                          'Date: %{x}<br>' +
                          '<extra></extra>'
        ))

    # Short (sell) points
    short_points = filtered_trades[filtered_trades['action'] == 'short']
    if not short_points.empty:
        fig.add_trace(go.Scatter(
            x=short_points['timestamp'],
            y=short_points['entry_price'],
            mode='markers',
            name='Short Entry',
            marker=dict(color='red', size=10, symbol='triangle-down'),
            hovertemplate='<b>Short Entry</b><br>' +
                          'Price: $%{y:,.2f}<br>' +
                          'Date: %{x}<br>' +
                          '<extra></extra>'
        ))

    # Exit points
    exit_points = filtered_trades[(filtered_trades['status'] == 'CLOSED') & (filtered_trades['exit_price'].notna())]
    if not exit_points.empty:
        fig.add_trace(go.Scatter(
            x=exit_points['exit_timestamp'] if 'exit_timestamp' in exit_points.columns else exit_points['timestamp'],
            y=exit_points['exit_price'],
            mode='markers',
            name='Exit',
            marker=dict(color='yellow', size=8, symbol='circle'),
            hovertemplate='<b>Exit</b><br>' +
                          'Price: $%{y:,.2f}<br>' +
                          'Date: %{x}<br>' +
                          '<extra></extra>'
        ))

    # Set chart layout
    fig.update_layout(
        title='Bitcoin Price & Trading Points',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        hovermode='x unified',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # Trading Performance Charts
    st.markdown("<h2 class='subheader'>Trading Performance</h2>", unsafe_allow_html=True)
    chart_cols = st.columns(2)

    with chart_cols[0]:
        closed_trades = filtered_trades[filtered_trades['status'] == 'CLOSED']
        if not closed_trades.empty:
            # Cumulative profit chart
            trades_sorted = closed_trades.sort_values('timestamp')
            trades_sorted['cumulative_pl'] = trades_sorted['profit_loss'].cumsum()
            
            fig = px.line(
                trades_sorted, 
                x='timestamp', 
                y='cumulative_pl',
                title='Cumulative Profit/Loss',
                labels={'timestamp': 'Date', 'cumulative_pl': 'P/L (USDT)'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No closed trades to display.")

    with chart_cols[1]:
        total_trades = len(closed_trades)
        if total_trades > 0:
            # Trade direction distribution
            decisions = filtered_trades['action'].value_counts().reset_index()
            decisions.columns = ['Direction', 'Count']
            
            fig = px.pie(
                decisions,
                values='Count',
                names='Direction',
                title='Trade Direction Distribution',
                color='Direction',
                color_discrete_map={'long': '#00CC96', 'short': '#EF553B'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades to display.")

    # Trade History
    st.markdown("<h2 class='subheader'>Recent Trades</h2>", unsafe_allow_html=True)
    if not filtered_trades.empty:
        # Prepare data for display
        display_df = filtered_trades[['timestamp', 'action', 'entry_price', 'exit_price', 'status', 'profit_loss']].copy()
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        display_df = display_df.rename(columns={
            'timestamp': 'Date',
            'action': 'Direction',
            'entry_price': 'Entry Price',
            'exit_price': 'Exit Price',
            'status': 'Status',
            'profit_loss': 'P/L'
        })
        
        # Display dataframe
        st.dataframe(
            display_df,
            height=400,
            use_container_width=True
        )
    else:
        st.info("No trades in the selected time period.")

    # Open Position Info
    if has_open_position:
        st.markdown("<h2 class='subheader'>Current Open Position</h2>", unsafe_allow_html=True)
        
        position_cols = st.columns(2)
        with position_cols[0]:
            entry_time = current_position['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            st.markdown(f"""
            ### Position Details
            - **Direction**: {current_position['action'].upper()}
            - **Entry Time**: {entry_time}
            - **Entry Price**: ${current_position['entry_price']:,.2f}
            - **Leverage**: {current_position['leverage']}x
            - **Amount**: {current_position['amount']} BTC
            """)
        
        with position_cols[1]:
            # Current vs. Entry Price Comparison
            if isinstance(current_btc_price, (int, float)):
                price_diff = current_btc_price - current_position['entry_price']
                price_diff_pct = (price_diff / current_position['entry_price']) * 100
                price_color = "green" if (current_position['action'] == 'long' and price_diff > 0) or (current_position['action'] == 'short' and price_diff < 0) else "red"
                
                st.markdown(f"""
                ### Current Performance
                - **Current Price**: ${current_btc_price:,.2f}
                - **Price Change**: ${price_diff:,.2f} ({price_diff_pct:.2f}%)
                - **Estimated P/L**: <span style='color:{price_color};'>${price_diff * current_position['amount'] * current_position['leverage']:,.2f}</span>
                """, unsafe_allow_html=True)

    # AI Analysis Section
    st.markdown("<h2 class='subheader'>Latest AI Analysis</h2>", unsafe_allow_html=True)
    if not ai_analysis_df.empty:
        latest_analysis = ai_analysis_df.iloc[0]
        
        analysis_cols = st.columns(2)
        with analysis_cols[0]:
            direction_color = "green" if latest_analysis['direction'] == 'LONG' else "red" if latest_analysis['direction'] == 'SHORT' else "orange"
            st.markdown(f"""
            ### AI Analysis Summary
            - **Time**: {latest_analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
            - **Direction Recommendation**: <span style='color:{direction_color};'>{latest_analysis['direction']}</span>
            - **Recommended Leverage**: {latest_analysis['recommended_leverage']}x
            """, unsafe_allow_html=True)
        
        with analysis_cols[1]:
            st.markdown("### Analysis Reasoning")
            # Preview of reasoning
            reasoning_preview = latest_analysis['reasoning'][:200] + "..." if len(latest_analysis['reasoning']) > 200 else latest_analysis['reasoning']
            st.write(reasoning_preview)
            
            if st.button("View Full Analysis"):
                st.write(latest_analysis['reasoning'])
    else:
        st.info("No AI analysis data available.")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.stop()