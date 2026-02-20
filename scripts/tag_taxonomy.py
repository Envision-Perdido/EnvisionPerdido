"""Compatibility shim: tag_taxonomy is now at scripts/core/tag_taxonomy.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_core_tag_taxonomy",
    _pl.Path(__file__).parent / "core" / "tag_taxonomy.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
