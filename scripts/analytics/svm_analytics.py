#!/usr/bin/env python3
"""Generate SVM analytics plots and a markdown report.

This module focuses on practical diagnostics for the trained SVM pipeline:
- Confusion matrix and class metrics
- Precision/recall tradeoff across decision thresholds
- Confidence distribution and review workload behavior
- Top weighted text features (model interpretability)
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import sparse
from sklearn.decomposition import PCA
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline

from scripts.ml.svm_train_from_file import build_features, make_series_id
from scripts.ml.training_support import (
    binary_metrics,
    compute_confidence,
    threshold_sweep as shared_threshold_sweep,
)


BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_DATASET = BASE_DIR / "data" / "processed" / "consolidated_training_data.csv"
DEFAULT_MODEL = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
DEFAULT_REPORTS = BASE_DIR / "docs" / "reports"
DEFAULT_PLOTS_ROOT = BASE_DIR / "output" / "analytics"


def _coerce_labels(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
    if label_col not in df.columns:
        raise SystemExit(f"Dataset missing '{label_col}' column: {label_col}")

    labels = df[label_col].astype(str).str.strip().str.replace(".0", "", regex=False)
    mask = labels.isin(["0", "1"])
    labeled = df.loc[mask].copy()
    labeled[label_col] = labels.loc[mask].astype(int)
    if labeled.empty:
        raise SystemExit("No rows with valid 0/1 labels were found in input dataset")
    return labeled


def _load_eval_dataset(path: Path, label_col: str) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, str]:
    df = pd.read_csv(path)
    labeled = _coerce_labels(df, label_col)

    for col in ["uid", "url", "title", "description", "start", "location"]:
        if col not in labeled.columns:
            labeled[col] = ""

    if "series_id" not in labeled.columns:
        labeled["series_id"] = make_series_id(
            labeled,
            id_col="uid",
            url_col="url",
            title_col="title",
            loc_col="location",
        )
    labeled["series_id"] = labeled["series_id"].fillna("").astype(str)

    X, _ = build_features(labeled, "title", "description", "start", "location")
    y = labeled[label_col].astype(int).values

    split_mode = "full_dataset"
    groups = labeled["series_id"].astype(str).values
    unique_groups = pd.Series(groups).nunique()
    unique_labels = pd.Series(y).nunique()

    if unique_groups >= 3 and unique_labels >= 2 and len(labeled) >= 20:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        _, test_idx = next(splitter.split(X, y, groups))
        X_eval = X.iloc[test_idx]
        y_eval = y[test_idx]
        split_mode = "group_shuffle_split"
    elif unique_labels >= 2 and len(labeled) >= 20:
        _, X_eval, _, y_eval = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )
        split_mode = "stratified_split"
    else:
        X_eval = X
        y_eval = y

    return labeled, y, X_eval, y_eval, split_mode


def _load_model(path: Path) -> tuple[Pipeline, dict[str, float]]:
    model_obj = joblib.load(path)
    policy = {
        "decision_threshold": 0.0,
        "review_margin": 0.35,
        "confidence_threshold": 0.75,
    }

    if isinstance(model_obj, dict) and "pipe" in model_obj:
        pipe = model_obj["pipe"]
        policy["decision_threshold"] = float(model_obj.get("decision_threshold", 0.0))
        policy["review_margin"] = float(model_obj.get("review_margin", 0.35))
        policy["confidence_threshold"] = float(model_obj.get("confidence_threshold", 0.75))
    elif isinstance(model_obj, Pipeline):
        pipe = model_obj
    else:
        raise SystemExit("Unsupported model artifact format for analytics")

    if not isinstance(pipe, Pipeline):
        raise SystemExit("Loaded model pipeline is invalid")

    return pipe, policy


def _threshold_sweep(
    y_true: np.ndarray,
    scores: np.ndarray,
    confidence_threshold: float,
    review_margin: float,
) -> pd.DataFrame:
    return shared_threshold_sweep(
        y_true=y_true,
        scores=scores,
        confidence_threshold=confidence_threshold,
        review_margin=review_margin,
    )


def _top_features(pipe: Pipeline, top_n: int = 20) -> pd.DataFrame:
    clf = pipe.named_steps.get("clf")
    pre = pipe.named_steps.get("pre")
    if clf is None or pre is None or not hasattr(clf, "coef_"):
        return pd.DataFrame(columns=["feature", "weight", "direction"])

    try:
        names = pre.get_feature_names_out()
    except Exception:
        names = np.array([f"feature_{i}" for i in range(clf.coef_.shape[1])])

    coefs = clf.coef_[0]
    if len(names) != len(coefs):
        n = min(len(names), len(coefs))
        names = names[:n]
        coefs = coefs[:n]

    idx = np.argsort(np.abs(coefs))[::-1][:top_n]
    out = pd.DataFrame(
        {
            "feature": names[idx],
            "weight": coefs[idx],
        }
    )
    out["direction"] = np.where(out["weight"] >= 0, "community", "non_community")
    return out


def _plot_confusion(cm: np.ndarray, output_path: Path) -> None:
    plt.figure(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def _plot_class_metrics(metrics: dict[str, float], output_path: Path) -> None:
    rows = [
        ("precision", metrics["precision_0"], metrics["precision_1"]),
        ("recall", metrics["recall_0"], metrics["recall_1"]),
        ("f1", metrics["f1_0"], metrics["f1_1"]),
    ]
    df = pd.DataFrame(rows, columns=["metric", "class_0", "class_1"])
    x = np.arange(len(df))
    w = 0.35

    plt.figure(figsize=(8, 5))
    plt.bar(x - w / 2, df["class_0"], width=w, label="class 0")
    plt.bar(x + w / 2, df["class_1"], width=w, label="class 1")
    plt.xticks(x, df["metric"])
    plt.ylim(0, 1.05)
    plt.title("Per-Class Metrics")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def _plot_threshold_tradeoff(sweep_df: pd.DataFrame, decision_threshold: float, output_path: Path) -> None:
    plt.figure(figsize=(9, 5))
    plt.plot(sweep_df["threshold"], sweep_df["precision_1"], label="precision_1")
    plt.plot(sweep_df["threshold"], sweep_df["recall_1"], label="recall_1")
    plt.plot(sweep_df["threshold"], sweep_df["f1_1"], label="f1_1")
    plt.axvline(decision_threshold, color="red", linestyle="--", label="active threshold")
    plt.ylim(0, 1.05)
    plt.xlabel("Decision Threshold")
    plt.ylabel("Score")
    plt.title("Class-1 Threshold Tradeoff")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def _plot_confidence(scores: np.ndarray, output_path: Path) -> None:
    conf = compute_confidence(scores)
    plt.figure(figsize=(8, 5))
    sns.histplot(conf, bins=30, kde=True)
    plt.xlabel("Confidence")
    plt.ylabel("Count")
    plt.title("Prediction Confidence Distribution")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def _plot_review_volume(sweep_df: pd.DataFrame, decision_threshold: float, output_path: Path) -> None:
    plt.figure(figsize=(9, 5))
    plt.plot(sweep_df["threshold"], sweep_df["review_rate"])
    plt.axvline(decision_threshold, color="red", linestyle="--", label="active threshold")
    plt.ylim(0, 1.05)
    plt.xlabel("Decision Threshold")
    plt.ylabel("Review Rate")
    plt.title("Estimated Review Volume vs Threshold")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def _plot_top_features(top_df: pd.DataFrame, output_path: Path) -> None:
    if top_df.empty:
        plt.figure(figsize=(7, 3))
        plt.text(0.1, 0.5, "No feature coefficients available", fontsize=12)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()
        return

    plot_df = top_df.sort_values("weight")
    colors = ["#2E86AB" if w >= 0 else "#C0392B" for w in plot_df["weight"]]
    plt.figure(figsize=(10, 7))
    plt.barh(plot_df["feature"], plot_df["weight"], color=colors)
    plt.title("Top Weighted Features")
    plt.xlabel("Coefficient Weight")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def _plot_pca_projection(
    pipe: Pipeline,
    X_eval: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_path: Path,
    output_csv: Path,
) -> None:
    """Project transformed features to 2D with PCA for visual drill-down."""
    pre = pipe.named_steps.get("pre")
    if pre is None:
        # Fallback placeholder if preprocessor is not available.
        plt.figure(figsize=(8, 4))
        plt.text(0.1, 0.5, "PCA unavailable: preprocessor not found", fontsize=12)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()
        pd.DataFrame(columns=["pc1", "pc2", "true_label", "pred_label"]).to_csv(output_csv, index=False)
        return

    transformed = pre.transform(X_eval)
    if sparse.issparse(transformed):
        dense = transformed.toarray()
    else:
        dense = np.asarray(transformed)

    if dense.ndim != 2 or dense.shape[0] < 2 or dense.shape[1] < 2:
        plt.figure(figsize=(8, 4))
        plt.text(0.1, 0.5, "PCA unavailable: insufficient dimensionality", fontsize=12)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()
        pd.DataFrame(columns=["pc1", "pc2", "true_label", "pred_label"]).to_csv(output_csv, index=False)
        return

    pca = PCA(n_components=2, random_state=42)
    pcs = pca.fit_transform(dense)

    pca_df = pd.DataFrame(
        {
            "pc1": pcs[:, 0],
            "pc2": pcs[:, 1],
            "true_label": y_true.astype(int),
            "pred_label": y_pred.astype(int),
            "correct": (y_true.astype(int) == y_pred.astype(int)).astype(int),
        }
    )
    pca_df.to_csv(output_csv, index=False)

    plt.figure(figsize=(9, 6))
    sns.scatterplot(
        data=pca_df,
        x="pc1",
        y="pc2",
        hue="true_label",
        style="correct",
        palette="Set2",
        alpha=0.8,
    )
    plt.title("PCA Projection (True Label + Correctness)")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def _write_report(
    report_path: Path,
    plots_dir: Path,
    dataset_path: Path,
    model_path: Path,
    split_mode: str,
    y_eval: np.ndarray,
    base_metrics: dict[str, float],
    tuned_metrics: dict[str, float],
    decision_threshold: float,
    review_margin: float,
    confidence_threshold: float,
    review_rate: float,
) -> None:
    def rel_plot(name: str) -> str:
        target = plots_dir / name
        return Path(os.path.relpath(target, start=report_path.parent)).as_posix()

    cm_base = confusion_matrix(y_eval, tuned_metrics["y_pred"])
    body = f"""# SVM Analytics Report

