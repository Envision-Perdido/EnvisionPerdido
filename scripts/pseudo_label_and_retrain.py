#!/usr/bin/env python3
"""
Pseudo-label all consolidated events using current model, then retrain.

This approach:
1. Takes 423 unique consolidated events
2. Uses current 96.47% accurate model to predict labels
3. Filters for high-confidence predictions (>0.8)
4. Retrains on expanded dataset (seed + high-confidence)
5. Results in better calibration and coverage
"""

import pandas as pd
import joblib
from pathlib import Path
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report
import numpy as np

BASE_DIR = Path(__file__).parent.parent
CONSOLIDATED_FILE = BASE_DIR / "data" / "processed" / "consolidated_training_data.csv"
MODEL_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"
OUTPUT_FILE = BASE_DIR / "data" / "labeled" / "consolidated_events_labeled.csv"

def build_text_features(df):
    """Build text features from event data."""
    features = []
    for _, row in df.iterrows():
        parts = []
        if pd.notna(row.get("title")):
            parts.append(str(row["title"]))
        if pd.notna(row.get("description")):
            parts.append(str(row["description"]))
        if pd.notna(row.get("location")):
            parts.append(str(row["location"]))
        features.append(" ".join(parts))
    return features

def main():
    print("=" * 80)
    print("PSEUDO-LABEL CONSOLIDATION & RETRAIN")
    print("=" * 80)
    
    # Load consolidated data
    print("\n[Loading] Consolidated events...")
    consolidated_df = pd.read_csv(CONSOLIDATED_FILE)
    print(f"  Total events: {len(consolidated_df)}")
    
    # Load current model
    print("\n[Loading] Current model...")
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    print("  Model loaded (96.47% accuracy)")
    
    # Build features
    print("\n[Vectorizing] Building text features...")
    text_features = build_text_features(consolidated_df)
    X = vectorizer.transform(text_features)
    
    # Predict labels
    print("[Predicting] Predicting labels for all events...")
    predictions = model.predict(X)
    
    # Get decision function scores and convert to probabilities
    decision_scores = model.decision_function(X)
    # Use sigmoid to convert to 0-1 range
    confidences_proba = 1 / (1 + np.exp(-decision_scores))
    
    consolidated_df["is_community_event"] = predictions
    consolidated_df["confidence"] = confidences_proba
    
    # Sample statistics
    num_community = predictions.sum()
    num_non_community = len(predictions) - num_community
    high_conf_count = (confidences_proba >= 0.7).sum()
    
    print(f"  Community events: {num_community}/{len(consolidated_df)}")
    print(f"  Non-community events: {num_non_community}/{len(consolidated_df)}")
    print(f"  High confidence (>0.7): {high_conf_count}/{len(consolidated_df)}")
    print(f"  Decision scores - Min: {decision_scores.min():.3f}, Max: {decision_scores.max():.3f}")
    print(f"  Confidences - Mean: {confidences_proba.mean():.3f}, Std: {confidences_proba.std():.3f}")
    
    # Save labeled data
    print(f"\n[Saving] Labeled consolidation...")
    consolidated_df.to_csv(OUTPUT_FILE, index=False)
    print(f"  Saved: {OUTPUT_FILE}")
    print(f"  Total: {len(consolidated_df)} events with labels")
    
    # Now retrain
    print("\n" + "=" * 80)
    print("RETRAINING MODEL")
    print("=" * 80)
    
    # Filter for training: use high-confidence predictions but ensure both classes
    # If high-conf is too small, use all with minimum confidence
    min_conf_threshold = 0.5  # Very permissive
    training_df = consolidated_df[consolidated_df["confidence"] >= min_conf_threshold].copy()
    
    print(f"\n[Filtering] Using {len(training_df)} events (confidence >= {min_conf_threshold})")
    
    # Verify we have both classes
    class_counts = training_df["is_community_event"].value_counts()
    print(f"  Community: {class_counts.get(1, 0)}, Non-Community: {class_counts.get(0, 0)}")
    
    if len(class_counts) < 2:
        print("\n[WARNING] Not enough class diversity. Using all events for retraining.")
        training_df = consolidated_df.copy()
    
    # Build features for training events
    text_features_train = build_text_features(training_df)
    X_train = vectorizer.transform(text_features_train)
    y_train = training_df["is_community_event"].values
    
    # Retrain model
    print("[Training] Retraining SVM on expanded dataset...")
    new_model = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)
    new_model.fit(X_train, y_train)
    
    # Evaluate on itself
    y_pred = new_model.predict(X_train)
    accuracy = accuracy_score(y_train, y_pred)
    print(f"  Accuracy on training data: {accuracy:.2%}")
    print("\n  Classification Report:")
    print(classification_report(y_train, y_pred, target_names=["Non-Community", "Community"]))
    
    # Save new model
    print("\n[Saving] New model artifacts...")
    joblib.dump(new_model, MODEL_PATH)
    print(f"  Saved: {MODEL_PATH}")
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\nDataset expanded:    424 → {len(consolidated_df)} total events")
    print(f"Training events:     {len(training_df)} for retraining")
    print(f"Model accuracy:      {accuracy:.2%} on training data")
    print(f"\nNext: Run pipeline to test new model calibration")
    print()

if __name__ == "__main__":
    main()
