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


def _evaluate_model(
    train_input: Path,
    model_path: Path,
    label_col: str,
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

    y_pred = pipe.predict(X_eval)
    acc = float(accuracy_score(y_eval, y_pred))
    cm = confusion_matrix(y_eval, y_pred)
    report = classification_report(y_eval, y_pred, digits=3)

    return {
        "split_mode": split_mode,
        "labeled_rows": int(len(labeled)),
        "eval_rows": int(len(y_eval)),
        "class_0": int((labeled[label_col].astype(int) == 0).sum()),
        "class_1": int((labeled[label_col].astype(int) == 1).sum()),
        "accuracy": acc,
        "confusion_matrix": cm,
        "classification_report": report,
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

- Accuracy: {metrics['accuracy']:.4f}

### Confusion Matrix

```
{cm_text}
```

### Classification Report

```
{metrics['classification_report']}
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
    print(f"  accuracy: {metrics['accuracy']:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())