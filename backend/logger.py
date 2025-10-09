import logging
import os
from typing import Optional
from config import config


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Set up structured logging for the application.

    Args:
        name: Logger name, defaults to __name__ of the calling module

    Returns:
        Configured logger instance
    """
    logger_name = name if name else __name__
    logger = logging.getLogger(logger_name)

    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger

    # Set log level from config
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(config.LOG_FORMAT)

    # Console handler (always present)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log file is configured)
    if config.LOG_FILE:
        try:
            # Ensure log directory exists
            os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)

            file_handler = logging.FileHandler(config.LOG_FILE)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name, if None uses the calling module name

    Returns:
        Logger instance
    """
    return setup_logging(name)