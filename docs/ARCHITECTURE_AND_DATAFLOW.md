# ML Pipeline Architecture & Data Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENVISION PERDIDO                             │
│              ML Event Classification Pipeline                    │
└─────────────────────────────────────────────────────────────────┘

INPUT
  │
  ├─ Web Scraper
  │  └─> Raw Event Data (JSON/CSV)
  │
  └─ ICS Parser
     └─> Event Details

        │
        ▼
  ┌─────────────────┐
  │  Data Loader    │  (Envision_Perdido_DataCollection.py)
  │  & Normalizer   │
  └────────┬────────┘
           │
           ▼
    ┌──────────────┐
    │  Events DF   │  (events.csv with title, description, etc.)
    │   N events   │
    └──────┬───────┘
           │
     ┌─────┴─────────────────────────────────┐
     │                                       │
     ▼                                       ▼
┌────────────────┐               ┌──────────────────┐
│ Training Path  │               │ Inference Path   │
│ (Offline)      │               │ (Real-time)      │
└────────┬───────┘               └────────┬─────────┘
         │                               │
         ├─► SVM Training                │
         │   (SVC/LinearSVC)             │
         │   └─> Save Model              │
         │                               │
         └─► Feature Engineering         │
             └─> TF-IDF Vectorizer       │
                 └─> Save Vectorizer     │
                                         │
                                    ┌────┴──────────┐
                                    │               │
                               data/artifacts/
                              ├─ event_classifier_model.pkl
                              └─ event_vectorizer.pkl
                                         │
                                  ┌──────┴─────────────────┐
                                  │    Load Model          │
                                  │  & Vectorizer (Cache)  │
                                  └──────┬─────────────────┘
                                         │
                           ┌─────────────┴──────────────┐
                           │                            │
                       ▼▼▼▼▼▼▼▼▼▼▼▼          ┌─────────────────┐
                    classify_events()       │  Dev Tools      │
                    (automated_pipeline)    │  (Optional)     │
                           │                │                 │
                    ┌──────┴──────────────┐ ├─ Profile:       │
                    │                     │ │  • Speed        │
                ┌───┴────────────────┐    │ │  • Memory       │
                │ classify_events_   │    │ │  • Bottlenecks  │
                │ batch()            │    │ │                 │
                │ NEW! ✨            │    │ ├─ Visualize:    │
                │                    │    │ │  • Features     │
                │ Process in batches │    │ │  • Matrices     │
                │ (500 events/batch) │    │ │  • Reports      │
                │                    │    │ │                 │
                │ ┌─ Vectorize       │    │ └─────────────────┘
                │ │  (TF-IDF)        │    │
                │ │                  │    │  scripts/dev/
                │ ├─ Split text      │    │  ├─ visualize_pipeline.py
                │ │  into batches    │    │  └─ profile_inference.py
                │ │                  │    │
                │ ├─ Predict         │    │
                │ │  (SVM.predict)   │    │
                │ │                  │    │
                │ ├─ Confidence      │    │
                │ │  (decision_func) │    │
                │ │                  │    │
                │ └─ Merge results   │    │
                │    with full data  │    │
                └─────┬──────────────┘    │
                      │                   │
  OUTPUT ENRICHMENT   │                   │
        │             │                   │
        ▼             ▼                   │
   ┌─────────────────────────┐            │
   │ Event Normalizer        │            │
   │ • Enrich with tags      │            │
   │ • Add venue info        │            │
   │ • Mark needs_review     │            │
   │ • Filter spam/long      │            │
   └──────────┬──────────────┘            │
              │                           │
              ▼                           │
    ┌──────────────────┐                 │
    │ Image Assignment │                 │
    │ • Match keywords │                 │
    │ • Score events   │                 │
    │ • Assign images  │                 │
    └──────────┬───────┘                 │
               │                         │
               ▼                         │
    ┌──────────────────┐                 │
    │ Export Events    │                 │
    │ (CSV/JSON)       │                 │
    └──────────┬───────┘                 │
               │                         │
               ▼                         │
    ┌──────────────────┐                 │
    │ Email Summary    │                 │
    │ (To reviewers)   │                 │
    └──────────┬───────┘                 │
               │                         │
               ▼                         │
    ┌──────────────────────┐             │
    │ WordPress Upload     │             │
    │ • Create drafts      │             │
    │ • Set metadata       │             │
    │ • Publish (optional) │             │
    └──────────┬───────────┘             │
               │                         │
               ├─────────────────────────┘
               │
               ▼
         output/pipeline/
         ├─ calendar_upload_<timestamp>.csv
         ├─ emails/
         └─ logs/

