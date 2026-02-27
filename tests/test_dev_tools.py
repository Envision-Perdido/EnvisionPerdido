#!/usr/bin/env python3
"""Tests for ML pipeline dev tools.

Tests verify that visualization and profiling tools work correctly.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestVisualizeTools:
    """Test suite for visualize_pipeline.py"""

    def test_load_artifacts_missing_files(self):
        """Test load_artifacts handles missing model files gracefully."""
        from scripts.dev.visualize_pipeline import load_artifacts

        with patch("pathlib.Path.exists", return_value=False):
            model, vectorizer = load_artifacts()
            assert model is None
            assert vectorizer is None

    def test_plot_feature_importance_returns_dataframe(self):
        """Test that plot_feature_importance returns proper DataFrame."""
        from scripts.dev.visualize_pipeline import plot_feature_importance

        # Create mock objects
        mock_model = MagicMock()
        mock_vectorizer = MagicMock()

        # Mock get_feature_names_out
        mock_vectorizer.get_feature_names_out.return_value = np.array(
            ["community", "event", "festival", "park", "library"],
        )

        # Create sparse matrix mock
        X_test = MagicMock()
        X_test.shape = (100, 5)
        y_test = np.array([1, 0, 1] * 33 + [1])

        # Mock permutation importance result
        importance_result = MagicMock()
        importance_result.importances_mean = np.array([0.1, 0.2, 0.15, 0.05, 0.08])
        importance_result.importances_std = np.array([0.01, 0.02, 0.01, 0.005, 0.01])

        with patch(
            "scripts.dev.visualize_pipeline.permutation_importance",
            return_value=importance_result,
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                result_df = plot_feature_importance(
                    mock_model, mock_vectorizer, X_test, y_test, Path(tmpdir), top_n=5
                )

                assert result_df is not None
                assert "feature" in result_df.columns
                assert "importance_mean" in result_df.columns
                assert len(result_df) == 5

    def test_generate_classification_report(self):
        """Test classification report generation."""
        from scripts.dev.visualize_pipeline import generate_classification_report

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1, 0, 1, 0, 1] * 20)

        X_test = MagicMock()
        X_test.shape = (100, 5)
        y_test = np.array([1, 0, 1, 0, 1] * 20)

        with tempfile.TemporaryDirectory() as tmpdir:
            report = generate_classification_report(mock_model, X_test, y_test, Path(tmpdir))

            assert "precision" in report.lower()
            assert "recall" in report.lower()
            assert "f1-score" in report.lower()


class TestProfileTools:
    """Test suite for profile_inference.py"""

    def test_generate_sample_texts(self):
        """Test sample text generation."""
        from scripts.dev.profile_inference import generate_sample_texts

        texts = generate_sample_texts(n_samples=50)

        assert len(texts) == 50
        assert all(isinstance(t, str) for t in texts)
        assert all(len(t) > 0 for t in texts)

    def test_profile_vectorization(self):
        """Test vectorization profiling."""
        from scripts.dev.profile_inference import profile_vectorization

        mock_vectorizer = MagicMock()
        mock_vectorizer.transform.return_value = MagicMock(shape=(10, 10))

        texts = ["test event"] * 10

        results = profile_vectorization(mock_vectorizer, texts, n_runs=2)

        assert "vectorization_mean_ms" in results
        assert "vectorization_per_sample_ms" in results
        assert results["vectorization_mean_ms"] >= 0
        assert results["vectorization_per_sample_ms"] >= 0

    def test_profile_prediction(self):
        """Test prediction profiling."""
        from scripts.dev.profile_inference import profile_prediction

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0, 1, 0, 1])

        X_test = MagicMock()
        X_test.shape = (4, 10)

        results = profile_prediction(mock_model, X_test, n_runs=2)

        assert "prediction_mean_ms" in results
        assert "prediction_per_sample_ms" in results
        assert results["prediction_mean_ms"] >= 0
        assert results["n_samples"] == 4

    def test_profile_batch_inference(self):
        """Test batch inference profiling."""
        from scripts.dev.profile_inference import profile_batch_inference

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0, 1, 0, 1])

        mock_vectorizer = MagicMock()
        mock_vectorizer.transform.return_value = MagicMock(shape=(4, 10))

        texts = ["test event"] * 100

        results = profile_batch_inference(mock_model, mock_vectorizer, texts, batch_size=25)

        assert "batch_size" in results
        assert "n_batches" in results
        assert results["batch_size"] == 25
        assert results["n_batches"] == 4

    def test_print_recommendations(self):
        """Test that recommendations are printed without errors."""
        from scripts.dev.profile_inference import print_recommendations

        profile_results = {
            "vectorization_mean_ms": 100.0,
            "prediction_mean_ms": 20.0,
            "full_pipeline_per_sample_ms": 1.2,
        }

        # Should not raise any exceptions
        print_recommendations(profile_results)


class TestBatchClassification:
    """Test suite for batch classification in automated_pipeline"""

    def test_classify_events_batch_shapes(self):
        """Test that batch classification returns correct output shapes."""
        from scripts.automated_pipeline import classify_events_batch

        # Create mock objects
        mock_model = MagicMock()
        mock_vectorizer = MagicMock()

        # Create test DataFrame
        df_test = pd.DataFrame(
            {
                "title": ["Event 1", "Event 2", "Event 3"],
                "description": ["Description 1", "Description 2", "Description 3"],
                "location": ["Location 1", "Location 2", "Location 3"],
                "category": ["Festival", "Meeting", "Workshop"],
            }
        )

        # Mock predictions
        mock_model.predict.return_value = np.array([1, 0, 1])
        mock_model.decision_function.return_value = np.array([0.5, -0.3, 0.8])

        # Mock vectorizer
        mock_vectorizer.transform.return_value = MagicMock(shape=(3, 10))

        predictions, confidences = classify_events_batch(
            df_test, mock_model, mock_vectorizer, batch_size=2
        )

        assert len(predictions) == 3
        assert len(confidences) == 3
        assert predictions.dtype in [int, np.int64, np.int32]
        assert confidences.dtype in [float, np.float64, np.float32]


class TestIntegration:
    """Integration tests for the full workflow"""

    def test_pipeline_with_mock_model(self):
        """Test the pipeline with mock model to ensure batch processing works."""
        # This is more of a smoke test to ensure nothing breaks
        assert True  # Placeholder for full integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
