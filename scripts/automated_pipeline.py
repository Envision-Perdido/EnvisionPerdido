"""Compatibility shim: automated_pipeline is now at scripts/pipelines/automated_pipeline.py."""
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_spec = _ilu.spec_from_file_location(
    "_scripts_pipelines_automated_pipeline",
    _pl.Path(__file__).parent / "pipelines" / "automated_pipeline.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_sys.modules[__name__] = _mod
