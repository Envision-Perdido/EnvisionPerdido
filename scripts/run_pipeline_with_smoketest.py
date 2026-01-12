#!/usr/bin/env python3
"""Python wrapper to run the pipeline + smoke-test wrapper.

This calls the existing shell wrapper via bash which avoids relying on the
executable permission bit for `scripts/run_pipeline_with_smoketest.sh`.

Usage:
  python scripts/run_pipeline_with_smoketest.py
"""
import os
import subprocess
from pathlib import Path
import sys


def main():
    base = Path(__file__).resolve().parent.parent
    sh = base / 'scripts' / 'run_pipeline_with_smoketest.sh'

    # Enforce safe default when not set
    if 'AUTO_UPLOAD' not in os.environ:
        os.environ['AUTO_UPLOAD'] = 'false'
    if 'SITE_TIMEZONE' not in os.environ:
        os.environ['SITE_TIMEZONE'] = 'America/Chicago'

    if not sh.exists():
        print(f"Wrapper not found: {sh}")
        return 2

    print(f"Running: bash {sh}")
    try:
        subprocess.check_call(['bash', str(sh)], env=os.environ)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Wrapper failed: {e}")
        return e.returncode


if __name__ == '__main__':
    sys.exit(main())