FEEDBACK LOOP
       │
       └──► Label corrections
           → Update training data
           → Retrain model
           → Profile improvements
           → Commit changes
```

## Batch Classification Flow

```
Input Events (1500 total)
        │
        ▼
┌──────────────────────────┐
│ classify_events_batch()  │
│ batch_size=500           │
└──────────┬───────────────┘
           │
    ┌──────┴──────┬──────────┬──────────┐
    │             │          │          │
    ▼             ▼          ▼          ▼
┌────────┐   ┌────────┐  ┌────────┐  ┌────────┐
│Batch 1 │   │Batch 2 │  │Batch 3 │  │Batch 4 │
│ 500    │   │ 500    │  │ 500    │  │  ?     │
│events  │   │events  │  │events  │  │remaining
└────┬───┘   └────┬───┘  └────┬───┘  └────┬───┘
     │            │           │            │
     ▼            ▼           ▼            ▼
  Vectorize   Vectorize   Vectorize    Vectorize
  (TF-IDF)    (TF-IDF)    (TF-IDF)     (TF-IDF)
     │            │           │            │
     ▼            ▼           ▼            ▼
  Predict     Predict     Predict      Predict
  (SVM)       (SVM)       (SVM)        (SVM)
     │            │           │            │
     ▼            ▼           ▼            ▼
Confidence  Confidence  Confidence   Confidence
  Scores     Scores     Scores       Scores
     │            │           │            │
     └────────┬───┴────┬──────┴──────┬─────┘
              │        │            │
              ▼        ▼            ▼
        [Predictions] [Confidence Scores]
              │        │
              └────┬───┘
                   │
         Progress: 500/1500 ✓
         Progress: 1000/1500 ✓
         Progress: 1500/1500 ✓
                   │
                   ▼
        ┌─ Merge with original data
        ├─ Add is_community_event column
        ├─ Add confidence column
        └─ Add needs_review flag
```

## Data Transformation Pipeline

```
RAW EVENT
┌──────────────────────┐
│ title                │
│ description          │  (From web scraper or ICS)
│ location             │
│ start_date           │
│ url                  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Feature Engineering  │ (build_features)
│                      │
│ "title + desc +      │
│  location +          │
│  category"           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Vectorization        │ (TfidfVectorizer)
│                      │
│ Uni-grams +          │
│ Bi-grams             │
│ (1-2 word terms)     │
│                      │
│ Vectorizer Config:   │
│ • min_df: 2          │
│ • max_df: 0.9        │
│ • ngram_range: (1,2) │
│ • strip_accents      │
│ • sublinear_tf       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Feature Matrix       │ (Sparse)
│                      │
│ Shape: (N, ~1000)    │ N = # events
│ Type: csr_matrix     │ ~1000 = # terms
│ Density: ~1-2%       │ Mostly zeros
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ SVM Classification   │ (LinearSVC)
│                      │
│ Input: Feature matrix│
│ Output:              │
│ • Prediction: 0/1    │
│ • Decision score: ℝ  │
│                      │
│ Model Config:        │
│ • class_weight:      │
│   "balanced"         │
│ • max_iter: 1000     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Confidence Score     │
│                      │
│ sigmoid(decision)    │
│ Maps to [0, 1]       │
│                      │
│ Interpretation:      │
│ • 0.5 = neutral      │
│ • 0.9 = very sure    │
│ • 0.1 = very unsure  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Enriched Event       │
│                      │
│ • is_community: 1/0  │
│ • confidence: [0,1]  │
│ • needs_review: T/F  │ (if < 0.75)
│ • tags: [...]        │
│ • venue: resolved    │
│ • image_url: path    │
└──────────────────────┘
```

## Development Tools Integration

```
┌─────────────────────────────────────────┐
│         Pipeline Execution              │
│   (automated_pipeline.py)               │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────────┐
    │                             │
    ▼                             ▼
