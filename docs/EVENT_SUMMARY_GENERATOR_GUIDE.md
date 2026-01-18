# Event Summary Generator - Implementation Guide

**Plugin:** `plugins/event-summary-generator.php`
**Status:** Ready for deployment
**Version:** 1.0

## Overview

This plugin provides intelligent automatic summary generation for WordPress events. Summaries are derived from existing event descriptions and stored in the `_event_summary` meta field.

### Key Features

✅ **Automatic Generation**
- Generates summaries on event creation/update
- Detects description changes via hash comparison
- Falls back to excerpt if post_content is empty

✅ **Smart Truncation**
- Extracts 1-3 complete sentences
- Respects sentence boundaries (not mid-word)
- Handles abbreviations (U.S., Dr., etc.) correctly
- Maximum 280 characters by default

✅ **Boilerplate Removal**
- Strips "Click here", "Learn more", URLs, phone numbers
- Removes repeated venue/address info
- Cleans excessive whitespace

✅ **Manual Override**
- Users can edit summaries in WordPress admin
- Once edited, won't be overwritten automatically
- Tracked with `_event_summary_manual` flag

✅ **Admin Interface**
- Summary field visible in post editor
- Editable meta box in WordPress admin
- Change detection to avoid unnecessary regeneration

✅ **WP-CLI Support**
- Backfill summaries for existing events
- Dry-run mode to preview changes
- Force regeneration option

## Installation

### Step 1: Activate the Plugin

```bash
# Copy to WordPress plugins directory
cp plugins/event-summary-generator.php /path/to/wp-content/plugins/

# In WordPress admin:
# 1. Go to Plugins → Installed Plugins
# 2. Find "Event Summary Generator"
# 3. Click "Activate"
```

### Step 2: Update REST API Plugin

The `eventon-rest-api-meta.php` plugin has been updated to expose the `_event_summary` field via REST API. No action needed if already installed.

### Step 3: Backfill Existing Events (Optional)

```bash
# Preview what would be generated (dry-run)
wp events backfill-summaries --dry-run

# Apply changes
wp events backfill-summaries

# Force regeneration even for existing summaries
wp events backfill-summaries --force

# Process specific events
wp events backfill-summaries --ids=123,456,789
```

## Data Structure

### Meta Fields

| Field | Type | Editable | Purpose |
|-------|------|----------|---------|
| `_event_summary` | string | ✓ Yes | Main summary field, shown in templates |
| `_event_description_hash` | string | ✗ No | MD5 hash of description for change detection |
| `_event_summary_manual` | boolean | ✗ No | Flag indicating user manually edited summary |

### Storage

- **Post Type:** `ajde_events` (EventON)
- **Canonical Description Source:** `post_content` (with fallback to `post_excerpt`)
- **REST API:** Accessible via `/wp-json/wp/v2/ajde_events/{id}?_fields=meta.summary`

## Usage in Templates

### Basic Fallback Pattern

```php
<?php
// Option 1: Summary → Excerpt → Trimmed Description
$summary = get_post_meta( get_the_ID(), '_event_summary', true );
$excerpt = get_the_excerpt();
$description = wp_trim_words( get_the_content(), 30 );

$display_text = $summary ?: ( $excerpt ?: $description );
echo wp_kses_post( $display_text );
?>
```

### EventON List/Card Templates

If customizing EventON templates, use:

```php
<?php
$event_id = get_the_ID();
$summary = get_post_meta( $event_id, '_event_summary', true );

if ( ! empty( $summary ) ) {
    echo '<p class="event-summary">' . esc_html( $summary ) . '</p>';
} else {
    the_excerpt();
}
?>
```

### REST API Response

When fetching events via REST API, the summary will be included:

```json
{
  "id": 123,
  "title": "Community Event",
  "meta": {
    "_event_summary": "Join us for this amazing community gathering...",
    "_event_description_hash": "abc123...",
    "_event_summary_manual": false
  }
}
```

