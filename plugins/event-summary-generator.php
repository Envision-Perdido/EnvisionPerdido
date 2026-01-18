<?php
/**
 * Plugin Name: Event Summary Generator
 * Description: Automatically generates and manages event summaries from full descriptions
 * Version: 1.0
 * Author: Community Calendar Integration
 * 
 * Features:
 * - Auto-generates summaries when events are created/updated
 * - Stores summaries in _event_summary meta field (editable in WP admin)
 * - Detects description changes via _event_description_hash
 * - WP-CLI command: wp events backfill-summaries
 * - Fallback: summary -> excerpt -> trimmed description
 * 
 * Installation:
 * 1. Save this file as: wp-content/plugins/event-summary-generator.php
 * 2. Log into WordPress admin
 * 3. Go to Plugins → Installed Plugins
 * 4. Find "Event Summary Generator" and click Activate
 */

if (!defined('ABSPATH')) {
    exit;
}

// phpcs:disable WordPress.DB.DirectDatabaseQuery.DirectQuery
// phpcs:disable WordPress.DB.DirectDatabaseQuery.NoCaching

// ============================================================================
// CONFIGURATION & CONSTANTS
// ============================================================================

const EVENT_SUMMARY_META_KEY = '_event_summary';
const EVENT_DESCRIPTION_HASH_META_KEY = '_event_description_hash';
const DEFAULT_SUMMARY_MAX_CHARS = 280;

/**
 * Abbreviations that should not be treated as sentence endings
 */
function get_abbreviations() {
    return [
        'U.S.', 'U.K.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.',
        'Ph.D.', 'M.D.', 'Inc.', 'Ltd.', 'Corp.', 'Co.', 'St.', 'Ave.', 'Blvd.',
        'No.', 'Dept.', 'Est.', 'Gov.', 'etc.', 'i.e.', 'e.g.', 'a.m.', 'p.m.',
        'v.s.', 'vs.', 'oz.', 'etc', 'et al.', 'e.v.'
    ];
}

// ============================================================================
// CORE SUMMARY GENERATION FUNCTION
// ============================================================================

/**
 * Generate a summary from event description
 *
 * @param int    $post_id   The event post ID
 * @param int    $max_chars Maximum length for summary (default: 280)
 * @return string Generated summary text (empty string if no description)
 */
function generate_event_summary( $post_id, $max_chars = DEFAULT_SUMMARY_MAX_CHARS ) {
    // Get the full event description
    $post = get_post( $post_id );
    if ( ! $post || 'ajde_events' !== $post->post_type ) {
        return '';
    }

    // Prefer post_content, fallback to excerpt
    $description = trim( $post->post_content ?: $post->post_excerpt );
    if ( empty( $description ) ) {
        return '';
    }

    // Strip HTML tags and shortcodes
    $text = wp_strip_all_tags( do_shortcode( $description ) );

    // Remove common boilerplate phrases
    $boilerplate_patterns = [
        '/\s*click\s+here\s*/i',
        '/\s*learn\s+more\s*/i',
        '/\s*for\s+more\s+information.*?(?=\.|$)/i',
        '/https?:\/\/[^\s]+/i',  // URLs
        '/\b[\d\(\)\s-]{10,}\b/i', // Phone numbers like (123) 456-7890
    ];

    foreach ( $boilerplate_patterns as $pattern ) {
        $text = preg_replace( $pattern, ' ', $text );
    }

    // Remove multiple spaces
    $text = preg_replace( '/\s+/', ' ', $text );
    $text = trim( $text );

    if ( empty( $text ) ) {
        return '';
    }

    // If already short enough, return as-is
    if ( strlen( $text ) <= $max_chars ) {
        return $text;
    }

    // Extract 1-3 sentences without truncating mid-word
    $summary = truncate_at_sentence_boundary( $text, $max_chars );

    return trim( $summary );
}

/**
 * Truncate text at sentence boundary
 *
 * Tries to fit as many complete sentences as possible within max_chars.
 * Falls back to word boundary if no sentence boundaries found.
 *
 * @param string $text      Text to truncate
 * @param int    $max_chars Maximum length
 * @return string Truncated text
 */
