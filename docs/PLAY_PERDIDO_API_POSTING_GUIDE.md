# Play Perdido API Posting Guide

This document explains how to connect to the existing WordPress/EventON API and
post events in a way that complies with the Play Perdido contract stored under
[docs/remote-handoffs/event-engine-bundle](remote-handoffs/event-engine-bundle/00_READ_ME_FIRST.md).

This is not just a transport guide.

The destination site expects:

- specific public categories
- specific audience and discovery tags
- structured locations
- disciplined geography
- user-facing copy that is useful and clean

If an upstream system sends technically valid but contract-invalid records,
WordPress will still accept them and the site will accumulate junk taxonomy and
weak copy.

Use this document together with:

- [WORDPRESS_EVENT_API_SPEC](WORDPRESS_EVENT_API_SPEC.md)
- [WORDPRESS_INTEGRATION_GUIDE](WORDPRESS_INTEGRATION_GUIDE.md)
- [Play Perdido Event Submission Contract](remote-handoffs/event-engine-bundle/01_play_perdido_event_submission_contract.md)
- [Play Perdido LLM Copy Contract](remote-handoffs/event-engine-bundle/03_play_perdido_event_llm_copy_contract.md)
- [Play Perdido Taxonomy Strategy](remote-handoffs/event-engine-bundle/06_play_perdido_data_model_taxonomy_strategy.md)

## Purpose

The current site-facing API is still the WordPress/EventON REST API.

The Play Perdido contract sits above that API and should govern what gets sent.

The correct flow is:

1. build a contract-compliant event bundle
2. validate taxonomy, geography, copy, and locations
3. downgrade weak records to `review`
4. transform approved records into the EventON API payload
5. create drafts first
6. publish only when the record meets the quality bar

Do not post raw source events directly to WordPress.

## Current API Surface

The existing uploader in
[scripts/pipeline/wordpress_uploader.py](../scripts/pipeline/wordpress_uploader.py)
uses these endpoints:

- `POST /wp-json/wp/v2/ajde_events`
  Creates EventON events
- `POST /wp-json/wp/v2/ajde_events/{id}`
  Updates or publishes existing events
- `GET/POST /wp-json/wp/v2/event_location`
  Resolves or creates location taxonomy terms
- `GET/POST /wp-json/wp/v2/event_type`
  Resolves or creates EventON taxonomy terms
- `POST /wp-json/wp/v2/media`
  Uploads featured images

Authentication is via WordPress application password over basic auth.

Required environment variables in the current implementation:

- `WP_SITE_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`

## What The API Accepts vs What The Contract Requires

WordPress/EventON currently accepts a payload shaped like:

```json
{
  "title": "Friday Night Live Music at Bar45",
  "content": "Main event body text",
  "status": "draft",
  "type": "ajde_events",
  "event_location": 87,
  "event_type": [14, 22],
  "meta": {
    "evcal_srow": "1778079600",
    "evcal_erow": "1778086800",
    "_event_uid": "perdido:event:123",
    "_event_tags": "live_music,food_drink"
  }
}
```

That payload is not sufficient for Play Perdido compliance by itself.

Before creating it, the upstream system should already have a canonical event
record shaped like the Play Perdido contract:

```json
{
  "external_id": "evt-bar45-friday-music-2026-04-24",
  "title": "Friday Night Live Music at Bar45",
  "summary": "Start the weekend with local live music and an easy indoor hangout.",
  "body": "Live music runs Friday evening after happy hour. Good fit for a relaxed night out near Perdido.",
  "start_at": "2026-04-24T18:00:00-05:00",
  "end_at": "2026-04-24T21:00:00-05:00",
  "timezone": "America/Chicago",
  "status": "publish",
  "location_external_id": "venue-bar45-one-club",
  "categories": ["Live Music", "Food & Drink", "Nightlife"],
  "audience_tags": ["Date night", "Recurring"],
  "discovery_tags": ["tonight", "live-music", "food-drink"],
  "perdido_fit": "adjacent",
  "source_url": "https://source.example.com/events/bar45-friday",
  "raw_source_categories": ["Music", "Nightlife"],
  "review_notes": "",
  "quality_score": 0.91
}
```

The API payload should be treated as a downstream representation of that
contract record, not the source of truth.

## Connection and Authentication

The existing uploader uses basic auth against the WordPress REST API.

Example Python setup:

```python
import requests

site_url = "https://sandbox.envisionperdido.org"
api_base = f"{site_url.rstrip('/')}/wp-json/wp/v2"
auth = ("your-wordpress-username", "your-application-password")

session = requests.Session()
response = session.get(f"{api_base}/event_location", auth=auth, timeout=30)
response.raise_for_status()
```

Important:

- use the WordPress login username, not a display name
- use an application password, not the normal account password
- keep the API target in environment variables, not hardcoded

## Contract-First Posting Workflow

## Step 1: Build The Canonical Bundle

Before touching the API, produce a bundle with:

- `contract_version`
- `source_system`
- `locations`
- `events`

This is the reviewable artifact.

Do not jump straight from CSV rows to EventON payloads when building a
Play Perdido-compliant path.

## Step 2: Validate Required Product Rules

Reject or downgrade before upload when any of these are true:

- missing or unsupported `contract_version`
- invalid `categories`
- invalid `audience_tags`
- invalid `discovery_tags`
- unresolved `location_external_id`
- location exists only as plain text
- invalid timestamps
- empty required copy fields
- `perdido_fit` is weak or unknown

Contract compliance is not optional, because the destination site does not
enforce these semantics for us.

