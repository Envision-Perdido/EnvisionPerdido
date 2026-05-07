"""Unit tests for scripts.pipeline.api_retraining."""

from __future__ import annotations

import io
import json
from pathlib import Path

from scripts.pipeline.api_retraining import create_app


def _bundle_bytes(events: list[dict]) -> bytes:
    return json.dumps({"events": events}).encode("utf-8")


def _configure_temp_data_dirs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("scripts.pipeline.api_retraining.DATA_LABELED_DIR", tmp_path / "labeled")
    monkeypatch.setattr("scripts.pipeline.api_retraining.DATA_PROCESSED_DIR", tmp_path / "processed")


def test_trigger_retrain_rejects_missing_bundle_field(monkeypatch, tmp_path):
    _configure_temp_data_dirs(monkeypatch, tmp_path)
    app = create_app()
    client = app.test_client()

    resp = client.post("/api/retrain")

    assert resp.status_code == 400
    assert "bundle" in resp.get_json()["error"]


def test_trigger_retrain_creates_job_and_returns_202(monkeypatch, tmp_path):
    _configure_temp_data_dirs(monkeypatch, tmp_path)
    app = create_app()
    client = app.test_client()

    events = [
        {
            "event_id": "evt-1",
            "title": "Beach Cleanup",
            "description": "Volunteer cleanup",
            "source": "perdido_chamber",
            "actual_label": "community",
            "predicted_label": "community",
        },
        {
            "event_id": "evt-2",
            "title": "Sales Expo",
            "description": "Retail event",
            "source": "perdido_chamber",
            "actual_label": "non-community",
            "predicted_label": "community",
        },
    ]

    # Avoid background subprocess execution during unit tests.
    monkeypatch.setattr(
        "scripts.pipeline.api_retraining._run_retrain_job",
        lambda job_id, csv_path: None,
    )

    resp = client.post(
        "/api/retrain",
        data={"bundle": (io.BytesIO(_bundle_bytes(events)), "bundle.json")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 202
    body = resp.get_json()
    assert body["job_id"]
    assert body["status"] in {"pending", "running"}
    assert body["labeled_rows"] == 2


def test_trigger_retrain_returns_400_for_unlabeled_bundle(monkeypatch, tmp_path):
    _configure_temp_data_dirs(monkeypatch, tmp_path)
    app = create_app()
    client = app.test_client()

    events = [
        {
            "event_id": "evt-1",
            "title": "Unknown Event",
            "actual_label": None,
            "predicted_label": "community",
        }
    ]

    resp = client.post(
        "/api/retrain",
        data={"bundle": (io.BytesIO(_bundle_bytes(events)), "bundle.json")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["status"] == "failed"
    assert "no reviewed/labeled rows" in body["error_message"].lower()


def test_get_jobs_list_and_job_detail(monkeypatch, tmp_path):
    _configure_temp_data_dirs(monkeypatch, tmp_path)
    app = create_app()
    client = app.test_client()

    events = [
        {
            "event_id": "evt-1",
            "title": "Beach Cleanup",
            "actual_label": "community",
            "predicted_label": "community",
        }
    ]

    monkeypatch.setattr(
        "scripts.pipeline.api_retraining._run_retrain_job",
        lambda job_id, csv_path: None,
    )

    create_resp = client.post(
        "/api/retrain",
        data={"bundle": (io.BytesIO(_bundle_bytes(events)), "bundle.json")},
        content_type="multipart/form-data",
    )
    job_id = create_resp.get_json()["job_id"]

    list_resp = client.get("/api/retrain/jobs?limit=5")
    assert list_resp.status_code == 200
    jobs = list_resp.get_json()["jobs"]
    assert any(job["job_id"] == job_id for job in jobs)

    detail_resp = client.get(f"/api/retrain/jobs/{job_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["job_id"] == job_id


def test_api_key_guard(monkeypatch, tmp_path):
    _configure_temp_data_dirs(monkeypatch, tmp_path)
    monkeypatch.setenv("PIPELINE_API_KEY", "secret-key")
    app = create_app()
    client = app.test_client()

    events = [{"event_id": "evt-1", "actual_label": "community"}]

    # Missing auth header should fail
    denied = client.post(
        "/api/retrain",
        data={"bundle": (io.BytesIO(_bundle_bytes(events)), "bundle.json")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 401

    # Valid bearer token should pass
    monkeypatch.setattr(
        "scripts.pipeline.api_retraining._run_retrain_job",
        lambda job_id, csv_path: None,
    )
    allowed = client.post(
        "/api/retrain",
        data={"bundle": (io.BytesIO(_bundle_bytes(events)), "bundle.json")},
        content_type="multipart/form-data",
        headers={"Authorization": "Bearer secret-key"},
    )
    assert allowed.status_code == 202
