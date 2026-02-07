"""
Centralized logging configuration for the pipeline.
Provides colored output and progress tracking.
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Emoji indicators
    EMOJI = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠️',
        'ERROR': '✗',
        'CRITICAL': '🔥',
    }
    
    def format(self, record):
        # Add color based on level
        level_color = self.COLORS.get(record.levelname, '')
        emoji = self.EMOJI.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Special formatting for stage markers
        if hasattr(record, 'stage'):
            stage = record.stage
            message = record.getMessage()
            return f"{self.BOLD}{'='*60}{self.RESET}\n{emoji} {level_color}[{stage}]{self.RESET} {message}\n{self.BOLD}{'='*60}{self.RESET}"
        
        # Special formatting for progress updates
        if hasattr(record, 'progress'):
            message = record.getMessage()
            return f"  {emoji} {level_color}{message}{self.RESET}"
        
        # Standard formatting
        message = record.getMessage()
        return f"{level_color}[{timestamp}] {emoji} {message}{self.RESET}"


def setup_logging(level=logging.INFO):
    """
    Setup logging configuration for the entire pipeline.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Set formatter
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    # Also write logs to a file for later inspection (no ANSI colors)
    try:
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception:
        # If file logging fails, continue with console only
        pass
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logger


class StageLogger:
    """Helper class for logging stages with timing."""
    
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = logging.getLogger(__name__)
        self.start_time = None
    
    def start(self):
        """Log stage start."""
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting {self.stage_name}...", extra={'stage': f'STAGE: {self.stage_name}'})
    
    def progress(self, message: str):
        """Log progress within stage."""
        self.logger.info(message, extra={'progress': True})
    
    def complete(self, result_summary: str = ""):
        """Log stage completion with timing."""
        import time
        if self.start_time:
            elapsed = time.time() - self.start_time
            summary = f"{self.stage_name} completed in {elapsed:.1f}s"
            if result_summary:
                summary += f" - {result_summary}"
            self.logger.info(summary, extra={'stage': f'COMPLETE: {self.stage_name}'})
        else:
            self.logger.info(f"{self.stage_name} completed", extra={'stage': f'COMPLETE: {self.stage_name}'})
    
    def error(self, error_msg: str):
        """Log stage error."""
        self.logger.error(f"{self.stage_name} failed: {error_msg}", extra={'stage': f'ERROR: {self.stage_name}'})
