# Play Perdido Event Submission Contract
## Canonical Ingest Spec for Events, Locations, and Discovery Metadata

---

# Purpose

This document defines the contract an external event submission engine must use when pushing events into Play Perdido.

This is not just a transport schema.

It is a product contract intended to protect:

- the Play Perdido taxonomy model
- the discovery-first UI/UX
- the local brand voice
- the geographic discipline of the site
- the requirement that EventON remains the engine, not the raw interface

Use this together with:

- [06_play_perdido_data_model_taxonomy_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/06_play_perdido_data_model_taxonomy_strategy.md)
- [02_play_perdido_wordpress_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/02_play_perdido_wordpress_strategy.md)
- [09_play_perdido_llm_content_rubric_usage.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/09_play_perdido_llm_content_rubric_usage.md)
- [play_perdido_event_submission_contract.schema.json](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/contracts/play_perdido_event_submission_contract.schema.json)

---

# Contract Status

Current version:

- `1.0.0`

Payloads should include:

- `contract_version`

Breaking field or enum changes should increment the major version.

---

# Non-Negotiable Product Rules

The submission engine may suggest.

Play Perdido remains authoritative.

The ingest layer must enforce these rules:

1. Public categories must use the Play Perdido category model only.
2. Remote or source-system categories must never become public taxonomy automatically.
3. Every event must link to a structured location object.
4. Plain-text venue strings without a linked location are not acceptable as the final stored model.
5. Geography must remain Perdido-first.
6. The contract may carry raw source text, but Play Perdido may rewrite teasers, summaries, and excerpts to match the local brand voice.
7. The payload must support discovery-first rendering, not only archival storage.

---

# Canonical Submission Shape

Each push payload is a bundle with:

- source metadata
- zero or more location records
- one or more event records

High-level shape:

```json
{
  "contract_version": "1.0.0",
  "source_system": {},
  "locations": [],
  "events": []
}
```

---

# Source System Contract

The payload must identify where the records came from.

Required fields:

- `source_system.name`
- `source_system.environment`
- `source_system.exported_at`

Recommended fields:

- `source_system.base_url`
- `source_system.operator`

This allows Play Perdido to:

- trace provenance
- debug bad imports
- keep remote metadata separate from public taxonomy

---

# Location Contract

## Purpose

Locations are first-class data.

They are not just strings inside the event body.

The submission engine must send reusable location objects so Play Perdido can:

- attach multiple events to the same venue
- render consistent venue labels
- support later venue filtering
- support future cross-links across music, food, and adventures

## Required Fields

- `external_id`
- `name`
- `address_line_1`
- `city`
- `region`
- `postal_code`
- `country_code`
- `venue_type`

## Recommended Fields

- `address_line_2`
- `latitude`
- `longitude`
- `website_url`
- `phone`
- `service_area`
- `perdido_fit`

## Venue Type Enum

Allowed `venue_type` values:

- `bar`
- `restaurant`
- `beach`
- `marina`
- `park`
- `trailhead`
- `market`
- `event-space`
- `music-venue`
- `resort`
- `museum`
- `education`
- `golf-course`
- `community-space`
- `outdoor-site`
- `other`

## Perdido Fit Enum

Allowed `perdido_fit` values:

- `core`
- `adjacent`
- `supporting`
- `out_of_area`

Meaning:

- `core`: clearly in the intended Perdido footprint
- `adjacent`: near enough to support the product without weakening the core identity
- `supporting`: may be used sparingly when highly relevant to local users
- `out_of_area`: should generally be rejected from public Play Perdido views

## Location Rules

1. `name` must be human-readable and venue-first.
2. Raw address strings must not be used as the display name unless no better venue name exists.
3. Placeholder labels like `Departure Location` are invalid as final location names.
4. If the source only exposes an address, the submission engine should still send a structured location object and mark the record for review.
5. If coordinates are known, include them.

---

# Event Contract

## Required Event Fields

- `external_id`
- `title`
- `summary`
- `body`
- `start_at`
- `end_at`
- `timezone`
- `status`
- `location_external_id`
- `categories`
- `perdido_fit`

## Recommended Event Fields

- `featured_image`
- `audience_tags`
- `discovery_tags`
- `cost`
- `is_free`
- `cta`
- `organizer`
- `source_url`
- `raw_source_categories`
- `raw_source_location_text`
- `review_notes`

## Status Enum

Allowed `status` values:

- `draft`
- `review`
- `publish`
- `cancelled`

Use:

- `draft` when fields are incomplete
- `review` when the event is structurally valid but still needs human curation
- `publish` when the record is ready for ingestion and public display
- `cancelled` when the event should remain stored but clearly labeled

## Category Enum

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

## Category Rules

1. Categories answer: “What kind of thing is this?”
2. Categories do not express source ownership, member status, or chamber affiliation.
3. Each event should usually have `1` to `3` categories.
4. The engine may send `raw_source_categories`, but those are advisory only.
5. If a source category conflicts with the Play Perdido model, the canonical Play Perdido category wins.

## Audience Tag Enum

Allowed `audience_tags` values:

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

## Discovery Tag Enum

Allowed `discovery_tags` values:

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

These do not replace categories.

They exist to help the product route events into the correct discovery surfaces.

## Event Copy Rules

The submission engine must send useful structured text, but Play Perdido may rewrite surface copy.

Required text expectations:

- `title`: concise and specific
- `summary`: `1` to `3` sentences, practical first
- `body`: fuller detail for detail views and EventON expansion

Content rules:

1. Avoid chamber-style boilerplate.
2. Avoid keyword junk and source-system fragments.
3. Avoid all-caps promotional copy unless part of a proper noun.
4. Keep `summary` useful on mobile.
5. If the source text is poor, include the raw body and mark the record for `review`.

