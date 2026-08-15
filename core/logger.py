"""
core/logger.py
──────────────
Shared logging setup for the project.
"""

import logging
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LOGS_DIR

def setup_logging(name: str) -> logging.Logger:
    """
    Set up a logger with a file handler and a stream handler.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s")
    
    log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger
