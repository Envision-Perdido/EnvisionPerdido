#!/usr/bin/env python3
"""Run end-to-end retraining with threshold tuning, diagnostics, and hard negatives."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.ml.svm_train_from_file import build_features, make_series_id
from scripts.ml.training_support import (
    binary_metrics,
    compute_confidence,
    ensure_source_column,
    select_threshold_from_sweep,
    threshold_sweep,
)


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

    for col in [
        "title",
        "description",
        "start",
        "location",
        "url",
        "uid",
        "source",
        "_source_file",
        "label_source",
    ]:
        if col not in labeled.columns:
            labeled[col] = ""

    labeled = ensure_source_column(labeled)

    if "series_id" not in labeled.columns:
        labeled["series_id"] = make_series_id(
            labeled,
            id_col="uid",
            url_col="url",
            title_col="title",
            loc_col="location",
        )

    labeled["series_id"] = labeled["series_id"].fillna("").astype(str)
    labeled["source"] = labeled["source"].fillna("unknown").astype(str)
    labeled["label_source"] = labeled["label_source"].fillna("").astype(str)
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


def _split_labeled(
    labeled: pd.DataFrame,
    label_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, str]:
    y = labeled[label_col].astype(int).to_numpy()
    indices = np.arange(len(labeled))
    groups = labeled["series_id"].fillna("").astype(str).to_numpy()

    unique_groups = pd.Series(groups).nunique()
    unique_labels = pd.Series(y).nunique()

    split_mode = "full_dataset"
    train_idx = indices
    eval_idx = indices

    if unique_groups >= 3 and unique_labels >= 2 and len(labeled) >= 20:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, eval_idx = next(splitter.split(indices, y, groups))
        split_mode = "group_shuffle_split"
    elif unique_labels >= 2 and len(labeled) >= 20:
        train_idx, eval_idx = train_test_split(
            indices,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )
        split_mode = "stratified_split"

    train_df = labeled.iloc[train_idx].copy()
    eval_df = labeled.iloc[eval_idx].copy()
    return train_df, eval_df, np.asarray(train_idx), np.asarray(eval_idx), split_mode


def _source_balance_summary(
    labeled: pd.DataFrame,
    label_col: str,
    max_unknown_source_rate: float,
    max_source_positive_rate_delta: float,
) -> dict[str, object]:
    eligible = labeled.copy()
    if "label_source" in eligible.columns:
        eligible = eligible[
            eligible["label_source"].fillna("").astype(str).str.strip() != "hard_negative_mining"
        ].copy()
    eligible = ensure_source_column(eligible)

    train_df, eval_df, _, _, split_mode = _split_labeled(eligible, label_col)
    counts = eligible["source"].value_counts()
    reviewable_sources = sorted(counts[counts >= 10].index.tolist())
    unknown_rate = float((eligible["source"] == "unknown").mean()) if len(eligible) else 0.0

    missing_sources: list[str] = []
    deltas: dict[str, float] = {}
    for source in reviewable_sources:
        in_train = source in set(train_df["source"])
        in_eval = source in set(eval_df["source"])
        if not in_train or not in_eval:
            missing_sources.append(source)
            continue

        train_rate = float(train_df.loc[train_df["source"] == source, label_col].astype(int).mean())
        eval_rate = float(eval_df.loc[eval_df["source"] == source, label_col].astype(int).mean())
        deltas[source] = abs(train_rate - eval_rate)

    max_delta = max(deltas.values()) if deltas else 0.0
    failures: list[str] = []
    if unknown_rate > max_unknown_source_rate:
        failures.append(
            f"unknown source rate {unknown_rate:.2%} exceeds limit {max_unknown_source_rate:.2%}"
        )
    if missing_sources:
        failures.append(
            "sources missing from train or eval split: " + ", ".join(sorted(missing_sources))
        )
    if max_delta > max_source_positive_rate_delta:
        failures.append(
            f"source positive-rate delta {max_delta:.3f} exceeds limit {max_source_positive_rate_delta:.3f}"
        )

    return {
        "passed": not failures,
        "split_mode": split_mode,
        "unknown_source_rate": unknown_rate,
        "reviewable_sources": reviewable_sources,
        "missing_sources": sorted(missing_sources),
        "positive_rate_delta_by_source": deltas,
        "max_positive_rate_delta": max_delta,
        "failures": failures,
    }


def _top_coefficients(pipe: Pipeline, top_n: int = 10) -> dict[str, list[dict[str, float | str]]]:
    clf = pipe.named_steps.get("clf")
    pre = pipe.named_steps.get("pre")
    if clf is None or pre is None or not hasattr(clf, "coef_"):
        return {"positive": [], "negative": []}

    try:
        names = np.asarray(pre.get_feature_names_out())
    except Exception:
        names = np.array([f"feature_{i}" for i in range(clf.coef_.shape[1])])

    coefs = np.asarray(clf.coef_[0], dtype=float)
    n = min(len(names), len(coefs))
    names = names[:n]
    coefs = coefs[:n]

    pos_idx = np.argsort(coefs)[::-1][:top_n]
    neg_idx = np.argsort(coefs)[:top_n]
    return {
        "positive": [
            {"feature": str(names[i]), "coefficient": float(coefs[i])}
            for i in pos_idx
        ],
        "negative": [
            {"feature": str(names[i]), "coefficient": float(coefs[i])}
            for i in neg_idx
        ],
    }


def _evaluate_model(
    train_input: Path,
    model_path: Path,
    label_col: str,
    target_class1_recall: float,
    min_class1_precision: float,
    review_margin: float,
    confidence_threshold: float,
    max_unknown_source_rate: float,
    max_source_positive_rate_delta: float,
) -> dict[str, object]:
    labeled = _load_labeled(train_input, label_col)
    train_df, eval_df, train_idx, eval_idx, split_mode = _split_labeled(labeled, label_col)
    pipe = _load_pipeline(model_path)

    y_train = train_df[label_col].astype(int).to_numpy()
    y_eval = eval_df[label_col].astype(int).to_numpy()
    X_train, _ = build_features(train_df, "title", "description", "start", "location")
    X_eval, _ = build_features(eval_df, "title", "description", "start", "location")

    y_pred_default = np.asarray(pipe.predict(X_eval), dtype=int)
    if hasattr(pipe, "decision_function"):
        decision_scores = np.asarray(pipe.decision_function(X_eval), dtype=float).ravel()
    else:
        decision_scores = y_pred_default.astype(float)

    sweep_df = threshold_sweep(
        y_true=y_eval,
        scores=decision_scores,
        confidence_threshold=confidence_threshold,
        review_margin=review_margin,
    )
    threshold, threshold_summary, threshold_mode = select_threshold_from_sweep(
        sweep_df=sweep_df,
        target_recall=target_class1_recall,
        min_precision=min_class1_precision,
    )
    y_pred_threshold = (decision_scores >= threshold).astype(int)

    default_metrics = binary_metrics(y_eval, y_pred_default)
    threshold_metrics = binary_metrics(y_eval, y_pred_threshold)
    default_cm = confusion_matrix(y_eval, y_pred_default)
    threshold_cm = confusion_matrix(y_eval, y_pred_threshold)
    default_report = classification_report(y_eval, y_pred_default, digits=3)
    threshold_report = classification_report(y_eval, y_pred_threshold, digits=3)
    review_rate = float(
        np.mean(
            (compute_confidence(decision_scores) < confidence_threshold)
            | (np.abs(decision_scores - threshold) < review_margin)
        )
    )

    source_balance = _source_balance_summary(
        labeled=labeled,
        label_col=label_col,
        max_unknown_source_rate=max_unknown_source_rate,
        max_source_positive_rate_delta=max_source_positive_rate_delta,
    )

    return {
        "pipe": pipe,
        "labeled": labeled,
        "train_df": train_df,
        "eval_df": eval_df,
        "train_idx": train_idx,
        "eval_idx": eval_idx,
        "X_train": X_train,
        "X_eval": X_eval,
        "y_train": y_train,
        "y_eval": y_eval,
        "decision_scores": decision_scores,
        "y_pred_default": y_pred_default,
        "y_pred_threshold": y_pred_threshold,
        "split_mode": split_mode,
        "labeled_rows": int(len(labeled)),
        "eval_rows": int(len(y_eval)),
        "class_0": int((labeled[label_col].astype(int) == 0).sum()),
        "class_1": int((labeled[label_col].astype(int) == 1).sum()),
        "accuracy": default_metrics["accuracy"],
        "confusion_matrix": default_cm,
        "classification_report": default_report,
        "decision_threshold": threshold,
        "threshold_mode": threshold_mode,
        "threshold_accuracy": threshold_metrics["accuracy"],
        "threshold_confusion_matrix": threshold_cm,
        "threshold_classification_report": threshold_report,
        "threshold_metrics": threshold_metrics,
        "threshold_selection_summary": {
            **threshold_summary,
            "mode": threshold_mode,
            "target_class1_recall": float(target_class1_recall),
            "min_class1_precision": float(min_class1_precision),
        },
        "review_margin": float(review_margin),
        "confidence_threshold": float(confidence_threshold),
        "review_rate": review_rate,
        "sweep_df": sweep_df,
        "source_balance_summary": source_balance,
        "top_coefficients": _top_coefficients(pipe),
    }


def _mine_hard_negatives(
    eval_df: pd.DataFrame,
    y_eval: np.ndarray,
    decision_scores: np.ndarray,
    decision_threshold: float,
    top_n: int,
    multiplier: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    inspected = eval_df.copy()
    inspected["decision_score"] = np.asarray(decision_scores, dtype=float)
    inspected["abs_confidence"] = np.abs(inspected["decision_score"])
    inspected["predicted_label"] = (inspected["decision_score"] >= decision_threshold).astype(int)
    inspected["true_label"] = np.asarray(y_eval, dtype=int)

    false_positives = inspected[
        (inspected["true_label"] == 0) & (inspected["predicted_label"] == 1)
    ].copy()

    if "label_source" in false_positives.columns and false_positives["label_source"].notna().any():
        false_positives = false_positives[
            false_positives["label_source"].fillna("").astype(str).str.strip() != "model_prediction"
        ].copy()

    false_positives = false_positives.sort_values("abs_confidence", ascending=False).head(top_n)
    if false_positives.empty or multiplier <= 0:
        return false_positives, pd.DataFrame(columns=eval_df.columns)

    mined = pd.concat([false_positives[eval_df.columns].copy() for _ in range(multiplier)], ignore_index=True)
    mined["label"] = 0
    mined["label_source"] = "hard_negative_mining"
    return false_positives.reset_index(drop=True), mined


def _write_augmented_training_input(
    original_input: Path,
    hard_negative_rows: pd.DataFrame,
) -> Path:
    base_df = pd.read_csv(original_input)
    if hard_negative_rows.empty:
        return original_input

    augmented = pd.concat([base_df, hard_negative_rows], ignore_index=True, sort=False)
    augmented = ensure_source_column(augmented)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = BASE_DIR / "data" / "processed" / f"hard_negative_augmented_{ts}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    augmented.to_csv(output_path, index=False)
    return output_path


def _persist_threshold_policy(
    model_path: Path,
    threshold: float,
    review_margin: float,
    confidence_threshold: float,
    selection_summary: dict[str, object],
    source_balance_summary: dict[str, object],
    diagnostics_output_dir: str,
) -> None:
    """Attach threshold, diagnostics, and source-balance metadata to model artifact."""
    model_obj = joblib.load(model_path)

    payload = {
        "decision_threshold": float(threshold),
        "review_margin": float(review_margin),
        "confidence_threshold": float(confidence_threshold),
        "threshold_selection_summary": selection_summary,
        "diagnostics_output_dir": diagnostics_output_dir,
        "source_balance_summary": source_balance_summary,
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }

    if isinstance(model_obj, dict):
        model_obj.update(payload)
        model_obj["threshold_policy"] = payload
        joblib.dump(model_obj, model_path)
        return

    if isinstance(model_obj, Pipeline):
        wrapped = {"pipe": model_obj, **payload, "threshold_policy": payload}
        joblib.dump(wrapped, model_path)
        return

    raise SystemExit("Cannot persist threshold policy: unsupported model artifact type")


def _run_diagnostics(metrics: dict[str, object], output_dir: Path) -> Path:
    from analysis.svm_diagnostics import main as run_svm_diagnostics

    output_dir.mkdir(parents=True, exist_ok=True)
    run_svm_diagnostics(
        model=metrics["pipe"],
        X_test=metrics["X_eval"],
        y_test=metrics["y_eval"],
        raw_data_df=metrics["eval_df"],
        X_train=metrics["X_train"],
        y_train=metrics["y_train"],
        output_dir=output_dir,
        top_n=20,
        decision_threshold=float(metrics["decision_threshold"]),
    )
    return output_dir


def _format_feature_block(rows: list[dict[str, float | str]]) -> str:
    if not rows:
        return "- none"
    return "\n".join(
        f"- {row['feature']}: {float(row['coefficient']):.4f}"
        for row in rows
    )


def _format_source_balance(summary: dict[str, object]) -> str:
    lines = [
        f"- Passed: {summary['passed']}",
        f"- Unknown source rate: {summary['unknown_source_rate']:.2%}",
        f"- Split mode: {summary['split_mode']}",
    ]
    if summary["reviewable_sources"]:
        lines.append("- Reviewable sources: " + ", ".join(summary["reviewable_sources"]))
    if summary["missing_sources"]:
        lines.append("- Missing sources: " + ", ".join(summary["missing_sources"]))
    if summary["positive_rate_delta_by_source"]:
        for source, delta in summary["positive_rate_delta_by_source"].items():
            lines.append(f"- Positive-rate delta ({source}): {delta:.3f}")
    if summary["failures"]:
        for failure in summary["failures"]:
            lines.append(f"- Failure: {failure}")
    return "\n".join(lines)


def _write_report(
    report_dir: Path,
    run_started: datetime,
    prep_output: Path | None,
    review_output: Path | None,
    consolidated_path: Path,
    train_input: Path,
    model_path: Path,
    first_pass: dict[str, object],
    final_metrics: dict[str, object],
    hard_negative_candidates: pd.DataFrame,
    augmented_train_input: Path,
    diagnostics_dir: Path,
    promoted: bool,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"retrain_evaluation_report_{ts}.md"

    report = f"""# Retrain Evaluation Report

- Run started (UTC): {run_started.isoformat()}
- Report generated (UTC): {datetime.now(UTC).isoformat()}
- Model promoted: {promoted}

## Inputs and Artifacts

- Prepared canonical labeled dataset: {prep_output if prep_output else 'not found'}
- Prepared review queue: {review_output if review_output else 'not found'}
- Consolidated dataset: {consolidated_path}
- Base training input used: {train_input}
- Final training input used: {augmented_train_input}
- Model artifact: {model_path}
- Diagnostics output: {diagnostics_dir}

## Dataset Summary

- Labeled rows available: {final_metrics['labeled_rows']}
- Evaluation rows: {final_metrics['eval_rows']}
- Class 0 count: {final_metrics['class_0']}
- Class 1 count: {final_metrics['class_1']}
- Split mode: {final_metrics['split_mode']}
- Hard-negative candidates mined: {len(hard_negative_candidates)}

## First-Pass Threshold Policy

- Decision threshold: {first_pass['decision_threshold']:.4f}
- Selection mode: {first_pass['threshold_mode']}
- Class-1 precision: {first_pass['threshold_metrics']['precision_1']:.4f}
- Class-1 recall: {first_pass['threshold_metrics']['recall_1']:.4f}

## Final Threshold Policy

- Selection mode: {final_metrics['threshold_mode']}
- Decision threshold (class-1): {final_metrics['decision_threshold']:.4f}
- Review margin around threshold: {final_metrics['review_margin']:.4f}
- Confidence threshold: {final_metrics['confidence_threshold']:.4f}
- Estimated review rate on eval split: {final_metrics['review_rate']:.2%}
- Class-1 precision at threshold: {final_metrics['threshold_metrics']['precision_1']:.4f}
- Class-1 recall at threshold: {final_metrics['threshold_metrics']['recall_1']:.4f}

## Metrics

- Accuracy (default threshold=0.0): {final_metrics['accuracy']:.4f}
- Accuracy (optimized threshold={final_metrics['decision_threshold']:.4f}): {final_metrics['threshold_accuracy']:.4f}

### Default Confusion Matrix

```
{final_metrics['confusion_matrix']}
```

### Default Classification Report

```
{final_metrics['classification_report']}
```

### Thresholded Confusion Matrix

```
{final_metrics['threshold_confusion_matrix']}
```

### Thresholded Classification Report

```
{final_metrics['threshold_classification_report']}
```

## Source Balance Gate

{_format_source_balance(final_metrics['source_balance_summary'])}

## Top Positive Coefficients

{_format_feature_block(final_metrics['top_coefficients']['positive'])}

## Top Negative Coefficients

{_format_feature_block(final_metrics['top_coefficients']['negative'])}
"""

    report_path.write_text(report, encoding="utf-8")
    return report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run prepare -> consolidate -> train -> hard-negative retrain -> diagnostics"
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
        help="Final promoted model artifact path",
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
    parser.add_argument(
        "--hard-negative-top-n",
        type=int,
        default=25,
        help="Maximum tuned-threshold false positives to mine into hard negatives",
    )
    parser.add_argument(
        "--hard-negative-multiplier",
        type=int,
        default=3,
        help="How many extra copies of each mined hard negative to append",
    )
    parser.add_argument(
        "--max-unknown-source-rate",
        type=float,
        default=0.20,
        help="Maximum allowed fraction of labeled rows with source=unknown",
    )
    parser.add_argument(
        "--max-source-positive-rate-delta",
        type=float,
        default=0.20,
        help="Maximum allowed train/eval positive-rate delta for any well-represented source",
    )
    return parser


def _train_model(
    train_input: Path,
    model_path: Path,
    label_col: str,
    collapse_series: bool,
    no_propagate_series_labels: bool,
) -> None:
    py = sys.executable
    train_cmd = [
        py,
        str(TRAIN_SCRIPT),
        "--input",
        str(train_input),
        "--model-path",
        str(model_path),
        "--label",
        label_col,
    ]
    if not no_propagate_series_labels:
        train_cmd.append("--propagate-series-labels")
    if collapse_series:
        train_cmd.append("--collapse-series")
    _run_step("svm_train_from_file", train_cmd)


def main() -> int:
    args = build_parser().parse_args()
    run_started = datetime.now(UTC)
    candidate_model_path = args.model_path.with_name(
        f"{args.model_path.stem}_candidate{args.model_path.suffix}"
    )
    diagnostics_dir = (
        BASE_DIR
        / "output"
        / "analytics"
        / f"retrain_diagnostics_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    )

    py = sys.executable

    if not args.skip_prepare:
        prepare_cmd = [py, str(PREP_SCRIPT), "--review-limit", str(args.review_limit)]
        _run_step("prepare_retraining_dataset", prepare_cmd)

    if not args.skip_consolidate:
        consolidate_cmd = [py, str(CONSOLIDATE_SCRIPT)]
        _run_step("consolidate_training_data", consolidate_cmd)

    _train_model(
        train_input=args.train_input,
        model_path=candidate_model_path,
        label_col=args.label_col,
        collapse_series=args.collapse_series,
        no_propagate_series_labels=args.no_propagate_series_labels,
    )

    first_pass = _evaluate_model(
        train_input=args.train_input,
        model_path=candidate_model_path,
        label_col=args.label_col,
        target_class1_recall=args.target_class1_recall,
        min_class1_precision=args.min_class1_precision,
        review_margin=args.review_margin,
        confidence_threshold=args.confidence_threshold,
        max_unknown_source_rate=args.max_unknown_source_rate,
        max_source_positive_rate_delta=args.max_source_positive_rate_delta,
    )

    hard_negative_candidates, hard_negative_rows = _mine_hard_negatives(
        eval_df=first_pass["eval_df"],
        y_eval=first_pass["y_eval"],
        decision_scores=first_pass["decision_scores"],
        decision_threshold=float(first_pass["decision_threshold"]),
        top_n=args.hard_negative_top_n,
        multiplier=args.hard_negative_multiplier,
    )
    final_train_input = _write_augmented_training_input(args.train_input, hard_negative_rows)

    if not hard_negative_rows.empty:
        _train_model(
            train_input=final_train_input,
            model_path=candidate_model_path,
            label_col=args.label_col,
            collapse_series=args.collapse_series,
            no_propagate_series_labels=args.no_propagate_series_labels,
        )

    final_metrics = _evaluate_model(
        train_input=final_train_input,
        model_path=candidate_model_path,
        label_col=args.label_col,
        target_class1_recall=args.target_class1_recall,
        min_class1_precision=args.min_class1_precision,
        review_margin=args.review_margin,
        confidence_threshold=args.confidence_threshold,
        max_unknown_source_rate=args.max_unknown_source_rate,
        max_source_positive_rate_delta=args.max_source_positive_rate_delta,
    )

    try:
        diagnostics_output = _run_diagnostics(final_metrics, diagnostics_dir)
    except Exception as exc:
        raise SystemExit(f"Diagnostics gate failed: {exc}") from exc

    _persist_threshold_policy(
        model_path=candidate_model_path,
        threshold=float(final_metrics["decision_threshold"]),
        review_margin=args.review_margin,
        confidence_threshold=args.confidence_threshold,
        selection_summary=final_metrics["threshold_selection_summary"],
        source_balance_summary=final_metrics["source_balance_summary"],
        diagnostics_output_dir=str(diagnostics_output),
    )

    gate_failures: list[str] = []
    if final_metrics["threshold_metrics"]["precision_1"] < args.min_class1_precision:
        gate_failures.append(
            "class-1 precision "
            f"{final_metrics['threshold_metrics']['precision_1']:.4f} "
            f"is below minimum {args.min_class1_precision:.4f}"
        )
    if not final_metrics["source_balance_summary"]["passed"]:
        gate_failures.extend(final_metrics["source_balance_summary"]["failures"])

    promoted = False
    report_model_path = candidate_model_path
    if not gate_failures:
        candidate_model_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_model_path.replace(args.model_path)
        promoted = True
        report_model_path = args.model_path

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
        model_path=report_model_path,
        first_pass=first_pass,
        final_metrics=final_metrics,
        hard_negative_candidates=hard_negative_candidates,
        augmented_train_input=final_train_input,
        diagnostics_dir=diagnostics_output,
        promoted=promoted,
    )

    print("\nEnd-to-end retraining complete")
    print(f"  candidate model: {report_model_path}")
    print(f"  report: {report_path}")
    print(f"  diagnostics: {diagnostics_output}")
    print(
        "  threshold policy: "
        f"decision_threshold={final_metrics['decision_threshold']:.4f}, "
        f"class1_recall={final_metrics['threshold_metrics']['recall_1']:.4f}, "
        f"class1_precision={final_metrics['threshold_metrics']['precision_1']:.4f}"
    )

    if gate_failures:
        raise SystemExit("Deployment gate failed: " + "; ".join(gate_failures))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
