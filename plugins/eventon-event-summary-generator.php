<?php
/**
 * Plugin Name: EventON Event Summary Generator
 * Description: Generates and stores AI-free event summaries for card displays
 * Version: 1.0
 * Author: EnvisionPerdido Development
 * 
 * Installation:
 * 1. Save this file to: wp-content/plugins/eventon-event-summary-generator.php
 * 2. Log into WordPress admin
 * 3. Go to Plugins → Installed Plugins
 * 4. Find "EventON Event Summary Generator" and click Activate
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// ============================================================================
// CORE FUNCTIONS
// ============================================================================

/**
 * Generate a short summary from an event description.
 * 
 * @param int $post_id Post ID of the event
 * @param int $max_chars Maximum characters for summary (default 280)
 * @return string Generated summary
 */
function eventon_generate_event_summary($post_id, $max_chars = 280) {
    // Get description from post content
    $post = get_post($post_id);
    if (!$post) {
        return '';
    }

    $description = $post->post_content;
    
    if (empty(trim($description))) {
        return '';
    }

    // Strip HTML tags
    $text = wp_strip_all_tags($description);

    // Remove common boilerplate phrases
    $boilerplate_patterns = array(
        '/\s*click\s+here\s*/i',
        '/\s*learn\s+more\s*/i',
        '/\s*for\s+more\s+information.*?(?=\.|$)/i',
        '/https?:\/\/[^\s.]+(?:\.\S+)?/',
        '/\b[\d\(\)\s-]{10,}\b/',
        '/\s*RSVP\s+(?:at|to).*?(?=\.|$)/i',
        '/\s+or\s+call\s*/i',
        '/\.com(?![a-z])/',
    );

    $replacements = array(
        ' ',
        ' ',
        ' ',
        '',
        ' ',
        ' ',
        ' ',
        '',
    );

    $text = preg_replace($boilerplate_patterns, $replacements, $text);

    // Remove multiple spaces and clean up orphaned punctuation
    $text = preg_replace('/\s+/', ' ', trim($text));
    $text = preg_replace('/[\s.!?]+$/', '', $text);

    if (empty(trim($text))) {
        return '';
    }

    // If already short enough, return as-is
    if (strlen($text) <= $max_chars) {
        return trim($text);
    }

    // Extract 1-3 sentences without truncating mid-word
    return trim(eventon_truncate_at_sentence_boundary($text, $max_chars));
}

/**
 * Truncate text at sentence boundary.
 * 
 * @param string $text Text to truncate
 * @param int $max_chars Maximum characters
 * @return string Truncated text at sentence boundary
 */
function eventon_truncate_at_sentence_boundary($text, $max_chars = 280) {
    if (strlen($text) <= $max_chars) {
        return $text;
    }

    // Split at sentence boundaries using lookahead for capital letter
    $pattern = '/[.!?]+\s+(?=[A-Z])/';
    $sentences = preg_split($pattern, substr($text, 0, $max_chars * 2));

    $summary = '';
    $sentence_count = 0;

    foreach ($sentences as $sentence) {
        $sentence = trim($sentence);
        if (empty($sentence)) {
            continue;
        }

        $test_summary = !empty($summary) ? $summary . ' ' . $sentence : $sentence;

        // Stop if we've hit 3 sentences or exceeded max length
        if ($sentence_count >= 2 || strlen($test_summary) > $max_chars) {
            break;
        }

        $summary = $test_summary;
        $sentence_count++;
    }

    return trim($summary);
}

/**
 * Get event summary (with fallback).
 * Returns _event_summary if available, otherwise generates from description.
 * 
 * @param int $post_id Post ID of the event
 * @return string Event summary
 */
function eventon_get_event_summary($post_id) {
    // Try to get stored summary first
    $stored_summary = get_post_meta($post_id, '_event_summary', true);
    if (!empty(trim($stored_summary))) {
        return $stored_summary;
    }

    // Fallback: generate from description
    return eventon_generate_event_summary($post_id);
}

