"""Export normalized pipeline results to the external event handoff contract."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from scripts.tooling.venue_registry import get_venue_by_id, normalize_location_text, resolve_venue


DEFAULT_BUNDLE_SOURCE = "envision_perdido_pipeline"
DEFAULT_TIMEZONE = "America/Chicago"


def _is_empty_value(value) -> bool:
    """Return True when a normalized value should be omitted from output."""
    return value is None or value == "" or value == []


def _utc_now_iso() -> str:
    """Return current UTC timestamp in contract-friendly ISO format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_string(value) -> str:
    """Normalize optional string values to a trimmed string."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_title(text: str) -> str:
    """Normalize titles for deduping and light cleanup."""
    cleaned = _clean_string(text)
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[|]+", " | ", cleaned)
    return cleaned.strip()


def _title_cleaned(title: str) -> str:
    """Apply light, low-risk title cleanup while preserving raw copy separately."""
    cleaned = _normalize_title(title)
    cleaned = re.sub(r"\s*[—–-]\s*[—–-]+\s*", " - ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _clean_bool(value):
    """Normalize optional booleans while preserving unknown values."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _json_ready(value):
    """Convert pandas and numpy values into JSON-safe Python values."""
    if value is None:
        return None
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            serialized = _json_ready(item)
            if serialized is not None:
                cleaned[str(key)] = serialized
        return cleaned
    if isinstance(value, (list, tuple, set)):
        items = [_json_ready(item) for item in value]
        return [item for item in items if item is not None]
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _parse_recurrence(value) -> dict:
    """Normalize recurrence payloads to a dict."""
    if value is None or pd.isna(value):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"raw": text}
    return {}


def _parse_datetime(value, timezone_name: str) -> str:
    """Convert source datetimes to timezone-aware ISO strings."""
    if value is None or pd.isna(value):
        return ""

    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return ""

    tz = ZoneInfo(timezone_name)
    if ts.tzinfo is None:
        ts = ts.tz_localize(tz)
    else:
        ts = ts.tz_convert(tz)

    return ts.isoformat()


def _parse_datetime_obj(value, timezone_name: str) -> pd.Timestamp | None:
    """Return a timezone-aware pandas timestamp for duplicate comparisons."""
    if value is None or pd.isna(value):
        return None

    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None

    tz = ZoneInfo(timezone_name)
    if ts.tzinfo is None:
        return ts.tz_localize(tz)
    return ts.tz_convert(tz)


def _build_external_id(event_dict: dict) -> str:
    """Choose a stable external ID, generating one only as a fallback."""
    for key in ("external_id", "uid", "id"):
        candidate = _clean_string(event_dict.get(key))
        if candidate:
            return candidate

    parts = [
        _clean_string(event_dict.get("source")),
        _clean_string(event_dict.get("url")),
        _clean_string(event_dict.get("title")),
        _clean_string(event_dict.get("start")),
    ]
    raw = "|".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"generated-{digest}"


def _build_review_notes(event_dict: dict) -> str:
    """Summarize review-relevant signals for downstream editorial handling."""
    notes = []

    if _clean_bool(event_dict.get("needs_review")):
        notes.append("Model confidence flagged this event for review.")

    filter_reason = _clean_string(event_dict.get("filter_reason"))
    if filter_reason:
        notes.append(f"Pipeline filter reason present: {filter_reason}.")

    if not _clean_string(event_dict.get("venue_id")) and _clean_string(event_dict.get("location")):
        notes.append("Location is unresolved and only available as raw text.")

    if not _clean_string(event_dict.get("summary")):
        notes.append("No source summary was available; editorial summary is still needed.")

    return " ".join(notes)


