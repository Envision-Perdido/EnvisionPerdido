#!/usr/bin/env python3
"""Compatibility wrapper for moved module."""

from scripts.pipeline.run_pipeline_with_smoketest import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.pipeline.run_pipeline_with_smoketest", run_name="__main__")
