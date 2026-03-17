#!/usr/bin/env python3
"""Run end-to-end retraining flow and generate a post-train evaluation report.

Chained stages:
1) prepare_retraining_dataset.py
2) consolidate_training_data.py
3) svm_train_from_file.py
4) markdown evaluation report generation
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.ml.svm_train_from_file import build_features, make_series_id


PREP_SCRIPT = BASE_DIR / "scripts" / "ml" / "prepare_retraining_dataset.py"
CONSOLIDATE_SCRIPT = BASE_DIR / "scripts" / "ml" / "consolidate_training_data.py"
TRAIN_SCRIPT = BASE_DIR / "scripts" / "ml" / "svm_train_from_file.py"


def _run_step(name: str, cmd: list[str]) -> None:
    print(f"\n[{name}] {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=BASE_DIR)
    if completed.returncode != 0:
        raise SystemExit(f"Step failed: {name} (exit code {completed.returncode})")


def _latest(path_glob: str) -> Path | None:
    candidates = sorted((BASE_DIR / "data" / "processed").glob(path_glob))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_labeled(df_path: Path, label_col: str) -> pd.DataFrame:
    df = pd.read_csv(df_path)
    if label_col not in df.columns:
        raise SystemExit(f"Training input does not contain '{label_col}': {df_path}")

    labels = df[label_col].astype(str).str.strip().str.replace(".0", "", regex=False)
    mask = labels.isin(["0", "1"])
    labeled = df.loc[mask].copy()
    labeled[label_col] = labels.loc[mask].astype(int)

    if labeled.empty:
        raise SystemExit("No labeled rows found for evaluation after training")

    for col in ["title", "description", "start", "location", "url", "uid"]:
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

    return labeled


def _load_pipeline(model_path: Path) -> Pipeline:
    model_obj = joblib.load(model_path)
    if isinstance(model_obj, dict) and "pipe" in model_obj:
        pipe = model_obj["pipe"]
    elif isinstance(model_obj, Pipeline):
        pipe = model_obj
    else:
        raise SystemExit(
            "Model artifact is not a unified pipeline. "
            "Expected dict with 'pipe' or sklearn Pipeline."
        )

    if not isinstance(pipe, Pipeline):
        raise SystemExit("Loaded object under 'pipe' is not a sklearn Pipeline")
    return pipe


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute binary metrics with class-1 emphasis."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    precision_1 = tp / (tp + fp) if (tp + fp) else 0.0
    recall_1 = tp / (tp + fn) if (tp + fn) else 0.0
    precision_0 = tn / (tn + fn) if (tn + fn) else 0.0
    recall_0 = tn / (tn + fp) if (tn + fp) else 0.0
    accuracy = float((tp + tn) / len(y_true)) if len(y_true) else 0.0

    return {
        "accuracy": accuracy,
        "precision_1": float(precision_1),
        "recall_1": float(recall_1),
        "precision_0": float(precision_0),
        "recall_0": float(recall_0),
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


def _select_recall_threshold(
    y_true: np.ndarray,
    scores: np.ndarray,
    target_recall: float,
    min_precision: float,
) -> tuple[float, dict[str, float], str]:
    """Select a decision threshold that favors class-1 recall.

    Strategy:
    - Scan score cutoffs and keep candidates meeting min precision.
    - Prefer the candidate with highest class-1 recall.
    - If none satisfy precision, use fallback maximizing recall.
    """
    y_true = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=float)

    unique_thresholds = np.unique(scores)
    # Include default and a lower bound to allow strong recall behavior.
    candidates = np.unique(np.concatenate([unique_thresholds, np.array([0.0, scores.min() - 1e-6])]))

    best_meeting_precision: tuple[float, dict[str, float]] | None = None
    best_recall_fallback: tuple[float, dict[str, float]] | None = None

    for threshold in candidates:
        y_pred = (scores >= threshold).astype(int)
        metrics = _binary_metrics(y_true, y_pred)

        if best_recall_fallback is None or metrics["recall_1"] > best_recall_fallback[1]["recall_1"]:
            best_recall_fallback = (float(threshold), metrics)

        if metrics["precision_1"] >= min_precision:
            if best_meeting_precision is None:
                best_meeting_precision = (float(threshold), metrics)
            else:
                _, cur = best_meeting_precision
                if metrics["recall_1"] > cur["recall_1"]:
                    best_meeting_precision = (float(threshold), metrics)
                elif metrics["recall_1"] == cur["recall_1"] and threshold > best_meeting_precision[0]:
                    # Tie-break toward higher threshold to reduce review burden.
                    best_meeting_precision = (float(threshold), metrics)

    if best_meeting_precision is not None:
        threshold, metrics = best_meeting_precision
        mode = "precision_constrained"
    else:
        threshold, metrics = best_recall_fallback if best_recall_fallback else (0.0, _binary_metrics(y_true, (scores >= 0.0).astype(int)))
        mode = "recall_fallback"

    # If the precision-constrained best misses target recall badly, choose explicit target-seeking fallback.
    if metrics["recall_1"] < target_recall and best_recall_fallback is not None:
        fb_threshold, fb_metrics = best_recall_fallback
        if fb_metrics["recall_1"] > metrics["recall_1"]:
            threshold, metrics = fb_threshold, fb_metrics
            mode = "target_recall_fallback"

    return float(threshold), metrics, mode


def _persist_threshold_policy(
    model_path: Path,
    threshold: float,
    review_margin: float,
    confidence_threshold: float,
    mode: str,
    min_precision: float,
    target_recall: float,
) -> None:
    """Attach threshold and review policy metadata to model artifact."""
    model_obj = joblib.load(model_path)

    policy = {
        "decision_threshold": float(threshold),
        "review_margin": float(review_margin),
        "confidence_threshold": float(confidence_threshold),
        "mode": mode,
        "target_class1_recall": float(target_recall),
        "min_class1_precision": float(min_precision),
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }

    if isinstance(model_obj, dict):
        model_obj["decision_threshold"] = float(threshold)
        model_obj["review_margin"] = float(review_margin)
        model_obj["confidence_threshold"] = float(confidence_threshold)
        model_obj["threshold_policy"] = policy
        joblib.dump(model_obj, model_path)
        return

    if isinstance(model_obj, Pipeline):
        wrapped = {
            "pipe": model_obj,
            "decision_threshold": float(threshold),
            "review_margin": float(review_margin),
            "confidence_threshold": float(confidence_threshold),
            "threshold_policy": policy,
        }
        joblib.dump(wrapped, model_path)
        return

    raise SystemExit("Cannot persist threshold policy: unsupported model artifact type")


def _evaluate_model(
    train_input: Path,
    model_path: Path,
    label_col: str,
    target_class1_recall: float,
    min_class1_precision: float,
    review_margin: float,
) -> dict[str, object]:
    labeled = _load_labeled(train_input, label_col)
    y = labeled[label_col].astype(int).values
    X, _ = build_features(labeled, "title", "description", "start", "location")

    groups = labeled["series_id"].fillna("").astype(str).values
    unique_groups = pd.Series(groups).nunique()
    unique_labels = pd.Series(y).nunique()

    pipe = _load_pipeline(model_path)

    split_mode = "full_dataset"
    if unique_groups >= 3 and unique_labels >= 2 and len(labeled) >= 20:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups))
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

    y_pred_default = pipe.predict(X_eval)
    default_acc = float(accuracy_score(y_eval, y_pred_default))
    default_cm = confusion_matrix(y_eval, y_pred_default)
    default_report = classification_report(y_eval, y_pred_default, digits=3)

    if hasattr(pipe, "decision_function"):
        decision_scores = np.asarray(pipe.decision_function(X_eval), dtype=float)
    else:
        # Fallback to default predictions if no decision function is available.
        decision_scores = np.asarray(y_pred_default, dtype=float)

    threshold, threshold_metrics, threshold_mode = _select_recall_threshold(
        y_true=np.asarray(y_eval, dtype=int),
        scores=decision_scores,
        target_recall=target_class1_recall,
        min_precision=min_class1_precision,
    )
    y_pred_threshold = (decision_scores >= threshold).astype(int)
    threshold_acc = float(accuracy_score(y_eval, y_pred_threshold))
    threshold_cm = confusion_matrix(y_eval, y_pred_threshold)
    threshold_report = classification_report(y_eval, y_pred_threshold, digits=3)

    needs_review = (np.abs(decision_scores - threshold) < review_margin).sum()
    review_rate = float(needs_review / len(y_eval)) if len(y_eval) else 0.0

    return {
        "split_mode": split_mode,
        "labeled_rows": int(len(labeled)),
        "eval_rows": int(len(y_eval)),
        "class_0": int((labeled[label_col].astype(int) == 0).sum()),
        "class_1": int((labeled[label_col].astype(int) == 1).sum()),
        "accuracy": default_acc,
        "confusion_matrix": default_cm,
        "classification_report": default_report,
        "decision_threshold": threshold,
        "threshold_mode": threshold_mode,
        "threshold_accuracy": threshold_acc,
        "threshold_confusion_matrix": threshold_cm,
        "threshold_classification_report": threshold_report,
        "threshold_metrics": threshold_metrics,
        "review_margin": float(review_margin),
        "review_rate": review_rate,
    }


def _write_report(
    report_dir: Path,
    run_started: datetime,
    prep_output: Path | None,
    review_output: Path | None,
    consolidated_path: Path,
    train_input: Path,
    model_path: Path,
    metrics: dict[str, object],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"retrain_evaluation_report_{ts}.md"

    cm = metrics["confusion_matrix"]
    cm_text = str(cm)

    report = f"""# Retrain Evaluation Report

