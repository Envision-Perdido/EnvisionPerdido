"""
Compatibility shim for tests that expect Envision_Perdido_DataCollection.py to live under the
top-level `tests/` directory. This file simply executes the real script located in
`scripts/Envision_Perdido_DataCollection.py` so tests can import it by path.

This is intentionally minimal and avoids modifying the original script.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_SCRIPT = ROOT / "scripts" / "Envision_Perdido_DataCollection.py"
if not REAL_SCRIPT.exists():
    raise FileNotFoundError(f"Expected script at {REAL_SCRIPT}")

# Execute the real script source inside this shim module's globals so
# that functions' global lookups resolve to this module's attributes.
# We set __name__ to the current module name so the script's
# if __name__ == '__main__' block does not execute.
source = REAL_SCRIPT.read_text()
# Execute in this module's actual globals so definitions bind here and tests
# can override module-level variables like `sess`.
module_globals = globals()
module_globals["__name__"] = __name__
exec(compile(source, str(REAL_SCRIPT), "exec"), module_globals)
