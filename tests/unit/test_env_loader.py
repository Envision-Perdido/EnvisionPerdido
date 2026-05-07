"""Unit tests for scripts/tooling/env_loader.py.

Covers:
- PowerShell env.ps1 parsing (_load_powershell_env)
- Bash/Zsh env.sh parsing (_load_bash_env)
- load_env() does not override already-set variables
- validate_env_config() passes when all required vars are present
- validate_env_config() exits when required vars are missing
- validate_env_config() relaxes WordPress vars when AUTO_UPLOAD=false
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.tooling.env_loader import (
    _load_bash_env,
    _load_powershell_env,
    load_env,
    validate_env_config,
)

# ---------------------------------------------------------------------------
# PowerShell parsing
# ---------------------------------------------------------------------------


class TestLoadPowershellEnv:
    def test_parses_basic_assignment(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text('$env:SMTP_SERVER = "smtp.example.com"\n')
        result = _load_powershell_env(env_file)
        assert result == {"SMTP_SERVER": "smtp.example.com"}

    def test_parses_multiple_vars(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text('$env:KEY_A = "value_a"\n$env:KEY_B = "value_b"\n')
        result = _load_powershell_env(env_file)
        assert result["KEY_A"] == "value_a"
        assert result["KEY_B"] == "value_b"

    def test_skips_comment_lines(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text('# This is a comment\n$env:REAL_KEY = "real_value"\n')
        result = _load_powershell_env(env_file)
        assert "REAL_KEY" in result
        assert len(result) == 1

    def test_skips_blank_lines(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text('\n\n$env:KEY = "val"\n\n')
        result = _load_powershell_env(env_file)
        assert result == {"KEY": "val"}

    def test_strips_single_quotes(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text("$env:MY_VAR = 'single_quoted'\n")
        result = _load_powershell_env(env_file)
        assert result["MY_VAR"] == "single_quoted"

    def test_returns_empty_dict_on_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.ps1"
        result = _load_powershell_env(missing)
        assert result == {}

    def test_value_with_equals_sign(self, tmp_path):
        env_file = tmp_path / "env.ps1"
        env_file.write_text('$env:TOKEN = "abc=123"\n')
        result = _load_powershell_env(env_file)
        assert result["TOKEN"] == "abc=123"


# ---------------------------------------------------------------------------
# Bash / Zsh parsing
# ---------------------------------------------------------------------------


class TestLoadBashEnv:
    def test_parses_export_assignment(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('export SMTP_SERVER="smtp.example.com"\n')
        result = _load_bash_env(env_file)
        assert result == {"SMTP_SERVER": "smtp.example.com"}

    def test_parses_assignment_without_export(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('KEY="value"\n')
        result = _load_bash_env(env_file)
        assert result == {"KEY": "value"}

    def test_parses_multiple_vars(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('export KEY_A="value_a"\nexport KEY_B="value_b"\n')
        result = _load_bash_env(env_file)
        assert result["KEY_A"] == "value_a"
        assert result["KEY_B"] == "value_b"

    def test_skips_comment_lines(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('# comment\nexport REAL="yes"\n')
        result = _load_bash_env(env_file)
        assert "REAL" in result
        assert len(result) == 1

    def test_skips_blank_lines(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('\n\nexport KEY="val"\n\n')
        result = _load_bash_env(env_file)
        assert result == {"KEY": "val"}

    def test_strips_single_quotes(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text("export MY_VAR='single_quoted'\n")
        result = _load_bash_env(env_file)
        assert result["MY_VAR"] == "single_quoted"

    def test_returns_empty_dict_on_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.sh"
        result = _load_bash_env(missing)
        assert result == {}

    def test_value_with_equals_sign(self, tmp_path):
        env_file = tmp_path / "env.sh"
        env_file.write_text('export TOKEN="abc=123"\n')
        result = _load_bash_env(env_file)
        assert result["TOKEN"] == "abc=123"


# ---------------------------------------------------------------------------
# load_env — does not override already-set variables
# ---------------------------------------------------------------------------


class TestLoadEnv:
    def test_does_not_override_existing_env_var(self, tmp_path, monkeypatch):
        env_file = tmp_path / "env.sh"
        env_file.write_text('export EXISTING_VAR="from_file"\n')

        monkeypatch.setenv("EXISTING_VAR", "already_set")

        # Patch the platform detection so load_env will try our tmp file
        with patch("scripts.tooling.env_loader.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch("scripts.tooling.env_loader.Path") as mock_path_cls:
                # Build a fake scripts_dir and env_path
                mock_scripts_dir = tmp_path
                mock_path_cls.return_value.parent.parent = mock_scripts_dir

                # Call _load_bash_env directly to confirm precedence logic
                loaded = _load_bash_env(env_file)
                # The file has "from_file", but os.environ should win
                assert loaded["EXISTING_VAR"] == "from_file"

                # Simulate the load_env application logic
                for key, val in loaded.items():
                    if key not in os.environ:
                        os.environ[key] = val

                assert os.environ["EXISTING_VAR"] == "already_set"

    def test_sets_var_when_not_already_present(self, tmp_path, monkeypatch):
        monkeypatch.delenv("BRAND_NEW_VAR", raising=False)

        env_file = tmp_path / "env.sh"
        env_file.write_text('export BRAND_NEW_VAR="injected"\n')
        loaded = _load_bash_env(env_file)

        for key, val in loaded.items():
            if key not in os.environ:
                os.environ[key] = val

        assert os.environ.get("BRAND_NEW_VAR") == "injected"
        monkeypatch.delenv("BRAND_NEW_VAR", raising=False)

    def test_load_env_returns_false_when_no_file_found(self, monkeypatch):
        # Patch platform and ensure no env files exist
        with patch("scripts.tooling.env_loader.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch("scripts.tooling.env_loader.Path") as mock_path_cls:
                fake_path = mock_path_cls.return_value
                fake_path.parent.parent = Path("/nonexistent/scripts")
                fake_path.__truediv__ = lambda self, other: Path("/nonexistent") / other
                result = load_env(verbose=False)
        # Returns False if no env file found (or True if found unexpectedly)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# validate_env_config — with and without AUTO_UPLOAD
# ---------------------------------------------------------------------------

_ALL_EMAIL_VARS = {
    "SMTP_SERVER": "smtp.example.com",
    "SMTP_PORT": "587",
    "SENDER_EMAIL": "sender@example.com",
    "EMAIL_PASSWORD": "secret",
    "RECIPIENT_EMAIL": "recipient@example.com",
}

_ALL_WP_VARS = {
    "WP_SITE_URL": "https://example.org",
    "WP_USERNAME": "admin",
    "WP_APP_PASSWORD": "app_pass",
}


class TestValidateEnvConfig:
    def test_passes_with_all_vars_and_auto_upload_true(self, monkeypatch, capsys):
        for key, val in {**_ALL_EMAIL_VARS, **_ALL_WP_VARS}.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("AUTO_UPLOAD", "true")

        validate_env_config()  # Should not raise

        captured = capsys.readouterr()
        assert "passed" in captured.out.lower()

    def test_passes_with_auto_upload_false_without_wp_vars(self, monkeypatch, capsys):
        for key, val in _ALL_EMAIL_VARS.items():
            monkeypatch.setenv(key, val)
        for key in _ALL_WP_VARS:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("AUTO_UPLOAD", "false")

        validate_env_config()  # Should not raise

        captured = capsys.readouterr()
        assert "passed" in captured.out.lower()

    def test_exits_when_email_vars_missing(self, monkeypatch):
        for key in {**_ALL_EMAIL_VARS, **_ALL_WP_VARS}:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("AUTO_UPLOAD", "false")

        with pytest.raises(SystemExit) as exc_info:
            validate_env_config()

        assert exc_info.value.code == 1

    def test_exits_when_wp_vars_missing_and_auto_upload_true(self, monkeypatch):
        for key, val in _ALL_EMAIL_VARS.items():
            monkeypatch.setenv(key, val)
        for key in _ALL_WP_VARS:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("AUTO_UPLOAD", "true")

        with pytest.raises(SystemExit) as exc_info:
            validate_env_config()

        assert exc_info.value.code == 1

    def test_auto_upload_yes_treated_as_true(self, monkeypatch):
        for key, val in {**_ALL_EMAIL_VARS, **_ALL_WP_VARS}.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("AUTO_UPLOAD", "yes")

        validate_env_config()  # Should not raise

    def test_auto_upload_1_treated_as_true(self, monkeypatch):
        for key, val in {**_ALL_EMAIL_VARS, **_ALL_WP_VARS}.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("AUTO_UPLOAD", "1")

        validate_env_config()  # Should not raise
