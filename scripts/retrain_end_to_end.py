#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ != "__main__":
    from scripts.ml.retrain_end_to_end import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.retrain_end_to_end", run_name="__main__")