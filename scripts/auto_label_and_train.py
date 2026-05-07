#!/usr/bin/env python3
"""Compatibility wrapper for moved module.

DEPRECATED: Import directly from scripts.ml.auto_label_and_train.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.auto_label_and_train is deprecated. "
    "Use 'scripts.ml.auto_label_and_train' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.ml.auto_label_and_train import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.auto_label_and_train", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.auto_label_and_train", run_name="__main__")
