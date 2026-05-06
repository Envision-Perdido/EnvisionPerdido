# Play Perdido Implementation Plan

This document explains how the Envision Perdido pipeline should enforce the
Play Perdido remote handoff bundle stored in this directory.

Read these first:

1. [00_READ_ME_FIRST](00_READ_ME_FIRST.md)
2. [01 Play Perdido Event Submission Contract](01_play_perdido_event_submission_contract.md)
3. [02 Submission Schema](02_play_perdido_event_submission_contract.schema.json)
4. [03 Event LLM Copy Contract](03_play_perdido_event_llm_copy_contract.md)

## Current Gap Summary

The current pipeline does not yet satisfy the handoff contract.

- The optional OpenAI step in
  [scripts/pipeline/automated_pipeline.py](/opt/EnvisionPerdido/scripts/pipeline/automated_pipeline.py:1154)
  and
  [scripts/pipeline/regenerate_descriptions.py](/opt/EnvisionPerdido/scripts/pipeline/regenerate_descriptions.py:1)
  only rewrites a description field with a generic prompt.
- The WordPress uploader in
  [scripts/pipeline/wordpress_uploader.py](/opt/EnvisionPerdido/scripts/pipeline/wordpress_uploader.py:536)
  creates drafts from `title` and `description`, but does not validate a
  canonical Play Perdido payload, does not store a `summary`/excerpt field, and
  does not enforce the handoff review gates.
- The export flow in
  [scripts/pipeline/automated_pipeline.py](/opt/EnvisionPerdido/scripts/pipeline/automated_pipeline.py:1279)
  still treats CSV as the main interchange artifact.

## Enforcement Goals

The pipeline should enforce these rules before anything reaches WordPress:

1. Payload shape must match the Play Perdido contract and schema.
2. Public categories must use the canonical Play Perdido enums only.
3. Every event must resolve to a structured location object.
4. Weak or uncertain records must downgrade to `review` instead of silently
   publishing.
5. LLM-generated copy must pass the Play Perdido copy contract and quality bar.
6. Uploads must preserve source, review, and quality metadata for auditability.

## Implementation Phases

## Phase 1: Add a Canonical Submission Layer

Create a Play Perdido contract module that converts internal event records into
the canonical bundle defined by
[01_play_perdido_event_submission_contract.md](01_play_perdido_event_submission_contract.md)
and
[02_play_perdido_event_submission_contract.schema.json](02_play_perdido_event_submission_contract.schema.json).

Recommended scope:

- Add a pipeline-side builder that emits:
  - `contract_version`
  - `source_system`
  - `locations`
  - `events`
- Export the bundle as JSON in `output/pipeline/` alongside existing CSV output.
- Preserve source hints like `source_url`, `raw_source_categories`, and raw
  location text as metadata only.

Suggested implementation location:

- `scripts/pipeline/play_perdido_contract.py`

## Phase 2: Add Schema Validation and Rejection Gates

Validate the canonical bundle before upload.

Hard-fail on:

- missing or unsupported `contract_version`
- event records that reference missing locations
- non-canonical categories
- invalid timestamps
- empty required content fields
- location data that never resolves beyond plain text

Downgrade to `review` instead of `publish` on:

- weak but recoverable location data
- borderline geography
- weak source copy
- uncertain image quality
- low-confidence taxonomy mapping

Suggested implementation:

- Add a validator that reads the JSON schema from this directory.
- Return a structured validation report for each event and for the bundle.
- Store the validation result in the run output for audit purposes.

## Phase 3: Replace the Generic Description Rewriter

Refactor the current OpenAI description step into a Play Perdido content
generation workflow aligned with
[03_play_perdido_event_llm_copy_contract.md](03_play_perdido_event_llm_copy_contract.md).

The new copy layer should generate:

- `normalized_title`
- `summary`
- `detail_copy`
- `cta_label`
- `copy_quality_report`
- `review_required`
- `why_review_required`

Required workflow:

1. Extract supported facts only.
2. Draft copy.
3. Score against the Play Perdido rubric.
4. Run an analytical rewrite pass.
5. Re-score.
6. Escalate to human review after repeated failure.

Important constraint:

- The model may clarify, but must not invent facts.

## Phase 4: Make Review State Block Publish

The current pipeline can auto-upload after export when `AUTO_UPLOAD` is enabled
at
[scripts/pipeline/automated_pipeline.py](/opt/EnvisionPerdido/scripts/pipeline/automated_pipeline.py:1297).
That is too permissive for this contract.

Update the workflow so auto-upload only operates on events that:

- passed schema validation
- passed category and location normalization
- passed copy quality thresholds
- are not marked `review`
- are not marked `out_of_area` unless there is an explicit override

Events that fail those checks should still export and appear in review email and
logs, but should not auto-publish.

## Phase 5: Update WordPress Mapping

Refactor the uploader to consume contract-shaped records instead of relying on a
minimal CSV row.

Target mapping:

- `title` -> post title
- `summary` -> excerpt or curated teaser field
- `body` -> post content
- `categories[]` -> `event_type` taxonomy terms
- location object -> resolved `event_location`
- `featured_image.source_url` -> featured image sideload
- source and QA fields -> `_pp_*` meta fields

Recommended custom meta:

- `_pp_source_system`
- `_pp_source_event_id`
- `_pp_source_url`
- `_pp_raw_source_categories`
- `_pp_perdido_fit`
- `_pp_quality_score`
- `_pp_review_notes`

## Phase 6: Add Geography and Taxonomy Normalization

Create explicit mapping rules for:

- Play Perdido categories
- `perdido_fit`
- audience tags
- discovery tags
- venue type

This should be deterministic and should not depend on source taxonomy becoming
public taxonomy automatically.

## Phase 7: Add Audit Artifacts

Every Play Perdido-eligible run should persist:

- canonical submission JSON
- schema validation report
- copy quality report
- rejected events
- review-downgraded events
- final upload decision summary

This creates an auditable trail that the current CSV-only flow does not provide.

## Recommended Delivery Order

1. Build the canonical contract model and JSON export.
2. Add schema validation and review gating.
3. Refactor the LLM step into structured copy generation plus scoring.
4. Update the uploader to consume contract-shaped data and store `_pp_*` meta.
5. Update operator docs after the enforcement path is real.

## Files Most Likely To Change

- `scripts/pipeline/automated_pipeline.py`
- `scripts/pipeline/regenerate_descriptions.py`
- `scripts/pipeline/wordpress_uploader.py`
- new contract/validation helpers under `scripts/pipeline/`
- docs in `docs/remote-handoffs/` and `docs/WORDPRESS_INTEGRATION_GUIDE.md`

## Operational Rule

If the system cannot produce contract-valid, high-quality, review-safe event
records, it should route them to `review` instead of publishing low-trust copy
or weak metadata.