- Run started (UTC): {run_started.isoformat()}
- Report generated (UTC): {datetime.now(UTC).isoformat()}

## Inputs and Artifacts

- Prepared canonical labeled dataset: {prep_output if prep_output else 'not found'}
- Prepared review queue: {review_output if review_output else 'not found'}
- Consolidated dataset: {consolidated_path}
- Training input used: {train_input}
- Model artifact: {model_path}

## Dataset Summary

- Labeled rows available: {metrics['labeled_rows']}
- Evaluation rows: {metrics['eval_rows']}
- Class 0 count: {metrics['class_0']}
- Class 1 count: {metrics['class_1']}
- Split mode: {metrics['split_mode']}

## Metrics

- Accuracy (default threshold=0.0): {metrics['accuracy']:.4f}
- Accuracy (optimized threshold={metrics['decision_threshold']:.4f}): {metrics['threshold_accuracy']:.4f}

## Threshold Policy

- Selection mode: {metrics['threshold_mode']}
- Decision threshold (class-1): {metrics['decision_threshold']:.4f}
- Review margin around threshold: {metrics['review_margin']:.4f}
- Estimated review rate on eval split: {metrics['review_rate']:.2%}
- Class-1 precision at threshold: {metrics['threshold_metrics']['precision_1']:.4f}
- Class-1 recall at threshold: {metrics['threshold_metrics']['recall_1']:.4f}

