"""Compatibility shim: Envision_Perdido_DataCollection is now at scripts/scrapers/."""
import sys as _sys
import os as _os

_scrapers_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "scrapers")
if _scrapers_dir not in _sys.path:
    _sys.path.insert(0, _scrapers_dir)

# Import the real module under its plain name.  Using a plain ``import``
# instead of importlib ensures that both sys.modules keys point to the same
# object, which is required for unittest.mock.patch targets to work when the
# pipeline calls ``Envision_Perdido_DataCollection.scrape_month(...)``.
import Envision_Perdido_DataCollection as _m  # noqa: E402

# Register this shim's module name as an alias for the real module so that
# patch('scripts.Envision_Perdido_DataCollection.scrape_month') patches the
# same object that automated_pipeline.py holds a reference to.
_sys.modules[__name__] = _m
_sys.modules["Envision_Perdido_DataCollection"] = _m
