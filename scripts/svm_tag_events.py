#!/usr/bin/env python3
"""Compatibility wrapper for moved module.

DEPRECATED: Import directly from scripts.ml.svm_tag_events.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.svm_tag_events is deprecated. "
    "Use 'scripts.ml.svm_tag_events' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.ml.svm_tag_events import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.svm_tag_events", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.svm_tag_events", run_name="__main__")
