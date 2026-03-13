#!/usr/bin/env python3
"""Visualization and debugging tools for the SVM event classifier.

This module provides tools to:
- Visualize feature importance (permutation-based)
- Plot confusion matrices
- Inspect model predictions and confidence scores
- Compare pipeline transformations

Usage:
    python scripts/dev/visualize_pipeline.py --mode importance --output-dir output/
    python scripts/dev/visualize_pipeline.py --mode confusion --output-dir output/
    python scripts/dev/visualize_pipeline.py --mode pipeline-stats --output-dir output/
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay,
    precision_recall_curve,
    auc,
)

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
MODEL_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 10


def load_artifacts() -> Tuple[Optional[object], Optional[object]]:
    """Load trained model and vectorizer.

    Returns:
        Tuple of (model, vectorizer), or (None, None) if not found.
    """
    if not MODEL_PATH.exists():
        print(f"❌ Model not found at {MODEL_PATH}")
        return None, None
    
    if not VECTORIZER_PATH.exists():
        print(f"❌ Vectorizer not found at {VECTORIZER_PATH}")
        return None, None
    
    try:
        model = joblib.load(MODEL_PATH)
        vectorizer = joblib.load(VECTORIZER_PATH)
        print(f"✅ Loaded model and vectorizer")
        return model, vectorizer
    except Exception as e:
        print(f"❌ Failed to load artifacts: {e}")
        return None, None


def plot_feature_importance(
    model: object,
    vectorizer: object,
    X_test: object,
    y_test: np.ndarray,
    output_dir: Path,
    top_n: int = 20,
) -> pd.DataFrame:
    """Compute and plot permutation importance for top N features.

    Args:
        model: Trained classifier
        vectorizer: TfidfVectorizer
        X_test: Test feature matrix (sparse)
        y_test: Test labels
        output_dir: Directory to save plot
        top_n: Number of top features to display

    Returns:
        DataFrame with feature importance statistics.
    """
    print(f"\n📊 Computing permutation importance for top {top_n} features...")
    
    try:
        result = permutation_importance(
            model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1
        )
    except Exception as e:
        print(f"❌ Failed to compute permutation importance: {e}")
        return None

    # Get feature names from vectorizer
    if hasattr(vectorizer, 'get_feature_names_out'):
        feature_names = vectorizer.get_feature_names_out()
    else:
        feature_names = vectorizer.get_feature_names()

    # Sort by importance
    indices = np.argsort(result.importances_mean)[-top_n:]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(range(len(indices)), result.importances_mean[indices], color="steelblue")
    ax.set_yticks(range(len(indices)))
    ax.set_yticklabels(feature_names[indices])
    ax.set_xlabel("Permutation Importance (Mean Decrease in Accuracy)", fontsize=11)
    ax.set_title(f"Top {top_n} Feature Importance (SVM Classifier)", fontsize=12, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    output_path = output_dir / "feature_importance.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✅ Saved feature importance plot to {output_path}")
    plt.close()

    # Create DataFrame for export
    importance_df = pd.DataFrame({
        "feature": feature_names[indices],
        "importance_mean": result.importances_mean[indices],
        "importance_std": result.importances_std[indices],
    }).sort_values("importance_mean", ascending=False)

    # Save as CSV
    csv_path = output_dir / "feature_importance.csv"
    importance_df.to_csv(csv_path, index=False)
    print(f"✅ Saved feature importance CSV to {csv_path}")

    return importance_df


def plot_confusion_matrix(
    model: object, X_test: object, y_test: np.ndarray, output_dir: Path
) -> None:
    """Plot confusion matrix for classification performance.

    Args:
        model: Trained classifier
        X_test: Test feature matrix
        y_test: Test labels
        output_dir: Directory to save plot
    """
    print(f"\n📊 Creating confusion matrix...")

    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)

    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Non-Community", "Community"])
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    ax.set_title("Classification Confusion Matrix", fontsize=12, fontweight="bold")
    plt.tight_layout()

    output_path = output_dir / "confusion_matrix.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✅ Saved confusion matrix to {output_path}")
    plt.close()


def plot_precision_recall(
    model: object, X_test: object, y_test: np.ndarray, output_dir: Path
) -> None:
    """Plot precision-recall curve.

    Args:
        model: Trained classifier
        X_test: Test feature matrix
        y_test: Test labels
        output_dir: Directory to save plot
    """
    print(f"\n📊 Creating precision-recall curve...")

    try:
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X_test)
        elif hasattr(model, "predict_proba"):
            scores = model.predict_proba(X_test)[:, 1]
        else:
            print("⚠️  Model does not support probability/decision scores")
            return

        precision, recall, _ = precision_recall_curve(y_test, scores)
        pr_auc = auc(recall, precision)

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(recall, precision, color="steelblue", lw=2, label=f"PR Curve (AUC={pr_auc:.3f})")
        ax.set_xlabel("Recall", fontsize=11)
        ax.set_ylabel("Precision", fontsize=11)
        ax.set_title("Precision-Recall Curve", fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3)
        plt.tight_layout()

        output_path = output_dir / "precision_recall_curve.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✅ Saved precision-recall curve to {output_path}")
        plt.close()
    except Exception as e:
        print(f"❌ Failed to create precision-recall curve: {e}")


def generate_classification_report(
    model: object, X_test: object, y_test: np.ndarray, output_dir: Path
) -> str:
    """Generate detailed classification report.

    Args:
        model: Trained classifier
        X_test: Test feature matrix
        y_test: Test labels
        output_dir: Directory to save report

    Returns:
        Report string.
    """
    print(f"\n📊 Generating classification report...")

    y_pred = model.predict(X_test)
    report = classification_report(
        y_test,
        y_pred,
        target_names=["Non-Community", "Community"],
        digits=3,
    )

    # Save to text file
    report_path = output_dir / "classification_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"✅ Saved classification report to {report_path}")

    return report


def summarize_model_and_data(
    model: object, vectorizer: object, X_test: object, y_test: np.ndarray, output_dir: Path
) -> None:
    """Generate a summary of model architecture and test data.

    Args:
        model: Trained model
        vectorizer: Vectorizer
        X_test: Test feature matrix
        y_test: Test labels
        output_dir: Directory to save summary
    """
    print(f"\n📊 Generating model summary...")

    summary = {
        "model_type": str(type(model).__name__),
        "model_path": str(MODEL_PATH),
        "vectorizer_type": str(type(vectorizer).__name__),
        "vectorizer_path": str(VECTORIZER_PATH),
        "test_set_size": len(y_test),
        "test_set_positive_ratio": float(y_test.sum() / len(y_test)),
        "test_set_negatives": int((1 - y_test).sum()),
        "test_set_positives": int(y_test.sum()),
        "feature_matrix_shape": X_test.shape if hasattr(X_test, 'shape') else None,
        "feature_matrix_type": type(X_test).__name__,
    }

    if hasattr(vectorizer, 'get_feature_names_out'):
        feature_names = vectorizer.get_feature_names_out()
    elif hasattr(vectorizer, 'get_feature_names'):
        feature_names = vectorizer.get_feature_names()
    else:
        feature_names = []

    summary["n_features"] = len(feature_names)

    # Save summary
    summary_path = output_dir / "model_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Saved model summary to {summary_path}")

    # Print summary
    print("\n📋 Model Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description="Visualize and debug the SVM event classifier pipeline."
    )
    parser.add_argument(
        "--mode",
        default="all",
        choices=["all", "importance", "confusion", "precision-recall", "report", "summary"],
        help="Visualization mode",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "output" / "visualizations",
        help="Output directory for plots",
    )
    parser.add_argument(
        "--test-data",
        type=Path,
        help="Path to test data CSV (optional, for standalone analysis)",
    )
    parser.add_argument(
        "--top-features",
        type=int,
        default=20,
        help="Number of top features to display (default: 20)",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load model and vectorizer
    model, vectorizer = load_artifacts()
    if model is None or vectorizer is None:
        print("❌ Failed to load artifacts. Exiting.")
        return

    # Load test data if provided
    if args.test_data:
        try:
            df_test = pd.read_csv(args.test_data)
            print(f"✅ Loaded test data from {args.test_data}")

            # Assume CSV has 'text' and 'label' columns
            texts = df_test.get("text", df_test.iloc[:, 0]).tolist()
            y_test = df_test.get("label", df_test.iloc[:, -1]).values
            X_test = vectorizer.transform(texts)
        except Exception as e:
            print(f"❌ Failed to load test data: {e}")
            X_test = None
            y_test = None
    else:
        print("⚠️  No test data provided. Some visualizations will be skipped.")
        print("   Use --test-data <path> to provide test data CSV.")
        X_test = None
        y_test = None

    # Run selected visualizations
    if args.mode in ["all", "summary"]:
        if X_test is not None and y_test is not None:
            summarize_model_and_data(model, vectorizer, X_test, y_test, args.output_dir)

    if X_test is not None and y_test is not None:
        if args.mode in ["all", "importance"]:
            plot_feature_importance(model, vectorizer, X_test, y_test, args.output_dir, args.top_features)

        if args.mode in ["all", "confusion"]:
            plot_confusion_matrix(model, X_test, y_test, args.output_dir)

        if args.mode in ["all", "precision-recall"]:
            plot_precision_recall(model, X_test, y_test, args.output_dir)

        if args.mode in ["all", "report"]:
            report = generate_classification_report(model, X_test, y_test, args.output_dir)
            print("\n" + report)

    print(f"\n✅ All visualizations saved to {args.output_dir}")


if __name__ == "__main__":
    main()
