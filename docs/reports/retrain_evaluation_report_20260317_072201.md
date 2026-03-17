# Retrain Evaluation Report

- Run started (UTC): 2026-03-17T07:22:00.461487+00:00
- Report generated (UTC): 2026-03-17T07:22:01.759920+00:00

## Inputs and Artifacts

- Prepared canonical labeled dataset: /home/jacobmiller/EnvisionPerdido/data/processed/canonical_labeled_training_20260317_021813.csv
- Prepared review queue: /home/jacobmiller/EnvisionPerdido/data/processed/review_queue_20260317_021813.csv
- Consolidated dataset: /home/jacobmiller/EnvisionPerdido/data/processed/consolidated_training_data.csv
- Training input used: /home/jacobmiller/EnvisionPerdido/data/processed/consolidated_training_data.csv
- Model artifact: /home/jacobmiller/EnvisionPerdido/data/artifacts/event_classifier_model.pkl

## Dataset Summary

- Labeled rows available: 422
- Evaluation rows: 374
- Class 0 count: 186
- Class 1 count: 236
- Split mode: group_shuffle_split

## Metrics

- Accuracy (default threshold=0.0): 0.8075
- Accuracy (optimized threshold=-0.5890): 0.8342

## Threshold Policy

- Selection mode: precision_constrained
- Decision threshold (class-1): -0.5890
- Review margin around threshold: 0.4000
- Estimated review rate on eval split: 50.53%
- Class-1 precision at threshold: 0.7769
- Class-1 recall at threshold: 0.9701

### Confusion Matrix

```
[[152  21]
 [ 51 150]]
```

### Classification Report

```
              precision    recall  f1-score   support

           0      0.749     0.879     0.809       173
           1      0.877     0.746     0.806       201

    accuracy                          0.807       374
   macro avg      0.813     0.812     0.807       374
weighted avg      0.818     0.807     0.807       374

```

### Thresholded Confusion Matrix

```
[[117  56]
 [  6 195]]
```

### Thresholded Classification Report

```
              precision    recall  f1-score   support

           0      0.951     0.676     0.791       173
           1      0.777     0.970     0.863       201

    accuracy                          0.834       374
   macro avg      0.864     0.823     0.827       374
weighted avg      0.858     0.834     0.829       374

```
