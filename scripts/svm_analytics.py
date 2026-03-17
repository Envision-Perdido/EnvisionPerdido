#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ != "__main__":
    from scripts.analytics.svm_analytics import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.analytics.svm_analytics", run_name="__main__")