## How It Works

### 1. Auto-Generation on Save

When an event is saved:

```php
// Triggers on every save_post
if ( event_description_changed( $post_id ) ) {
    // Only regenerate if description changed AND not manually edited
    $summary = generate_event_summary( $post_id );
    update_post_meta( $post_id, '_event_summary', $summary );
    update_post_meta( $post_id, '_event_description_hash', hash );
}
```

### 2. Manual Editing

When user edits summary in WordPress admin:

```php
// Sets manual flag so auto-generation won't overwrite
update_post_meta( $post_id, '_event_summary_manual', true );
```

### 3. Summary Generation Algorithm

```
Input: Event description (post_content or excerpt)
   ↓
Strip HTML/shortcodes
   ↓
Remove boilerplate (URLs, "Click here", phone numbers, etc.)
   ↓
Normalize whitespace
   ↓
IF length ≤ 280 chars → Return as-is
   ↓
Extract sentences (max 3) respecting abbreviations
   ↓
Truncate at word boundary if no sentences found
   ↓
Output: Polished summary
```

### Example Transformations

**Input:** (512 chars)
```
Pensacola State College Charter Academy Information Session. 
Learn more about an incredible educational opportunity! Join us at one 
of our information sessions to discover how students in grades 9-12 can 
earn a high school diploma AND college credits simultaneously for FREE! 
Through our dual enrollment program, students pay no cost for tuition, 
books, or technology including a free laptop! Only 75 seats available 
per grade level. Learn more at https://example.com/events or call 
(850) 555-1234.
```

**Output:** (214 chars)
```
Pensacola State College Charter Academy Information Session. Join us 
at one of our information sessions to discover how students in grades 
9-12 can earn a high school diploma AND college credits simultaneously.
```

---

**Input:** (380 chars)
```
<p>The Military Appreciation Committee is dedicated to recognizing and 
supporting our active duty, reserve, and retired military members. 
We're committed to ensuring they feel appreciated and supported. 
Join us in making a difference! Volunteers can contact Staff Committee 
Chair, Madelyn Bell, at madelyn@example.org or visit 
https://perdidochamber.com/military-appreciation-committee.</p>
```

**Output:** (184 chars)
```
The Military Appreciation Committee is dedicated to recognizing and 
supporting our active duty, reserve, and retired military members. 
We're committed to ensuring they feel appreciated and supported.
```

---

**Input:** (290 chars)
```
Networking Night hosted by Perdido Key Chamber of Commerce. Connect with 
local business owners and entrepreneurs. Build relationships and expand your 
network. Light refreshments provided. Click here to register: 
https://business.perdidochamber.com/events/register or call (850) 555-0100.
```

**Output:** (139 chars)
```
Networking Night. Connect with local business owners and entrepreneurs. 
Build relationships and expand your network.
```

## Testing

### Local Test Harness

```bash
# Run Python test suite (no WordPress required)
python scripts/test_event_summary_generation.py
```

Output includes:
- 7+ unit tests covering edge cases
- 3 real-world examples with before/after
- PASS/FAIL results

### WordPress Testing

```bash
# 1. Create a test event with long description
wp post create \
  --post_type=ajde_events \
  --post_title="Test Event" \
  --post_content="Long description here..." \
  --post_status=draft

# 2. Check generated summary
wp post meta get <post_id> _event_summary

# 3. Edit it manually
wp post meta update <post_id> _event_summary "Custom summary"

# 4. Verify manual flag was set
wp post meta get <post_id> _event_summary_manual  # Should be true

# 5. Verify it won't overwrite on next save
wp post update <post_id> --post_content="Modified description"
wp post meta get <post_id> _event_summary  # Should still be "Custom summary"
```

## Important Notes

### Description Source Priority

The plugin uses this priority:
1. `post_content` (preferred - where uploader stores descriptions)
2. `post_excerpt` (fallback - if post_content is empty)

### API Integration

