"""Tests for structured logging system."""

import json
import tempfile
from pathlib import Path

import pytest

# Import the logger we'll create
from scripts.logger import PipelineLogger, PipelineMetrics, get_logger, reset_logger


class TestPipelineMetrics:
    """Test PipelineMetrics tracking and reporting."""

    def test_pipeline_metrics_tracking(self):
        """Test that pipeline metrics can be tracked."""
        metrics = PipelineMetrics()
        metrics.add_scraped(50)
        metrics.add_classified(45)
        metrics.add_skipped_duplicates(5)
        metrics.add_uploaded(40)
        metrics.add_error("test error")

        assert metrics.scraped == 50
        assert metrics.classified == 45
        assert metrics.skipped_duplicates == 5
        assert metrics.uploaded == 40
        assert len(metrics.errors) == 1
        assert "test error" in metrics.errors

    def test_metrics_summary(self):
        """Test that metrics can be summarized."""
        metrics = PipelineMetrics()
        metrics.add_scraped(100)
        metrics.add_classified(95)
        metrics.add_uploaded(90)

        summary = metrics.get_summary()
        assert "100 events scraped" in summary
        assert "95 events classified" in summary
        assert "90 events uploaded" in summary

    def test_metrics_summary_with_errors(self):
        """Test that errors are included in summary."""
        metrics = PipelineMetrics()
        metrics.add_scraped(100)
        metrics.add_error("Network timeout on Perdido Chamber")
        metrics.add_error("Missing image config")

        summary = metrics.get_summary()
        assert "Errors: 2" in summary
        assert "Network timeout" in summary
        assert "Missing image config" in summary


class TestPipelineLogger:
    """Test PipelineLogger class and structured logging."""

    def test_logger_creation(self):
        """Test that logger can be created and configured."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            assert logger is not None
            assert Path(tmpdir).exists()
            assert logger.logger is not None
            logger.__exit__(None, None, None)
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_file_created(self):
        """Test that log file is created in correct location."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            # Should create a file like pipeline_2026-01-14.log
            log_files = list(Path(tmpdir).glob("pipeline_*.log"))
            assert len(log_files) > 0
            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_info_logging(self):
        """Test that info level logs are written."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.info("Test info message")
            logger.file_handler.flush()  # Ensure write

            # Read the log file
            log_file = list(Path(tmpdir).glob("pipeline_*.log"))[0]
            content = log_file.read_text()
            assert "Test info message" in content
            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_warning_logging(self):
        """Test that warning level logs are written."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.warning("Test warning message")
            logger.file_handler.flush()

            log_file = list(Path(tmpdir).glob("pipeline_*.log"))[0]
            content = log_file.read_text()
            assert "Test warning message" in content
            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_error_logging(self):
        """Test that error level logs are written."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.error("Test error message")
            logger.file_handler.flush()

            log_file = list(Path(tmpdir).glob("pipeline_*.log"))[0]
            content = log_file.read_text()
            assert "Test error message" in content
            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_json_log_format(self):
        """Test that file logs are in JSON format."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.info("Test message with JSON")
            logger.file_handler.flush()

            log_file = list(Path(tmpdir).glob("pipeline_*.log"))[0]
            lines = log_file.read_text().strip().split("\n")

            # At least one line should be valid JSON
            json_lines = [l for l in lines if l.strip()]
            assert len(json_lines) > 0

            # Try to parse as JSON
            try:
                parsed = json.loads(json_lines[0])
                assert "message" in parsed
                assert "level" in parsed
                assert "timestamp" in parsed
            except json.JSONDecodeError:
                pytest.fail("Log line is not valid JSON")

            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_console_output_human_readable(self, capsys):
        """Test that console output is human-readable (not JSON)."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.info("Human readable test")

            captured = capsys.readouterr()
            # Console should not have raw JSON (should have timestamp format)
            assert "Human readable test" in captured.out
            # Should have timestamp like [2026-01-14 HH:MM:SS]
            assert "[" in captured.out and "]" in captured.out

            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_logger_context_manager(self):
        """Test that logger can be used as context manager."""
        tmpdir = tempfile.mkdtemp()
        try:
            with PipelineLogger(log_dir=tmpdir) as logger:
                logger.info("Test within context")
                assert logger is not None

            # After context, logger should be cleaned up
            log_file = list(Path(tmpdir).glob("pipeline_*.log"))[0]
            assert "Test within context" in log_file.read_text()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_logger_methods_exist(self):
        """Test that logger has all required methods."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = PipelineLogger(log_dir=tmpdir)

            # Check methods exist and are callable
            assert hasattr(logger, "info")
            assert callable(logger.info)
            assert hasattr(logger, "warning")
            assert callable(logger.warning)
            assert hasattr(logger, "error")
            assert callable(logger.error)
            assert hasattr(logger, "critical")
            assert callable(logger.critical)
            assert hasattr(logger, "debug")
            assert callable(logger.debug)

            logger.__exit__(None, None, None)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_logger_singleton(self):
        """Test that get_logger returns consistent instance."""
        tmpdir = tempfile.mkdtemp()
        try:
            reset_logger()  # Start fresh
            logger1 = get_logger(log_dir=tmpdir)
            # Create another with same dir - should be same instance
            logger2 = get_logger(log_dir=tmpdir)
            assert logger1 is logger2

            logger1.__exit__(None, None, None)
            reset_logger()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