The brand rubric applies:

- copy should feel local
- specific
- useful
- discovery-oriented
- consistent with `Get Lost in Perdido`

## Event Time Rules

1. `start_at` and `end_at` must be valid ISO 8601 timestamps.
2. `timezone` must be an IANA timezone like `America/Chicago`.
3. Multi-day events are allowed.
4. All-day events should still declare an explicit time treatment in source logic.

## Media Rules

If available, send a `featured_image` object with:

- `source_url`
- `alt_text`
- `copyright_notice` if known

Image guidance:

1. Use real event or place imagery when possible.
2. Avoid generic flyer spam as the preferred featured image.
3. If no usable image exists, the event may still ingest, but should expect lower discovery quality.

## CTA Rules

Optional CTA fields:

- `label`
- `url`
- `target`

Allowed `target`:

- `self`
- `blank`

CTA labels should remain practical:

- `View Details`
- `Get Tickets`
- `Register`
- `Learn More`

Avoid:

- vague promo language
- salesy phrases

---

# Moderation and Review Contract

The submission engine should support review-state hints.

Recommended fields:

- `review_notes`
- `quality_score`
- `confidence_score`
- `suggested_featured`

Play Perdido may reject or downgrade events when:

- the event is outside the intended geography
- the category mapping is weak
- the location is unresolved
- the copy is junky
- the image quality is too poor
- the record weakens the discovery experience

---

# Geography Enforcement

Play Perdido is geographically disciplined.

The engine must not assume that every regional event belongs on the site.

Required behavior:

1. Mark the event with `perdido_fit`.
2. Mark the linked location with `perdido_fit` when known.
3. Preserve `source_url` for review.
4. If a record is clearly outside the product footprint, send it as `review` or exclude it upstream.

This prevents spillover inventory from quietly turning the site into a generic Gulf Coast dump.

---

# WordPress and EventON Mapping

This is the intended local mapping.

## Event Mapping

- Event record -> `ajde_events` post
- `title` -> post title
- `summary` -> post excerpt or curated teaser source
- `body` -> post content
- `featured_image.source_url` -> featured image sideload

## Time Mapping

- `start_at`
- `end_at`
- `timezone`

These map into EventON date/time meta fields.

## Category Mapping

- `categories[]` -> `event_type` taxonomy terms

## Location Mapping

- location object -> `event_location` taxonomy term
- `location_external_id` -> ingest resolver for the correct linked term

## Source Metadata Mapping

Recommended local meta:

- `_pp_source_system`
- `_pp_source_event_id`
- `_pp_source_url`
- `_pp_raw_source_categories`
- `_pp_perdido_fit`
- `_pp_quality_score`
- `_pp_review_notes`

---

# Rejection Conditions

The ingest layer should reject the payload when:

1. `contract_version` is missing or unsupported
2. an event references a missing location
3. categories fall outside the canonical enum
4. timestamps are invalid
5. required content fields are empty
6. the location is only a plain-text string with no structured record

The ingest layer should accept into `review` rather than `publish` when:

1. location data is weak but recoverable
2. geography is borderline
3. copy needs rewriting
4. source categories were noisy but usable
5. image quality is uncertain

---

# Example Payload

```json
{
  "contract_version": "1.0.0",
  "source_system": {
    "name": "perdido-submission-engine",
    "environment": "production",
    "exported_at": "2026-05-05T18:30:00Z",
    "base_url": "https://submissions.example.com"
  },
  "locations": [
    {
      "external_id": "venue-bar45-one-club",
      "name": "Bar45 at ONE Club",
      "address_line_1": "20050 Oak Road East",
      "city": "Gulf Shores",
      "region": "AL",
      "postal_code": "36542",
      "country_code": "US",
      "venue_type": "bar",
      "perdido_fit": "adjacent",
      "latitude": 30.281,
      "longitude": -87.689
    }
  ],
  "events": [
    {
      "external_id": "evt-bar45-friday-music-2026-04-24",
      "title": "Friday Night Live Music at Bar45",
      "summary": "Start the weekend with local live music, happy hour, and an easy indoor hangout at Bar45 inside ONE Club.",
      "body": "Live music runs Friday evening after happy hour. This event works best for visitors and locals looking for a relaxed night out near Perdido.",
      "start_at": "2026-04-24T18:00:00-05:00",
      "end_at": "2026-04-24T21:00:00-05:00",
      "timezone": "America/Chicago",
      "status": "publish",
      "location_external_id": "venue-bar45-one-club",
      "categories": [
        "Live Music",
        "Food & Drink",
        "Nightlife"
      ],
      "audience_tags": [
        "Date night",
        "Recurring"
      ],
      "discovery_tags": [
        "tonight",
        "live-music"
      ],
      "perdido_fit": "adjacent",
      "source_url": "https://example.com/events/bar45-friday-music",
      "featured_image": {
        "source_url": "https://example.com/media/bar45-friday.jpg",
        "alt_text": "Live music setup at Bar45"
      },
      "cta": {
        "label": "View Details",
        "url": "https://example.com/events/bar45-friday-music",
        "target": "blank"
      },
      "raw_source_categories": [
        "Happy Hour",
        "Live Music"
      ]
    }
  ]
}
```

---

# Operational Guidance

When building the submission engine:

1. validate against the JSON Schema before sending
2. normalize source categories into the Play Perdido enum before transport
3. resolve or create structured locations before transport
4. send raw source hints only as metadata, never as public taxonomy
5. mark weak records as `review`
6. expect Play Perdido to curate surface copy for brand fit

This contract exists to protect the product from becoming a generic calendar ingest pipe.
