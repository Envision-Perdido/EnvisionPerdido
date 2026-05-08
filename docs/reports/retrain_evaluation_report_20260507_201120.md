# Retrain Evaluation Report

- Run started (UTC): 2026-05-07T20:11:11.420200+00:00
- Report generated (UTC): 2026-05-07T20:11:20.041975+00:00
- Model promoted: True

## Inputs and Artifacts

- Prepared canonical labeled dataset: C:\Users\Jacob\EnvisionPerdido\data\processed\canonical_labeled_training_20260317_021813.csv
- Prepared review queue: C:\Users\Jacob\EnvisionPerdido\data\processed\review_queue_20260317_021347.csv
- Consolidated dataset: C:\Users\Jacob\EnvisionPerdido\data\processed\consolidated_training_data.csv
- Base training input used: C:\Users\Jacob\EnvisionPerdido\data\processed\admin_retrain_input_e634b4f907ba420db2f57fd50e1ea7ea.csv
- Final training input used: C:\Users\Jacob\EnvisionPerdido\data\processed\admin_retrain_input_e634b4f907ba420db2f57fd50e1ea7ea.csv
- Model artifact: C:\Users\Jacob\EnvisionPerdido\data\artifacts\event_classifier_model.pkl
- Diagnostics output: C:\Users\Jacob\EnvisionPerdido\output\analytics\retrain_diagnostics_20260507_201111

## Dataset Summary

- Labeled rows available: 260
- Evaluation rows: 52
- Class 0 count: 113
- Class 1 count: 147
- Split mode: group_shuffle_split
- Hard-negative candidates mined: 0

## First-Pass Threshold Policy

- Decision threshold: 0.0652
- Selection mode: recall_and_precision
- Class-1 precision: 1.0000
- Class-1 recall: 0.9286

## Final Threshold Policy

- Selection mode: recall_and_precision
- Decision threshold (class-1): 0.0652
- Review margin around threshold: 0.3500
- Confidence threshold: 0.7500
- Estimated review rate on eval split: 100.00%
- Class-1 precision at threshold: 1.0000
- Class-1 recall at threshold: 0.9286

## Metrics

- Accuracy (default threshold=0.0): 0.9615
- Accuracy (optimized threshold=0.0652): 0.9615

### Default Confusion Matrix

```
[[24  0]
 [ 2 26]]
```

### Default Classification Report

```
              precision    recall  f1-score   support

           0      0.923     1.000     0.960        24
           1      1.000     0.929     0.963        28

    accuracy                          0.962        52
   macro avg      0.962     0.964     0.961        52
weighted avg      0.964     0.962     0.962        52

```

### Thresholded Confusion Matrix

```
[[24  0]
 [ 2 26]]
```

### Thresholded Classification Report

```
              precision    recall  f1-score   support

           0      0.923     1.000     0.960        24
           1      1.000     0.929     0.963        28

    accuracy                          0.962        52
   macro avg      0.962     0.964     0.961        52
weighted avg      0.964     0.962     0.962        52

```

## Source Balance Gate

- Passed: True
- Unknown source rate: 0.00%
- Split mode: group_shuffle_split
- Reviewable sources: perdido_chamber
- Positive-rate delta (perdido_chamber): 0.034

## Top Positive Coefficients

- feature_285: 0.5400
- feature_172: 0.5400
- feature_286: 0.5400
- feature_244: 0.5222
- feature_238: 0.5143
- feature_54: 0.5143
- feature_55: 0.5143
- feature_81: 0.4695
- feature_27: 0.4485
- feature_179: 0.4420

## Top Negative Coefficients

- feature_48: -1.0184
- feature_152: -0.7358
- feature_275: -0.6353
- feature_68: -0.5962
- feature_178: -0.5768
- feature_225: -0.5572
- feature_224: -0.5572
- feature_0: -0.5572
- feature_197: -0.5326
- feature_215: -0.5191