- Generated (UTC): {datetime.now(UTC).isoformat()}
- Dataset: {dataset_path}
- Model: {model_path}
- Split mode: {split_mode}

## Policy

- Decision threshold: {decision_threshold:.4f}
- Review margin: {review_margin:.4f}
- Confidence threshold: {confidence_threshold:.4f}
- Estimated review rate: {review_rate:.2%}

## Metrics

- Accuracy (active threshold): {tuned_metrics['accuracy']:.4f}
- Class-1 precision: {tuned_metrics['precision_1']:.4f}
- Class-1 recall: {tuned_metrics['recall_1']:.4f}
- Class-1 F1: {tuned_metrics['f1_1']:.4f}

## Confusion Matrix

```
{cm_base}
```

![Confusion Matrix]({rel_plot('confusion_matrix.png')})

## Per-Class Metrics

![Class Metrics]({rel_plot('class_metrics.png')})

## Threshold Tradeoff

![Threshold Tradeoff]({rel_plot('threshold_tradeoff.png')})

## Confidence Distribution

![Confidence Distribution]({rel_plot('confidence_distribution.png')})

## Review Volume

![Review Volume]({rel_plot('review_volume.png')})

## Top Features

![Top Features]({rel_plot('top_features.png')})

## PCA Projection

![PCA Projection]({rel_plot('pca_projection.png')})
"""
    report_path.write_text(body, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate SVM analytics graphs and markdown report")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    p.add_argument("--label-col", default="label")
    p.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS)
    p.add_argument("--plots-root", type=Path, default=DEFAULT_PLOTS_ROOT)
    p.add_argument("--top-features", type=int, default=20)
    return p


def main() -> int:
    sns.set_style("whitegrid")
    args = build_parser().parse_args()

    dataset_path = args.dataset.expanduser().resolve()
    model_path = args.model.expanduser().resolve()

    labeled, _, X_eval, y_eval, split_mode = _load_eval_dataset(dataset_path, args.label_col)
    pipe, policy = _load_model(model_path)

    decision_scores = np.asarray(pipe.decision_function(X_eval), dtype=float)
    y_pred_base = pipe.predict(X_eval)
    y_pred_tuned = (decision_scores >= policy["decision_threshold"]).astype(int)

    base_metrics = binary_metrics(y_eval, y_pred_base)
    tuned_metrics = binary_metrics(y_eval, y_pred_tuned)
    tuned_metrics["y_pred"] = y_pred_tuned

    sweep_df = _threshold_sweep(
        y_eval,
        decision_scores,
        policy["confidence_threshold"],
        policy["review_margin"],
    )
    conf = compute_confidence(decision_scores)
    review_rate = float(
        np.mean(
            (conf < policy["confidence_threshold"])
            | (np.abs(decision_scores - policy["decision_threshold"]) < policy["review_margin"])
        )
    )

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    plots_dir = args.plots_root.expanduser().resolve() / f"svm_analytics_{run_id}"
    plots_dir.mkdir(parents=True, exist_ok=True)
    report_dir = args.report_dir.expanduser().resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    _plot_confusion(confusion_matrix(y_eval, y_pred_tuned), plots_dir / "confusion_matrix.png")
    _plot_class_metrics(tuned_metrics, plots_dir / "class_metrics.png")
    _plot_threshold_tradeoff(sweep_df, policy["decision_threshold"], plots_dir / "threshold_tradeoff.png")
    _plot_confidence(decision_scores, plots_dir / "confidence_distribution.png")
    _plot_review_volume(sweep_df, policy["decision_threshold"], plots_dir / "review_volume.png")

    top_df = _top_features(pipe, top_n=args.top_features)
    _plot_top_features(top_df, plots_dir / "top_features.png")
    _plot_pca_projection(
        pipe=pipe,
        X_eval=X_eval,
        y_true=y_eval,
        y_pred=y_pred_tuned,
        output_path=plots_dir / "pca_projection.png",
        output_csv=plots_dir / "pca_projection.csv",
    )

    top_df.to_csv(plots_dir / "top_features.csv", index=False)
    sweep_df.to_csv(plots_dir / "threshold_sweep.csv", index=False)

    report_path = report_dir / f"svm_analytics_report_{run_id}.md"
    _write_report(
        report_path=report_path,
        plots_dir=plots_dir,
        dataset_path=dataset_path,
        model_path=model_path,
        split_mode=split_mode,
        y_eval=y_eval,
        base_metrics=base_metrics,
        tuned_metrics=tuned_metrics,
        decision_threshold=policy["decision_threshold"],
        review_margin=policy["review_margin"],
        confidence_threshold=policy["confidence_threshold"],
        review_rate=review_rate,
    )

    print("SVM analytics generated")
    print(f"  report: {report_path}")
    print(f"  plots:  {plots_dir}")
    print(
        "  tuned metrics: "
        f"acc={tuned_metrics['accuracy']:.4f}, "
        f"precision_1={tuned_metrics['precision_1']:.4f}, "
        f"recall_1={tuned_metrics['recall_1']:.4f}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
