#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.svm_train_from_file import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.svm_train_from_file", run_name="__main__")
