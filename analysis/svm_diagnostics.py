#!/usr/bin/env python3
"""SVM diagnostics module for the Envision Perdido community event classifier.

Provides visualization and debugging tools to diagnose over-prediction of the
"community" class and unreliable confidence scores from a scikit-learn SVM
pipeline trained on structured + TF-IDF text features.

Typical usage
-------------
>>> from analysis.svm_diagnostics import main
>>> main(model, X_test, y_test, raw_df, X_train=X_train, y_train=y_train)

Or call individual diagnostic functions:
>>> from analysis.svm_diagnostics import (
...     plot_confusion_matrix,
...     plot_decision_distribution,
...     inspect_misclassifications,
... )
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------------
# Optional dependency guards — all three are available but we degrade
# gracefully if a future environment is missing them.
# ---------------------------------------------------------------------------
try:
    import yellowbrick  # noqa: F401 — version probe
    from yellowbrick.classifier import (
        ClassificationReport as YBClassificationReport,
        ConfusionMatrix as YBConfusionMatrix,
        ROCAUC as YBROCAUC,
    )

    _YELLOWBRICK = True
except Exception:  # ImportError or any sklearn-compat error on import
    _YELLOWBRICK = False

try:
    import eli5
    from eli5.sklearn import PermutationImportance  # noqa: F401

    _ELI5 = True
except Exception:
    _ELI5 = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASS_LABELS: list[str] = ["non-community", "community"]

#: Default output root used by :func:`main` when no ``output_dir`` is given.
_DEFAULT_OUTPUT = Path("output/analytics/diagnostics")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if it does not exist, then return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_fig(fig: plt.Figure, path: Optional[Path]) -> None:
    """Save *fig* to *path* at 200 DPI, or display it interactively."""
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=200, bbox_inches="tight")
    else:
        plt.show()
    plt.close(fig)


def _decision_scores(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Return raw ``decision_function`` scores as a 1-D float array."""
    return np.asarray(model.decision_function(X), dtype=float).ravel()


# ---------------------------------------------------------------------------
# 1. Confusion matrix
# ---------------------------------------------------------------------------


def plot_confusion_matrix(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    output_path: Optional[Path] = None,
) -> None:
    """Plot a labeled confusion matrix using seaborn.

    Axes are clearly labeled ("Predicted" / "Actual") with the class names
    ``["non-community", "community"]``.

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_test: Feature :class:`~pandas.DataFrame` matching training columns.
        y_test: Ground-truth binary labels (0 = non-community, 1 = community).
        output_path: File path to save the figure.  If ``None``, the figure is
            displayed interactively and then closed.
    """
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=True,
        xticklabels=CLASS_LABELS,
        yticklabels=CLASS_LABELS,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_xlabel("Predicted", fontsize=12, labelpad=8)
    ax.set_ylabel("Actual", fontsize=12, labelpad=8)
    ax.set_title("Confusion Matrix", fontsize=14, pad=12)
    # Make class labels readable at 45°
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    fig.tight_layout()
    _save_fig(fig, output_path)


# ---------------------------------------------------------------------------
# 2. Classification report heatmap
# ---------------------------------------------------------------------------


