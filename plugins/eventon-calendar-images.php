<?php
/**
 * Plugin Name: EventON Calendar Image Display
 * Description: Display images on EventON calendar tiles without showing in popup
 * Version: 1.0
 * Author: Calendar Integration
 * 
 * Installation:
 * 1. Save this file in: wp-content/plugins/eventon-calendar-images.php
 * 2. Go to Plugins → Installed Plugins
 * 3. Click Activate on "EventON Calendar Image Display"
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Hook into EventON event rendering to set featured image via meta, not featured_media
 */
add_filter('the_post', function($post) {
    // Only for EventON events
    if ($post->post_type !== 'ajde_events') {
        return $post;
    }
    
    // If there's a custom image ID stored in meta, set featured_media dynamically
    // but only for calendar display, not for popup
    $image_id = get_post_meta($post->ID, '_event_image_id', true);
    if ($image_id) {
        // Set the featured image for calendar tile display
        set_post_thumbnail($post->ID, (int)$image_id);
    }
    
    return $post;
});

/**
 * Modify EventON REST response to exclude featured_media from event details
 */
add_filter('rest_prepare_ajde_events', function($response, $post, $request) {
    // Get the featured media from meta, not from featured_media
    $image_id = get_post_meta($post->ID, '_event_image_id', true);
    
    // Get current data
    $data = $response->get_data();
    
    // Remove featured_media from response to prevent popup display
    $data['featured_media'] = null;
    
    // Add custom meta field for image if available
    if ($image_id) {
        $data['meta']['_event_image_id'] = $image_id;
        $image_url = get_post_meta($post->ID, '_event_image_url', true);
        if ($image_url) {
            $data['meta']['_event_image_url'] = $image_url;
        }
    }
    
    // Update response
    $response->set_data($data);
    
    return $response;
}, 10, 3);

/**
 * Register custom meta fields for REST API
 */
add_action('init', function() {
    register_rest_field('ajde_events', '_event_image_id', array(
        'get_callback' => function($post) {
            return get_post_meta($post['id'], '_event_image_id', true);
        },
    ));
    
    register_rest_field('ajde_events', '_event_image_url', array(
        'get_callback' => function($post) {
            return get_post_meta($post['id'], '_event_image_url', true);
        },
    ));
});

/**
 * CSS to hide featured image in EventON popup
 */
add_action('wp_footer', function() {
    if (is_page() || is_single()) {
        ?>
        <style>
            /* Hide featured image in EventON event card popup */
            .event_description .evocard_box.ftimage,
            #event_ftimage {
                display: none !important;
            }
            
            /* Ensure description and time are visible */
            .event_description .evocard_box.eventdetails,
            #event_eventdetails,
            .event_description .evocard_box.time,
            #event_time {
                display: block !important;
            }
        </style>
        <?php
    }
});
?>
