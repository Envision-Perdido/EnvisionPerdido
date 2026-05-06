#!/usr/bin/env python3
"""Compatibility wrapper for moved module.

DEPRECATED: Import directly from scripts.ml.svm_train_from_file.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.svm_train_from_file is deprecated. "
    "Use 'scripts.ml.svm_train_from_file' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.ml.svm_train_from_file import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.svm_train_from_file", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.svm_train_from_file", run_name="__main__")