/**
 * Detect if the event description has changed since last summary generation.
 * 
 * @param int $post_id Post ID of the event
 * @return bool True if description changed or summary is missing
 */
function eventon_description_changed($post_id) {
    $post = get_post($post_id);
    if (!$post) {
        return false;
    }

    $current_hash = md5($post->post_content);
    $stored_hash = get_post_meta($post_id, '_event_description_hash', true);

    // Return true if hash doesn't match or stored hash is empty
    return empty($stored_hash) || $stored_hash !== $current_hash;
}

// ============================================================================
// HOOKS: Auto-generate on save
// ============================================================================

/**
 * Auto-generate summary when event is saved.
 */
function eventon_auto_generate_summary($post_id, $post, $update) {
    // Only process ajde_events post type
    if ($post->post_type !== 'ajde_events') {
        return;
    }

    // Skip autosave and revisions
    if (wp_is_post_autosave($post_id) || wp_is_post_revision($post_id)) {
        return;
    }

    // Only regenerate if description changed or summary is empty
    if (!eventon_description_changed($post_id)) {
        $stored_summary = get_post_meta($post_id, '_event_summary', true);
        if (!empty(trim($stored_summary))) {
            return; // Summary exists and description didn't change
        }
    }

    // Generate summary
    $summary = eventon_generate_event_summary($post_id);
    
    // Store summary
    if (!empty(trim($summary))) {
        update_post_meta($post_id, '_event_summary', $summary);
    }

    // Store hash of description for future change detection
    $description_hash = md5(get_post($post_id)->post_content);
    update_post_meta($post_id, '_event_description_hash', $description_hash);
}
add_action('wp_insert_post', 'eventon_auto_generate_summary', 10, 3);

// ============================================================================
// REST API REGISTRATION
// ============================================================================

/**
 * Register the _event_summary field with REST API.
 */
function eventon_register_summary_meta_field() {
    register_post_meta('ajde_events', '_event_summary', array(
        'show_in_rest' => true,
        'single' => true,
        'type' => 'string',
        'auth_callback' => function() {
            return current_user_can('edit_posts');
        }
    ));

    register_post_meta('ajde_events', '_event_description_hash', array(
        'show_in_rest' => false,  // Don't expose this to REST API
        'single' => true,
        'type' => 'string',
        'auth_callback' => function() {
            return current_user_can('edit_posts');
        }
    ));
}
add_action('rest_api_init', 'eventon_register_summary_meta_field');

// ============================================================================
// ADMIN INTERFACE
// ============================================================================

/**
 * Add meta box to event edit page.
 */
function eventon_add_summary_metabox() {
    add_meta_box(
        'eventon_summary',
        'Event Summary',
        'eventon_summary_metabox_callback',
        'ajde_events',
        'normal',
        'default'
    );
}
add_action('add_meta_boxes', 'eventon_add_summary_metabox');

/**
 * Display the summary meta box.
 */
function eventon_summary_metabox_callback($post) {
    $summary = get_post_meta($post->ID, '_event_summary', true);
    $generated = eventon_generate_event_summary($post->ID);
    
    wp_nonce_field('eventon_summary_nonce', 'eventon_summary_nonce');
    ?>
    <div style="padding: 10px;">
        <p>
            <label for="eventon_summary"><strong>Summary (280 chars max):</strong></label>
        </p>
        <textarea 
            id="eventon_summary" 
            name="eventon_summary" 
            rows="4" 
            style="width: 100%; padding: 8px; border: 1px solid #ddd;"
            placeholder="Leave empty to auto-generate from description"
        ><?php echo esc_textarea($summary); ?></textarea>
        
        <p style="margin-top: 10px; padding: 10px; background: #f5f5f5; border-left: 4px solid #0073aa;">
            <strong>Auto-generated:</strong><br>
            <em><?php echo esc_html($generated); ?></em>
        </p>
        
        <p style="margin-top: 10px; font-size: 12px; color: #666;">
            <strong>How it works:</strong>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>Leave this field empty to use the auto-generated summary</li>
                <li>Edit manually to customize the summary for this event</li>
                <li>Summary is limited to 280 characters</li>
                <li>Auto-generation happens every time you update the event</li>
            </ul>
        </p>
    </div>
    <?php
}

