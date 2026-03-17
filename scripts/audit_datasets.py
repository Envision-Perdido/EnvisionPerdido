#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.ml.audit_datasets import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.ml.audit_datasets", run_name="__main__")
