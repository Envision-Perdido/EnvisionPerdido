"""
Unit Tests for Tag Taxonomy

Tests tag inference, validation, and taxonomy management.
"""

import unittest

from scripts.tag_taxonomy import (
    TagTaxonomy,
    get_all_tags,
    infer_tags,
    validate_tags,
)


class TestTagInference(unittest.TestCase):
    """Test tag inference from event data."""

    def test_live_music_detection(self):
        """Test detection of live music events."""
        tags = infer_tags(
            title="Live Band Tonight", description="Join us for an evening of live music"
        )
        self.assertIn(TagTaxonomy.LIVE_MUSIC, tags)

    def test_dj_detection(self):
        """Test DJ event detection."""
        tags = infer_tags(title="DJ Night at the Beach")
        self.assertIn(TagTaxonomy.DJ, tags)

    def test_karaoke_detection(self):
        """Test karaoke detection."""
        tags = infer_tags(description="Karaoke every Thursday night")
        self.assertIn(TagTaxonomy.KARAOKE, tags)

    def test_food_drink_detection(self):
        """Test food and drink event detection."""
        tags = infer_tags(
            title="Wine Tasting Event", description="Sample wines from local vineyards"
        )
        self.assertIn(TagTaxonomy.WINE, tags)
        # May also detect food_drink

    def test_happy_hour_detection(self):
        """Test happy hour detection."""
        tags = infer_tags(description="Happy Hour specials 4-7pm")
        self.assertIn(TagTaxonomy.HAPPY_HOUR, tags)

    def test_family_friendly_detection(self):
        """Test family-friendly detection."""
        tags = infer_tags(description="Family friendly event, all ages welcome")
        self.assertIn(TagTaxonomy.FAMILY_FRIENDLY, tags)

    def test_beach_event_detection(self):
        """Test beach event detection."""
        tags = infer_tags(title="Beach Volleyball Tournament", location="Gulf State Park Beach")
        self.assertIn(TagTaxonomy.BEACH, tags)

    def test_run_walk_detection(self):
        """Test run/walk event detection."""
        tags = infer_tags(title="Annual 5K Fun Run for Charity")
        self.assertIn(TagTaxonomy.RUN_WALK, tags)

    def test_fundraiser_detection(self):
        """Test fundraiser detection."""
        tags = infer_tags(
            title="Charity Fundraiser Dinner", description="Raising funds for local nonprofit"
        )
        self.assertIn(TagTaxonomy.FUNDRAISER, tags)

    def test_festival_detection(self):
        """Test festival detection."""
        tags = infer_tags(title="Perdido Key Seafood Festival")
        self.assertIn(TagTaxonomy.FESTIVAL, tags)

    def test_comedy_detection(self):
        """Test comedy event detection."""
        tags = infer_tags(description="Stand-up comedy show featuring local comedians")
        self.assertIn(TagTaxonomy.COMEDY, tags)

    def test_trivia_detection(self):
        """Test trivia night detection."""
        tags = infer_tags(title="Tuesday Night Trivia")
        self.assertIn(TagTaxonomy.TRIVIA, tags)

    def test_sports_watch_detection(self):
        """Test sports watch party detection."""
        tags = infer_tags(description="Game watch party for the big game")
        self.assertIn(TagTaxonomy.SPORTS_WATCH, tags)

    def test_multiple_tags(self):
        """Test multiple tag detection."""
        tags = infer_tags(
            title="Beach Festival with Live Music and Food",
            description="Family-friendly outdoor festival on the beach",
        )
        # Should detect multiple relevant tags
        self.assertTrue(len(tags) >= 2)
        self.assertIn(TagTaxonomy.BEACH, tags)
        self.assertIn(TagTaxonomy.FESTIVAL, tags)

    def test_max_tags_limit(self):
        """Test that max_tags limit is respected."""
        tags = infer_tags(
            title="Beach Music Festival with Food Drink Kids Comedy",
            description="Live music DJ karaoke outdoor family friendly",
            max_tags=3,
        )
        self.assertLessEqual(len(tags), 3)

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        tags_lower = infer_tags(title="live music tonight")
        tags_upper = infer_tags(title="LIVE MUSIC TONIGHT")
        tags_mixed = infer_tags(title="Live Music Tonight")

        self.assertEqual(tags_lower, tags_upper)
        self.assertEqual(tags_lower, tags_mixed)

    def test_no_matches(self):
        """Test event with no tag matches."""
        tags = infer_tags(title="Quarterly Business Meeting", description="Discuss Q4 results")
        # May get networking or educational, or may be empty
        # Just verify no crash
        self.assertIsInstance(tags, list)


