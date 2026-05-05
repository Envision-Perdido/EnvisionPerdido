#!/usr/bin/env python3
"""Compatibility wrapper for moved logger module.

DEPRECATED: Import directly from scripts.tooling.logger.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.logger is deprecated. "
    "Use 'scripts.tooling.logger' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.tooling.logger import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.tooling.logger", run_name="__main__")

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.tooling.logger", run_name="__main__")
