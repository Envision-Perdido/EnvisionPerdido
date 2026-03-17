#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.events_to_labelset import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.events_to_labelset", run_name="__main__")
