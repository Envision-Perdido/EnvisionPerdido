"""Compatibility shim: event_normalizer is now at scripts/data_processing/event_normalizer.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_dp_event_normalizer",
    _pl.Path(__file__).parent / "data_processing" / "event_normalizer.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