### Confusion Matrix

```
{cm_text}
```

### Classification Report

```
{metrics['classification_report']}
```

### Thresholded Confusion Matrix

```
{metrics['threshold_confusion_matrix']}
```

### Thresholded Classification Report

```
{metrics['threshold_classification_report']}
```
"""

    report_path.write_text(report, encoding="utf-8")
    return report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run prepare -> consolidate -> train -> evaluation report"
    )
    parser.add_argument(
        "--review-limit",
        type=int,
        default=200,
        help="Forwarded to prepare_retraining_dataset.py",
    )
    parser.add_argument(
        "--train-input",
        type=Path,
        default=BASE_DIR / "data" / "processed" / "consolidated_training_data.csv",
        help="Training CSV passed to svm_train_from_file.py",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl",
        help="Path to write trained model artifact",
    )
    parser.add_argument(
        "--label-col",
        default="label",
        help="Label column for post-train evaluation",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=BASE_DIR / "docs" / "reports",
        help="Directory to write markdown evaluation report",
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="Skip prepare_retraining_dataset.py stage",
    )
    parser.add_argument(
        "--skip-consolidate",
        action="store_true",
        help="Skip consolidate_training_data.py stage",
    )
    parser.add_argument(
        "--collapse-series",
        action="store_true",
        help="Forward --collapse-series to svm_train_from_file.py",
    )
    parser.add_argument(
        "--no-propagate-series-labels",
        action="store_true",
        help="Disable --propagate-series-labels for svm_train_from_file.py",
    )
    parser.add_argument(
        "--target-class1-recall",
        type=float,
        default=0.90,
        help="Target class-1 recall when selecting decision threshold",
    )
    parser.add_argument(
        "--min-class1-precision",
        type=float,
        default=0.70,
        help="Minimum class-1 precision constraint for threshold search",
    )
    parser.add_argument(
        "--review-margin",
        type=float,
        default=0.35,
        help="Decision-score margin around threshold that triggers needs_review",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.75,
        help="Confidence threshold persisted into model policy",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_started = datetime.now(UTC)

    py = sys.executable

    if not args.skip_prepare:
        prepare_cmd = [py, str(PREP_SCRIPT), "--review-limit", str(args.review_limit)]
        _run_step("prepare_retraining_dataset", prepare_cmd)

    if not args.skip_consolidate:
        consolidate_cmd = [py, str(CONSOLIDATE_SCRIPT)]
        _run_step("consolidate_training_data", consolidate_cmd)

    train_cmd = [
        py,
        str(TRAIN_SCRIPT),
        "--input",
        str(args.train_input),
        "--model-path",
        str(args.model_path),
        "--label",
        args.label_col,
    ]
    if not args.no_propagate_series_labels:
        train_cmd.append("--propagate-series-labels")
    if args.collapse_series:
        train_cmd.append("--collapse-series")

    _run_step("svm_train_from_file", train_cmd)

    metrics = _evaluate_model(
        train_input=args.train_input,
        model_path=args.model_path,
        label_col=args.label_col,
        target_class1_recall=args.target_class1_recall,
        min_class1_precision=args.min_class1_precision,
        review_margin=args.review_margin,
    )

    _persist_threshold_policy(
        model_path=args.model_path,
        threshold=float(metrics["decision_threshold"]),
        review_margin=args.review_margin,
        confidence_threshold=args.confidence_threshold,
        mode=str(metrics["threshold_mode"]),
        min_precision=args.min_class1_precision,
        target_recall=args.target_class1_recall,
    )

    prep_output = _latest("canonical_labeled_training_*.csv")
    review_output = _latest("review_queue_*.csv")
    consolidated_path = BASE_DIR / "data" / "processed" / "consolidated_training_data.csv"

    report_path = _write_report(
        report_dir=args.report_dir,
        run_started=run_started,
        prep_output=prep_output,
        review_output=review_output,
        consolidated_path=consolidated_path,
        train_input=args.train_input,
        model_path=args.model_path,
        metrics=metrics,
    )

    print("\nEnd-to-end retraining complete")
    print(f"  model: {args.model_path}")
    print(f"  report: {report_path}")
    print(f"  accuracy (default): {metrics['accuracy']:.4f}")
    print(
        "  threshold policy: "
        f"decision_threshold={metrics['decision_threshold']:.4f}, "
        f"class1_recall={metrics['threshold_metrics']['recall_1']:.4f}, "
        f"class1_precision={metrics['threshold_metrics']['precision_1']:.4f}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())