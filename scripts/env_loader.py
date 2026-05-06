#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

try:
    # Preferred import when repository root is on sys.path
    from scripts.tooling.env_loader import *  # type: ignore # noqa: F401,F403
except ModuleNotFoundError:
    # Fallback for direct script execution where only ./scripts is on sys.path
    from tooling.env_loader import *  # type: ignore # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    try:
        runpy.run_module("scripts.tooling.env_loader", run_name="__main__")
    except ModuleNotFoundError:
        runpy.run_module("tooling.env_loader", run_name="__main__")