function truncate_at_sentence_boundary( $text, $max_chars ) {
    if ( strlen( $text ) <= $max_chars ) {
        return $text;
    }

    // Get abbreviations to avoid splitting on
    $abbreviations = get_abbreviations();
    $abbrev_pattern = implode( '|', array_map( 'preg_quote', $abbreviations ) );

    // Try to split at sentence boundaries (., !, ?)
    // But avoid splitting on known abbreviations
    $pattern = '/(?<!' . $abbrev_pattern . ')\s*[.!?]+\s+/';
    $sentences = preg_split( $pattern, substr( $text, 0, $max_chars * 2 ) );

    $summary = '';
    $sentence_count = 0;

    foreach ( $sentences as $sentence ) {
        $test_summary = $summary . ( $summary ? ' ' : '' ) . trim( $sentence );

        // Stop if we've hit 3 sentences or exceeded max length
        if ( $sentence_count >= 2 || strlen( $test_summary ) > $max_chars ) {
            break;
        }

        if ( ! empty( trim( $sentence ) ) ) {
            $summary = $test_summary;
            $sentence_count++;
        }
    }

    // If we have a good summary from sentences, add period if missing
    if ( ! empty( $summary ) && ! in_array( substr( $summary, -1 ), [ '.', '!', '?' ] ) ) {
        $summary .= '.';
    }

    // Fallback: if no sentences found or summary is empty, truncate at word boundary
    if ( empty( $summary ) ) {
        $summary = substr_replace( substr( $text, 0, $max_chars ), '', strrpos( substr( $text, 0, $max_chars ), ' ' ) );
        if ( ! empty( $summary ) ) {
            $summary .= '...';
        }
    }

    return trim( $summary );
}

/**
 * Hash the event description for change detection
 *
 * @param string $text Text to hash
 * @return string MD5 hash
 */
function hash_event_description( $text ) {
    return md5( wp_strip_all_tags( do_shortcode( $text ) ) );
}

/**
 * Check if event description has changed
 *
 * @param int $post_id Event post ID
 * @return bool True if description changed or hash doesn't exist
 */
function event_description_changed( $post_id ) {
    $post = get_post( $post_id );
    if ( ! $post ) {
        return false;
    }

    $current_description = $post->post_content ?: $post->post_excerpt;
    $current_hash = hash_event_description( $current_description );
    $stored_hash = get_post_meta( $post_id, EVENT_DESCRIPTION_HASH_META_KEY, true );

    // If no stored hash or hash differs, description has changed
    return empty( $stored_hash ) || $stored_hash !== $current_hash;
}

// ============================================================================
// HOOKS FOR AUTO-GENERATION ON SAVE
// ============================================================================

/**
 * Auto-generate summary when event is saved
 *
 * @param int    $post_id Post ID
 * @param object $post    Post object
 */
function auto_generate_event_summary( $post_id, $post ) {
    // Bail if not an event post type
    if ( 'ajde_events' !== $post->post_type ) {
        return;
    }

    // Bail if autosave
    if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) {
        return;
    }

    // Bail if user doesn't have capability
    if ( ! current_user_can( 'edit_post', $post_id ) ) {
        return;
    }

    // Check if user manually edited the summary - if so, don't overwrite
    $manual_summary = get_post_meta( $post_id, '_event_summary_manual', true );

    // Get current summary
    $current_summary = get_post_meta( $post_id, EVENT_SUMMARY_META_KEY, true );

    // Only regenerate if: summary is empty OR description changed AND not manually set
    if ( empty( $current_summary ) || ( event_description_changed( $post_id ) && ! $manual_summary ) ) {
        $new_summary = generate_event_summary( $post_id, DEFAULT_SUMMARY_MAX_CHARS );
        update_post_meta( $post_id, EVENT_SUMMARY_META_KEY, $new_summary );

        // Update the description hash
        $description = $post->post_content ?: $post->post_excerpt;
        $new_hash = hash_event_description( $description );
        update_post_meta( $post_id, EVENT_DESCRIPTION_HASH_META_KEY, $new_hash );
    }
}

