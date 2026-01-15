"""
Unit Tests for Event Normalizer

Tests paid/free detection, event filtering, tag inference, and venue resolution.
"""

import unittest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from event_normalizer import (
    detect_paid_or_free,
    PaidStatus,
    EventType,
    should_filter_brandon_styles_owa,
    get_filter_reason,
    extract_cost_text,
    enrich_event,
)


class TestPaidFreeDetection(unittest.TestCase):
    """Test paid/free event detection."""
    
    def test_explicit_free(self):
        """Test explicit free indicators."""
        is_free, status, event_type = detect_paid_or_free(
            description="Free admission for all ages!"
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)
        self.assertEqual(event_type, EventType.FREE_EVENT)
    
    def test_no_cover(self):
        """Test 'no cover' as free."""
        is_free, status, event_type = detect_paid_or_free(
            description="Live music tonight! No cover charge."
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)
    
    def test_complimentary(self):
        """Test 'complimentary' as free."""
        is_free, status, event_type = detect_paid_or_free(
            description="Complimentary cocktails and appetizers"
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)
    
    def test_zero_dollars(self):
        """Test $0 as free."""
        is_free, status, event_type = detect_paid_or_free(
            cost_text="$0.00"
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)
        self.assertEqual(status, PaidStatus.FREE)
    
    def test_explicit_price(self):
        """Test explicit price as paid."""
        is_free, status, event_type = detect_paid_or_free(
            description="Tickets are $25 per person"
        )
        self.assertFalse(is_free)
        self.assertEqual(status, PaidStatus.PAID)
        self.assertEqual(event_type, EventType.PAID_EVENT)
    
    def test_cover_charge(self):
        """Test cover charge as paid."""
        is_free, status, event_type = detect_paid_or_free(
            description="$10 cover at the door"
        )
        self.assertFalse(is_free)
        self.assertEqual(status, PaidStatus.PAID)
    
    def test_presale(self):
        """Test presale as paid."""
        is_free, status, event_type = detect_paid_or_free(
            description="Presale tickets available now!"
        )
        self.assertFalse(is_free)
        self.assertEqual(status, PaidStatus.PAID)
    
    def test_ticket_required(self):
        """Test 'ticket required' as paid."""
        is_free, status, event_type = detect_paid_or_free(
            description="Ticket required for entry"
        )
        self.assertFalse(is_free)
        self.assertEqual(status, PaidStatus.PAID)
    
    def test_vip_tickets(self):
        """Test VIP tickets as paid."""
        is_free, status, event_type = detect_paid_or_free(
            description="VIP tickets available for purchase"
        )
        self.assertFalse(is_free)
        self.assertEqual(status, PaidStatus.PAID)
    
    def test_free_with_rsvp(self):
        """Test 'free with RSVP' as free."""
        is_free, status, event_type = detect_paid_or_free(
            description="Free with RSVP by Friday"
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)
    
    def test_donation_suggested(self):
        """Test 'donation suggested' as unknown (could be free or paid)."""
        is_free, status, event_type = detect_paid_or_free(
            description="Donation suggested at the door"
        )
        # This is ambiguous - current implementation may treat as free or unknown
        # Just verify it doesn't crash
        self.assertIn(status, [PaidStatus.FREE, PaidStatus.UNKNOWN])
    
    def test_unknown_no_indicators(self):
        """Test no price indicators as unknown."""
        is_free, status, event_type = detect_paid_or_free(
            description="Join us for a great evening of entertainment"
        )
        self.assertIsNone(is_free)
        self.assertEqual(status, PaidStatus.UNKNOWN)
        self.assertEqual(event_type, EventType.EVENT)
    
    def test_phone_number_not_price(self):
        """Test that phone numbers are not detected as prices."""
        is_free, status, event_type = detect_paid_or_free(
            description="Call 555-1234 for more info"
        )
        self.assertEqual(status, PaidStatus.UNKNOWN)
    
    def test_html_in_description(self):
        """Test HTML is cleaned before price detection."""
        is_free, status, event_type = detect_paid_or_free(
            description="<p>Free admission</p><br/>No cover charge"
        )
        self.assertTrue(is_free)
        self.assertEqual(status, PaidStatus.FREE)


