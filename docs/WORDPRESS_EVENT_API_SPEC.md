# WordPress Event API Payload Spec

This document describes the JSON payload that this repo sends to the
WordPress REST API when creating EventON events.

It is intended as an implementation reference for future Codex sessions.
Use it together with:

- [WORDPRESS_INTEGRATION_GUIDE](WORDPRESS_INTEGRATION_GUIDE.md)
- [EVENTON_PLUGIN_INSTALL](EVENTON_PLUGIN_INSTALL.md)
- [scripts/pipeline/wordpress_uploader.py](../scripts/pipeline/wordpress_uploader.py)

## Endpoint

The uploader creates events by POSTing JSON to:

```text
/wp-json/wp/v2/ajde_events
```

`ajde_events` is the EventON custom post type.

## Payload Shape

The uploader builds the create payload in
[scripts/pipeline/wordpress_uploader.py](../scripts/pipeline/wordpress_uploader.py).
The top-level payload looks like this:

```json
{
  "title": "Blue Angels Practice",
  "content": "Watch the Blue Angels practice over Pensacola Beach. Bring chairs and water.",
  "status": "draft",
  "type": "ajde_events",
  "featured_media": 4123,
  "event_location": 87,
  "event_type": [14, 22],
  "meta": {
    "evcal_srow": "1778079600",
    "evcal_erow": "1778086800",
    "evcal_start_date": "2026-06-05",
    "evcal_start_time_hour": "10",
    "evcal_start_time_min": "00",
    "evcal_start_time_ampm": "am",
    "evcal_end_date": "2026-06-05",
    "evcal_end_time_hour": "12",
    "evcal_end_time_min": "00",
    "evcal_end_time_ampm": "pm",
    "_event_uid": "perdido:blue-angels-practice:2026-06-05",
    "_venue_id": "pensacola_beach_waterfront",
    "evcal_lmlink": "https://example.org/events/blue-angels-practice",
    "_event_cost": "Free admission.",
    "_event_type": "free",
    "_paid_status": "free",
    "_is_free": "yes",
    "_event_image_id": "4123",
    "_event_image_url": "https://sandbox.envisionperdido.org/wp-content/uploads/2026/05/blue-angels.jpg",
    "_event_tags": "family_friendly,outdoor,festival",
    "_event_tags_display": "Family Friendly,Outdoor,Festival",
    "_evcal_exlink_option": "1",
    "_evcal_exlink_target": "yes",
    "evo_hide_endtime": "no",
    "evo_year_long": "no",
    "_evo_featured_img": "no"
  }
}
```

Notes:

- `featured_media`, `event_location`, and `event_type` are optional.
- `meta` always exists, but its contents vary by the event row.
- Events are created as `draft` first. Publishing is a later update step.

## Top-Level Field Reference

### `title`

- Type: `string`
- Meaning: WordPress post title for the EventON event.
- Source: event row `title`

### `content`

- Type: `string`
- Meaning: Main body/description for the event.
- Source: event row `description`

### `status`

- Type: `string`
- Current value: `"draft"`
- Meaning: Initial WordPress post status.
- Current behavior: uploader creates drafts before publish.

### `type`

- Type: `string`
- Current value: `"ajde_events"`
- Meaning: EventON custom post type.

### `featured_media`

- Type: `integer`
- Meaning: WordPress media attachment ID for the event image.
- Source: returned by the media upload flow when an image is available.

### `event_location`

- Type: `integer`
- Meaning: EventON location taxonomy term ID.
- Source: resolved from `normalized_location` or `location`
- Important: this is sent as a top-level field, not left inside `meta`

### `event_type`

- Type: `array[integer]`
- Meaning: EventON taxonomy term IDs for tags/categories.
- Source: uploader resolves or creates taxonomy terms from event tag slugs.

## `meta` Field Reference

## Date and Time Fields

These are built from the event row `start` and `end` values.

### `evcal_srow`

- Type: `string`
- Meaning: Event start timestamp used by EventON.
- Source: `start`
- Important: uploader currently stores a "local epoch" workaround, not a
  normalized UTC epoch.

### `evcal_erow`

- Type: `string`
- Meaning: Event end timestamp used by EventON.
- Source: `end`

### `evcal_start_date`

- Type: `string`
- Format: `YYYY-MM-DD`
- Meaning: Display start date.

### `evcal_start_time_hour`

- Type: `string`
- Format: 12-hour clock, zero-padded
- Example: `"10"`

### `evcal_start_time_min`

- Type: `string`
- Example: `"00"`

### `evcal_start_time_ampm`

- Type: `string`
- Allowed values: `"am"`, `"pm"`

### `evcal_end_date`

- Type: `string`
- Format: `YYYY-MM-DD`

### `evcal_end_time_hour`

- Type: `string`

### `evcal_end_time_min`

- Type: `string`

### `evcal_end_time_ampm`

