"""Compatibility shim: google_sheets_source is now at scripts/scrapers/google_sheets_source.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_scrapers_google_sheets_source",
    _pl.Path(__file__).parent / "scrapers" / "google_sheets_source.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
