# SVM Analytics Report

- Generated (UTC): 2026-03-17T07:36:06.914001+00:00
- Dataset: /home/jacobmiller/EnvisionPerdido/data/processed/consolidated_training_data.csv
- Model: /home/jacobmiller/EnvisionPerdido/data/artifacts/event_classifier_model.pkl
- Split mode: group_shuffle_split

## Policy

- Decision threshold: -0.5890
- Review margin: 0.4000
- Confidence threshold: 0.7500
- Estimated review rate: 92.78%

## Metrics

- Accuracy (active threshold): 0.8342
- Class-1 precision: 0.7769
- Class-1 recall: 0.9701
- Class-1 F1: 0.8628

## Confusion Matrix

```
[[117  56]
 [  6 195]]
```

![Confusion Matrix](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/confusion_matrix.png)

## Per-Class Metrics

![Class Metrics](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/class_metrics.png)

## Threshold Tradeoff

![Threshold Tradeoff](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/threshold_tradeoff.png)

## Confidence Distribution

![Confidence Distribution](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/confidence_distribution.png)

## Review Volume

![Review Volume](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/review_volume.png)

## Top Features

![Top Features](/home/jacobmiller/EnvisionPerdido/output/analytics/svm_analytics_20260317_073605/top_features.png)
