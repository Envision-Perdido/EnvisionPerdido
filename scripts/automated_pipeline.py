#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.pipeline.automated_pipeline import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.pipeline.automated_pipeline", run_name="__main__")
