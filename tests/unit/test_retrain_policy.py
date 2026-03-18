"""Tests for threshold policy, hard-negative mining, and source balancing."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from scripts.ml.retrain_end_to_end import _mine_hard_negatives, _source_balance_summary
from scripts.ml.training_support import ensure_source_column, select_threshold_from_sweep, threshold_sweep


class DummyPipe:
    """Simple deterministic pipe for svm_tag_events threshold tests."""

    def predict(self, X):
        return [0] * len(X)

    def decision_function(self, X):
        return [-0.4, 0.2, 0.8][: len(X)]


def test_select_threshold_prefers_highest_nondefault_candidate():
    y_true = [1, 1, 1, 0, 0, 0]
    scores = [0.9, 0.8, 0.3, 0.2, 0.1, -0.4]

    sweep_df = threshold_sweep(
        y_true=y_true,
        scores=scores,
        confidence_threshold=0.75,
        review_margin=0.35,
    )
    threshold, summary, mode = select_threshold_from_sweep(
        sweep_df=sweep_df,
        target_recall=0.95,
        min_precision=0.75,
    )

    assert threshold == 0.3
    assert summary["precision_1"] == 1.0
    assert summary["recall_1"] == 1.0
    assert mode == "recall_and_precision"


def test_mine_hard_negatives_excludes_model_predictions_and_duplicates():
    eval_df = pd.DataFrame(
        {
            "title": ["a", "b", "c", "d"],
            "label": [0, 0, 0, 1],
            "label_source": ["manual_or_previous", "model_prediction", "", "manual_or_previous"],
            "source": ["perdido_chamber"] * 4,
        }
    )
    candidates, mined = _mine_hard_negatives(
        eval_df=eval_df,
        y_eval=[0, 0, 0, 1],
        decision_scores=[0.9, 0.8, 0.7, -0.2],
        decision_threshold=0.0,
        top_n=25,
        multiplier=3,
    )

    assert candidates["title"].tolist() == ["a", "c"]
    assert len(mined) == 6
    assert set(mined["label_source"]) == {"hard_negative_mining"}
    assert set(mined["label"]) == {0}


def test_ensure_source_column_backfills_url_then_file_then_unknown():
    df = pd.DataFrame(
        {
            "source": ["", "", "already_set", ""],
            "url": [
                "https://business.perdidochamber.com/events/details/foo",
                "",
                "",
                "",
            ],
            "_source_file": ["", "wren_haven_export.csv", "", ""],
        }
    )

    result = ensure_source_column(df)

    assert result["source"].tolist() == [
        "perdido_chamber",
        "wren_haven",
        "already_set",
        "unknown",
    ]


def test_source_balance_summary_flags_unknown_source_overage():
    rows = []
    for i in range(8):
        rows.append(
            {
                "title": f"unknown {i}",
                "description": "",
                "start": f"2026-01-{i + 1:02d}T10:00:00+00:00",
                "location": "",
                "url": "",
                "uid": f"u{i}",
                "series_id": f"u{i}",
                "source": "unknown",
                "label": i % 2,
                "label_source": "manual_or_previous",
            }
        )
    for i in range(12):
        rows.append(
            {
                "title": f"perdido {i}",
                "description": "",
                "start": f"2026-02-{(i % 9) + 1:02d}T10:00:00+00:00",
                "location": "",
                "url": f"https://business.perdidochamber.com/events/{i}",
                "uid": f"p{i}",
                "series_id": f"p{i}",
                "source": "perdido_chamber",
                "label": i % 2,
                "label_source": "manual_or_previous",
            }
        )

    summary = _source_balance_summary(
        labeled=pd.DataFrame(rows),
        label_col="label",
        max_unknown_source_rate=0.20,
        max_source_positive_rate_delta=0.20,
    )

    assert not summary["passed"]
    assert "unknown source rate" in summary["failures"][0]


def test_source_balance_summary_passes_for_balanced_sources():
    rows = []
    for source_prefix, source_name in [("p", "perdido_chamber"), ("w", "wren_haven")]:
        for i in range(12):
            rows.append(
                {
                    "title": f"{source_name} {i}",
                    "description": "",
                    "start": f"2026-03-{(i % 9) + 1:02d}T10:00:00+00:00",
                    "location": "",
                    "url": f"https://example.com/{source_prefix}/{i}",
                    "uid": f"{source_prefix}{i}",
                    "series_id": f"{source_prefix}{i}",
                    "source": source_name,
                    "label": i % 2,
                    "label_source": "manual_or_previous",
                }
            )

    summary = _source_balance_summary(
        labeled=pd.DataFrame(rows),
        label_col="label",
        max_unknown_source_rate=0.20,
        max_source_positive_rate_delta=0.60,
    )

    assert summary["passed"]
    assert summary["missing_sources"] == []


def test_svm_tag_events_uses_persisted_decision_threshold(monkeypatch, tmp_path):
    from scripts.ml import svm_tag_events

    model_path = tmp_path / "model.pkl"
    input_path = tmp_path / "events.csv"
    output_path = tmp_path / "tagged.csv"
    model_path.write_text("placeholder", encoding="utf-8")
    input_path.write_text("placeholder", encoding="utf-8")

    df = pd.DataFrame(
        {
            "title": ["a", "b", "c"],
            "description": ["", "", ""],
            "start": ["2026-01-01T00:00:00Z"] * 3,
            "location": ["", "", ""],
        }
    )

    monkeypatch.setattr(
        svm_tag_events.joblib,
        "load",
        lambda path: {
            "pipe": DummyPipe(),
            "decision_threshold": 0.15,
            "columns": {
                "title": "title",
                "desc": "description",
                "start": "start",
                "loc": "location",
            },
        },
    )
    monkeypatch.setattr(svm_tag_events, "load_any", lambda path: df.copy())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "svm_tag_events.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--model-path",
            str(model_path),
        ],
    )

    svm_tag_events.main()

    tagged = pd.read_csv(output_path)
    assert tagged["predicted_label"].tolist() == [0, 1, 1]
