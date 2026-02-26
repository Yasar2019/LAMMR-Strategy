"""LAMMR Strategy - Run all agents in sequence."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.data_agent import DataAgent
from src.agents.signal_agent import SignalAgent
from src.agents.portfolio_agent import PortfolioAgent
from src.agents.orders_agent import OrdersAgent
from src.agents.backtest_agent import BacktestAgent
from src.agents.monitor_agent import MonitorAgent
from src.utils.config import load_config
from src.utils.helpers import get_logger, setup_logging

# Setup logging
setup_logging("lammr.log")
logger = get_logger(__name__)

config = load_config("config.yaml")


def run_all_agents():
    """Run all agents in sequence."""
    
    logger.info("=" * 80)
    logger.info("LAMMR STRATEGY - RUNNING ALL AGENTS")
    logger.info("=" * 80)
    
    # 1. Data Agent
    logger.info("\n[1/6] DATA AGENT: Loading OHLCV and VIX data...")
    data_agent = DataAgent(data_dir=config['data_dir'], db_path=config['db_path'])
    data_results = data_agent.discover_and_load_csvs()
    data_agent.close()
    logger.info(f"✓ Loaded {len(data_results)} symbols")
    
    # 2. Signal Agent
    logger.info("\n[2/6] SIGNAL AGENT: Computing Z-score reversal signals...")
    signal_agent = SignalAgent(db_path=config['db_path'])
    signal_results = signal_agent.generate_signals_for_all_symbols()
    signal_agent.close()
    logger.info(f"✓ Generated signals for {len(signal_results)} symbols")
    
    # 3. Portfolio Agent
    logger.info("\n[3/6] PORTFOLIO AGENT: Position sizing and risk management...")
    portfolio_agent = PortfolioAgent(db_path=config['db_path'])
    metrics = portfolio_agent.calculate_portfolio_metrics()
    portfolio_agent.close()
    logger.info(f"✓ Portfolio metrics computed")
    
    # 4. Orders Agent
    logger.info("\n[4/6] ORDERS AGENT: Generating executable orders...")
    orders_agent = OrdersAgent(db_path=config['db_path'])
    orders_file = orders_agent.generate_orders_from_latest_signals()
    orders_agent.close()
    logger.info(f"✓ Orders generated")
    
    # 5. Backtest Agent
    logger.info("\n[5/6] BACKTEST AGENT: Running vectorized backtests...")
    backtest_agent = BacktestAgent(db_path=config['db_path'])
    backtest_results = backtest_agent.backtest_all_symbols()
    for symbol, result in backtest_results.items():
        backtest_agent.save_backtest_results(result)
    backtest_agent.close()
    logger.info(f"✓ Backtested {len(backtest_results)} symbols")
    
    # 6. Monitor Agent
    logger.info("\n[6/6] MONITOR AGENT: Computing monitoring metrics...")
    monitor_agent = MonitorAgent(db_path=config['db_path'])
    dashboard = monitor_agent.get_monitoring_dashboard_data()
    alerts = monitor_agent.check_alerts()
    monitor_agent.close()
    logger.info(f"✓ Monitoring metrics computed ({len(alerts)} alerts)")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ ALL AGENTS COMPLETE")
    logger.info("=" * 80)
    logger.info("\nNext: Launch Streamlit dashboard with:")
    logger.info("  streamlit run app.py")


if __name__ == "__main__":
    run_all_agents()
