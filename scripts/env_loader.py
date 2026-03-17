#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.tooling.env_loader import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.tooling.env_loader", run_name="__main__")
