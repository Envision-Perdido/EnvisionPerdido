#!/usr/bin/env python3
"""
Cross-Platform Environment Loader

Loads environment variables from platform-specific config files:
- Windows: scripts/windows/env.ps1 (PowerShell format)
- macOS/Linux: scripts/macos/env.sh (Bash/Zsh format)

Usage: Import this before other scripts
    from env_loader import load_env
    load_env()
"""

import os
import sys
from pathlib import Path


def _load_powershell_env(env_path):
    """Parse PowerShell env.ps1 format: $env:KEY = "value" """
    env_vars = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    # Parse: $env:KEY = "value"
                    key, val = line.split("=", 1)
                    key = key.replace("$env:", "").strip()
                    val = val.strip().strip('"').strip("'")
                    env_vars[key] = val
    except Exception as e:
        print(f"Error loading PowerShell env file {env_path}: {e}")

    return env_vars


def _load_bash_env(env_path):
    """Parse Bash/Zsh env.sh format: export KEY="value" """
    env_vars = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Handle: export KEY="value" or KEY="value"
                if "export " in line:
                    line = line.replace("export ", "", 1).strip()

                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    env_vars[key] = val
    except Exception as e:
        print(f"Error loading Bash env file {env_path}: {e}")

    return env_vars


def load_env(verbose=False):
    """
    Load environment variables from platform-specific config file.

    Priority order:
    1. Environment variables already set (won't override)
    2. Windows: scripts/windows/env.ps1
    3. macOS/Linux: scripts/macos/env.sh
    4. Fallback: ~/.secrets/envision_env.ps1 or ~/.secrets/envision_env.sh

    Returns: True if successfully loaded, False otherwise
    """

    scripts_dir = Path(__file__).parent
    repo_root = scripts_dir.parent

    # Detect platform
    is_windows = sys.platform == "win32"
    is_macos = sys.platform == "darwin"
    is_linux = sys.platform.startswith("linux")

    env_vars = {}
    loaded_from = None

    # Platform 1: Windows
    if is_windows:
        env_path = scripts_dir / "windows" / "env.ps1"
        if env_path.exists():
            env_vars = _load_powershell_env(env_path)
            loaded_from = str(env_path)
        else:
            # Fallback: Check ~/.secrets/envision_env.ps1
            secrets_path = Path.home() / ".secrets" / "envision_env.ps1"
            if secrets_path.exists():
                env_vars = _load_powershell_env(secrets_path)
                loaded_from = str(secrets_path)

    # Platform 2: macOS / Linux
    elif is_macos or is_linux:
        env_path = scripts_dir / "macos" / "env.sh"
        if env_path.exists():
            env_vars = _load_bash_env(env_path)
            loaded_from = str(env_path)
        else:
            # Fallback: Check ~/.secrets/envision_env.sh
            secrets_path = Path.home() / ".secrets" / "envision_env.sh"
            if secrets_path.exists():
                env_vars = _load_bash_env(secrets_path)
                loaded_from = str(secrets_path)

    # Apply loaded variables to os.environ (don't override existing)
    if env_vars:
        for key, val in env_vars.items():
            if key not in os.environ:
                os.environ[key] = val

        if verbose:
            print(f"Loaded {len(env_vars)} environment variables from {loaded_from}")
        return True
    else:
        if verbose:
            if is_windows:
                print(
                    "Warning: No env file found (checked scripts/windows/env.ps1 and ~/.secrets/)"
                )
            else:
                print("Warning: No env file found (checked scripts/macos/env.sh and ~/.secrets/)")
        return False


def validate_env_config():
    """
    Validate all required environment variables at startup.

    Checks both email and WordPress config, failing fast if any are missing.
    For AUTO_UPLOAD=false, WordPress vars are optional.

    Raises SystemExit(1) if validation fails.
    """
    required_vars = {
        "SMTP_SERVER": "Email SMTP server (e.g., smtp.gmail.com)",
        "SMTP_PORT": "Email SMTP port (e.g., 587)",
        "SENDER_EMAIL": "Email sender address (your email)",
        "EMAIL_PASSWORD": "Email password (Gmail App Password)",
        "RECIPIENT_EMAIL": "Email recipient address (where to send notifications)",
    }

    # Check if AUTO_UPLOAD is enabled (default: true)
    auto_upload = os.getenv("AUTO_UPLOAD", "true").lower() in {"true", "1", "yes"}

    if auto_upload:
        required_vars.update(
            {
                "WP_SITE_URL": "WordPress site URL (e.g., https://your-site.org)",
                "WP_USERNAME": "WordPress username (admin user)",
                "WP_APP_PASSWORD": "WordPress Application Password (not plain password)",
            }
        )

    # Check for missing variables
    missing = []
    for key, description in required_vars.items():
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(f"  • {key}: {description}")

    if missing:
        print("\n" + "=" * 80)
        print("ERROR: Missing required environment variables")
        print("=" * 80)
        print("\nPlease set the following in your environment:\n")
        print("\n".join(missing))
        print("\n" + "=" * 80)

        # Platform-specific guidance
        if sys.platform == "win32":
            print("\nOn Windows, set these in scripts/windows/env.ps1:")
            print("  Example:")
            print('    $env:SMTP_SERVER = "smtp.gmail.com"')
            print('    $env:SENDER_EMAIL = "your_email@gmail.com"')
            print("    # ... etc")
        else:
            print("\nOn macOS/Linux, set these in scripts/macos/env.sh:")
            print("  Example:")
            print('    export SMTP_SERVER="smtp.gmail.com"')
            print('    export SENDER_EMAIL="your_email@gmail.com"')
            print("    # ... etc")

        print("\nOr set them in your shell session:")
        if sys.platform == "win32":
            print('  $env:SENDER_EMAIL = "your_email@gmail.com"')
        else:
            print('  export SENDER_EMAIL="your_email@gmail.com"')

        print("=" * 80 + "\n")
        sys.exit(1)

    # All required variables are set
    print("Environment validation passed")


# Auto-load on import (silent mode)
if __name__ != "__main__":
    load_env(verbose=False)
