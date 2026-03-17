#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.tooling.logger import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.tooling.logger", run_name="__main__")