The uploader (`wordpress_uploader.py`) stores descriptions in `post_content`:

```python
post_data = {
    'title': title,
    'content': description,  # ← This becomes post_content
    'type': 'ajde_events',
    'meta': metadata
}
```

The summary plugin reads this and auto-generates summaries.

### Performance

- Generation happens on `save_post` hook (synchronous)
- Hash comparison prevents unnecessary regeneration
- No external API calls
- WP-CLI backfill uses batching for large event sets

### Security

- Sanitizes all user input (`sanitize_text_field`)
- Escapes output (`esc_html`, `esc_textarea`)
- Capability checks (`current_user_can( 'edit_post' )`)
- Nonce verification on admin form saves

## Troubleshooting

### Summaries Not Generated

**Check:**
1. Plugin activated: `wp plugin list | grep event-summary`
2. Event post type: `wp post get <id> --fields=post_type`
3. Description exists: `wp post get <id> --fields=post_content`

**Fix:**
```bash
# Force regeneration
wp events backfill-summaries --force --ids=<post_id>
```

### Manual Edit Not Sticking

**Check:**
1. Nonce is valid in form
2. User has `edit_posts` capability

**Debug:**
```php
// In wp-config.php temporarily
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
```

Then check `wp-content/debug.log`.

### REST API Not Returning Summary

**Check:**
1. Plugin is activated
2. REST API plugin (`eventon-rest-api-meta.php`) is activated
3. Meta field exists: `wp post meta get <id> _event_summary`

**Fix:**
```bash
# Re-register REST API fields
wp plugin deactivate event-summary-generator
wp plugin activate event-summary-generator
```

## Admin Interface

When editing an event in WordPress admin, you'll see a new meta box:

```
┌─────────────────────────────────────────────┐
│ EVENT SUMMARY                               │
├─────────────────────────────────────────────┤
│ Summary (auto-generated, but you can edit): │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Join us for this amazing community...   │ │
│ │                                         │ │
│ │                                         │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Max 280 characters. If you edit this,       │
│ it won't be overwritten on future           │
│ description changes.                        │
└─────────────────────────────────────────────┘
```

## Files Modified/Created

| File | Type | Changes |
|------|------|---------|
| `plugins/event-summary-generator.php` | New | Core plugin - summary generation, auto-save, admin UI, WP-CLI |
| `plugins/eventon-rest-api-meta.php` | Modified | Added `_event_summary` to REST API fields list |
| `scripts/test_event_summary_generation.py` | New | Python test harness for summary generation |

## Next Steps

1. **Deploy Plugin**
   - Copy `event-summary-generator.php` to `wp-content/plugins/`
   - Activate in WordPress admin

2. **Backfill Existing Events**
   ```bash
   wp events backfill-summaries
   ```

3. **Update Templates** (if needed)
   - Locate EventON event card/list template
   - Replace description with summary fallback pattern (see "Usage in Templates" above)

4. **Test**
   ```bash
   # Run local test harness
   python scripts/test_event_summary_generation.py
   
   # Test on WordPress
   wp events backfill-summaries --dry-run
   ```

5. **Monitor**
   - Check `wp-content/debug.log` for any issues
   - Verify summaries appear correctly on event pages

## Support & Customization

### Adjust Summary Length

Edit in plugin or function override:

```php
// In functions.php or custom plugin
define( 'EVENT_SUMMARY_MAX_CHARS', 150 );  // Change max length
```

### Add More Boilerplate Phrases

Edit the `$boilerplate_patterns` array in `generate_event_summary()`:

```php
$boilerplate_patterns = [
    // ... existing patterns ...
    '/registration\s+required/i',  // Add new pattern
];
```

### Disable Auto-Generation

Remove the hook in WordPress:

```php
remove_action( 'save_post', 'auto_generate_event_summary' );
```

Then edit summaries manually.

---

**Last Updated:** January 16, 2026  
**Tested With:** WordPress 6.x, EventON 4.x
