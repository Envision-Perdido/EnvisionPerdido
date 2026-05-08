# Retrain Evaluation Report

- Run started (UTC): 2026-05-07T19:58:05.628805+00:00
- Report generated (UTC): 2026-05-07T19:58:16.358823+00:00
- Model promoted: True

## Inputs and Artifacts

- Prepared canonical labeled dataset: C:\Users\Jacob\EnvisionPerdido\data\processed\canonical_labeled_training_20260317_021813.csv
- Prepared review queue: C:\Users\Jacob\EnvisionPerdido\data\processed\review_queue_20260317_021347.csv
- Consolidated dataset: C:\Users\Jacob\EnvisionPerdido\data\processed\consolidated_training_data.csv
- Base training input used: C:\Users\Jacob\EnvisionPerdido\data\processed\admin_retrain_input_a70d8086ec744e3c9191a46797cba1f5.csv
- Final training input used: C:\Users\Jacob\EnvisionPerdido\data\processed\hard_negative_augmented_20260507_195808.csv
- Model artifact: C:\Users\Jacob\EnvisionPerdido\data\artifacts\event_classifier_model.pkl
- Diagnostics output: C:\Users\Jacob\EnvisionPerdido\output\analytics\retrain_diagnostics_20260507_195805

## Dataset Summary

- Labeled rows available: 137
- Evaluation rows: 37
- Class 0 count: 56
- Class 1 count: 81
- Split mode: group_shuffle_split
- Hard-negative candidates mined: 4

## First-Pass Threshold Policy

- Decision threshold: -0.2797
- Selection mode: recall_and_precision
- Class-1 precision: 0.8000
- Class-1 recall: 1.0000

## Final Threshold Policy

- Selection mode: precision_only_fallback
- Decision threshold (class-1): 0.9735
- Review margin around threshold: 0.3500
- Confidence threshold: 0.7500
- Estimated review rate on eval split: 100.00%
- Class-1 precision at threshold: 1.0000
- Class-1 recall at threshold: 0.0625

## Metrics

- Accuracy (default threshold=0.0): 0.5946
- Accuracy (optimized threshold=0.9735): 0.5946

### Default Confusion Matrix

```
[[ 9 12]
 [ 3 13]]
```

### Default Classification Report

```
              precision    recall  f1-score   support

           0      0.750     0.429     0.545        21
           1      0.520     0.812     0.634        16

    accuracy                          0.595        37
   macro avg      0.635     0.621     0.590        37
weighted avg      0.651     0.595     0.584        37

```

### Thresholded Confusion Matrix

```
[[21  0]
 [15  1]]
```

### Thresholded Classification Report

```
              precision    recall  f1-score   support

           0      0.583     1.000     0.737        21
           1      1.000     0.062     0.118        16

    accuracy                          0.595        37
   macro avg      0.792     0.531     0.427        37
weighted avg      0.764     0.595     0.469        37

```

## Source Balance Gate

- Passed: True
- Unknown source rate: 0.00%
- Split mode: group_shuffle_split
- Reviewable sources: perdido_chamber
- Positive-rate delta (perdido_chamber): 0.010

## Top Positive Coefficients

- feature_110: 0.6958
- feature_122: 0.4883
- feature_23: 0.4154
- feature_106: 0.4154
- feature_24: 0.4154
- feature_92: 0.3306
- feature_54: 0.3306
- feature_53: 0.3306
- feature_55: 0.3306
- feature_14: 0.3144

## Top Negative Coefficients

- feature_21: -1.1322
- feature_74: -0.7231
- feature_75: -0.6902
- feature_32: -0.5884
- feature_33: -0.5307
- feature_71: -0.4705
- feature_20: -0.4705
- feature_19: -0.4705
- feature_119: -0.4705
- feature_115: -0.4705
