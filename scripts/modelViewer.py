#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.modelViewer import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.modelViewer", run_name="__main__")
