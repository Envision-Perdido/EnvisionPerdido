#!/usr/bin/env python3
"""Compatibility wrapper for moved module.

DEPRECATED: Import directly from scripts.ml.consolidate_training_data.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.consolidate_training_data is deprecated. "
    "Use 'scripts.ml.consolidate_training_data' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.ml.consolidate_training_data import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.consolidate_training_data", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.consolidate_training_data", run_name="__main__")
