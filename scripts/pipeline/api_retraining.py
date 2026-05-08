#!/usr/bin/env python3
"""Retraining API for EnvisionPerdido.

Exposes endpoints expected by the admin portal:
- POST /api/retrain
- GET /api/retrain/jobs/<job_id>
- GET /api/retrain/jobs

This API accepts a JSON bundle upload, converts reviewed rows to a labeled CSV,
and runs retraining in a background thread.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.ml.training_support import ensure_source_column, load_any

RETRAIN_SCRIPT = BASE_DIR / "scripts" / "ml" / "retrain_end_to_end.py"
DATA_LABELED_DIR = BASE_DIR / "data" / "labeled"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_ARTIFACT_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"

_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_label_to_binary(value: Any) -> int | None:
    x = str(value or "").strip().lower().replace(".0", "")
    if x in {"community", "1", "true", "yes"}:
        return 1
    if x in {"non-community", "noncommunity", "0", "false", "no"}:
        return 0
    return None


def _require_api_key() -> bool:
    return bool(os.getenv("PIPELINE_API_KEY", "").strip())


def _validate_api_key() -> bool:
    expected = os.getenv("PIPELINE_API_KEY", "").strip()
    if not expected:
        return True
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[len("Bearer ") :].strip()
    return provided == expected


def _set_job(job_key: str, **fields: Any) -> None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_key, {})
        job["job_id"] = job_key
        job.update(fields)
        _JOBS[job_key] = job


def _get_job(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def _list_jobs(limit: int) -> list[dict[str, Any]]:
    with _JOBS_LOCK:
        rows = list(_JOBS.values())
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows[:limit]


def _bundle_to_training_csv(bundle_path: Path, job_id: str) -> tuple[Path, int]:
    """Convert uploaded JSON bundle to retrain_end_to_end compatible CSV.

    Returns (csv_path, labeled_row_count).
    """
    df = load_any(bundle_path)
    if df.empty:
        raise ValueError("Uploaded bundle contains no events.")

    # Prefer reviewed ground truth, fallback to existing label if present.
    if "actual_label" in df.columns:
        df["label"] = df["actual_label"].apply(_normalize_label_to_binary)
    elif "label" in df.columns:
        df["label"] = df["label"].apply(_normalize_label_to_binary)
    else:
        raise ValueError("Bundle must include 'actual_label' or 'label'.")

    labeled = df[df["label"].notna()].copy()
    if labeled.empty:
        raise ValueError("Bundle contains no reviewed/labeled rows.")

    labeled["label"] = labeled["label"].astype(int)

    # Ensure required columns used downstream exist.
    for col in [
        "title",
        "description",
        "start",
        "location",
        "url",
        "uid",
        "source",
        "_source_file",
        "label_source",
        "series_id",
    ]:
        if col not in labeled.columns:
            labeled[col] = ""

    if "event_id" in labeled.columns and (labeled["uid"] == "").all():
        labeled["uid"] = labeled["event_id"].astype(str)

    # svm_train_from_file may run with --propagate-series-labels and expects
    # non-empty series_id groups; empty/NaN values can erase labels in transform.
    labeled["uid"] = labeled["uid"].fillna("").astype(str)
    labeled["series_id"] = labeled["series_id"].fillna("").astype(str)
    empty_series = labeled["series_id"].eq("")
    labeled.loc[empty_series, "series_id"] = labeled.loc[empty_series, "uid"]

    labeled["label_source"] = labeled["label_source"].replace("", "manual_or_previous")
    labeled = ensure_source_column(labeled)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_PROCESSED_DIR / f"admin_retrain_input_{job_id}.csv"
    labeled.to_csv(csv_path, index=False)
    return csv_path, int(len(labeled))


def _run_retrain_job(job_id: str, csv_input: Path) -> None:
    _set_job(
        job_id,
        status="running",
        progress=10,
        started_at=_utc_now(),
        error_message=None,
    )

    cmd = [
        sys.executable,
        str(RETRAIN_SCRIPT),
        "--skip-prepare",
        "--skip-consolidate",
        "--train-input",
        str(csv_input),
        "--model-path",
        str(MODEL_ARTIFACT_PATH),
    ]

    try:
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        base_path = str(BASE_DIR)
        env["PYTHONPATH"] = (
            f"{base_path}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else base_path
        )
        env.setdefault("PYTHONIOENCODING", "utf-8")

        completed = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            env=env,
        )

        if completed.returncode != 0:
            _set_job(
                job_id,
                status="failed",
                progress=100,
                completed_at=_utc_now(),
                error_message=(completed.stderr or completed.stdout or "Retrain failed")[:4000],
            )
            return

        _set_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=_utc_now(),
            model_artifact_path=str(MODEL_ARTIFACT_PATH),
            output_tail=(completed.stdout or "")[-2000:],
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            progress=100,
            completed_at=_utc_now(),
            error_message=str(exc),
        )


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def _auth_guard():
        if _require_api_key() and not _validate_api_key():
            return jsonify({"error": "Unauthorized."}), 401
        return None

    @app.route("/api/retrain", methods=["POST"])
    def trigger_retrain():
        if "bundle" not in request.files:
            return jsonify({"error": "Missing uploaded file field 'bundle'."}), 400

        bundle = request.files["bundle"]
        if not bundle.filename:
            return jsonify({"error": "Uploaded bundle file has no filename."}), 400

        job_id = uuid.uuid4().hex
        created_at = _utc_now()

        DATA_LABELED_DIR.mkdir(parents=True, exist_ok=True)
        bundle_path = DATA_LABELED_DIR / f"retrain_bundle_{job_id}.json"
        bundle.save(bundle_path)

        _set_job(
            job_id,
            status="pending",
            progress=0,
            created_at=created_at,
            bundle_path=str(bundle_path),
        )

        try:
            csv_input, labeled_rows = _bundle_to_training_csv(bundle_path, job_id)
        except Exception as exc:
            _set_job(
                job_id,
                status="failed",
                progress=100,
                completed_at=_utc_now(),
                error_message=str(exc),
            )
            return jsonify(_get_job(job_id)), 400

        _set_job(job_id, progress=5, train_input_path=str(csv_input), labeled_rows=labeled_rows)

        worker = threading.Thread(
            target=_run_retrain_job,
            args=(job_id, csv_input),
            daemon=True,
        )
        worker.start()

        return jsonify(_get_job(job_id)), 202

    @app.route("/api/retrain/jobs/<string:job_id>", methods=["GET"])
    def retrain_job(job_id: str):
        row = _get_job(job_id)
        if not row:
            return jsonify({"error": f"Job '{job_id}' not found."}), 404
        return jsonify(row), 200

    @app.route("/api/retrain/jobs", methods=["GET"])
    def retrain_jobs():
        try:
            limit = int(request.args.get("limit", 10))
        except (TypeError, ValueError):
            return jsonify({"error": "'limit' must be an integer."}), 400

        limit = max(1, min(limit, 100))
        return jsonify({"jobs": _list_jobs(limit)}), 200

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EnvisionPerdido retraining API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