def _split_location_fields(location_text: str) -> tuple[str, str, str]:
    """Split raw location text into candidate name and address fields when possible."""
    location_hint = _clean_string(location_text)
    if not location_hint:
        return "", "", ""

    patterns = [
        r"^(?P<name>.+?)\s{2,}(?P<address>\d.+)$",
        r"^(?P<name>.+?)\s+-\s+(?P<address>\d.+)$",
        r"^(?P<name>.+?),\s*(?P<address>\d.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, location_hint)
        if match:
            name = _clean_string(match.group("name"))
            address = _clean_string(match.group("address"))
            return name, address, location_hint

    address_match = re.search(r"\b\d{2,6}\s+[A-Za-z0-9].*$", location_hint)
    if address_match:
        address = _clean_string(address_match.group(0))
        name = _clean_string(location_hint[: address_match.start()])
        return name, address, location_hint

    return location_hint, "", location_hint


def _build_image_candidates(event_dict: dict) -> list[dict]:
    """Collect candidate source images without assuming publish readiness."""
    candidates = []

    for field_name in ("image_url", "image_path", "image"):
        value = _clean_string(event_dict.get(field_name))
        if not value:
            continue

        candidate_type = "url" if value.startswith(("http://", "https://")) else "local_path"
        candidates.append({"type": candidate_type, "value": value, "role": "hero"})
        break

    return candidates


def _build_tags_raw(event_dict: dict) -> list[str]:
    """Preserve internal tags as raw source tags for downstream taxonomy mapping."""
    value = event_dict.get("tags")
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    if pd.isna(value):
        return []
    return [str(value).strip()]


def _build_cost_evidence(event_dict: dict) -> str:
    """Return the source text that most directly supports the cost signal."""
    for field_name in ("cost_text", "cost"):
        value = _clean_string(event_dict.get(field_name))
        if value:
            return value

    description = _clean_string(event_dict.get("description"))
    if not description:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", description)
    for sentence in sentences:
        if re.search(
            r"\b(free|ticket|tickets|admission|registration|entry|cover|fee|fees|price|pricing|vip|purchase)\b|\$\d+(?:\.\d{2})?",
            sentence,
            re.IGNORECASE,
        ):
            return sentence.strip()
    return ""


def _pricing_confidence(event_dict: dict) -> float:
    """Estimate confidence in the paid/free signal."""
    if event_dict.get("cost"):
        return 0.95

    evidence = _build_cost_evidence(event_dict)
    if not evidence:
        return 0.0

    if re.search(r"\bfree\b|\bno\s+(?:cover|charge|cost|fee|admission)\b", evidence, re.IGNORECASE):
        return 0.85
    if re.search(
        r"\b(ticket|tickets|admission|registration|entry|cover|fee|fees)\b.{0,30}\$\d+|\$\d+(?:\.\d{2})?.{0,30}\b(ticket|tickets|admission|registration|entry|cover|fee|fees)\b",
        evidence,
        re.IGNORECASE,
    ):
        return 0.9
    return 0.35


def _location_candidates(event_dict: dict) -> tuple[str, float, str, list[dict]]:
    """Build tentative location match proposals for downstream reconciliation."""
    source_location_id = _clean_string(event_dict.get("location_external_id"))
    if source_location_id:
        basis = "source_location_external_id"
        candidate = {
            "external_id": source_location_id,
            "confidence": 1.0,
            "basis": basis,
        }
        return source_location_id, 1.0, basis, [candidate]

    raw_location = _clean_string(event_dict.get("location"))
    venue = resolve_venue(raw_location) if raw_location else None
    if not venue:
        return "", 0.0, "", []

    normalized_raw = normalize_location_text(raw_location)
    normalized_name = normalize_location_text(venue.canonical_name)
    if normalized_raw == normalized_name:
        confidence = 0.92
        basis = "exact_location_name_match"
    elif normalized_name in normalized_raw:
        confidence = 0.75
        basis = "canonical_name_contained_in_location"
    else:
        confidence = 0.6
        basis = "alias_or_partial_location_match"

    candidate = {
        "external_id": venue.id,
        "name": venue.canonical_name,
        "confidence": confidence,
        "basis": basis,
    }
    return venue.id, confidence, basis, [candidate]


def _extraction_confidence(event_dict: dict, location_name_raw: str, start_at: str) -> float:
    """Estimate how complete the extracted source facts are."""
    score = 0.0
    score += 0.25 if _clean_string(event_dict.get("title")) else 0.0
    score += 0.2 if _clean_string(event_dict.get("description")) else 0.0
    score += 0.2 if _clean_string(event_dict.get("url")) else 0.0
    score += 0.2 if start_at else 0.0
    score += 0.15 if location_name_raw or _clean_string(event_dict.get("location")) else 0.0
    return round(score, 3)


def _schedule_basis(event_dict: dict, start_at: str, end_at: str, recurrence: dict) -> str:
    """Describe which source fields drove schedule extraction."""
    if recurrence:
        return "recurrence_field"
    if start_at and end_at:
        return "start_and_end_fields"
    if start_at:
        return "start_field_only"
    return "no_usable_schedule_fields"


def build_handoff_event(event_dict: dict, timezone_name: str = DEFAULT_TIMEZONE) -> dict:
    """Map an enriched pipeline event into the external handoff contract."""
    start_at = _parse_datetime(event_dict.get("start"), timezone_name)
    end_at = _parse_datetime(event_dict.get("end"), timezone_name)
    recurrence = _parse_recurrence(event_dict.get("recurrence"))

    if recurrence:
        schedule_mode = "recurring"
    elif start_at:
        schedule_mode = "single_instance"
    else:
        schedule_mode = "unspecified"

    source_system = _clean_string(event_dict.get("source")) or DEFAULT_BUNDLE_SOURCE
    location_name_raw, location_address_raw, location_hint = _split_location_fields(
        event_dict.get("location")
    )
    suggested_location_external_id, location_match_confidence, location_match_basis, location_candidates = (
        _location_candidates(event_dict)
    )
    cost_evidence = _build_cost_evidence(event_dict)
    pricing_confidence = _pricing_confidence(event_dict)
    event = {
        "external_id": _build_external_id(event_dict),
        "source_system": source_system,
        "source_url": _clean_string(event_dict.get("url")),
        "source_type": _clean_string(event_dict.get("category")) or "community_event",
        "schedule_mode": schedule_mode,
        "title_raw": _clean_string(event_dict.get("title")),
        "title_cleaned": _title_cleaned(event_dict.get("title")),
        "summary_raw": _clean_string(event_dict.get("summary")),
        "description_raw": _clean_string(event_dict.get("description")),
        "location_name_raw": location_name_raw,
        "location_address_raw": location_address_raw,
        "location_hint": location_hint,
        "location_external_id": _clean_string(event_dict.get("location_external_id")),
        "suggested_location_external_id": suggested_location_external_id,
        "location_match_confidence": location_match_confidence,
        "location_match_basis": location_match_basis,
        "location_candidates": location_candidates,
        "start_at": start_at,
        "end_at": end_at,
        "timezone": timezone_name,
        "recurrence": recurrence,
        "schedule_basis": _schedule_basis(event_dict, start_at, end_at, recurrence),
        "image_candidates": _build_image_candidates(event_dict),
        "cost_raw": _clean_string(event_dict.get("cost_text") or event_dict.get("cost")),
        "cost_evidence": cost_evidence,
        "is_free": _clean_bool(event_dict.get("is_free")),
        "pricing_confidence": pricing_confidence,
        "tags_raw": _build_tags_raw(event_dict),
        "editorial_status": "raw",
        "needs_editorial_rewrite": True,
        "review_notes": _build_review_notes(event_dict),
        "extraction_confidence": _extraction_confidence(event_dict, location_name_raw, start_at),
        "duplicate_confidence": 0.0,
    }

    optional_fields = {
        "organizer_hint": _clean_string(event_dict.get("organizer")),
        "organizer_external_id": _clean_string(event_dict.get("organizer_id")),
        "audience_hint": _clean_string(event_dict.get("audience_hint")),
        "confidence": _json_ready(event_dict.get("confidence")),
        "decision_score": _json_ready(event_dict.get("decision_score")),
    }
    for key, value in optional_fields.items():
        if not _is_empty_value(value):
            event[key] = value

    raw_payload = {}
    for key, value in event_dict.items():
        serialized = _json_ready(value)
        if not _is_empty_value(serialized):
            raw_payload[key] = serialized
    if raw_payload:
        event["raw_payload"] = raw_payload

    return event


def build_location_record(event_dict: dict) -> dict | None:
    """Build a candidate structured location record when a known venue is resolved."""
    venue_id = _clean_string(event_dict.get("venue_id"))
    if not venue_id:
        return None

    venue = get_venue_by_id(venue_id)
    if not venue:
        return None

    return {
        "external_id": venue.id,
        "source_system": DEFAULT_BUNDLE_SOURCE,
        "name": venue.canonical_name,
        "address": venue.address or "",
        "city": venue.city or "",
        "state": venue.state or "",
        "raw_hint": _clean_string(event_dict.get("location")),
    }


def _duplicate_key(event_record: dict) -> str:
    """Build a normalized duplicate-group key."""
    title_key = normalize_location_text(event_record.get("title_cleaned") or event_record.get("title_raw"))
    location_key = normalize_location_text(
        event_record.get("location_name_raw")
        or event_record.get("location_address_raw")
        or event_record.get("location_hint")
    )
    return f"{title_key}|{location_key}"


def _duplicate_time_bucket(event_record: dict) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Return start/end timestamps for duplicate overlap checks."""
    start_at = _parse_datetime_obj(event_record.get("start_at"), event_record.get("timezone", DEFAULT_TIMEZONE))
    end_at = _parse_datetime_obj(event_record.get("end_at"), event_record.get("timezone", DEFAULT_TIMEZONE))
    return start_at, end_at


def _annotate_duplicate_groups(event_records: list[dict]) -> None:
    """Mark likely duplicate events for downstream importer review."""
    buckets: dict[str, list[int]] = {}
    for idx, event_record in enumerate(event_records):
        key = _duplicate_key(event_record)
        if not key.strip("|"):
            continue
        buckets.setdefault(key, []).append(idx)

    for _, indices in buckets.items():
        if len(indices) < 2:
            continue

        anchor_idx = indices[0]
        group_members = [anchor_idx]
        anchor_start, anchor_end = _duplicate_time_bucket(event_records[anchor_idx])

        for idx in indices[1:]:
            start_at, end_at = _duplicate_time_bucket(event_records[idx])
            if not anchor_start or not start_at:
                overlap = True
            else:
                anchor_end_cmp = anchor_end or anchor_start
                end_cmp = end_at or start_at
                overlap = abs((start_at - anchor_start).total_seconds()) <= 6 * 3600 or (
                    start_at <= anchor_end_cmp and anchor_start <= end_cmp
                )
            if overlap:
                group_members.append(idx)

        if len(group_members) < 2:
            continue

        group_id = f"dup-{hashlib.sha1(str(group_members).encode('utf-8')).hexdigest()[:10]}"
        anchor_external_id = event_records[anchor_idx]["external_id"]
        for offset, idx in enumerate(group_members):
            event_record = event_records[idx]
            event_record["possible_duplicate_group"] = group_id
            event_record["duplicate_confidence"] = 0.85
            event_record["duplicate_basis"] = (
                "normalized_title + normalized_location + overlapping_datetime"
            )
            if offset > 0:
                event_record["duplicate_candidate_of"] = anchor_external_id


def build_handoff_bundle(
    events_df: pd.DataFrame,
    bundle_id: str | None = None,
    source_system: str = DEFAULT_BUNDLE_SOURCE,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict:
    """Build a full external handoff bundle from classified community events."""
    built_at = _utc_now_iso()
    bundle_id = bundle_id or f"{source_system}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    event_records = []
    location_records = {}
    missing_summary = 0
    unresolved_locations = 0
    review_required = 0

    for _, row in events_df.iterrows():
        event_dict = row.to_dict()
        event_record = build_handoff_event(event_dict, timezone_name=timezone_name)
        event_records.append(event_record)

        if not event_record["summary_raw"]:
            missing_summary += 1
        if (
            not event_record["location_external_id"]
            and not event_record["suggested_location_external_id"]
            and event_record["location_hint"]
        ):
            unresolved_locations += 1
        if "review" in event_record["review_notes"].lower():
            review_required += 1

        location_record = build_location_record(event_dict)
        if location_record:
            location_records[location_record["external_id"]] = location_record

    _annotate_duplicate_groups(event_records)

    notes = []
    if missing_summary:
        notes.append(
            f"{missing_summary} events are missing summary_raw and still need editorial summaries."
        )
    if unresolved_locations:
        notes.append(
            f"{unresolved_locations} events only have location_hint text and no structured location_external_id."
        )
    if review_required:
        notes.append(f"{review_required} events include explicit review_notes for downstream QA.")
    duplicate_groups = len({event.get("possible_duplicate_group") for event in event_records if event.get("possible_duplicate_group")})
    if duplicate_groups:
        notes.append(f"{duplicate_groups} possible duplicate group(s) were flagged for downstream review.")

    return {
        "bundle_id": bundle_id,
        "source_system": source_system,
        "built_at": built_at,
        "events": event_records,
        "locations": list(location_records.values()),
        "notes": notes,
    }


def export_handoff_bundle(
    events_df: pd.DataFrame,
    output_dir: Path,
    bundle_id: str | None = None,
    source_system: str = DEFAULT_BUNDLE_SOURCE,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> Path:
    """Write the external handoff bundle to disk and return the output path."""
    bundle = build_handoff_bundle(
        events_df,
        bundle_id=bundle_id,
        source_system=source_system,
        timezone_name=timezone_name,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"external_event_handoff_{timestamp}.json"
    output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return output_path
