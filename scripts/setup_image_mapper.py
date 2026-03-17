#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.tooling.setup_image_mapper import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.tooling.setup_image_mapper", run_name="__main__")
