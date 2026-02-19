# Machine Learning & Classification

SVM-based event classification and auto-labeling scripts.

## Scripts (4)

- `svm_train_from_file.py` — Train SVM classifier from labeled event data
  - Builds feature vectors from event title, description, time, and venue
  - Uses text (TF-IDF), temporal, and venue features
  - Cross-validates with group-based splitting to avoid series leakage
  - Outputs model and vectorizer pickle files

- `svm_tag_events.py` — Classify events using a trained SVM model
  - Loads pre-trained model and vectorizer
  - Predicts labels with confidence scores
  - Supports CSV and JSON input/output
  - Flags low-confidence predictions for manual review

- `auto_label_and_train.py` — Auto-label new events and retrain model
  - Uses existing labeled data to train initial SVM
  - Predicts labels for new scraped events
  - Propagates labels within event series
  - Retrains final model on expanded dataset
  - Handles confidence thresholding and low-confidence flagging

- `smart_label_helper.py` — Interactive labeling assistant
  - Uses trained model to predict labels for unlabeled events
  - Flags uncertain predictions for manual review
  - Supports confident predictions (>0.75) for auto-approval
  - Provides summary statistics and review queue

## Workflow

Typical ML workflow:
```bash
# 1. Train model on labeled data
python ml/svm_train_from_file.py --input data/labeled/events.csv

# 2. Tag new events with trained model
python ml/svm_tag_events.py --input data/raw/new_events.csv --output data/tagged/

# 3. Auto-label and retrain
python ml/auto_label_and_train.py

# 4. Interactive review of uncertain predictions
python ml/smart_label_helper.py
```

## Model Artifacts

Models are stored in `data/artifacts/`:
- `event_classifier_model.pkl` — Trained SVM model
- `event_vectorizer.pkl` — Text vectorizer (TF-IDF)

## Configuration

Environment variables:
- `MODEL_PATH` — Path to trained model (default: `data/artifacts/event_classifier_model.pkl`)
- `VECTORIZER_PATH` — Path to vectorizer (default: `data/artifacts/event_vectorizer.pkl`)
- `CONFIDENCE_THRESHOLD` — Prediction confidence threshold (default: 0.75)

## Feature Engineering

The classifier uses:
- **Text features:** TF-IDF vectors from title + description
- **Temporal features:** Hour of day, day of week, weekend indicator
- **Venue features:** Keywords for library, park, church, museum

See `build_features()` in each script for implementation details.

## Accuracy & Evaluation

Models are evaluated using:
- Stratified cross-validation (prevents series bias)
- Classification report (precision, recall, F1)
- Confusion matrix
- Field-level accuracy analysis

Results are printed during training and saved to logs.