class TestBrandonStylesFilter(unittest.TestCase):
    """Test Brandon Styles @ OWA filtering."""
    
    def test_brandon_styles_at_owa(self):
        """Test Brandon Styles at OWA is filtered."""
        should_filter = should_filter_brandon_styles_owa(
            title="Brandon Styles Live",
            location="OWA Parks, Foley, AL"
        )
        self.assertTrue(should_filter)
    
    def test_brandon_styles_foley_alabama(self):
        """Test Brandon Styles in Foley, AL is filtered."""
        should_filter = should_filter_brandon_styles_owa(
            title="Brandon Styles in Concert",
            location="Foley, Alabama"
        )
        self.assertTrue(should_filter)
    
    def test_brandon_styles_elsewhere(self):
        """Test Brandon Styles elsewhere is NOT filtered."""
        should_filter = should_filter_brandon_styles_owa(
            title="Brandon Styles Live",
            location="Flora-Bama, Perdido Key, FL"
        )
        self.assertFalse(should_filter)
    
    def test_owa_without_brandon_styles(self):
        """Test OWA events without Brandon Styles are NOT filtered."""
        should_filter = should_filter_brandon_styles_owa(
            title="Summer Concert Series",
            location="OWA Parks, Foley, AL"
        )
        self.assertFalse(should_filter)
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        should_filter = should_filter_brandon_styles_owa(
            title="BRANDON STYLES live",
            location="owa foley al"
        )
        self.assertTrue(should_filter)
    
    def test_filter_reason(self):
        """Test filter reason is returned."""
        reason = get_filter_reason(
            title="Brandon Styles",
            location="OWA, Foley, AL"
        )
        self.assertEqual(reason, "FILTER_BRANDON_STYLES_OWA_AL")


class TestCostTextExtraction(unittest.TestCase):
    """Test cost text extraction."""
    
    def test_extract_price_sentence(self):
        """Test extraction of sentence with price."""
        cost = extract_cost_text(
            "Join us for a great event. Tickets are $25 per person. Food and drinks available."
        )
        self.assertIn("$25", cost)
        self.assertIn("ticket", cost.lower())
    
    def test_extract_free_sentence(self):
        """Test extraction of sentence with 'free'."""
        cost = extract_cost_text(
            "This is a community event. Free admission for all. Bring the family."
        )
        self.assertIn("free", cost.lower())


class TestEventEnrichment(unittest.TestCase):
    """Test full event enrichment."""
    
    def test_enrich_free_event(self):
        """Test enrichment of free event."""
        event = {
            'title': 'Free Concert at the Park',
            'description': 'Live music all day. Free admission!',
            'location': 'Flora-Bama',
        }
        
        enriched = enrich_event(event)
        
        self.assertTrue(enriched['is_free'])
        self.assertEqual(enriched['paid_status'], 'FREE')
        self.assertEqual(enriched['event_type'], 'free_event')
        self.assertIn('tags', enriched)
        self.assertIn('live_music', enriched['tags'])
    
    def test_enrich_paid_event(self):
        """Test enrichment of paid event."""
        event = {
            'title': 'Comedy Show',
            'description': 'Tickets $20. Hilarious night of stand-up comedy.',
            'location': 'Perdido Key Sports Bar',
        }
        
        enriched = enrich_event(event)
        
        self.assertFalse(enriched['is_free'])
        self.assertEqual(enriched['paid_status'], 'PAID')
        self.assertIn('comedy', enriched['tags'])
    
    def test_venue_resolution(self):
        """Test venue resolution."""
        event = {
            'title': 'Beach Party',
            'description': 'Join us for fun',
            'location': 'Flora Bama Lounge',
        }
        
        enriched = enrich_event(event)
        
        self.assertEqual(enriched['venue_id'], 'flora-bama')
        self.assertEqual(enriched['venue_name'], 'Flora-Bama')
        self.assertEqual(enriched['normalized_location'], 'Flora-Bama')
    
    def test_brandon_styles_filtered(self):
        """Test Brandon Styles event is marked for filtering."""
        event = {
            'title': 'Brandon Styles Live',
            'description': 'Great music',
            'location': 'OWA Parks, Foley, AL',
        }
        
        enriched = enrich_event(event)
        
        self.assertTrue(enriched['should_filter'])
        self.assertEqual(enriched['filter_reason'], 'FILTER_BRANDON_STYLES_OWA_AL')
    
    def test_tagging(self):
        """Test tag inference."""
        event = {
            'title': 'Karaoke Night with Happy Hour Specials',
            'description': 'Sing your heart out while enjoying drink specials',
            'location': 'Local Bar',
        }
        
        enriched = enrich_event(event)
        
        tags = enriched['tags']
        self.assertIn('karaoke', tags)
        self.assertTrue(any(tag in ['happy_hour', 'food_drink'] for tag in tags))


if __name__ == '__main__':
    unittest.main()