class TestTagTaxonomy(unittest.TestCase):
    """Test tag taxonomy management."""

    def test_get_all_tags(self):
        """Test getting all tags."""
        all_tags = get_all_tags()
        self.assertIsInstance(all_tags, list)
        self.assertGreater(len(all_tags), 20)  # Should have at least 20 tags
        self.assertIn(TagTaxonomy.LIVE_MUSIC, all_tags)
        self.assertIn(TagTaxonomy.BEACH, all_tags)

    def test_validate_tags(self):
        """Test tag validation."""
        valid = validate_tags([TagTaxonomy.LIVE_MUSIC, TagTaxonomy.BEACH])
        self.assertEqual(len(valid), 2)

        mixed = validate_tags([TagTaxonomy.LIVE_MUSIC, "invalid_tag", TagTaxonomy.BEACH])
        self.assertEqual(len(mixed), 2)
        self.assertNotIn("invalid_tag", mixed)

    def test_tag_consistency(self):
        """Test that tags use consistent format (lowercase with underscores)."""
        all_tags = get_all_tags()
        for tag in all_tags:
            self.assertEqual(tag, tag.lower())
            self.assertNotIn(" ", tag)  # No spaces
            self.assertNotIn("-", tag)  # No hyphens, use underscores


class TestRepresentativeEvents(unittest.TestCase):
    """Test tagging on representative real-world events."""

    def test_event_1_beach_concert(self):
        """Beach concert event."""
        tags = infer_tags(
            title="Sunset Concert on the Beach",
            description="Live acoustic music as the sun sets over the Gulf",
            location="Gulf State Park Beach",
        )
        self.assertIn(TagTaxonomy.LIVE_MUSIC, tags)
        self.assertIn(TagTaxonomy.BEACH, tags)

    def test_event_2_trivia_happy_hour(self):
        """Trivia with happy hour."""
        tags = infer_tags(
            title="Tuesday Trivia Night",
            description="Test your knowledge! Happy hour drink specials 6-8pm",
        )
        self.assertIn(TagTaxonomy.TRIVIA, tags)
        self.assertIn(TagTaxonomy.HAPPY_HOUR, tags)

    def test_event_3_charity_run(self):
        """Charity 5K run."""
        tags = infer_tags(
            title="5K Run for Local Schools",
            description="Family-friendly fundraiser. All proceeds benefit education.",
        )
        self.assertIn(TagTaxonomy.RUN_WALK, tags)
        self.assertIn(TagTaxonomy.FUNDRAISER, tags)
        # family_friendly may be present but might not make top 5
        # Just verify the primary tags are there

    def test_event_4_comedy_show(self):
        """Comedy show."""
        tags = infer_tags(
            title="Comedy Night at the Lounge",
            description="Stand-up comedy featuring regional comedians",
        )
        self.assertIn(TagTaxonomy.COMEDY, tags)

    def test_event_5_fishing_tournament(self):
        """Fishing rodeo."""
        tags = infer_tags(
            title="Annual Fishing Rodeo",
            description="Compete for prizes in this fishing competition",
        )
        self.assertIn(TagTaxonomy.FISHING, tags)
        self.assertIn(TagTaxonomy.SPORTS_EVENT, tags)

    def test_event_6_art_market(self):
        """Arts and crafts market."""
        tags = infer_tags(
            title="Perdido Key Art Market",
            description="Local artisans showcase handmade crafts and art",
        )
        self.assertIn(TagTaxonomy.MARKET, tags)
        self.assertTrue(TagTaxonomy.ART in tags or TagTaxonomy.CRAFT in tags)

    def test_event_7_wine_tasting(self):
        """Wine tasting event."""
        tags = infer_tags(
            title="Wine & Cheese Tasting", description="Sample wines paired with artisan cheeses"
        )
        self.assertIn(TagTaxonomy.WINE, tags)
        # food_drink or craft may be present
        # Just verify wine is detected

    def test_event_8_yoga_beach(self):
        """Beach yoga."""
        tags = infer_tags(
            title="Sunrise Yoga on the Beach",
            description="Start your day with yoga by the ocean",
            location="Perdido Key Beach",
        )
        self.assertIn(TagTaxonomy.FITNESS, tags)
        self.assertIn(TagTaxonomy.BEACH, tags)
        # outdoors may be present but beach and fitness are the primary tags

    def test_event_9_holiday_parade(self):
        """Holiday parade."""
        tags = infer_tags(
            title="Christmas Parade", description="Annual holiday parade through downtown"
        )
        self.assertIn(TagTaxonomy.HOLIDAY, tags)
        self.assertIn(TagTaxonomy.PARADE, tags)

    def test_event_10_karaoke_bar(self):
        """Karaoke night."""
        tags = infer_tags(
            title="Karaoke Thursday", description="Sing your favorite songs. Full bar available."
        )
        self.assertIn(TagTaxonomy.KARAOKE, tags)


if __name__ == "__main__":
    unittest.main()
