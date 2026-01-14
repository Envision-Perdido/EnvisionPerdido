#!/usr/bin/env python3
"""
Environment Loader Utility

This module loads environment variables from scripts/windows/env.ps1
and sets them in os.environ for use by Python scripts.

Usage: Import this before other scripts
    from scripts.env_loader import load_env
    load_env()
"""

import os
from pathlib import Path

def load_env():
    """Load environment variables from env.ps1 file"""
    env_path = Path(__file__).parent / "windows" / "env.ps1"
    
    if not env_path.exists():
        print(f"Warning: env.ps1 not found at {env_path}")
        return False
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    # Parse PowerShell format: $env:KEY = "value"
                    key, val = line.split('=', 1)
                    key = key.replace('$env:', '').strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
        
        return True
    except Exception as e:
        print(f"Error loading env.ps1: {e}")
        return False

# Auto-load on import
if __name__ != "__main__":
    load_env()
