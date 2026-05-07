"""Unit tests for environment loading and validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.tooling import env_loader

REQUIRED_EMAIL_VARS = {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SENDER_EMAIL": "sender@example.com",
    "EMAIL_PASSWORD": "secret",
    "RECIPIENT_EMAIL": "recipient@example.com",
}

REQUIRED_WP_VARS = {
    "WP_SITE_URL": "https://example.com",
    "WP_USERNAME": "admin",
    "WP_APP_PASSWORD": "app-password",
}


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [*REQUIRED_EMAIL_VARS, *REQUIRED_WP_VARS, "AUTO_UPLOAD", "EXISTING_ONLY", "NEW_KEY"]:
        monkeypatch.delenv(key, raising=False)


def test_load_powershell_env_parses_comments_and_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / "env.ps1"
    env_file.write_text(
        """
# Comment line
$env:SMTP_SERVER = "smtp.gmail.com"
$env:SENDER_EMAIL='alerts@example.com'
$env:SMTP_PORT = 587
""".strip()
    )

    assert env_loader._load_powershell_env(env_file) == {
        "SMTP_SERVER": "smtp.gmail.com",
        "SENDER_EMAIL": "alerts@example.com",
        "SMTP_PORT": "587",
    }


def test_load_bash_env_parses_export_and_plain_assignments(tmp_path: Path) -> None:
    env_file = tmp_path / "env.sh"
    env_file.write_text(
        """
# Comment line
export SMTP_SERVER="smtp.gmail.com"
SENDER_EMAIL='alerts@example.com'
SMTP_PORT=587
""".strip()
    )

    assert env_loader._load_bash_env(env_file) == {
        "SMTP_SERVER": "smtp.gmail.com",
        "SENDER_EMAIL": "alerts@example.com",
        "SMTP_PORT": "587",
    }


def test_load_env_reads_repo_bash_file_without_overriding_existing_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_env(monkeypatch)

    fake_repo_root = tmp_path / "repo"
    fake_scripts_dir = fake_repo_root / "scripts"
    fake_tooling_dir = fake_scripts_dir / "tooling"
    fake_tooling_dir.mkdir(parents=True)
    (fake_scripts_dir / "macos").mkdir(parents=True)
    (fake_scripts_dir / "macos" / "env.sh").write_text(
        """
export EXISTING_ONLY="from-file"
export NEW_KEY="loaded-value"
""".strip()
    )

    monkeypatch.setattr(env_loader, "__file__", str(fake_tooling_dir / "env_loader.py"))
    monkeypatch.setattr(env_loader.sys, "platform", "linux")
    monkeypatch.setenv("EXISTING_ONLY", "from-env")

    loaded = env_loader.load_env(verbose=True)

    assert loaded is True
    assert env_loader.os.environ["EXISTING_ONLY"] == "from-env"
    assert env_loader.os.environ["NEW_KEY"] == "loaded-value"
    assert "Loaded 2 environment variables" in capsys.readouterr().out


def test_validate_env_config_allows_missing_wordpress_when_auto_upload_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_env(monkeypatch)
    for key, value in REQUIRED_EMAIL_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUTO_UPLOAD", "false")

    env_loader.validate_env_config()

    assert "Environment validation passed" in capsys.readouterr().out


def test_validate_env_config_requires_wordpress_when_auto_upload_enabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_env(monkeypatch)
    for key, value in REQUIRED_EMAIL_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUTO_UPLOAD", "true")
    monkeypatch.setattr(env_loader.sys, "platform", "linux")

    with pytest.raises(SystemExit) as exc:
        env_loader.validate_env_config()

    output = capsys.readouterr().out
    assert exc.value.code == 1
    assert "Missing required environment variables" in output
    assert "WP_SITE_URL" in output
    assert "scripts/macos/env.sh" in output


def test_validate_env_config_passes_when_all_required_values_exist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_env(monkeypatch)
    for key, value in {**REQUIRED_EMAIL_VARS, **REQUIRED_WP_VARS}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUTO_UPLOAD", "yes")

    env_loader.validate_env_config()

    assert capsys.readouterr().out.strip() == "Environment validation passed"