/**
 * Save summary meta box.
 */
function eventon_save_summary_metabox($post_id) {
    // Verify nonce
    if (!isset($_POST['eventon_summary_nonce']) || 
        !wp_verify_nonce($_POST['eventon_summary_nonce'], 'eventon_summary_nonce')) {
        return;
    }

    // Check permissions
    if (!current_user_can('edit_post', $post_id)) {
        return;
    }

    // Check if this is an autosave
    if (wp_is_post_autosave($post_id)) {
        return;
    }

    // Get submitted value
    $summary = isset($_POST['eventon_summary']) ? sanitize_textarea_field($_POST['eventon_summary']) : '';

    // Truncate to 280 chars if needed
    if (strlen($summary) > 280) {
        // Try to truncate at word boundary
        $summary = substr($summary, 0, 280);
        // Remove partial word at end
        $summary = substr($summary, 0, strrpos($summary, ' '));
    }

    // If user cleared the field, let it auto-generate next time
    if (empty(trim($summary))) {
        delete_post_meta($post_id, '_event_summary');
    } else {
        update_post_meta($post_id, '_event_summary', $summary);
    }
}
add_action('save_post_ajde_events', 'eventon_save_summary_metabox');

// ============================================================================
// WP-CLI COMMAND
// ============================================================================

if (defined('WP_CLI') && WP_CLI) {
    /**
     * WP-CLI command to backfill summaries for events.
     */
    class EventON_Summary_Command extends WP_CLI_Command {
        /**
         * Backfill event summaries.
         *
         * ## OPTIONS
         *
         * [--dry-run]
         * : Show what would be done without actually saving
         *
         * ## EXAMPLES
         *
         *     wp events backfill-summaries
         *     wp events backfill-summaries --dry-run
         */
        public function __invoke($args, $assoc_args) {
            $dry_run = isset($assoc_args['dry-run']);

            if ($dry_run) {
                WP_CLI::log('Running in DRY-RUN mode. No changes will be saved.');
            }

            // Get all events
            $events = get_posts(array(
                'post_type' => 'ajde_events',
                'posts_per_page' => -1,
                'post_status' => 'any',
            ));

            $total = count($events);
            $generated = 0;
            $skipped = 0;

            WP_CLI::log("Found {$total} events.");

            foreach ($events as $event) {
                $existing = get_post_meta($event->ID, '_event_summary', true);

                if (!empty(trim($existing))) {
                    WP_CLI::log("SKIP: Event {$event->ID} ({$event->post_title}) - already has summary");
                    $skipped++;
                    continue;
                }

                $summary = eventon_generate_event_summary($event->ID);

                if (empty(trim($summary))) {
                    WP_CLI::log("SKIP: Event {$event->ID} ({$event->post_title}) - no description");
                    $skipped++;
                    continue;
                }

                if ($dry_run) {
                    WP_CLI::log("WOULD GENERATE: Event {$event->ID}");
                    WP_CLI::log("  Title: {$event->post_title}");
                    WP_CLI::log("  Summary: {$summary}");
                } else {
                    update_post_meta($event->ID, '_event_summary', $summary);
                    $description_hash = md5($event->post_content);
                    update_post_meta($event->ID, '_event_description_hash', $description_hash);
                    WP_CLI::log("GENERATED: Event {$event->ID} ({$event->post_title})");
                }

                $generated++;
            }

            WP_CLI::log('');
            WP_CLI::success("Backfill complete!");
            WP_CLI::log("  Total events: {$total}");
            WP_CLI::log("  Generated: {$generated}");
            WP_CLI::log("  Skipped: {$skipped}");

            if ($dry_run) {
                WP_CLI::log("  (DRY-RUN: no changes saved)");
            }
        }
    }

    WP_CLI::add_command('events backfill-summaries', 'EventON_Summary_Command');
}

?>
