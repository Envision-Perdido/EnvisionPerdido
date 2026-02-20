"""Compatibility shim: logger is now at scripts/core/logger.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_core_logger",
    _pl.Path(__file__).parent / "core" / "logger.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