## Step 3: Normalize Taxonomy

Play Perdido public taxonomy must be canonical.

Allowed public categories:

- `Live Music`
- `Family Friendly`
- `Food & Drink`
- `Markets & Makers`
- `Community`
- `Arts & Culture`
- `Beach & Water`
- `Nature & Outdoors`
- `Free`
- `Classes & Workshops`
- `Nightlife`
- `Seasonal`

Allowed audience tags:

- `Kid-friendly`
- `Pet friendly`
- `Date night`
- `Low-cost`
- `Outdoor`
- `On the water`
- `Recurring`
- `Local favorite`
- `Educational`
- `Volunteer`
- `Food available`
- `Rainy day`

Allowed discovery tags:

- `today`
- `tonight`
- `this-weekend`
- `live-music`
- `family`
- `free`
- `food-drink`
- `on-the-water`
- `markets`
- `nature`
- `nightlife`

Do not:

- post raw source categories directly
- use internal pipeline slugs as public taxonomy
- let EventON term creation happen from arbitrary source labels

Example of what not to do:

- internal tag `food_drink` should not become a public category label by accident
- source category `Member Event` should never become a public taxonomy term

## Step 4: Resolve Structured Locations

Every event must link to a structured location object.

Required location fields in the contract:

- `external_id`
- `name`
- `address_line_1`
- `city`
- `region`
- `postal_code`
- `country_code`
- `venue_type`

Posting rule:

1. resolve the contract location record by `location_external_id`
2. map it to an EventON `event_location` term
3. only then create the event post

Do not treat a raw venue string as sufficient final data.

## Step 5: Map Contract Fields To EventON Payload

Recommended mapping:

- contract `title` -> WordPress `title`
- contract `body` -> WordPress `content`
- contract `summary` -> excerpt or custom teaser field
- contract `location_external_id` -> resolved `event_location`
- contract `categories` -> EventON `event_type` terms
- contract `featured_image.source_url` -> media upload + `featured_media`

Recommended Play Perdido metadata in `meta`:

- `_pp_source_system`
- `_pp_source_event_id`
- `_pp_source_url`
- `_pp_raw_source_categories`
- `_pp_perdido_fit`
- `_pp_quality_score`
- `_pp_review_notes`
- `_pp_audience_tags`
- `_pp_discovery_tags`

These should exist alongside existing EventON-required fields like:

- `evcal_srow`
- `evcal_erow`
- `_event_uid`

## Step 6: Create As Draft First

Even when the contract record says `publish`, the safer operational pattern is:

1. create as `draft`
2. confirm taxonomy, location, and media mapping succeeded
3. publish in a second call only for records that passed all gates

That keeps the transport flow aligned with the product contract.

## Example Create Call

Example transport payload after contract validation:

```json
{
  "title": "Friday Night Live Music at Bar45",
  "content": "Live music runs Friday evening after happy hour. Good fit for a relaxed night out near Perdido.",
  "status": "draft",
  "type": "ajde_events",
  "featured_media": 4123,
  "event_location": 87,
  "event_type": [14, 22, 31],
  "meta": {
    "evcal_srow": "1777071600",
    "evcal_erow": "1777082400",
    "_event_uid": "evt-bar45-friday-music-2026-04-24",
    "_pp_source_system": "perdido-submission-engine",
    "_pp_source_event_id": "evt-bar45-friday-music-2026-04-24",
    "_pp_source_url": "https://source.example.com/events/bar45-friday",
    "_pp_raw_source_categories": "Music,Nightlife",
    "_pp_perdido_fit": "adjacent",
    "_pp_quality_score": "0.91",
    "_pp_review_notes": "",
    "_pp_audience_tags": "Date night,Recurring",
    "_pp_discovery_tags": "tonight,live-music,food-drink",
    "_event_tags": "live_music,food_drink,nightlife",
    "_event_tags_display": "Live Music,Food & Drink,Nightlife"
  }
}
```

## Copy Quality Requirements

The API should not be used as a blind sink for source copy.

Before upload:

- `title` must be concise and specific
- `summary` must be practical and mobile-friendly
- `body` must be fuller but still disciplined
- no chamber boilerplate
- no keyword stuffing
- no fabricated event facts

If the source text is weak:

- preserve raw data internally
- generate cleaned copy only if it follows the Play Perdido copy contract
- otherwise mark the event for `review`

## Review and Rejection Policy

Events should not be posted for public use when:

- categories are uncertain
- the location is unresolved
- geography is out of footprint
- copy quality is weak
- the image is spammy or missing where quality expectations require one

In those cases:

- keep the canonical record
- write a validation or review artifact
- do not auto-publish

## What Is Already Implemented vs Not Yet

Already implemented in this repo:

- EventON event creation
- location term resolution
- event type term resolution
- media upload
- `_event_uid` deduplication

Not yet fully implemented against the Play Perdido contract:

- canonical submission bundle output
- schema validation
- canonical category mapping
- audience/discovery tag enforcement
- `perdido_fit` enforcement
- summary/excerpt handling
- `_pp_*` audit metadata
- contract-driven review gates

## Recommended Implementation Order

If a future Codex session is building this for real, use this order:

1. build the canonical Play Perdido bundle
2. add enum and taxonomy validation
3. add deterministic category/tag/fit mapping
4. add review gating
5. update uploader transformation
6. add structured copy generation only after the data model is stable

## Operational Rule

The API is not the source of truth.

The Play Perdido contract is the source of truth.

Only contract-valid, taxonomy-safe, geography-safe, user-facing-quality event
records should be transformed into the WordPress/EventON API payload.
