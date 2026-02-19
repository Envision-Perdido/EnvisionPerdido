"""Structured logging system for EnvisionPerdido pipeline.

Provides:
- JSON format for file logs (machine-readable)
- Human-readable format for console
- Automatic log rotation (10 MB default, configurable)
- Pipeline metrics collection and reporting
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import sys


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON for file logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }
        
        # Add any extra fields from the record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                # Skip standard logging fields
                if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName',
                               'levelname', 'levelno', 'lineno', 'module', 'msecs',
                               'message', 'pathname', 'process', 'processName', 'relativeCreated',
                               'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'):
                    try:
                        json.dumps(value)  # Check if serializable
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Custom formatter for human-readable console output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console (human-readable)."""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)
        message = record.getMessage()
        return f"[{timestamp}] {level} {message}"


class PipelineLogger:
    """Structured logger for the pipeline with file and console handlers."""

    _instance = None  # Singleton pattern
    
    def __init__(self, log_dir: Optional[str] = None, max_bytes: int = 10485760, 
                 backup_count: int = 5, level: int = logging.INFO):
        """Initialize pipeline logger.
        
        Args:
            log_dir: Directory for log files. Defaults to 'output/logs'
            max_bytes: Maximum bytes before log rotation (default 10 MB)
            backup_count: Number of backup logs to keep
            level: Logging level (default INFO)
        """
        self.log_dir = Path(log_dir or 'output/logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.level = level
        self.file_handler = None
        self.console_handler = None
        
        # Create logger
        self.logger = logging.getLogger('EnvisionPerdido')
        self.logger.setLevel(level)
        
        # Remove any existing handlers (for testing/reinitialization)
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        
        # Create file handler with rotation
        log_file = self.log_dir / f"pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        self.file_handler.setLevel(level)
        self.file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(self.file_handler)
        
        # Create console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(level)
        self.console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(self.console_handler)

    def info(self, message: str, **kwargs):
        """Log info level message."""
        if kwargs:
            self.logger.info(message, extra=kwargs)
        else:
            self.logger.info(message)

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        if kwargs:
            self.logger.warning(message, extra=kwargs)
        else:
            self.logger.warning(message)

    def error(self, message: str, **kwargs):
        """Log error level message."""
        if kwargs:
            self.logger.error(message, extra=kwargs)
        else:
            self.logger.error(message)

    def critical(self, message: str, **kwargs):
        """Log critical level message."""
        if kwargs:
            self.logger.critical(message, extra=kwargs)
        else:
            self.logger.critical(message)

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        if kwargs:
            self.logger.debug(message, extra=kwargs)
        else:
            self.logger.debug(message)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Flush and close all handlers
        for handler in self.logger.handlers[:]:
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)
        return False


class PipelineMetrics:
    """Track metrics throughout the pipeline execution."""

    def __init__(self):
        """Initialize metrics."""
        self.scraped = 0
        self.classified = 0
        self.needs_review = 0
        self.skipped_duplicates = 0
        self.uploaded = 0
        self.errors = []
        self.start_time = datetime.now()

    def add_scraped(self, count: int):
        """Add scraped event count."""
        self.scraped += count

    def add_classified(self, count: int):
        """Add classified event count."""
        self.classified += count

    def add_needs_review(self, count: int):
        """Add count of events needing review."""
        self.needs_review += count

    def add_skipped_duplicates(self, count: int):
        """Add skipped duplicate count."""
        self.skipped_duplicates += count

    def add_uploaded(self, count: int):
        """Add uploaded event count."""
        self.uploaded += count

    def add_error(self, error: str):
        """Add error message."""
        self.errors.append(error)

    def get_summary(self) -> str:
        """Get formatted summary of pipeline execution."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        summary = f"""
================== PIPELINE SUMMARY ==================
Execution Time: {duration:.1f} seconds

{self.scraped} events scraped
{self.classified} events classified
{self.needs_review} events needing review
{self.skipped_duplicates} duplicate events skipped
{self.uploaded} events uploaded

Efficiency:
  Classification Rate:       {self.classified}/{self.scraped} ({100*self.classified/self.scraped if self.scraped else 0:.1f}%)
  Upload Rate:               {self.uploaded}/{self.classified} ({100*self.uploaded/self.classified if self.classified else 0:.1f}%)

Errors: {len(self.errors)}
"""
        
        if self.errors:
            summary += "\n--- Errors Encountered ---\n"
            for i, error in enumerate(self.errors, 1):
                summary += f"  {i}. {error}\n"
        
        summary += "====================================================\n"
        return summary


# Global singleton instance
_logger_instance = None


def get_logger(log_dir: Optional[str] = None, level: int = logging.INFO) -> PipelineLogger:
    """Get or create the global logger instance (singleton pattern).
    
    Args:
        log_dir: Directory for log files
        level: Logging level
        
    Returns:
        PipelineLogger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = PipelineLogger(log_dir=log_dir, level=level)
    
    return _logger_instance


def reset_logger():
    """Reset the global logger instance (useful for testing)."""
    global _logger_instance
    if _logger_instance is not None:
        # Close all handlers before resetting
        for handler in _logger_instance.logger.handlers[:]:
            handler.close()
            _logger_instance.logger.removeHandler(handler)
    _logger_instance = None
