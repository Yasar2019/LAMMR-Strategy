"""Streamlit Dashboard for LAMMR Strategy."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.data_agent import DataAgent
from src.agents.signal_agent import SignalAgent
from src.agents.portfolio_agent import PortfolioAgent
from src.agents.orders_agent import OrdersAgent
from src.agents.backtest_agent import BacktestAgent
from src.agents.monitor_agent import MonitorAgent
from src.utils.config import load_config
from src.db import get_connection

# Page config
st.set_page_config(page_title="LAMMR Strategy", layout="wide")

# Load config
config = load_config("config.yaml")
db_path = config['db_path']

# Sidebar
st.sidebar.title("LAMMR Strategy Dashboard")
page = st.sidebar.radio("Select Page", [
    "Overview",
    "Signals",
    "Backtest Results",
    "Portfolio",
    "Monitoring",
    "Settings",
    "Run Agents"
])

# Connection
conn = get_connection(db_path)
cursor = conn.cursor()


def page_overview():
    """Overview page."""
    st.title("📊 LAMMR Strategy Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Count of symbols
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv")
    symbol_count = cursor.fetchone()[0]
    col1.metric("Symbols Loaded", symbol_count)
    
    # Count of signals
    cursor.execute("SELECT COUNT(*) FROM signals")
    signal_count = cursor.fetchone()[0]
    col2.metric("Total Signals", signal_count)
    
    # Open positions
    cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'open'")
    open_pos = cursor.fetchone()[0]
    col3.metric("Open Positions", open_pos)
    
    # Closed trades
    cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'closed'")
    closed_trades = cursor.fetchone()[0]
    col4.metric("Closed Trades", closed_trades)
    
    st.markdown("---")
    
    # Data summary
    st.subheader("Loaded Data Summary")
    cursor.execute("""
        SELECT symbol, first_date, last_date, record_count 
        FROM data_metadata 
        WHERE data_type = 'ohlcv'
        ORDER BY symbol
    """)
    
    rows = cursor.fetchall()
    if rows:
        data_df = pd.DataFrame(rows, columns=['Symbol', 'First Date', 'Last Date', 'Records'])
        st.dataframe(data_df, use_container_width=True)
    
    st.subheader("Strategy Configuration")
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Z-Score Lookback:** {config['zscore_lookback']} bars")
    col1.write(f"**Buy Threshold:** Z < {config['zscore_buy_threshold']}")
    col1.write(f"**Sell Threshold:** Z > {config['zscore_sell_threshold']}")
    
    col2.write(f"**Min Confidence:** {config['min_confidence']:.2f}")
    col2.write(f"**Position Size:** {config['position_size_pct']:.1%}")
    col2.write(f"**Max Positions:** {config['max_positions']}")
    
    col3.write(f"**Slippage:** {config['slippage_bps']} bps")
    col3.write(f"**Commission:** {config['commission_bps']} bps")
    col3.write(f"**Max Drawdown Cap:** {config['max_drawdown_pct']:.1f}%")


def page_signals():
    """Signals page."""
    st.title("📈 Recent Signals")
    
    signal_agent = SignalAgent(db_path=db_path)
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Filter by Symbol", ["All"] + signal_agent.get_signals(limit=1000)['symbol'].unique().tolist() if 'symbol' in signal_agent.get_signals(limit=1000).columns else ["All"])
    
    with col2:
        limit = st.slider("Number of Signals", 5, 100, 20)
    
    # Get signals
    signals_df = signal_agent.get_recent_signals(symbol if symbol != "All" else None, limit)
    
    if len(signals_df) > 0:
        # Format display
        signals_df['date'] = pd.to_datetime(signals_df['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
        signals_df['z_score'] = signals_df['z_score'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        signals_df['liquidity'] = signals_df['liquidity_score'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        signals_df['confidence'] = signals_df['composite_score'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        st.dataframe(signals_df[['date', 'symbol', 'signal_type', 'z_score', 'liquidity', 'confidence', 'reason']], use_container_width=True)
    else:
        st.info("No signals found")
    
    signal_agent.close()


def page_backtest():
    """Backtest results page."""
    st.title("📊 Backtest Results")
    
    backtest_agent = BacktestAgent(db_path=db_path)
    
    results_df = backtest_agent.get_backtest_summary()
    
    if len(results_df) > 0:
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No backtest results yet. Run backtest from 'Run Agents' page.")
    
    backtest_agent.close()


def page_portfolio():
    """Portfolio page."""
    st.title("💼 Portfolio & Orders")
    
    orders_agent = OrdersAgent(db_path=db_path)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Open Positions")
        cursor.execute("""
            SELECT symbol, entry_price, quantity, position_value 
            FROM positions 
            WHERE status = 'open'
        """)
        
        positions = cursor.fetchall()
        if positions:
            pos_df = pd.DataFrame(positions, columns=['Symbol', 'Entry Price', 'Quantity', 'Value'])
            st.dataframe(pos_df, use_container_width=True)
        else:
            st.info("No open positions")
    
    with col2:
        st.subheader("Today's Orders")
        orders_today = orders_agent.get_today_orders()
        if len(orders_today) > 0:
            st.dataframe(orders_today, use_container_width=True)
        else:
            st.info("No signals today")
    
    orders_agent.close()


def page_monitoring():
    """Monitoring page."""
    st.title("⚠️ Monitoring & Alerts")
    
    monitor_agent = MonitorAgent(db_path=db_path)
    
    dashboard = monitor_agent.get_monitoring_dashboard_data()
    
    col1, col2 = st.columns(2)
    col1.metric("Rolling Sharpe (20d)", f"{dashboard['rolling_sharpe']:.2f}")
    col2.metric("Rolling Drawdown", f"{dashboard['rolling_drawdown_pct']:.2f}%")
    
    if dashboard['alerts']:
        st.subheader("⚠️ Active Alerts")
        for alert in dashboard['alerts']:
            if alert['severity'] == 'CRITICAL':
                st.error(f"**{alert['type']}:** {alert['message']}")
            else:
                st.warning(f"**{alert['type']}:** {alert['message']}")
    else:
        st.success("✓ No active alerts")
    
    monitor_agent.close()


def page_settings():
    """Settings page."""
    st.title("⚙️ Settings")
    
    st.subheader("Strategy Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Z-Score Settings**")
        st.code(f"Lookback: {config['zscore_lookback']}")
        st.code(f"Buy: Z < {config['zscore_buy_threshold']}")
        st.code(f"Sell: Z > {config['zscore_sell_threshold']}")
    
    with col2:
        st.write("**Position Settings**")
        st.code(f"Size: {config['position_size_pct']:.1%}")
        st.code(f"Max Positions: {config['max_positions']}")
        st.code(f"Max Position: {config['max_position_size_pct']:.1f}%")
    
    with col3:
        st.write("**Risk Settings**")
        st.code(f"Max DD: {config['max_drawdown_pct']:.1f}%")
        st.code(f"Slippage: {config['slippage_bps']} bps")
        st.code(f"Commission: {config['commission_bps']} bps")
    
    st.markdown("---")
    st.info("To modify settings, edit `config.yaml` and reload the app.")


def page_run_agents():
    """Run agents page."""
    st.title("🚀 Run Agents")
    
    st.markdown("""
    Manually trigger agent operations from this page.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Load Data", use_container_width=True):
            with st.spinner("Loading data..."):
                data_agent = DataAgent(data_dir=config['data_dir'], db_path=db_path)
                results = data_agent.discover_and_load_csvs()
                data_agent.close()
                
                st.success(f"✓ Loaded {len(results)} symbols")
                for symbol, count in sorted(results.items()):
                    st.write(f"  {symbol}: {count} records")
    
    with col2:
        if st.button("🎯 Generate Signals", use_container_width=True):
            with st.spinner("Generating signals..."):
                signal_agent = SignalAgent(db_path=db_path)
                results = signal_agent.generate_signals_for_all_symbols()
                signal_agent.close()
                
                st.success(f"✓ Generated signals for {len(results)} symbols")
                for symbol, count in sorted(results.items()):
                    st.write(f"  {symbol}: {count} signals")
    
    with col3:
        if st.button("📋 Generate Orders", use_container_width=True):
            with st.spinner("Generating orders..."):
                orders_agent = OrdersAgent(db_path=db_path)
                filepath = orders_agent.generate_orders_from_latest_signals()
                orders_agent.close()
                
                if filepath:
                    st.success(f"✓ Orders saved to {filepath}")
                    # Display orders
                    orders_df = pd.read_csv(filepath)
                    st.dataframe(orders_df, use_container_width=True)
                else:
                    st.warning("No orders generated")
    
    st.markdown("---")
    
    if st.button("🔍 Run Backtest", use_container_width=True):
        with st.spinner("Running backtest..."):
            backtest_agent = BacktestAgent(db_path=db_path)
            results = backtest_agent.backtest_all_symbols()
            
            for symbol, result in results.items():
                backtest_agent.save_backtest_results(result)
                metrics = result['metrics']
                st.write(f"**{symbol}**")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Return", f"{metrics['total_return_pct']:.1f}%")
                col2.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
                col3.metric("Max DD", f"{metrics['max_drawdown_pct']:.1f}%")
                col4.metric("Trades", metrics['total_trades'])
            
            backtest_agent.close()
            st.success("✓ Backtest complete")


# Route to page
if page == "Overview":
    page_overview()
elif page == "Signals":
    page_signals()
elif page == "Backtest Results":
    page_backtest()
elif page == "Portfolio":
    page_portfolio()
elif page == "Monitoring":
    page_monitoring()
elif page == "Settings":
    page_settings()
elif page == "Run Agents":
    page_run_agents()

# Close connection
conn.close()

# Footer
st.markdown("---")
st.markdown("LAMMR Strategy | Local Paper Trading Only | No Broker Integration")
