"""
Logging utilities for Edge SBC Reliability Lab.

Provides consistent logging configuration across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union


def setup_logger(
    name: str = "edge_sbc_reliability_lab",
    level: int = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    console: bool = True,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional path to log file
        console: Whether to log to console
        format_string: Custom format string
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Default format
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "edge_sbc_reliability_lab") -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_logger(name)
    return logger


class ProgressLogger:
    """
    Simple progress logger for long-running operations.
    
    Provides periodic progress updates without flooding the console.
    """
    
    def __init__(
        self,
        total: int,
        logger: Optional[logging.Logger] = None,
        prefix: str = "Progress",
        update_interval: int = 10,
    ):
        """
        Initialize progress logger.
        
        Args:
            total: Total number of items
            logger: Logger to use (creates default if None)
            prefix: Prefix for progress messages
            update_interval: Percentage interval for updates (e.g., 10 = every 10%)
        """
        self.total = total
        self.logger = logger or get_logger()
        self.prefix = prefix
        self.update_interval = update_interval
        self.current = 0
        self.last_reported_pct = -update_interval
    
    def update(self, n: int = 1, message: str = ""):
        """
        Update progress by n items.
        
        Args:
            n: Number of items completed
            message: Optional additional message
        """
        self.current += n
        pct = (self.current / self.total) * 100 if self.total > 0 else 100
        
        if pct >= self.last_reported_pct + self.update_interval or self.current >= self.total:
            msg = f"{self.prefix}: {self.current}/{self.total} ({pct:.0f}%)"
            if message:
                msg += f" - {message}"
            self.logger.info(msg)
            self.last_reported_pct = int(pct / self.update_interval) * self.update_interval
    
    def finish(self, message: str = "Complete"):
        """Mark progress as complete."""
        self.current = self.total
        self.logger.info(f"{self.prefix}: {message}")