add_action( 'save_post', 'auto_generate_event_summary', 10, 2 );

// ============================================================================
// REST API REGISTRATION
// ============================================================================

/**
 * Register event summary fields with REST API
 */
function register_event_summary_meta_fields() {
    // Register summary field
    register_post_meta(
        'ajde_events',
        EVENT_SUMMARY_META_KEY,
        [
            'show_in_rest'      => true,
            'single'            => true,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'auth_callback'     => function() {
                return current_user_can( 'edit_posts' );
            },
        ]
    );

    // Register description hash field (internal use, not shown in REST API)
    register_post_meta(
        'ajde_events',
        EVENT_DESCRIPTION_HASH_META_KEY,
        [
            'show_in_rest'  => false,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => function() {
                return current_user_can( 'edit_posts' );
            },
        ]
    );

    // Register manual edit flag (internal use, not shown in REST API)
    register_post_meta(
        'ajde_events',
        '_event_summary_manual',
        [
            'show_in_rest'  => false,
            'single'        => true,
            'type'          => 'boolean',
            'auth_callback' => function() {
                return current_user_can( 'edit_posts' );
            },
        ]
    );
}

add_action( 'rest_api_init', 'register_event_summary_meta_fields' );

// ============================================================================
// WP-CLI COMMAND
// ============================================================================

/**
 * WP-CLI command for backfilling event summaries
 */
if ( defined( 'WP_CLI' ) && WP_CLI ) {
    class Event_Summary_CLI_Command {
        /**
         * Backfill summaries for events
         *
         * ## OPTIONS
         *
         * [--dry-run]
         * : Show what would be done without making changes
         *
         * [--force]
         * : Regenerate summaries even if they already exist
         *
         * [--ids=<post_ids>]
         * : Comma-separated list of event IDs to process
         *
         * ## EXAMPLES
         *
         *     wp events backfill-summaries --dry-run
         *     wp events backfill-summaries --apply
         *     wp events backfill-summaries --force
         *     wp events backfill-summaries --ids=123,456,789
         */
        public function backfill_summaries( $args, $assoc_args ) {
            $dry_run = isset( $assoc_args['dry-run'] );
            $force = isset( $assoc_args['force'] );
            $ids = isset( $assoc_args['ids'] ) ? explode( ',', $assoc_args['ids'] ) : [];

            // Build query
            $query_args = [
                'post_type'      => 'ajde_events',
                'posts_per_page' => -1,
                'post_status'    => 'any',
                'fields'         => 'ids',
            ];

            if ( ! empty( $ids ) ) {
                $query_args['post__in'] = array_map( 'intval', $ids );
            }

            $events = get_posts( $query_args );
            $total = count( $events );
            $processed = 0;
            $generated = 0;
            $skipped = 0;

            if ( $total === 0 ) {
                \WP_CLI::warning( 'No events found to process.' );
                return;
            }

            \WP_CLI::log( "Found {$total} event(s) to process" );

            if ( $dry_run ) {
                \WP_CLI::log( '🔍 DRY RUN MODE - No changes will be made' );
            }

            $progress = \WP_CLI\Utils\make_progress_bar( 'Processing events', $total );

            foreach ( $events as $post_id ) {
                $post = get_post( $post_id );
                $current_summary = get_post_meta( $post_id, EVENT_SUMMARY_META_KEY, true );
                $should_generate = empty( $current_summary ) || $force;

                if ( $should_generate ) {
                    $new_summary = generate_event_summary( $post_id, DEFAULT_SUMMARY_MAX_CHARS );

                    if ( ! empty( $new_summary ) ) {
                        if ( ! $dry_run ) {
                            update_post_meta( $post_id, EVENT_SUMMARY_META_KEY, $new_summary );

                            // Update the description hash
                            $description = $post->post_content ?: $post->post_excerpt;
                            $new_hash = hash_event_description( $description );
                            update_post_meta( $post_id, EVENT_DESCRIPTION_HASH_META_KEY, $new_hash );
                        }

                        $generated++;
                        \WP_CLI::log( "  ✓ ID {$post_id}: Generated summary" );
                    } else {
                        $skipped++;
                        \WP_CLI::log( "  ⊘ ID {$post_id}: No description to summarize" );
                    }
                } else {
                    $skipped++;
                }

                $processed++;
                $progress->tick();
            }

            $progress->finish();
            \WP_CLI::log( '' );
            \WP_CLI::success( "Processed {$processed}/{$total} events. Generated: {$generated}, Skipped: {$skipped}" );

            if ( $dry_run ) {
                \WP_CLI::line( '💡 Run without --dry-run to apply changes' );
            }
        }
    }

    \WP_CLI::add_command( 'events backfill-summaries', [ 'Event_Summary_CLI_Command', 'backfill_summaries' ] );
}

