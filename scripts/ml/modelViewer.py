import sys
from pathlib import Path

import joblib

# Resolve artifact paths relative to the repository root so this script runs
# regardless of where the repository is located on disk.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "data" / "artifacts"
model_path = ARTIFACTS_DIR / "event_classifier_model.pkl"
vectorizer_path = ARTIFACTS_DIR / "event_vectorizer.pkl"


def load_or_raise(p: Path):
    if not p.exists():
        raise FileNotFoundError(
            f"Expected artifact not found: {p}\n(looking relative to repo root: {REPO_ROOT})"
        )
    return joblib.load(p)


def main():
    try:
        model = load_or_raise(model_path)
        vectorizer = load_or_raise(vectorizer_path)
        print("Model and vectorizer loaded successfully\n")
        print("Model details:")
        print(model)
        print("\nVectorizer details:")
        print(vectorizer)

        # Example: Predict on new data
        example_texts = [
            "Sample event description about a community cleanup.",
            "Join us for a music festival downtown!",
        ]
        X = vectorizer.transform(example_texts)
        predictions = model.predict(X)
        print("\nPredictions for example texts:")
        for text, pred in zip(example_texts, predictions):
            print(f"Text: {text}\nPredicted label: {pred}\n")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"An error occurred while loading the model or vectorizer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