classf_events()        Dev Tools (Optional)
    │                             │
    ├─ classify_events_batch()   ├─ Profiling
    │  • Batch processing        │  └─ profile_inference.py
    │  • Progress reporting      │     • Speed metrics
    │  • Memory efficient        │     • Bottlenecks
    │                             │     • Optimization tips
    └─ Continue pipeline         │
       (enrich, filter, export)  └─ Visualization
                                  └─ visualize_pipeline.py
                                     • Feature importance
                                     • Confusion matrix
                                     • Precision-recall
                                     • Debug reports
```

## File Dependency Graph

```
scripts/
├── automated_pipeline.py
│   ├── imports: ..., Tuple
│   ├── calls: classify_events_batch()
│   ├── uses: event_normalizer
│   └── loads: model, vectorizer
│       (from data/artifacts/)
│
├── dev/
│   ├── __init__.py
│   │   └── makes package
│   │
│   ├── visualize_pipeline.py
│   │   ├── imports: sklearn.inspection, matplotlib, pandas
│   │   ├── calls: load_artifacts()
│   │   ├── uses: permutation_importance
│   │   └── generates: PNG, CSV, JSON outputs
│   │
│   └── profile_inference.py
│       ├── imports: cProfile, time, numpy
│       ├── calls: load_artifacts()
│       ├── uses: decision_function, vectorizer.transform
│       └── generates: JSON profiling data
│
└── svm_train_from_file.py
    ├── imports: sklearn.svm, TfidfVectorizer
    ├── trains: LinearSVC model
    └── saves: model.pkl, vectorizer.pkl

data/artifacts/
├── event_classifier_model.pkl
└── event_vectorizer.pkl

tests/
└── test_dev_tools.py
    ├── tests: visualize_pipeline functions
    ├── tests: profile_inference functions
    ├── tests: classify_events_batch
    └── imports: unittest.mock, pandas

docs/
├── ML_PIPELINE_INTEGRATION_GUIDE.md
├── IMPLEMENTATION_SUMMARY.md
└── GIT_WORKFLOW_QUICK_REFERENCE.md
```

## Git Workflow

```
main branch (production)
        │
        ├─ Create: feature/ml-pipeline-optimization
        │             │
        │             ├─ Add: visualize_pipeline.py
        │             ├─ Add: profile_inference.py
        │             ├─ Add: __init__.py
        │             ├─ Modify: automated_pipeline.py
        │             ├─ Add: test_dev_tools.py
        │             ├─ Add: documentation
        │             │
        │             └─ Commit: "feat(ml): Add pipeline tools"
        │                     │
        │                     ├─ Run tests ✓
        │                     ├─ Profile tools ✓
        │                     ├─ Visualize ✓
        │                     │
        │                     └─ Push: to remote
        │                             │
        │                             └─ Create: Pull Request
        │                                     │
        │                                     ├─ Code review
        │                                     ├─ CI checks ✓
        │                                     │
        │                                     └─ Merge to main
        │                                             │
        └─────────────────────────────────────────────┘
                     Back to main
              (with new tools integrated)
```

---

**Complete implementation with visualization, profiling, optimization, and git workflow integration.**
