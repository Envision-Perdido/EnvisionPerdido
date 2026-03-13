#!/usr/bin/env python3
"""Profiling and optimization tools for the event classification inference pipeline.

Measures inference speed, identifies bottlenecks, and provides recommendations for
optimization. Includes batch inference capabilities for efficient processing.

Usage:
    python scripts/dev/profile_inference.py --samples 100 --runs 10
    python scripts/dev/profile_inference.py --profile-cprofile --samples 50
"""

import argparse
import cProfile
import pstats
import time
from io import StringIO
from pathlib import Path
from typing import List

import joblib
import numpy as np

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
MODEL_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"


def load_artifacts():
    """Load trained model and vectorizer."""
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        print(f"❌ Model or vectorizer not found")
        return None, None

    try:
        model = joblib.load(MODEL_PATH)
        vectorizer = joblib.load(VECTORIZER_PATH)
        print(f"✅ Loaded model and vectorizer")
        return model, vectorizer
    except Exception as e:
        print(f"❌ Failed to load artifacts: {e}")
        return None, None


def generate_sample_texts(n_samples: int = 100) -> List[str]:
    """Generate sample event descriptions for profiling.

    Args:
        n_samples: Number of samples to generate

    Returns:
        List of sample text strings.
    """
    titles = [
        "Community Center Meeting",
        "Summer Music Festival",
        "Beach Cleanup Day",
        "Farmer's Market Opening",
        "Youth Sports Tournament",
        "Library Book Club",
        "Church Charity Event",
        "Park Picnic Gathering",
        "School Fundraiser Dinner",
        "Art Exhibition Opening",
    ]

    descriptions = [
        "Join us for a fun community gathering with music and refreshments",
        "Annual celebration featuring local artisans and performers",
        "Help clean our beautiful beaches and local parks",
        "Fresh produce directly from local farmers",
        "Youth compete in various athletic competitions",
        "Monthly discussion of featured books",
        "Charity event supporting local causes",
        "Bring your family for food and games",
        "Help support our school programs",
        "View works from regional artists",
    ]

    samples = []
    for i in range(n_samples):
        title = titles[i % len(titles)]
        description = descriptions[i % len(descriptions)]
        text = f"{title}. {description}"
        samples.append(text)

    return samples


def profile_vectorization(vectorizer, texts: List[str], n_runs: int = 10) -> dict:
    """Profile the vectorization step.

    Args:
        vectorizer: TfidfVectorizer
        texts: List of sample texts
        n_runs: Number of runs for averaging

    Returns:
        Dictionary with profiling results.
    """
    print(f"\n⏱️  Profiling vectorization ({n_runs} runs, {len(texts)} samples each)...")

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        X = vectorizer.transform(texts)
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)
    return {
        "vectorization_mean_ms": float(times.mean() * 1000),
        "vectorization_median_ms": float(np.median(times) * 1000),
        "vectorization_std_ms": float(times.std() * 1000),
        "vectorization_min_ms": float(times.min() * 1000),
        "vectorization_max_ms": float(times.max() * 1000),
        "vectorization_per_sample_ms": float(times.mean() * 1000 / len(texts)),
    }


def profile_prediction(model, X, n_runs: int = 10) -> dict:
    """Profile the prediction step.

    Args:
        model: Trained classifier
        X: Feature matrix (typically sparse)
        n_runs: Number of runs for averaging

    Returns:
        Dictionary with profiling results.
    """
    print(f"\n⏱️  Profiling prediction ({n_runs} runs)...")

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        predictions = model.predict(X)
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)
    return {
        "prediction_mean_ms": float(times.mean() * 1000),
        "prediction_median_ms": float(np.median(times) * 1000),
        "prediction_std_ms": float(times.std() * 1000),
        "prediction_min_ms": float(times.min() * 1000),
        "prediction_max_ms": float(times.max() * 1000),
        "n_samples": X.shape[0] if hasattr(X, 'shape') else None,
        "prediction_per_sample_ms": float(times.mean() * 1000 / X.shape[0]) if hasattr(X, 'shape') else None,
    }


def profile_decision_function(model, X, n_runs: int = 10) -> dict:
    """Profile the decision function (distance from hyperplane).

    Args:
        model: Trained classifier
        X: Feature matrix
        n_runs: Number of runs for averaging

    Returns:
        Dictionary with profiling results.
    """
    if not hasattr(model, "decision_function"):
        return {}

    print(f"\n⏱️  Profiling decision function ({n_runs} runs)...")

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        scores = model.decision_function(X)
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)
    return {
        "decision_function_mean_ms": float(times.mean() * 1000),
        "decision_function_median_ms": float(np.median(times) * 1000),
        "decision_function_per_sample_ms": float(times.mean() * 1000 / X.shape[0]) if hasattr(X, 'shape') else None,
    }


def profile_full_pipeline(
    model, vectorizer, texts: List[str], n_runs: int = 5
) -> dict:
    """Profile the complete inference pipeline end-to-end.

    Args:
        model: Trained classifier
        vectorizer: TfidfVectorizer
        texts: List of sample texts
        n_runs: Number of runs for averaging

    Returns:
        Dictionary with profiling results.
    """
    print(f"\n⏱️  Profiling full pipeline ({n_runs} runs, {len(texts)} samples each)...")

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        X = vectorizer.transform(texts)
        predictions = model.predict(X)
        scores = model.decision_function(X) if hasattr(model, "decision_function") else None
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)
    return {
        "full_pipeline_mean_ms": float(times.mean() * 1000),
        "full_pipeline_median_ms": float(np.median(times) * 1000),
        "full_pipeline_std_ms": float(times.std() * 1000),
        "full_pipeline_per_sample_ms": float(times.mean() * 1000 / len(texts)),
    }


