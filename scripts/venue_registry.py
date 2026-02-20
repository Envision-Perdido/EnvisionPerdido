"""Compatibility shim: venue_registry is now at scripts/core/venue_registry.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_core_venue_registry",
    _pl.Path(__file__).parent / "core" / "venue_registry.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
