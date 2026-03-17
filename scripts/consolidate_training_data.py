#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.consolidate_training_data import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.consolidate_training_data", run_name="__main__")