- Type: `string`
- Allowed values: `"am"`, `"pm"`

## Identity and Dedup Fields

### `_event_uid`

- Type: `string`
- Meaning: Stable unique ID used for deduplication across runs.
- Source: event row `uid`
- Critical behavior: uploader checks this before creating a new event.

### `_venue_id`

- Type: `string`
- Meaning: Internal normalized venue identifier from this pipeline.
- Source: event row `venue_id`
- Note: this is a project-specific reference field, not native WordPress.

## Link and Cost Fields

### `evcal_lmlink`

- Type: `string`
- Meaning: Source or outbound URL for the event.
- Source: event row `url`

### `_event_cost`

- Type: `string`
- Meaning: Extracted cost text such as `Free`, `$10`, or `Tickets $25`.
- Source: event row `cost_text`

### `_event_type`

- Type: `string`
- Meaning: Internal free/paid classification string.
- Source: event row `event_type`

### `_paid_status`

- Type: `string`
- Meaning: Normalized payment state.
- Source: event row `paid_status`

### `_is_free`

- Type: `string`
- Allowed values: `"yes"`, `"no"`
- Meaning: Boolean free/paid flag serialized for WordPress meta.
- Source: event row `is_free`

## Image Fields

### `_event_image_id`

- Type: `string`
- Meaning: WordPress media ID stored in meta for reference.
- Source: uploaded media result

### `_event_image_url`

- Type: `string`
- Meaning: Public URL for the uploaded image.
- Source: media lookup after image upload

## Tag Fields

### `_event_tags`

- Type: `string`
- Meaning: Internal tag slugs, comma-separated.
- Example: `"family_friendly,outdoor,live_music"`

### `_event_tags_display`

- Type: `string`
- Meaning: Human-readable tag labels, comma-separated.
- Example: `"Family Friendly,Outdoor,Live Music"`

## EventON Behavior Flags

### `_evcal_exlink_option`

- Type: `string`
- Current value: `"1"`
- Meaning: enable external link behavior

### `_evcal_exlink_target`

- Type: `string`
- Current value: `"yes"`
- Meaning: open external links in a new tab/window

### `evo_hide_endtime`

- Type: `string`
- Current value: `"no"`
- Meaning: show end time in EventON

### `evo_year_long`

- Type: `string`
- Current value: `"no"`
- Meaning: event is not year-long

### `_evo_featured_img`

- Type: `string`
- Current value: `"no"`
- Meaning: do not show the featured image in the EventON popup/details view

## Source Row to Payload Mapping

This is the practical mapping from the event dataframe row to the API payload.

| Source row field | Payload field | Notes |
| --- | --- | --- |
| `title` | `title` | top-level |
| `description` | `content` | top-level |
| `start` | `meta.evcal_srow` + display start fields | transformed |
| `end` | `meta.evcal_erow` + display end fields | transformed |
| `uid` | `meta._event_uid` | dedup key |
| `normalized_location` or `location` | `event_location` | resolved to taxonomy term ID |
| `venue_id` | `meta._venue_id` | internal reference |
| `url` | `meta.evcal_lmlink` | outbound/source URL |
| `cost_text` | `meta._event_cost` | extracted text |
| `event_type` | `meta._event_type` | internal classification |
| `paid_status` | `meta._paid_status` | internal classification |
| `is_free` | `meta._is_free` | serialized to `yes` / `no` |
| `tags` | `event_type`, `meta._event_tags`, `meta._event_tags_display` | taxonomy plus mirrored meta |
| image column | `featured_media`, `meta._event_image_id`, `meta._event_image_url` | if image upload succeeds |

## Create vs Publish

The uploader uses a two-step model:

1. Create the event as a draft with the payload above.
2. Publish later with an update call to the created event.

Future Codex sessions should not assume that a successful create call means the
event is already published.

## Validation and Invariants for Future Changes

Another Codex session changing this flow should preserve these behaviors unless
there is an explicit migration plan:

- `_event_uid` must remain stable and queryable for deduplication.
- `event_location` must remain a top-level taxonomy assignment.
- `event_type` term IDs should stay top-level when taxonomy assignment works.
- Event create should remain idempotent across reruns.
- Date/time fields must remain consistent with the site timezone logic.

## Known Quirks

### UID lookup depends on WordPress-side support

The uploader expects the WordPress/EventON side to support querying by
`_event_uid`. A sandbox plugin fix was required to make these lookups reliable.

### `get_event_by_uid()` should verify exact meta matches

Even when the endpoint returns a record, the uploader should only treat it as a
duplicate if the returned event's `meta._event_uid` exactly matches the
requested UID.

### Local epoch workaround

The timestamp fields currently use a "local epoch" workaround. Any Codex
session touching time logic should review the surrounding implementation in
[scripts/pipeline/wordpress_uploader.py](../scripts/pipeline/wordpress_uploader.py)
before changing it.
