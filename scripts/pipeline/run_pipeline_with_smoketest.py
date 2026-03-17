#!/usr/bin/env python3
"""
Windows-compatible wrapper to run the pipeline + smoke-test.

This script:
1. Runs the automated pipeline (scrapes, classifies, exports events)
2. Runs the smoke-test to validate evcal_srow epoch calculations
3. Enforces safe defaults (AUTO_UPLOAD=false by default)

Works on both Windows and macOS (cross-platform).

Usage:
  python scripts/run_pipeline_with_smoketest.py

Environment Variables:
  AUTO_UPLOAD    - Set to "true" to auto-upload (default: "false")
  SITE_TIMEZONE  - WordPress timezone (default: "America/Chicago")
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run pipeline + smoke test with safe defaults"""

    base = Path(__file__).resolve().parent.parent.parent

    # Enforce safe defaults
    if "AUTO_UPLOAD" not in os.environ:
        os.environ["AUTO_UPLOAD"] = "false"
    if "SITE_TIMEZONE" not in os.environ:
        os.environ["SITE_TIMEZONE"] = "America/Chicago"

    print(
        f"[run] AUTO_UPLOAD={os.environ['AUTO_UPLOAD']} SITE_TIMEZONE={os.environ['SITE_TIMEZONE']}"
    )
    print()

    # Step 1: Run pipeline
    print("[run] Running pipeline (safe defaults: AUTO_UPLOAD=false)...")
    print("-" * 70)
    try:
        pipeline_script = base / "scripts" / "automated_pipeline.py"
        result = subprocess.run([sys.executable, str(pipeline_script)], cwd=base, env=os.environ)
        if result.returncode != 0:
            print(f"Pipeline failed with exit code {result.returncode}")
            return result.returncode
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1

    print()
    print("[run] Running evcal_srow smoke-test against latest CSV...")
    print("-" * 70)

    # Step 2: Run smoke test (if it exists)
    smoketest_script = base / "scripts" / "dev" / "check_evcal_srow.py"
    if not smoketest_script.exists():
        print(f"[warn] Smoke test script not found: {smoketest_script}")
        print("[warn] Skipping smoke test (this is optional)")
        print()
        print("[run] Done.")
        return 0

    try:
        result = subprocess.run([sys.executable, str(smoketest_script)], cwd=base, env=os.environ)
        if result.returncode != 0:
            print(f"Smoke test failed with exit code {result.returncode}")
            return result.returncode
    except Exception as e:
        print(f"Error running smoke test: {e}")
        return 1

    print()
    print("[run] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
