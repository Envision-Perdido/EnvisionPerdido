"""Compatibility shim: wren_haven_scraper is now at scripts/scrapers/wren_haven_scraper.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_scrapers_wren_haven_scraper",
    _pl.Path(__file__).parent / "scrapers" / "wren_haven_scraper.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
