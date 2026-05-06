"""Smoke tests — verify every public entrypoint can be imported without error.

These tests are intentionally cheap: they only check that module-level code
(imports, constant definitions, class/function registration) doesn't blow up.
They do *not* make network calls, hit the filesystem for credentials, or run
the ML model.

Run with::

    uv run pytest tests/smoke/ -m "not network and not slow and not integration"
"""

import importlib
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so scripts.* imports resolve
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _can_import(module_path: str) -> None:
    """Assert that *module_path* can be imported."""
    importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# Pipeline entrypoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "scripts.pipeline.automated_pipeline",
        "scripts.pipeline.wordpress_uploader",
        "scripts.pipeline.health_check",
    ],
)
def test_pipeline_entrypoints_importable(module: str) -> None:
    _can_import(module)


# ---------------------------------------------------------------------------
# Stage modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "scripts.pipeline.stages.scrape",
        "scripts.pipeline.stages.classify",
        "scripts.pipeline.stages.enrich",
        "scripts.pipeline.stages.export",
        "scripts.pipeline.stages.notify",
        "scripts.pipeline.stages.upload",
    ],
)
def test_stage_modules_importable(module: str) -> None:
    _can_import(module)


# ---------------------------------------------------------------------------
# ML modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "scripts.ml.training_support",
        "scripts.ml.svm_train_from_file",
        "scripts.ml.svm_tag_events",
    ],
)
def test_ml_modules_importable(module: str) -> None:
    _can_import(module)


# ---------------------------------------------------------------------------
# Scraper modules (canonical sub-packages)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "scripts.scrapers.multi_calendar.models",
        "scripts.scrapers.multi_calendar.fetch",
        "scripts.scrapers.multi_calendar.scraper",
        "scripts.scrapers.multi_calendar",
        "scripts.scrapers.wren_haven.cache",
        "scripts.scrapers.wren_haven.fetch",
        "scripts.scrapers.wren_haven.scraper",
        "scripts.scrapers.wren_haven",
        "scripts.scrapers.perdido_chamber_scraper",
    ],
)
def test_scraper_modules_importable(module: str) -> None:
    _can_import(module)


# ---------------------------------------------------------------------------
# Tooling modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "scripts.tooling.logger",
        "scripts.tooling.env_loader",
    ],
)
def test_tooling_modules_importable(module: str) -> None:
    _can_import(module)
