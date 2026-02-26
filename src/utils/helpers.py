"""Logging and utility helpers."""

from datetime import datetime
import logging
from pathlib import Path


def setup_logging(log_file: str = "lammr.log", level=logging.INFO):
    """Setup logging to file and console."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def unix_timestamp_to_date(unix_ts: int) -> str:
    """Convert Unix timestamp to YYYY-MM-DD string."""
    from datetime import datetime
    return datetime.utcfromtimestamp(unix_ts).strftime('%Y-%m-%d')


def unix_timestamp_to_datetime(unix_ts: int) -> str:
    """Convert Unix timestamp to YYYY-MM-DD HH:MM:SS string."""
    from datetime import datetime
    return datetime.utcfromtimestamp(unix_ts).strftime('%Y-%m-%d %H:%M:%S')


def date_to_unix_timestamp(date_str: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp."""
    from datetime import datetime
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return int(dt.timestamp())


if __name__ == "__main__":
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Logging setup test")
