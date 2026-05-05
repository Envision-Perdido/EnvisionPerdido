"""Stage 2 — SVM classification, threshold policy, confidence flagging.

This module owns model loading, caching, threshold management, and batch
inference.  It does *not* perform enrichment, filtering, or image assignment;
those belong to the ``enrich`` stage.
"""

from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from scripts.ml.training_support import (
    build_text_features,
    compute_confidence,
    normalize_event_text_series,
)
from scripts.tooling.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths & tunable defaults (resolved relative to repo root)
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).parent.parent.parent.parent  # …/EnvisionPerdido
MODEL_PATH = _BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = _BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
MODEL_DECISION_THRESHOLD = float(os.getenv("MODEL_DECISION_THRESHOLD", "0.0"))
REVIEW_MARGIN = float(os.getenv("REVIEW_MARGIN", "0.35"))
_THRESHOLD_OVERRIDE_ENV = "MODEL_DECISION_THRESHOLD_OVERRIDE"

# ---------------------------------------------------------------------------
# Module-level model cache  (avoids reloading across multiple pipeline runs
# within the same process)
# ---------------------------------------------------------------------------

_MODEL_CACHE: dict = {
    "model": None,
    "vectorizer": None,
    "decision_threshold": MODEL_DECISION_THRESHOLD,
    "persisted_decision_threshold": MODEL_DECISION_THRESHOLD,
    "decision_threshold_source": "default",
    "review_margin": REVIEW_MARGIN,
    "confidence_threshold": CONFIDENCE_THRESHOLD,
    "model_format": "unknown",
    "model_path": str(MODEL_PATH),
    "model_size_kb": 0.0,
    "model_modified": "unknown",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_threshold_override() -> float | None:
    raw = os.getenv(_THRESHOLD_OVERRIDE_ENV)
    if not raw or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "Ignoring invalid %s=%r — expected a float.", _THRESHOLD_OVERRIDE_ENV, raw
        )
        return None


def _apply_threshold_policy() -> None:
    persisted = float(
        _MODEL_CACHE.get("persisted_decision_threshold", MODEL_DECISION_THRESHOLD)
    )
    override = _read_threshold_override()
    if override is not None:
        _MODEL_CACHE["decision_threshold"] = override
        _MODEL_CACHE["decision_threshold_source"] = f"env:{_THRESHOLD_OVERRIDE_ENV}"
    else:
        _MODEL_CACHE["decision_threshold"] = persisted
        _MODEL_CACHE["decision_threshold_source"] = "model_artifact"