def profile_batch_inference(
    model, vectorizer, texts: List[str], batch_size: int = 100
) -> dict:
    """Profile batch inference at different batch sizes.

    Args:
        model: Trained classifier
        vectorizer: TfidfVectorizer
        texts: List of sample texts
        batch_size: Batch size to test

    Returns:
        Dictionary with batch profiling results.
    """
    print(f"\n⏱️  Profiling batch inference (batch_size={batch_size})...")

    start = time.perf_counter()

    all_predictions = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        X = vectorizer.transform(batch)
        preds = model.predict(X)
        all_predictions.extend(preds)

    end = time.perf_counter()
    total_time_ms = (end - start) * 1000

    return {
        "batch_size": batch_size,
        "n_batches": (len(texts) + batch_size - 1) // batch_size,
        "total_time_ms": float(total_time_ms),
        "per_sample_ms": float(total_time_ms / len(texts)),
    }


def profile_cprofile(model, vectorizer, texts: List[str]) -> str:
    """Profile using cProfile for detailed function-level statistics.

    Args:
        model: Trained classifier
        vectorizer: TfidfVectorizer
        texts: List of sample texts

    Returns:
        profiling report as string
    """
    print(f"\n⏱️  Running cProfile analysis ({len(texts)} samples)...")

    pr = cProfile.Profile()
    pr.enable()

    # Vectorize
    X = vectorizer.transform(texts)
    # Predict
    predictions = model.predict(X)
    # Decision scores
    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)

    pr.disable()

    # Generate report
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(15)  # Top 15 functions

    report = s.getvalue()
    return report


def print_recommendations(profile_results: dict) -> None:
    """Print optimization recommendations based on profiling results.

    Args:
        profile_results: Dictionary with profiling results.
    """
    print("\n" + "=" * 60)
    print("💡 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 60)

    # Check vectorization vs prediction balance
    vec_time = profile_results.get("vectorization_mean_ms", 0)
    pred_time = profile_results.get("prediction_mean_ms", 0)
    total_time = vec_time + pred_time

    if total_time > 0:
        vec_pct = (vec_time / total_time) * 100
        pred_pct = (pred_time / total_time) * 100

        print(f"\nTime Breakdown:")
        print(f"  Vectorization: {vec_pct:.1f}% ({vec_time:.2f}ms)")
        print(f"  Prediction:    {pred_pct:.1f}% ({pred_time:.2f}ms)")

        if vec_pct > 60:
            print("\n  ⚠️  Vectorization dominates! Consider:")
            print("     - Pre-vectorize common texts")
            print("     - Use sparse matrix caching")
            print("     - Batch process texts")
        elif pred_pct > 60:
            print("\n  ⚠️  Prediction dominates! Consider:")
            print("     - Use model quantization")
            print("     - Implement early stopping")
            print("     - Use approximate methods")

    per_sample = profile_results.get("full_pipeline_per_sample_ms", 0)
    if per_sample > 5:
        print(f"\n  ⚠️  Per-sample inference is slow ({per_sample:.2f}ms)")
        print("     Consider batch inference for throughput improvements")
    elif per_sample > 0:
        print(f"\n  ✅ Per-sample inference is fast ({per_sample:.2f}ms)")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Profile and optimize the event classifier inference pipeline."
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of sample texts to generate (default: 100)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of profiling runs for averaging (default: 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for batch inference profiling (default: 100)",
    )
    parser.add_argument(
        "--profile-cprofile",
        action="store_true",
        help="Run detailed cProfile analysis",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Save profiling results to JSON file",
    )

    args = parser.parse_args()

    # Load model
    model, vectorizer = load_artifacts()
    if model is None or vectorizer is None:
        print("❌ Failed to load artifacts. Exiting.")
        return

    # Generate sample texts
    print(f"Generating {args.samples} sample texts...")
    texts = generate_sample_texts(args.samples)

    # Run profiling
    results = {}

    # Vectorization profiling
    results.update(profile_vectorization(vectorizer, texts, args.runs))

    # Vectorize once for prediction profiling
    X = vectorizer.transform(texts)

    # Prediction profiling
    results.update(profile_prediction(model, X, args.runs))

    # Decision function profiling
    results.update(profile_decision_function(model, X, args.runs))

    # Full pipeline profiling
    results.update(profile_full_pipeline(model, vectorizer, texts, args.runs - 5))

    # Batch inference profiling
    results.update(profile_batch_inference(model, vectorizer, texts, args.batch_size))

    # Print results
    print("\n" + "=" * 60)
    print("📊 PROFILING RESULTS")
    print("=" * 60)
    for key, value in sorted(results.items()):
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")

    # cProfile analysis
    if args.profile_cprofile:
        cprof_report = profile_cprofile(model, vectorizer, texts[:20])
        print("\n" + "=" * 60)
        print("📊 CPROFILE ANALYSIS (Top Functions)")
        print("=" * 60)
        print(cprof_report)

    # Print recommendations
    print_recommendations(results)

    # Save results if requested
    if args.output_file:
        import json

        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.output_file}")


if __name__ == "__main__":
    main()
