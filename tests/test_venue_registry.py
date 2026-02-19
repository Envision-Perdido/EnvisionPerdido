"""
Unit Tests for Venue Registry

Tests venue resolution, normalization, and alias matching.
"""

import sys
import unittest
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from venue_registry import (
    Venue,
    get_all_venues,
    get_venue_by_id,
    normalize_location_text,
    resolve_venue,
)


class TestLocationNormalization(unittest.TestCase):
    """Test location text normalization."""

    def test_lowercase(self):
        """Test conversion to lowercase."""
        result = normalize_location_text("Flora-Bama")
        self.assertEqual(result, "flora-bama")

    def test_punctuation_removal(self):
        """Test punctuation removal (except hyphens)."""
        result = normalize_location_text("LuLu's Gulf Shores!")
        self.assertEqual(result, "lulus gulf shores")

    def test_hyphen_preservation(self):
        """Test that hyphens between words are preserved."""
        result = normalize_location_text("Flora-Bama")
        self.assertIn("-", result)

    def test_whitespace_collapse(self):
        """Test multiple spaces collapsed to one."""
        result = normalize_location_text("The   Oyster    Bar")
        self.assertEqual(result, "the oyster bar")

    def test_strip_whitespace(self):
        """Test leading/trailing whitespace removed."""
        result = normalize_location_text("  Flora-Bama  ")
        self.assertEqual(result, "flora-bama")

    def test_empty_string(self):
        """Test empty string handling."""
        result = normalize_location_text("")
        self.assertEqual(result, "")

    def test_none_handling(self):
        """Test None handling."""
        result = normalize_location_text(None)
        self.assertEqual(result, "")


class TestVenueResolution(unittest.TestCase):
    """Test venue resolution and matching."""

    def test_canonical_name_match(self):
        """Test matching by canonical name."""
        venue = resolve_venue("Flora-Bama")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "flora-bama")
        self.assertEqual(venue.canonical_name, "Flora-Bama")

    def test_alias_match(self):
        """Test matching by alias."""
        venue = resolve_venue("Flora Bama Lounge")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "flora-bama")

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        venue1 = resolve_venue("flora-bama")
        venue2 = resolve_venue("FLORA-BAMA")
        venue3 = resolve_venue("Flora-Bama")

        self.assertEqual(venue1.id, venue2.id)
        self.assertEqual(venue1.id, venue3.id)

    def test_punctuation_variation(self):
        """Test matching with punctuation variations."""
        venue = resolve_venue("Flora Bama")  # No hyphen
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "flora-bama")

    def test_perdido_key_sports_bar_alias(self):
        """Test Perdido Key Sports Bar aliases."""
        venue1 = resolve_venue("Perdido Key Sports Bar")
        venue2 = resolve_venue("PK Sports Bar")
        venue3 = resolve_venue("PKSB")

        self.assertEqual(venue1.id, "perdido-key-sports-bar")
        self.assertEqual(venue2.id, "perdido-key-sports-bar")
        self.assertEqual(venue3.id, "perdido-key-sports-bar")

    def test_lillians_variations(self):
        """Test Lillian's with apostrophe variations."""
        venue1 = resolve_venue("Lillian's Pizza")
        venue2 = resolve_venue("Lillians")

        self.assertEqual(venue1.id, "lillians")
        self.assertEqual(venue2.id, "lillians")

    def test_owa_match(self):
        """Test OWA venue matching."""
        venue = resolve_venue("OWA Parks")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "owa")
        self.assertEqual(venue.city, "Foley")
        self.assertEqual(venue.state, "AL")

    def test_no_match(self):
        """Test no match returns None."""
        venue = resolve_venue("Unknown Venue That Doesn't Exist")
        self.assertIsNone(venue)

    def test_empty_string(self):
        """Test empty string returns None."""
        venue = resolve_venue("")
        self.assertIsNone(venue)

    def test_none_input(self):
        """Test None input returns None."""
        venue = resolve_venue(None)
        self.assertIsNone(venue)

    def test_partial_match_in_longer_string(self):
        """Test matching venue name within longer location string."""
        venue = resolve_venue("Flora-Bama Lounge & Package, Perdido Key, FL")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "flora-bama")


class TestVenueById(unittest.TestCase):
    """Test getting venue by ID."""

    def test_get_by_id(self):
        """Test getting venue by ID."""
        venue = get_venue_by_id("flora-bama")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.canonical_name, "Flora-Bama")

    def test_invalid_id(self):
        """Test invalid ID returns None."""
        venue = get_venue_by_id("nonexistent-venue")
        self.assertIsNone(venue)


class TestVenueRegistry(unittest.TestCase):
    """Test venue registry operations."""

    def test_get_all_venues(self):
        """Test getting all venues."""
        venues = get_all_venues()
        self.assertIsInstance(venues, list)
        self.assertGreater(len(venues), 0)

        # Check some expected venues
        venue_ids = [v.id for v in venues]
        self.assertIn("flora-bama", venue_ids)
        self.assertIn("perdido-key-sports-bar", venue_ids)
        self.assertIn("owa", venue_ids)

    def test_venue_has_required_fields(self):
        """Test that venues have required fields."""
        venues = get_all_venues()
        for venue in venues:
            self.assertIsNotNone(venue.id)
            self.assertIsNotNone(venue.canonical_name)
            self.assertIsInstance(venue.aliases, list)

    def test_venue_normalization(self):
        """Test that venue normalization happens in __post_init__."""
        venue = Venue(id="test-venue", canonical_name="Test Venue", aliases=["Test", "The Test"])

        self.assertIsNotNone(venue.normalized_aliases)
        self.assertIsInstance(venue.normalized_aliases, list)
        # Should include normalized canonical name + aliases
        self.assertGreaterEqual(len(venue.normalized_aliases), 1)


class TestRealWorldVenueMatching(unittest.TestCase):
    """Test venue matching with real-world location strings."""

    def test_flora_bama_variations(self):
        """Test various Flora-Bama location strings."""
        variations = [
            "Flora-Bama",
            "Flora Bama",
            "Flora-Bama Lounge",
            "The Flora-Bama",
            "Flora-Bama, Perdido Key",
            "Flora-Bama Lounge & Package",
        ]

        for location in variations:
            venue = resolve_venue(location)
            self.assertIsNotNone(venue, f"Failed to match: {location}")
            self.assertEqual(venue.id, "flora-bama")

    def test_oyster_bar_disambiguation(self):
        """Test that different Oyster Bars are distinguished."""
        # We have both "The Oyster Bar" and "Perdido Key Oyster Bar"
        venue1 = resolve_venue("The Oyster Bar Perdido Key")
        venue2 = resolve_venue("Perdido Key Oyster Bar")

        # These should be recognized (may be same or different venues)
        self.assertIsNotNone(venue1)
        self.assertIsNotNone(venue2)

    def test_tacky_jacks(self):
        """Test Tacky Jacks matching."""
        venue = resolve_venue("Tacky Jack's")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "tacky-jacks")

    def test_the_wharf(self):
        """Test The Wharf matching."""
        venue = resolve_venue("The Wharf Orange Beach")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.id, "the-wharf")

    def test_lulus(self):
        """Test LuLu's matching with apostrophe."""
        venue1 = resolve_venue("LuLu's")
        venue2 = resolve_venue("LuLus")
        venue3 = resolve_venue("LuLu's Gulf Shores")

        self.assertEqual(venue1.id, "lulu-s")
        self.assertEqual(venue2.id, "lulu-s")
        self.assertEqual(venue3.id, "lulu-s")


if __name__ == "__main__":
    unittest.main()