// ============================================================================
// ADMIN UI - ALLOW MANUAL EDITING OF SUMMARIES
// ============================================================================

/**
 * Register meta field in WordPress admin
 */
function register_event_summary_admin_field() {
    add_meta_box(
        'event_summary_meta_box',
        'Event Summary',
        'render_event_summary_meta_box',
        'ajde_events',
        'normal',
        'default'
    );
}

add_action( 'add_meta_boxes', 'register_event_summary_admin_field' );

/**
 * Render the summary meta box in WordPress admin
 *
 * @param object $post The post object
 */
function render_event_summary_meta_box( $post ) {
    $summary = get_post_meta( $post->ID, EVENT_SUMMARY_META_KEY, true );
    $manual = get_post_meta( $post->ID, '_event_summary_manual', true );
    $nonce = wp_create_nonce( 'event_summary_nonce' );

    ?>
    <div style="margin: 10px 0;">
        <label for="event_summary_field">
            <strong>Summary (auto-generated, but you can edit):</strong>
        </label>
        <textarea
            id="event_summary_field"
            name="event_summary"
            rows="4"
            style="width: 100%; padding: 8px;"
            placeholder="Leave empty to auto-generate from description..."
        ><?php echo esc_textarea( $summary ); ?></textarea>
        <small style="display: block; margin-top: 5px; color: #666;">
            Max 280 characters. If you edit this, it won't be overwritten on future description changes.
        </small>
    </div>
    <input type="hidden" name="event_summary_nonce" value="<?php echo esc_attr( $nonce ); ?>" />
    <?php
}

/**
 * Save summary from admin editor
 *
 * @param int $post_id Post ID
 */
function save_event_summary_meta_box( $post_id ) {
    // Verify nonce
    if ( ! isset( $_POST['event_summary_nonce'] ) || ! wp_verify_nonce( $_POST['event_summary_nonce'], 'event_summary_nonce' ) ) {
        return;
    }

    // Check capability
    if ( ! current_user_can( 'edit_post', $post_id ) ) {
        return;
    }

    // Handle summary input
    if ( isset( $_POST['event_summary'] ) ) {
        $summary = sanitize_text_field( wp_unslash( $_POST['event_summary'] ) );

        // If user provided content, mark as manually edited
        if ( ! empty( $summary ) ) {
            update_post_meta( $post_id, '_event_summary_manual', true );
        } else {
            delete_post_meta( $post_id, '_event_summary_manual' );
        }

        update_post_meta( $post_id, EVENT_SUMMARY_META_KEY, $summary );
    }
}

add_action( 'save_post_ajde_events', 'save_event_summary_meta_box' );

// ============================================================================
// PLUGIN ACTIVATION HOOK
// ============================================================================

/**
 * Activation hook - backfill summaries for existing events
 */
function activate_event_summary_generator() {
    // For safety, don't auto-generate on activation in WordPress
    // User should run wp events backfill-summaries or manually check
    error_log( 'Event Summary Generator activated. Run: wp events backfill-summaries' );
}

register_activation_hook( __FILE__, 'activate_event_summary_generator' );