def _log_model_config() -> None:
    logger.info(
        "Active model: path=%s  format=%s  size_kb=%.1f  modified=%s",
        _MODEL_CACHE.get("model_path", MODEL_PATH),
        _MODEL_CACHE.get("model_format", "unknown"),
        _MODEL_CACHE.get("model_size_kb", 0.0),
        _MODEL_CACHE.get("model_modified", "unknown"),
    )
    logger.info(
        "Threshold policy: persisted=%.4f  active=%.4f  source=%s  "
        "review_margin=%.4f  confidence_threshold=%.4f",
        float(_MODEL_CACHE.get("persisted_decision_threshold", MODEL_DECISION_THRESHOLD)),
        float(_MODEL_CACHE.get("decision_threshold", MODEL_DECISION_THRESHOLD)),
        _MODEL_CACHE.get("decision_threshold_source", "unknown"),
        float(_MODEL_CACHE.get("review_margin", REVIEW_MARGIN)),
        float(_MODEL_CACHE.get("confidence_threshold", CONFIDENCE_THRESHOLD)),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_model_and_vectorizer() -> tuple[object | None, object | None]:
    """Load (and cache) the event classifier model + vectorizer.

    Supports three artifact formats:

    * **unified bundle** – ``dict`` with ``"pipe"`` key (new default format)
    * **unified direct** – bare ``sklearn.pipeline.Pipeline`` instance
    * **legacy** – separate ``model`` + ``vectorizer`` joblib files

    Returns:
        ``(model, vectorizer)`` on success, or ``(None, None)`` when
        artifacts are missing (a descriptive error is logged).

    Raises:
        SystemExit: Never.  Missing artifacts are surfaced as log errors so
            the caller can decide how to handle them.
    """
    from sklearn.pipeline import Pipeline  # lazy import avoids sklearn at module level

    global _MODEL_CACHE

    if _MODEL_CACHE["model"] is not None and _MODEL_CACHE["vectorizer"] is not None:
        _apply_threshold_policy()
        return _MODEL_CACHE["model"], _MODEL_CACHE["vectorizer"]

    if not MODEL_PATH.exists():
        logger.error(
            "Model file not found: %s — run "
            "scripts/ml/svm_train_from_file.py to train.", MODEL_PATH
        )
        return None, None

    model_data = joblib.load(MODEL_PATH)
    stat = MODEL_PATH.stat()
    from datetime import datetime

    _MODEL_CACHE["model_path"] = str(MODEL_PATH)
    _MODEL_CACHE["model_size_kb"] = round(stat.st_size / 1024, 1)
    _MODEL_CACHE["model_modified"] = datetime.fromtimestamp(stat.st_mtime).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if isinstance(model_data, dict) and "pipe" in model_data:
        _MODEL_CACHE["model"] = model_data["pipe"]
        _MODEL_CACHE["vectorizer"] = "UNIFIED_PIPELINE"
        _MODEL_CACHE["persisted_decision_threshold"] = float(
            model_data.get("decision_threshold", MODEL_DECISION_THRESHOLD)
        )
        _MODEL_CACHE["review_margin"] = float(model_data.get("review_margin", REVIEW_MARGIN))
        _MODEL_CACHE["confidence_threshold"] = float(
            model_data.get("confidence_threshold", CONFIDENCE_THRESHOLD)
        )
        _MODEL_CACHE["model_format"] = "unified_pipeline_bundle"
        logger.info("Loaded unified pipeline bundle model.")

    elif isinstance(model_data, Pipeline):
        _MODEL_CACHE["model"] = model_data
        _MODEL_CACHE["vectorizer"] = "UNIFIED_PIPELINE"
        _MODEL_CACHE["persisted_decision_threshold"] = MODEL_DECISION_THRESHOLD
        _MODEL_CACHE["review_margin"] = REVIEW_MARGIN
        _MODEL_CACHE["confidence_threshold"] = CONFIDENCE_THRESHOLD
        _MODEL_CACHE["model_format"] = "unified_pipeline_direct"
        logger.info("Loaded unified pipeline (direct) model.")

    else:
        if not VECTORIZER_PATH.exists():
            logger.error(
                "Vectorizer file not found: %s — run "
                "scripts/ml/svm_train_from_file.py to train.", VECTORIZER_PATH
            )
            return None, None
        _MODEL_CACHE["model"] = model_data
        _MODEL_CACHE["vectorizer"] = joblib.load(VECTORIZER_PATH)
        _MODEL_CACHE["persisted_decision_threshold"] = MODEL_DECISION_THRESHOLD
        _MODEL_CACHE["review_margin"] = REVIEW_MARGIN
        _MODEL_CACHE["confidence_threshold"] = CONFIDENCE_THRESHOLD
        _MODEL_CACHE["model_format"] = "legacy_model_plus_vectorizer"
        logger.info("Loaded legacy (separate model + vectorizer) format.")

    _apply_threshold_policy()
    return _MODEL_CACHE["model"], _MODEL_CACHE["vectorizer"]


def classify_events_batch(
    events_df: pd.DataFrame,
    model: object,
    vectorizer: object,
    batch_size: int = 500,
    verbose: bool = True,
    decision_threshold: float = 0.0,
    return_decision_scores: bool = False,
) -> "tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, np.ndarray]":
    """Classify events in batches for memory efficiency.

    Returns:
        ``(predictions, confidence)`` — or ``(predictions, confidence,
        decision_scores)`` when *return_decision_scores* is ``True``.
    """
    n = len(events_df)
    all_predictions = np.zeros(n, dtype=int)
    all_confidences = np.zeros(n, dtype=float)
    all_decision_scores = np.zeros(n, dtype=float)

    use_unified = vectorizer == "UNIFIED_PIPELINE"

    for i in range(0, n, batch_size):
        end = min(i + batch_size, n)
        batch = events_df.iloc[i:end].copy()
        expected = end - i

        if use_unified:
            text = normalize_event_text_series(
                batch.get("title", pd.Series()).fillna("")
                + " "
                + batch.get("description", pd.Series()).fillna("")
            )
            dt = pd.to_datetime(
                batch.get("start", pd.Series()), errors="coerce", utc=True
            )
            hour = dt.dt.hour.fillna(-1).astype(int)
            dow = dt.dt.dayofweek.fillna(-1).astype(int)
            is_weekend = dow.between(5, 6).astype(int)
            loc = batch.get("location", pd.Series()).fillna("").str.lower()
            X = pd.DataFrame(
                {
                    "text": text,
                    "hour": hour,
                    "is_weekend": is_weekend,
                    "venue_library": loc.str.contains(r"\blibrary\b", na=False).astype(int),
                    "venue_park": loc.str.contains(r"\bpark\b", na=False).astype(int),
                    "venue_church": loc.str.contains(r"\bchurch\b", na=False).astype(int),
                    "venue_museum": loc.str.contains(r"\bmuseum\b|gallery", na=False).astype(int),
                }
            )
        else:
            X_text = build_text_features(batch)
            X = vectorizer.transform(X_text)

        def _pad(arr: np.ndarray, length: int, fill: float = 0.0) -> np.ndarray:
            if len(arr) == length:
                return arr
            if len(arr) > length:
                return arr[:length]
            return np.pad(arr, (0, length - len(arr)), mode="edge")

        if hasattr(model, "decision_function"):
            dec = _pad(
                np.asarray(model.decision_function(X)).reshape(-1), expected
            )
            if decision_threshold != 0.0:
                preds = (dec >= decision_threshold).astype(int)
            else:
                preds = _pad(np.asarray(model.predict(X)).reshape(-1), expected)
            all_decision_scores[i:end] = dec
            batch_conf = compute_confidence(dec)
        else:
            preds = _pad(np.asarray(model.predict(X)).reshape(-1), expected)
            all_decision_scores[i:end] = np.nan
            batch_conf = np.full(len(preds), 0.5)

        all_predictions[i:end] = preds
        all_confidences[i:end] = batch_conf

        if verbose and (i + batch_size) % (batch_size * 5) == 0:
            logger.info("  Progress: %d/%d events classified", min(i + batch_size, n), n)

    if return_decision_scores:
        return all_predictions, all_confidences, all_decision_scores
    return all_predictions, all_confidences


def classify_events(events_df: pd.DataFrame) -> pd.DataFrame | None:
    """Run SVM classification and attach result columns to *events_df*.

    Adds: ``is_community_event``, ``confidence``, ``decision_score``,
    ``needs_review``.

    Does **not** perform enrichment, filtering, or image assignment; use the
    ``enrich`` stage for those.

    Returns:
        Annotated DataFrame, or ``None`` when the model cannot be loaded.
    """
    logger.info("Loading trained model...")
    model, vectorizer = load_model_and_vectorizer()
    if model is None or vectorizer is None:
        return None

    _log_model_config()

    decision_threshold = float(_MODEL_CACHE.get("decision_threshold", MODEL_DECISION_THRESHOLD))
    review_margin = float(_MODEL_CACHE.get("review_margin", REVIEW_MARGIN))
    confidence_threshold = float(_MODEL_CACHE.get("confidence_threshold", CONFIDENCE_THRESHOLD))

    logger.info(
        "Classifying %d events — threshold=%.4f  review_margin=%.4f  conf_threshold=%.4f",
        len(events_df),
        decision_threshold,
        review_margin,
        confidence_threshold,
    )

    predictions, confidence, decision_scores = classify_events_batch(
        events_df,
        model,
        vectorizer,
        batch_size=500,
        verbose=True,
        decision_threshold=decision_threshold,
        return_decision_scores=True,
    )

    events_df = events_df.copy()
    events_df["is_community_event"] = predictions
    events_df["confidence"] = confidence
    events_df["decision_score"] = decision_scores
    events_df["needs_review"] = (confidence < confidence_threshold) | (
        (events_df["decision_score"] - decision_threshold).abs() < review_margin
    )

    community_count = int(predictions.sum())
    zero_preds = (decision_scores >= 0.0).astype(int)
    flips = int(np.count_nonzero(predictions != zero_preds))
    logger.info(
        "Classification complete: %d community / %d non-community  "
        "threshold_flips=%d  needs_review=%d",
        community_count,
        len(events_df) - community_count,
        flips,
        int(events_df["needs_review"].sum()),
    )

    return events_df
