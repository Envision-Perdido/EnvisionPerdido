"""Unit tests for the SVM confidence calculation in automated_pipeline.py.

The key invariant being tested: confidence must be derived from the *absolute*
value of the LinearSVC decision score so that high-confidence class-0
(non-community) predictions are not incorrectly penalised.

For binary LinearSVC:
  - class-1 predictions  → positive decision score
  - class-0 predictions  → negative decision score

Without np.abs(), sigmoid(negative_score) < 0.5 < CONFIDENCE_THRESHOLD (0.75),
which caused *every* non-community event to be flagged for manual review.
"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd


def _make_df(n=3):
    categories = ["Festival", "Meeting", "Workshop", "Concert", "Fundraiser"]
    return pd.DataFrame(
        {
            "title": [f"Event {i}" for i in range(n)],
            "description": [f"Description {i}" for i in range(n)],
            "location": [f"Location {i}" for i in range(n)],
            "category": [categories[i % len(categories)] for i in range(n)],
        }
    )


class TestConfidenceCalculation:
    """Verify that classify_events_batch uses |decision_score| for confidence."""

    def _make_mock_model(self, predictions, decision_scores):
        mock = MagicMock()
        mock.predict.return_value = np.array(predictions)
        mock.decision_function.return_value = np.array(decision_scores, dtype=float)
        return mock

    def test_class0_confident_prediction_has_high_confidence(self):
        """A model that is sure an event is non-community (large negative score)
        should produce a high confidence score (>= 0.5), not a low one.

        Regression test for the bug where raw (unsigned) decision scores were
        used, giving sigmoid(-2) ≈ 0.12 instead of ~0.88.
        """
        from scripts.pipeline.automated_pipeline import classify_events_batch

        mock_model = self._make_mock_model(predictions=[0], decision_scores=[-2.0])
        mock_vec = MagicMock()
        mock_vec.transform.return_value = MagicMock(shape=(1, 10))

        df = _make_df(1)
        _, confidences = classify_events_batch(df, mock_model, mock_vec, batch_size=10)

        assert confidences[0] >= 0.5, (
            f"Confident class-0 prediction (score=-2.0) has confidence "
            f"{confidences[0]:.4f} < 0.5; np.abs() is likely missing from the "
            "decision-score confidence calculation."
        )

    def test_symmetric_scores_yield_equal_confidence(self):
        """Events with decision scores +d and -d are equally far from the
        boundary: their confidence should be identical regardless of class."""
        from scripts.pipeline.automated_pipeline import classify_events_batch

        mock_model = self._make_mock_model(predictions=[1, 0], decision_scores=[1.5, -1.5])
        mock_vec = MagicMock()
        mock_vec.transform.return_value = MagicMock(shape=(2, 10))

        df = _make_df(2)
        _, confidences = classify_events_batch(df, mock_model, mock_vec, batch_size=10)

        assert abs(confidences[0] - confidences[1]) < 1e-6, (
            f"Symmetric scores +1.5 and -1.5 should yield equal confidence, "
            f"got {confidences[0]:.6f} vs {confidences[1]:.6f}."
        )

    def test_borderline_prediction_has_lower_confidence_than_confident(self):
        """A prediction near the decision boundary (|score| ≈ 0) must have
        lower confidence than a prediction far from it."""
        from scripts.pipeline.automated_pipeline import classify_events_batch

        mock_model = self._make_mock_model(predictions=[0, 0], decision_scores=[-2.0, -0.1])
        mock_vec = MagicMock()
        mock_vec.transform.return_value = MagicMock(shape=(2, 10))

        df = _make_df(2)
        _, confidences = classify_events_batch(df, mock_model, mock_vec, batch_size=10)

        assert confidences[0] > confidences[1], (
            f"Confident class-0 (score=-2.0, conf={confidences[0]:.4f}) should "
            f"have higher confidence than borderline class-0 "
            f"(score=-0.1, conf={confidences[1]:.4f})."
        )

    def test_non_community_events_not_all_flagged_for_review(self):
        """With the correct confidence formula, high-confidence non-community
        events must *not* exceed the CONFIDENCE_THRESHOLD check that triggers
        the needs_review flag (i.e. confidence must be >= CONFIDENCE_THRESHOLD).
        """
        from scripts.pipeline.automated_pipeline import CONFIDENCE_THRESHOLD, classify_events_batch

        # Simulate a batch of confidently non-community events
        n = 5
        mock_model = self._make_mock_model(
            predictions=[0] * n,
            decision_scores=[-2.5, -2.0, -1.8, -1.5, -1.2],
        )
        mock_vec = MagicMock()
        mock_vec.transform.return_value = MagicMock(shape=(n, 10))

        df = _make_df(n)
        _, confidences = classify_events_batch(df, mock_model, mock_vec, batch_size=10)

        # At least some high-confidence non-community events should clear the threshold
        above_threshold = (confidences >= CONFIDENCE_THRESHOLD).sum()
        assert above_threshold > 0, (
            f"All {n} confident non-community events have confidence < "
            f"{CONFIDENCE_THRESHOLD} (max={confidences.max():.4f}). "
            "This indicates the confidence calculation does not use |score|."
        )

    def test_tuned_threshold_uses_score_greater_than_or_equal(self):
        """Shifted thresholds must use score >= threshold for class-1."""
        from scripts.pipeline.automated_pipeline import classify_events_batch

        mock_model = self._make_mock_model(
            predictions=[0, 0, 0],
            decision_scores=[-0.3, 0.2, 0.8],
        )
        mock_vec = MagicMock()
        mock_vec.transform.return_value = MagicMock(shape=(3, 10))

        df = _make_df(3)
        predictions, _ = classify_events_batch(
            df,
            mock_model,
            mock_vec,
            batch_size=10,
            decision_threshold=0.15,
        )

        assert predictions.tolist() == [0, 1, 1]
