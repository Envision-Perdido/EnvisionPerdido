#!/usr/bin/env python3
"""Shared helpers for SVM training, threshold policy, and dataset hygiene."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


# ---------------------------------------------------------------------------
# Shared I/O helpers
# ---------------------------------------------------------------------------


def load_any(p: "Path | str") -> pd.DataFrame:
    """Load events from a CSV or JSON file into a DataFrame.

    JSON files may be a bare list or a dict with an ``"events"`` key.
    Nested dicts are flattened via :func:`pandas.json_normalize`.
    """
    p = Path(p)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.suffix.lower() == ".json":
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "events" in data:
            data = data["events"]
        return pd.json_normalize(data)
    raise SystemExit("Input must be .csv or .json")


# ---------------------------------------------------------------------------
# Shared feature engineering
# ---------------------------------------------------------------------------


def build_structured_features(
    df: pd.DataFrame,
    title_col: str = "title",
    desc_col: str = "description",
    start_col: str = "start_date",
    loc_col: str = "location",
) -> "tuple[pd.DataFrame, list[str]]":
    """Build the canonical structured feature matrix used by training and tagging.

    Returns a ``(X, num_cols)`` tuple where *X* is a DataFrame containing a
    ``"text"`` column plus numeric venue/time features, and *num_cols* lists
    the names of the numeric columns.  Both training and inference should call
    this function so that the feature schema never diverges.

    .. note::
        ``automated_pipeline.py`` currently uses a text-only
        ``build_features()`` for compatibility with older model checkpoints.
        New model artifacts should be trained with this function and loaded
        via the unified pipeline format so the full feature set is used at
        inference time.
    """
    text = normalize_event_text_series(
        df.get(title_col, pd.Series(dtype=str)).fillna("")
        + " "
        + df.get(desc_col, pd.Series(dtype=str)).fillna("")
    )
    dt = pd.to_datetime(df.get(start_col, pd.Series(dtype=str)), errors="coerce", utc=True)
    hour = dt.dt.hour.fillna(-1).astype(int)
    dow = dt.dt.dayofweek.fillna(-1).astype(int)
    is_weekend = dow.between(5, 6).astype(int)

    loc = df.get(loc_col, pd.Series(dtype=str)).fillna("").str.lower()
    venue_library = loc.str.contains(r"\blibrary\b", regex=True).astype(int)
    venue_park = loc.str.contains(r"\bpark\b", regex=True).astype(int)
    venue_church = loc.str.contains(r"\bchurch\b", regex=True).astype(int)
    venue_museum = loc.str.contains(r"\bmuseum\b|gallery", regex=True).astype(int)

    num_cols = ["hour", "is_weekend", "venue_library", "venue_park", "venue_church", "venue_museum"]
    X = pd.DataFrame(
        {
            "text": text,
            "hour": hour,
            "is_weekend": is_weekend,
            "venue_library": venue_library,
            "venue_park": venue_park,
            "venue_church": venue_church,
            "venue_museum": venue_museum,
        }
    )
    return X, num_cols


def build_text_features(
    df: pd.DataFrame,
    title_col: str = "title",
    desc_col: str = "description",
    loc_col: str = "location",
    cat_col: str = "category",
) -> list[str]:
    """Build plain-text feature strings for legacy (non-structured) model formats.

    This is the text-only counterpart of :func:`build_structured_features`.
    It is used by the pipeline when loading a model artifact that was trained
    without structured (hour/venue) features, i.e., the legacy separate
    ``model.pkl + vectorizer.pkl`` format.

    .. note::
        New model artifacts should be trained with :func:`build_structured_features`
        so that structured features are available at inference time.
    """
    title = df.get(title_col, pd.Series(dtype=str)).fillna("").astype(str)
    description = df.get(desc_col, pd.Series(dtype=str)).fillna("").astype(str)
    location = df.get(loc_col, pd.Series(dtype=str)).fillna("").astype(str)
    category = df.get(cat_col, pd.Series(dtype=str)).fillna("").astype(str)
    features = normalize_event_text_series(
        title + " " + description + " " + location + " " + category
    )
    return features.tolist()


SHORTCUT_STOP_PHRASES: tuple[str, ...] = (
    "room",
    "limited",
    "will be",
    "1st",
)

BOILERPLATE_PATTERNS: tuple[str, ...] = (
    r"(?i)\bplease note,?\s*this is a virtual event\.?\s*we'?ll see you online!?",
    r"(?i)\bfor more information contact\b.*$",
    r"(?i)\bvisit our website\b.*$",
    r"(?i)\bregister online here\b.*$",
)

KNOWN_SOURCE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("perdidochamber.com", "perdido_chamber"),
    ("wrenhavenhomestead.com", "wren_haven"),
)


def _clean_source_value(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or text in {"nan", "none"}:
        return ""
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def infer_source_from_url(url: object) -> str:
    raw_url = str(url or "").strip()
    if not raw_url or raw_url.lower() == "nan":
        return ""

    parsed = urlparse(raw_url)
    netloc = parsed.netloc.lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    for pattern, source_name in KNOWN_SOURCE_PATTERNS:
        if pattern in netloc:
            return source_name

    return _clean_source_value(netloc)


def infer_source_from_file(source_file: object) -> str:
    stem = _clean_source_value(source_file)
    if not stem:
        return ""
    if "wren" in stem:
        return "wren_haven"
    if "perdido" in stem:
        return "perdido_chamber"
    return stem


def ensure_source_column(
    df: pd.DataFrame,
    source_col: str = "source",
    url_col: str = "url",
    source_file_col: str = "_source_file",
) -> pd.DataFrame:
    """Ensure *source_col* is populated using explicit value, URL, or source file."""
    out = df.copy()

    if source_col not in out.columns:
        out[source_col] = ""

    source = out[source_col].map(_clean_source_value)

    if url_col in out.columns:
        inferred_from_url = out[url_col].map(infer_source_from_url)
        source = source.where(source.ne(""), inferred_from_url)

    if source_file_col in out.columns:
        inferred_from_file = out[source_file_col].map(infer_source_from_file)
        source = source.where(source.ne(""), inferred_from_file)

    out[source_col] = source.where(source.ne(""), "unknown")
    return out


def normalize_event_text_series(text: pd.Series) -> pd.Series:
    """Normalize text to reduce boilerplate and weak source/style shortcuts."""
    normalized = text.fillna("").astype(str)
    for pattern in BOILERPLATE_PATTERNS:
        normalized = normalized.str.replace(pattern, " ", regex=True)
    for phrase in SHORTCUT_STOP_PHRASES:
        normalized = normalized.str.replace(rf"\b{re.escape(phrase)}\b", " ", regex=True)
    normalized = normalized.str.replace(r"\s+", " ", regex=True).str.strip()
    return normalized


def compute_confidence(scores: np.ndarray) -> np.ndarray:
    """Convert raw decision scores to a confidence-like [0.5, 1) value."""
    scores = np.asarray(scores, dtype=float)
    return 1 / (1 + np.exp(-np.abs(scores)))


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute binary classification metrics with class-1 emphasis."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_0": float(precision[0]),
        "recall_0": float(recall[0]),
        "f1_0": float(f1[0]),
        "precision_1": float(precision[1]),
        "recall_1": float(recall[1]),
        "f1_1": float(f1[1]),
    }


def threshold_sweep(
    y_true: np.ndarray,
    scores: np.ndarray,
    confidence_threshold: float,
    review_margin: float,
) -> pd.DataFrame:
    """Evaluate threshold policy tradeoffs over all candidate score cutoffs."""
    scores = np.asarray(scores, dtype=float)
    thresholds = np.unique(np.concatenate([scores, np.array([0.0])]))
    confidence = compute_confidence(scores)

    rows: list[dict[str, float]] = []
    for threshold in thresholds:
        y_pred = (scores >= threshold).astype(int)
        metrics = binary_metrics(y_true, y_pred)
        review_rate = float(
            np.mean(
                (confidence < confidence_threshold)
                | (np.abs(scores - threshold) < review_margin)
            )
        )
        rows.append(
            {
                "threshold": float(threshold),
                "accuracy": metrics["accuracy"],
                "precision_0": metrics["precision_0"],
                "recall_0": metrics["recall_0"],
                "f1_0": metrics["f1_0"],
                "precision_1": metrics["precision_1"],
                "recall_1": metrics["recall_1"],
                "f1_1": metrics["f1_1"],
                "review_rate": review_rate,
            }
        )

    return pd.DataFrame(rows).sort_values("threshold").reset_index(drop=True)


def select_threshold_from_sweep(
    sweep_df: pd.DataFrame,
    target_recall: float,
    min_precision: float,
) -> tuple[float, dict[str, float], str]:
    """Choose a decision threshold from a precomputed threshold sweep."""
    both_qualified = sweep_df[
        (sweep_df["recall_1"] >= target_recall) & (sweep_df["precision_1"] >= min_precision)
    ]
    if not both_qualified.empty:
        chosen = both_qualified.sort_values("threshold", ascending=False).iloc[0]
        mode = "recall_and_precision"
    else:
        precision_qualified = sweep_df[sweep_df["precision_1"] >= min_precision]
        if not precision_qualified.empty:
            chosen = precision_qualified.sort_values("threshold", ascending=False).iloc[0]
            mode = "precision_only_fallback"
        else:
            chosen = sweep_df.sort_values(["f1_1", "threshold"], ascending=[False, False]).iloc[0]
            mode = "best_f1_fallback"

    summary = {
        "threshold": float(chosen["threshold"]),
        "accuracy": float(chosen["accuracy"]),
        "precision_1": float(chosen["precision_1"]),
        "recall_1": float(chosen["recall_1"]),
        "f1_1": float(chosen["f1_1"]),
        "review_rate": float(chosen["review_rate"]),
    }
    return float(chosen["threshold"]), summary, mode
