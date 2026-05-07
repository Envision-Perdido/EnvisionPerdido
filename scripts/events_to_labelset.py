#!/usr/bin/env python3
"""Compatibility wrapper for moved module.

DEPRECATED: Import directly from scripts.ml.events_to_labelset.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.events_to_labelset is deprecated. "
    "Use 'scripts.ml.events_to_labelset' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.ml.events_to_labelset import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.events_to_labelset", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.events_to_labelset", run_name="__main__")
