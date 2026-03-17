#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.auto_label_and_train import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.auto_label_and_train", run_name="__main__")