def plot_classification_report(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    output_path: Optional[Path] = None,
) -> None:
    """Render sklearn's classification report as a seaborn heatmap.

    Converts the per-class ``precision``, ``recall``, and ``f1-score`` values
    into a :class:`~pandas.DataFrame` and plots them on a colour-scaled grid.
    The ``support`` column is omitted from the heatmap to keep the colour scale
    meaningful (it is displayed as an annotation instead).

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_test: Feature :class:`~pandas.DataFrame`.
        y_test: Ground-truth binary labels (0/1).
        output_path: Save path or ``None`` for interactive display.
    """
    y_pred = model.predict(X_test)
    report_dict: dict = classification_report(
        y_test,
        y_pred,
        labels=[0, 1],
        target_names=CLASS_LABELS,
        output_dict=True,
        zero_division=0,
    )

    # Keep only rows that are per-class or averaged dicts
    rows = {k: v for k, v in report_dict.items() if isinstance(v, dict)}
    df = pd.DataFrame(rows).T[["precision", "recall", "f1-score"]].astype(float)

    # Append support as plain-text annotations
    support = {k: v["support"] for k, v in report_dict.items() if isinstance(v, dict)}
    annot = df.copy().map(lambda x: f"{x:.3f}")
    for row_name in annot.index:
        if row_name in support:
            annot.loc[row_name, "f1-score"] = (
                f"{df.loc[row_name, 'f1-score']:.3f}\n(n={int(support[row_name])})"
            )

    fig, ax = plt.subplots(figsize=(9, 4))
    sns.heatmap(
        df,
        annot=annot,
        fmt="",
        cmap="YlOrRd",
        vmin=0.0,
        vmax=1.0,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Classification Report", fontsize=14, pad=12)
    ax.set_xlabel("Metric", fontsize=11)
    ax.set_ylabel("Class / Average", fontsize=11)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    fig.tight_layout()
    _save_fig(fig, output_path)


# ---------------------------------------------------------------------------
# 3. Decision-function score distribution
# ---------------------------------------------------------------------------


def plot_decision_distribution(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    output_path: Optional[Path] = None,
) -> None:
    """Histogram of raw ``decision_function`` scores overlaid per class.

    Scores are the signed distances from the SVM hyperplane — no sigmoid or
    normalisation is applied.  A distribution shifted predominantly to the
    right of 0 for *both* classes indicates the model is biased toward
    predicting "community".

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_test: Feature :class:`~pandas.DataFrame`.
        y_test: Ground-truth binary labels (0/1).
        output_path: Save path or ``None`` for interactive display.
    """
    scores = _decision_scores(model, X_test)
    palette = {0: "#C0392B", 1: "#2E86AB"}
    mean_colors = {0: "#7B241C", 1: "#1A5276"}

    fig, ax = plt.subplots(figsize=(11, 5))

    for label, name in zip([0, 1], CLASS_LABELS):
        mask = y_test == label
        ax.hist(
            scores[mask],
            bins=35,
            alpha=0.55,
            label=f"{name}  (n={int(mask.sum())})",
            color=palette[label],
            edgecolor="white",
            linewidth=0.4,
        )
        if mask.any():
            mean_val = float(scores[mask].mean())
            ax.axvline(
                mean_val,
                color=mean_colors[label],
                linestyle="--",
                linewidth=1.4,
                label=f"{name} mean = {mean_val:+.3f}",
            )

    ax.axvline(0.0, color="black", linestyle="-", linewidth=1.8, label="Hyperplane (score = 0)")
    ax.set_xlabel("Raw decision_function score (SVM margin distance)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title(
        "Decision-Score Distribution by True Class\n"
        "Both distributions shifted right of 0 → model biased toward 'community'",
        fontsize=13,
    )
    ax.legend(fontsize=9, framealpha=0.85)
    fig.tight_layout()
    _save_fig(fig, output_path)


# ---------------------------------------------------------------------------
# 4. Calibration / reliability curve
# ---------------------------------------------------------------------------


def plot_calibration(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    n_bins: int = 10,
    output_path: Optional[Path] = None,
) -> None:
    """Plot a reliability curve (predicted probability vs. actual positive rate).

    For :class:`~sklearn.svm.LinearSVC` (non-probabilistic), the raw
    ``decision_function`` scores are min-max normalised to ``[0, 1]`` **for
    visualisation purposes only** — this is *not* a true probability.  A
    large deviation from the diagonal indicates the model's confidence
    ordering is unreliable.

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_test: Feature :class:`~pandas.DataFrame`.
        y_test: Ground-truth binary labels (0/1).
        n_bins: Number of equally-spaced bins for the calibration curve.
        output_path: Save path or ``None`` for interactive display.
    """
    if hasattr(model, "predict_proba"):
        prob_pos = model.predict_proba(X_test)[:, 1]
        source_label = "predict_proba() — calibrated probabilities"
    else:
        scores = _decision_scores(model, X_test)
        s_min, s_max = scores.min(), scores.max()
        prob_pos = (
            (scores - s_min) / (s_max - s_min) if s_max > s_min else np.full_like(scores, 0.5)
        )
        source_label = "decision_function() min-max normalised [0,1] — NOT a true probability"

    fraction_pos, mean_pred = calibration_curve(
        y_test, prob_pos, n_bins=n_bins, strategy="uniform"
    )
    cal_error = float(np.mean(np.abs(fraction_pos - mean_pred)))

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1.2, label="Perfectly calibrated")
    ax.plot(mean_pred, fraction_pos, "o-", color="#2E86AB", linewidth=2, markersize=7, label=source_label)

    ax.fill_between(
        mean_pred,
        fraction_pos,
        mean_pred,
        alpha=0.12,
        color="#E74C3C",
        label="Calibration gap",
    )
    ax.text(
        0.03,
        0.91,
        f"Mean calibration error: {cal_error:.3f}",
        transform=ax.transAxes,
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "lightyellow", "alpha": 0.85},
    )
    ax.set_xlabel("Mean predicted score (normalised)", fontsize=11)
    ax.set_ylabel("Fraction of positives (actual rate)", fontsize=11)
    ax.set_title(
        "Reliability / Calibration Curve\n"
        "Deviation above diagonal → over-confidence in 'community'",
        fontsize=13,
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    _save_fig(fig, output_path)


# ---------------------------------------------------------------------------
# 5. False positive / false negative inspection
# ---------------------------------------------------------------------------


def inspect_misclassifications(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    raw_data_df: pd.DataFrame,
    top_n: int = 20,
    output_dir: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Identify and rank the highest-confidence misclassifications.

    Builds an inspection :class:`~pandas.DataFrame` that joins the original
    event text, true label, predicted label, and raw decision score.  Results
    are sorted by *absolute* decision confidence so the most confidently-wrong
    predictions appear first.

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_test: Feature :class:`~pandas.DataFrame`.  Its index is used to
            align with ``raw_data_df``.
        y_test: Ground-truth binary labels (0/1).
        raw_data_df: Original event :class:`~pandas.DataFrame` containing at
            least one of ``["title", "description", "text", "event_title"]``.
            Its index must be a superset of ``X_test.index``.
        top_n: Maximum rows to return (and print) for each error category.
        output_dir: Directory for saving ``false_positives.csv`` and
            ``false_negatives.csv``.  Skipped when ``None``.

    Returns:
        A tuple ``(false_positives_df, false_negatives_df)`` sorted by
        descending absolute decision score.
    """
    scores = _decision_scores(model, X_test)
    y_pred = (scores >= 0).astype(int)

    # Locate the most informative text column present in raw_data_df
    _text_candidates = ["title", "description", "text", "event_title"]
    text_col = next((c for c in _text_candidates if c in raw_data_df.columns), None)

    inspection = pd.DataFrame(
        {
            "true_label": y_test,
            "predicted_label": y_pred,
            "decision_score": scores,
            "abs_confidence": np.abs(scores),
        },
        index=X_test.index,
    )

    if text_col is not None:
        # Align by index — handle cases where raw_data_df is larger than X_test
        aligned = raw_data_df[text_col].reindex(X_test.index)
        inspection.insert(0, "event_text", aligned.values)
    else:
        inspection.insert(0, "event_text", "N/A")

    _cols = ["event_text", "true_label", "predicted_label", "decision_score", "abs_confidence"]

    # False positives: true=0 (non-community) → predicted=1 (community)
    fp_mask = (inspection["true_label"] == 0) & (inspection["predicted_label"] == 1)
    false_positives = (
        inspection.loc[fp_mask, _cols]
        .sort_values("abs_confidence", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    # False negatives: true=1 (community) → predicted=0 (non-community)
    fn_mask = (inspection["true_label"] == 1) & (inspection["predicted_label"] == 0)
    false_negatives = (
        inspection.loc[fn_mask, _cols]
        .sort_values("abs_confidence", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    if output_dir is not None:
        out = _ensure_dir(output_dir)
        false_positives.to_csv(out / "false_positives.csv", index=False)
        false_negatives.to_csv(out / "false_negatives.csv", index=False)
        print(f"  Misclassification CSVs saved → {out}")

    _print_misclassification_table(
        false_positives,
        fp_mask.sum(),
        "FALSE POSITIVES",
        "non-community predicted as community",
        top_n,
    )
    _print_misclassification_table(
        false_negatives,
        fn_mask.sum(),
        "FALSE NEGATIVES",
        "community predicted as non-community",
        top_n,
    )

    return false_positives, false_negatives


def _print_misclassification_table(
    df: pd.DataFrame,
    total: int,
    label: str,
    description: str,
    top_n: int,
) -> None:
    """Pretty-print a misclassification table to stdout."""
    print(f"\n{'─' * 70}")
    print(f"  TOP {top_n} {label}  ({description})")
    print(f"  Total {label.lower()} in test set: {total}")
    print(f"{'─' * 70}")
    if df.empty:
        print("  (none)")
        return
    with pd.option_context(
        "display.max_colwidth", 80,
        "display.max_rows", top_n,
        "display.float_format", "{:.4f}".format,
    ):
        print(df.to_string(index=True))


# ---------------------------------------------------------------------------
# 6. Feature importance (linear SVM)
# ---------------------------------------------------------------------------


def show_feature_importance(
    model: Pipeline,
    vectorizer=None,
    top_n: int = 20,
    output_path: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    """Extract and visualise SVM coefficients as feature importance.

    Works with a full :class:`~sklearn.pipeline.Pipeline` (extracts the ``pre``
    and ``clf`` named steps automatically) or a standalone
    :class:`~sklearn.svm.LinearSVC` paired with a separate vectorizer.

    If ``eli5`` is available, its human-readable weight report is printed to
    stdout in addition to the matplotlib figure.

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline` or a raw
            :class:`~sklearn.svm.LinearSVC`.
        vectorizer: Standalone TF-IDF vectorizer supplying
            ``get_feature_names_out()``.  Used only when ``model`` is not a
            Pipeline or when the Pipeline's preprocessor does not expose feature
            names.
        top_n: Number of top features to display for each direction.
        output_path: Save path or ``None`` for interactive display.

    Returns:
        A :class:`~pandas.DataFrame` with columns ``["feature", "coefficient",
        "direction"]``, or ``None`` when coefficients are unavailable.
    """
    # --- Resolve classifier and feature names ---
    clf = None
    feature_names: Optional[np.ndarray] = None

    if isinstance(model, Pipeline):
        clf = model.named_steps.get("clf")
        pre = model.named_steps.get("pre")
        if pre is not None and hasattr(pre, "get_feature_names_out"):
            try:
                feature_names = np.asarray(pre.get_feature_names_out())
            except Exception as exc:
                warnings.warn(f"Could not get feature names from preprocessor: {exc}")
    else:
        clf = model

    if feature_names is None and vectorizer is not None:
        if hasattr(vectorizer, "get_feature_names_out"):
            try:
                feature_names = np.asarray(vectorizer.get_feature_names_out())
            except Exception as exc:
                warnings.warn(f"Could not get feature names from vectorizer: {exc}")

    if clf is None or not hasattr(clf, "coef_"):
        print(
            "Feature importance requires a linear SVM (LinearSVC or SVC(kernel='linear'))."
            "  The current classifier does not expose coef_."
        )
        return None

    coefs: np.ndarray = clf.coef_[0]
    n = len(coefs)

    if feature_names is None or len(feature_names) != n:
        warnings.warn(
            f"Feature name count ({0 if feature_names is None else len(feature_names)}) "
            f"does not match coef_ length ({n}).  Using generic names."
        )
        feature_names = np.array([f"feature_{i}" for i in range(n)])

    # --- eli5 text report ---
    if _ELI5:
        try:
            expl = eli5.explain_weights(clf, feature_names=list(feature_names), top=top_n)
            print("\n=== eli5 Feature Weight Report ===")
            print(eli5.format_as_text(expl))
        except Exception as exc:
            warnings.warn(f"eli5.explain_weights failed ({exc}) — proceeding with matplotlib plot.")

    # --- Build combined DataFrame ---
    pos_idx = np.argsort(coefs)[::-1][:top_n]   # most positive → community
    neg_idx = np.argsort(coefs)[:top_n]          # most negative → non-community

    top_pos = pd.DataFrame(
        {
            "feature": feature_names[pos_idx],
            "coefficient": coefs[pos_idx],
            "direction": "community (+)",
        }
    )
    top_neg = pd.DataFrame(
        {
            "feature": feature_names[neg_idx],
            "coefficient": coefs[neg_idx],
            "direction": "non-community (−)",
        }
    )
    combined = pd.concat([top_pos, top_neg], ignore_index=True)

    # --- Side-by-side bar charts ---
    pos_plot = top_pos.sort_values("coefficient")
    neg_plot = top_neg.sort_values("coefficient", ascending=False).sort_values("coefficient")

    fig, axes = plt.subplots(1, 2, figsize=(18, max(6, top_n * 0.38)))

    axes[0].barh(
        pos_plot["feature"],
        pos_plot["coefficient"],
        color="#2E86AB",
        edgecolor="white",
        linewidth=0.4,
    )
    axes[0].axvline(0, color="black", linewidth=0.8)
    axes[0].set_title(f"Top {top_n} Community Indicators\n(positive coef → predicts community)", fontsize=11)
    axes[0].set_xlabel("Coefficient weight", fontsize=10)

    axes[1].barh(
        neg_plot["feature"],
        neg_plot["coefficient"],
        color="#C0392B",
        edgecolor="white",
        linewidth=0.4,
    )
    axes[1].axvline(0, color="black", linewidth=0.8)
    axes[1].set_title(
        f"Top {top_n} Non-Community Indicators\n(negative coef → predicts non-community)", fontsize=11
    )
    axes[1].set_xlabel("Coefficient weight", fontsize=10)

    fig.suptitle("LinearSVC Feature Importance (coef_)", fontsize=14, y=1.01)
    fig.tight_layout()
    _save_fig(fig, output_path)

    return combined


# ---------------------------------------------------------------------------
# 7. Yellowbrick visualisations
# ---------------------------------------------------------------------------


def run_yellowbrick_diagnostics(
    model: Pipeline,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    output_dir: Optional[Path] = None,
) -> None:
    """Run Yellowbrick classifier visualisers: ConfusionMatrix, ClassificationReport, ROCAUC.

    Yellowbrick visualisers follow a ``fit → score → finalize`` workflow, which
    means the pipeline is refitted on ``(X_train, y_train)`` for each
    visualiser.  Pass the same split used during the original evaluation to
    keep results consistent.

    ROCAUC is attempted for all models; :class:`~sklearn.svm.LinearSVC` exposes
    ``decision_function`` which Yellowbrick uses as a fallback for binary tasks.

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline`.
        X_train: Training feature :class:`~pandas.DataFrame` (for ``fit``).
        y_train: Training labels (for ``fit``).
        X_test: Test feature :class:`~pandas.DataFrame` (for ``score``).
        y_test: Ground-truth test labels (for ``score``).
        output_dir: Directory to save the three PNG files.  If ``None``,
            figures are displayed interactively.
    """
    if not _YELLOWBRICK:
        warnings.warn(
            "yellowbrick is not installed or failed to import.  "
            "Run:  pip install yellowbrick\n"
            "Skipping Yellowbrick diagnostics."
        )
        return

    out: Optional[Path] = _ensure_dir(output_dir) if output_dir is not None else None

    def _yb_save(fig: plt.Figure, name: str) -> None:
        if out is not None:
            fig.savefig(out / name, dpi=200, bbox_inches="tight")
        else:
            plt.show()
        plt.close(fig)

    # 1 — ConfusionMatrix
    try:
        fig_cm, ax_cm = plt.subplots(figsize=(7, 5))
        viz_cm = YBConfusionMatrix(model, classes=CLASS_LABELS, ax=ax_cm)
        viz_cm.fit(X_train, y_train)
        viz_cm.score(X_test, y_test)
        viz_cm.finalize()
        _yb_save(fig_cm, "yb_confusion_matrix.png")
        print("  [YB] ConfusionMatrix ✓")
    except Exception as exc:
        warnings.warn(f"Yellowbrick ConfusionMatrix failed: {exc}")
        plt.close("all")

    # 2 — ClassificationReport
    try:
        fig_cr, ax_cr = plt.subplots(figsize=(9, 5))
        viz_cr = YBClassificationReport(model, classes=CLASS_LABELS, support=True, ax=ax_cr)
        viz_cr.fit(X_train, y_train)
        viz_cr.score(X_test, y_test)
        viz_cr.finalize()
        _yb_save(fig_cr, "yb_classification_report.png")
        print("  [YB] ClassificationReport ✓")
    except Exception as exc:
        warnings.warn(f"Yellowbrick ClassificationReport failed: {exc}")
        plt.close("all")

    # 3 — ROCAUC (LinearSVC uses decision_function automatically for binary)
    try:
        fig_roc, ax_roc = plt.subplots(figsize=(7, 6))
        viz_roc = YBROCAUC(model, classes=CLASS_LABELS, ax=ax_roc)
        viz_roc.fit(X_train, y_train)
        viz_roc.score(X_test, y_test)
        viz_roc.finalize()
        _yb_save(fig_roc, "yb_roc_auc.png")
        print("  [YB] ROCAUC ✓")
    except Exception as exc:
        warnings.warn(
            f"Yellowbrick ROCAUC failed: {exc}\n"
            "Tip: wrap LinearSVC with CalibratedClassifierCV(cv='prefit') for true ROC curves."
        )
        plt.close("all")


# ---------------------------------------------------------------------------
# 8. Orchestration entry point
# ---------------------------------------------------------------------------


def main(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    raw_data_df: pd.DataFrame,
    X_train: Optional[pd.DataFrame] = None,
    y_train: Optional[np.ndarray] = None,
    vectorizer=None,
    output_dir: Optional[Path] = None,
    top_n: int = 20,
) -> None:
    """Run all diagnostics in sequence and save outputs to *output_dir*.

    Diagnostics executed:

    1. Seaborn confusion matrix
    2. Classification report heatmap
    3. Decision-function score distribution (per-class histogram)
    4. Calibration / reliability curve
    5. False positive / false negative inspection (CSV + console)
    6. Feature importance for linear SVM (with eli5 if available)
    7. Yellowbrick visualisers (requires ``X_train`` / ``y_train``)

    Args:
        model: Trained sklearn :class:`~sklearn.pipeline.Pipeline` (must
            expose ``decision_function``).
        X_test: Test feature :class:`~pandas.DataFrame`.
        y_test: Ground-truth binary labels (0 = non-community, 1 = community).
        raw_data_df: Original event data with at least one text column.  Its
            index must be a superset of ``X_test.index``.
        X_train: Training features for Yellowbrick.  If omitted, step 7 is
            skipped.
        y_train: Training labels for Yellowbrick.  If omitted, step 7 is
            skipped.
        vectorizer: Standalone TF-IDF vectorizer for feature name lookup.
            Only needed when the pipeline preprocessor does not expose
            ``get_feature_names_out()``.
        output_dir: Root directory for all saved plots and CSVs.  Defaults to
            ``output/analytics/diagnostics``.
        top_n: Number of top features / misclassifications to surface (default 20).
    """
    sns.set_style("whitegrid")
    plt.rcParams.update({"figure.dpi": 120})

    out = _ensure_dir(Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT)

    print("=" * 64)
    print(" SVM DIAGNOSTICS — Envision Perdido Community Classifier")
    print("=" * 64)
    print(f" Output directory: {out}\n")

    # ------------------------------------------------------------------
    print("[1/7] Confusion matrix")
    plot_confusion_matrix(
        model, X_test, y_test,
        output_path=out / "01_confusion_matrix.png",
    )

    # ------------------------------------------------------------------
    print("[2/7] Classification report heatmap")
    plot_classification_report(
        model, X_test, y_test,
        output_path=out / "02_classification_report.png",
    )

    # ------------------------------------------------------------------
    print("[3/7] Decision-score distribution")
    plot_decision_distribution(
        model, X_test, y_test,
        output_path=out / "03_decision_distribution.png",
    )

    # ------------------------------------------------------------------
    print("[4/7] Calibration / reliability curve")
    plot_calibration(
        model, X_test, y_test,
        output_path=out / "04_calibration_curve.png",
    )

    # ------------------------------------------------------------------
    print("[5/7] False positive / false negative inspection")
    inspect_misclassifications(
        model, X_test, y_test, raw_data_df,
        top_n=top_n,
        output_dir=out / "misclassifications",
    )

    # ------------------------------------------------------------------
    print("[6/7] Feature importance (linear SVM)")
    fi_df = show_feature_importance(
        model, vectorizer=vectorizer,
        top_n=top_n,
        output_path=out / "06_feature_importance.png",
    )
    if fi_df is not None:
        fi_df.to_csv(out / "06_feature_importance.csv", index=False)

    # ------------------------------------------------------------------
    print("[7/7] Yellowbrick visualisations")
    if X_train is not None and y_train is not None:
        run_yellowbrick_diagnostics(
            model, X_train, y_train, X_test, y_test,
            output_dir=out / "yellowbrick",
        )
    else:
        print(
            "  Skipped — X_train / y_train not provided.\n"
            "  Pass them to main() to enable Yellowbrick visualisers."
        )

    print(f"\n{'─' * 64}")
    print(f" Diagnostics complete.  All outputs saved to:\n  {out}")
    print(f"{'─' * 64}")
