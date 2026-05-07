"""Unit tests for the external handoff export mapping."""

from pathlib import Path

import pandas as pd

from scripts.pipeline.external_handoff_export import (
    build_handoff_bundle,
    build_handoff_event,
    export_handoff_bundle,
)


def test_build_handoff_event_maps_pipeline_fields():
    event = {
        "uid": "abc-123",
        "source": "perdido_chamber",
        "url": "https://example.org/event/abc-123",
        "title": "Community Potluck",
        "description": "Bring a dish and meet your neighbors.",
        "location": "Flora-Bama, 17400 Perdido Key Dr",
        "venue_id": "flora-bama",
        "start": "2026-06-12 18:00:00",
        "end": "2026-06-12 20:00:00",
        "image_url": "https://example.org/potluck.jpg",
        "cost_text": "Free admission",
        "is_free": True,
        "tags": ["family_friendly", "food_drink"],
        "needs_review": True,
        "confidence": 0.81,
    }

    mapped = build_handoff_event(event)

    assert mapped["external_id"] == "abc-123"
    assert mapped["source_system"] == "perdido_chamber"
    assert mapped["source_url"] == "https://example.org/event/abc-123"
    assert mapped["source_type"] == "community_event"
    assert mapped["schedule_mode"] == "single_instance"
    assert mapped["title_raw"] == "Community Potluck"
    assert mapped["title_cleaned"] == "Community Potluck"
    assert mapped["location_name_raw"] == "Flora-Bama"
    assert mapped["location_address_raw"] == "17400 Perdido Key Dr"
    assert mapped["location_external_id"] == ""
    assert mapped["suggested_location_external_id"] == "flora-bama"
    assert mapped["location_match_confidence"] > 0.0
    assert mapped["location_match_basis"]
    assert mapped["timezone"] == "America/Chicago"
    assert mapped["start_at"].endswith("-05:00") or mapped["start_at"].endswith("-06:00")
    assert mapped["image_candidates"] == [
        {"type": "url", "value": "https://example.org/potluck.jpg", "role": "hero"}
    ]
    assert mapped["editorial_status"] == "raw"
    assert mapped["needs_editorial_rewrite"] is True
    assert mapped["tags_raw"] == ["family_friendly", "food_drink"]
    assert mapped["cost_evidence"] == "Free admission"
    assert mapped["pricing_confidence"] >= 0.8
    assert mapped["schedule_basis"] == "start_and_end_fields"
    assert mapped["extraction_confidence"] > 0.0
    assert "review" in mapped["review_notes"].lower()
    assert mapped["confidence"] == 0.81


def test_build_handoff_bundle_collects_locations_and_notes():
    df = pd.DataFrame(
        [
            {
                "uid": "known-venue-event",
                "source": "perdido_chamber",
                "title": "Known Venue Event",
                "description": "Details",
                "location": "Flora-Bama",
                "venue_id": "flora-bama",
                "start": "2026-06-12 18:00:00",
            },
            {
                "uid": "raw-location-event",
                "source": "perdido_chamber",
                "title": "Raw Location Event",
                "description": "Details",
                "location": "Mystery Venue",
                "start": "2026-06-13 18:00:00",
            },
        ]
    )

    bundle = build_handoff_bundle(df, bundle_id="test-bundle")

    assert bundle["bundle_id"] == "test-bundle"
    assert len(bundle["events"]) == 2
    assert len(bundle["locations"]) == 1
    assert bundle["locations"][0]["external_id"] == "flora-bama"
    assert any("missing summary_raw" in note for note in bundle["notes"])
    assert any("location_hint text" in note for note in bundle["notes"])


def test_build_handoff_bundle_flags_possible_duplicates():
    df = pd.DataFrame(
        [
            {
                "uid": "dup-a",
                "source": "perdido_chamber",
                "title": "1st Impression Vendor Market",
                "description": "Details",
                "location": "1st Impressions, 11545 Sorrento Rd",
                "start": "2026-06-06 08:00:00",
                "end": "2026-06-06 12:00:00",
            },
            {
                "uid": "dup-b",
                "source": "perdido_chamber",
                "title": "1st Impression Vendor Market",
                "description": "Details",
                "location": "1st Impressions - 11545 Sorrento Rd",
                "start": "2026-06-06 09:00:00",
                "end": "2026-06-06 12:00:00",
            },
        ]
    )

    bundle = build_handoff_bundle(df, bundle_id="dup-test")

    assert bundle["events"][0]["possible_duplicate_group"]
    assert bundle["events"][1]["possible_duplicate_group"] == bundle["events"][0]["possible_duplicate_group"]
    assert bundle["events"][1]["duplicate_candidate_of"] == bundle["events"][0]["external_id"]
    assert bundle["events"][1]["duplicate_confidence"] > 0.0
    assert any("possible duplicate group" in note for note in bundle["notes"])


def test_export_handoff_bundle_writes_json(tmp_path: Path):
    df = pd.DataFrame(
        [
            {
                "uid": "export-test",
                "title": "Export Test",
                "description": "Details",
                "location": "Flora-Bama",
                "venue_id": "flora-bama",
                "start": "2026-06-12 18:00:00",
            }
        ]
    )

    output_path = export_handoff_bundle(df, tmp_path)

    assert output_path.exists()
    assert output_path.name.startswith("external_event_handoff_")
    assert output_path.suffix == ".json"
