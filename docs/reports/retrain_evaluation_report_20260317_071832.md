# Retrain Evaluation Report

- Run started (UTC): 2026-03-17T07:18:31.523997+00:00
- Report generated (UTC): 2026-03-17T07:18:32.759144+00:00

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

- Accuracy: 0.8075

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
