"""
Known Venues Registry for Location Normalization

This module maintains a registry of known venues with their canonical names,
aliases, and metadata. Used for location matching and normalization.
"""

import re
from typing import Optional, Dict, List
from dataclasses import dataclass


# ============================================================================
# LOCATION NORMALIZATION
# ============================================================================

def normalize_location_text(text: str) -> str:
    """
    Normalize location text for matching.
    
    - Convert to lowercase
    - Remove punctuation (except hyphens between words)
    - Collapse multiple spaces
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation except hyphens and spaces
    text = re.sub(r'[^\w\s\-]', '', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Strip whitespace
    text = text.strip()
    
    return text


@dataclass
class Venue:
    """Represents a known venue with metadata."""
    id: str
    canonical_name: str
    aliases: List[str]
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    
    def __post_init__(self):
        """Normalize aliases for matching."""
        # Include canonical name in aliases
        all_names = [self.canonical_name] + self.aliases
        # Normalize for matching: lowercase, no punctuation, collapse whitespace
        self.normalized_aliases = [normalize_location_text(name) for name in all_names]


# ============================================================================
# KNOWN VENUES REGISTRY
# ============================================================================

KNOWN_VENUES = [
    Venue(
        id="flora-bama",
        canonical_name="Flora-Bama",
        aliases=["Flora Bama", "Flora-Bama Lounge", "Flora-Bama Lounge & Package"],
        city="Perdido Key",
        state="FL",
    ),
    Venue(
        id="perdido-key-sports-bar",
        canonical_name="Perdido Key Sports Bar",
        aliases=["PK Sports Bar", "PKSB", "Perdido Key SB"],
        city="Perdido Key",
        state="FL",
    ),
    Venue(
        id="lillians",
        canonical_name="Lillian's Pizza",
        aliases=["Lillians", "Lillian's", "Lillians Pizza"],
        city="Lillian",
        state="AL",
    ),
    Venue(
        id="the-oyster-bar-perdido-key",
        canonical_name="The Oyster Bar",
        aliases=["Oyster Bar", "The Oyster Bar Perdido Key"],
        city="Perdido Key",
        state="FL",
    ),
    Venue(
        id="perdido-key-oyster-bar",
        canonical_name="Perdido Key Oyster Bar",
        aliases=["PK Oyster Bar", "PKOB"],
        city="Perdido Key",
        state="FL",
    ),
    Venue(
        id="big-lagoon-state-park",
        canonical_name="Big Lagoon State Park",
        aliases=["Big Lagoon Park", "Big Lagoon"],
        city="Pensacola",
        state="FL",
    ),
    Venue(
        id="gulf-state-park",
        canonical_name="Gulf State Park",
        aliases=["Gulf State Park Pier", "GSP"],
        city="Gulf Shores",
        state="AL",
    ),
    Venue(
        id="perdido-beach-resort",
        canonical_name="Perdido Beach Resort",
        aliases=["PBR", "Perdido Resort"],
        city="Orange Beach",
        state="AL",
    ),
    Venue(
        id="tacky-jacks",
        canonical_name="Tacky Jacks",
        aliases=["Tacky Jack's", "Tacky Jacks Gulf Shores"],
        city="Gulf Shores",
        state="AL",
    ),
    Venue(
        id="owa",
        canonical_name="OWA",
        aliases=["OWA Parks", "OWA Foley"],
        city="Foley",
        state="AL",
    ),
    Venue(
        id="the-wharf",
        canonical_name="The Wharf",
        aliases=["Wharf", "The Wharf Orange Beach"],
        city="Orange Beach",
        state="AL",
    ),
    Venue(
        id="lulu-s",
        canonical_name="LuLu's",
        aliases=["LuLu's Gulf Shores", "Lulus"],
        city="Gulf Shores",
        state="AL",
    ),
    Venue(
        id="the-hangout",
        canonical_name="The Hangout",
        aliases=["Hangout", "Hangout Gulf Shores"],
        city="Gulf Shores",
        state="AL",
    ),
    Venue(
        id="flora-bama-yacht-club",
        canonical_name="Flora-Bama Yacht Club",
        aliases=["FBYC", "Flora Bama Yacht Club"],
        city="Orange Beach",
        state="AL",
    ),
]


# Build lookup index for fast matching
_venue_lookup: Dict[str, Venue] = {}
for venue in KNOWN_VENUES:
    for normalized_alias in venue.normalized_aliases:
        _venue_lookup[normalized_alias] = venue


# ============================================================================
# VENUE RESOLUTION
# ============================================================================

def resolve_venue(location_text: str) -> Optional[Venue]:
    """
    Resolve a location string to a known venue.
    
    Args:
        location_text: The location string from event data
    
    Returns:
        Venue object if matched, None otherwise
    """
    if not location_text:
        return None
    
    normalized = normalize_location_text(location_text)
    
    # Direct lookup
    if normalized in _venue_lookup:
        return _venue_lookup[normalized]
    
    # Fuzzy matching - check if normalized text contains any venue name
    for venue in KNOWN_VENUES:
        for alias in venue.normalized_aliases:
            if alias in normalized or normalized in alias:
                return venue
    
    return None


def get_venue_by_id(venue_id: str) -> Optional[Venue]:
    """Get a venue by its ID."""
    for venue in KNOWN_VENUES:
        if venue.id == venue_id:
            return venue
    return None


def get_all_venues() -> List[Venue]:
    """Get list of all known venues."""
    return KNOWN_VENUES.copy()


def add_venue(venue: Venue) -> None:
    """
    Add a new venue to the registry (runtime only).
    
    Note: This does not persist the venue. For permanent additions,
    update the KNOWN_VENUES list in this module.
    """
    KNOWN_VENUES.append(venue)
    
    # Update lookup index
    for normalized_alias in venue.normalized_aliases:
        _venue_lookup[normalized_alias] = venue
