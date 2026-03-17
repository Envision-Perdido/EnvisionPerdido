#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.pipeline.health_check import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.pipeline.health_check", run_name="__main__")
