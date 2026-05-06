"""
Event Normalization and Enrichment

This module provides functions for normalizing and enriching event data:
- Paid/Free detection
- Event filtering (e.g., Brandon Styles @ OWA)
- Tag inference
- Venue resolution and linking
"""

import re
from enum import Enum

import pandas as pd


class PaidStatus(Enum):
    """Event paid status."""

    FREE = "FREE"
    PAID = "PAID"
    UNKNOWN = "UNKNOWN"


class EventType(Enum):
    """Event type based on cost."""

    FREE_EVENT = "free_event"
    PAID_EVENT = "paid_event"
    EVENT = "event"  # Unknown/unspecified


# ============================================================================
# PAID/FREE DETECTION
# ============================================================================

# Price patterns to detect
PRICE_PATTERNS = [
    r"\$\d+(?:\.\d{2})?",  # $10, $10.00
    r"\d+(?:\.\d{2})?\s*(?:dollar|usd)",  # 10 dollars, 10.00 USD
    r"(?:pre-?sale|presale)",  # pre-sale, presale
    r"(?:vip|ticket|admission).*(?:required|cost|price|fee|available|purchase)",
    r"(?:cover|charge).*\$",
    r"\$.*(?:ticket|admission|entry)",
]

# Free indicators
FREE_PATTERNS = [
    r"\bfree\b",
    r"\bno\s+(?:cover|charge|cost|fee|admission)\b",
    r"\bcomplimentary\b",
    r"\badmission\s+free\b",
    r"\$0(?:\.00)?\b",
    r"\b0\s+(?:dollar|usd)\b",
    r"\bzero\s+(?:dollar|usd)\b",
]

# Exclude these from price detection (false positives)
EXCLUDE_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # Phone numbers
    r"\b\d{3}[-.\s]?\d{4}\b",  # Short phone numbers
]


def clean_text_for_price_detection(text: str) -> str:
    """Clean text for price detection by removing HTML and extra whitespace."""
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def detect_paid_or_free(
    title: str = "", description: str = "", cost_text: str = ""
) -> tuple[bool, PaidStatus, EventType]:
    """
    Determine if an event is paid or free.

    Args:
        title: Event title
        description: Event description
        cost_text: Explicit cost/price text if available

    Returns:
        Tuple of (is_free: bool, paid_status: PaidStatus, event_type: EventType)
    """
    # Combine all text for analysis
    text_parts = []
    if title:
        text_parts.append(title)
    if description:
        text_parts.append(description)
    if cost_text:
        text_parts.append(cost_text)

    combined_text = " ".join(text_parts)
    cleaned_text = clean_text_for_price_detection(combined_text)

    # Check for excluded patterns (phone numbers, etc.)
    for pattern in EXCLUDE_PATTERNS:
        cleaned_text = re.sub(pattern, "", cleaned_text)

    # Check for free indicators FIRST (higher priority)
    free_found = any(re.search(pattern, cleaned_text, re.IGNORECASE) for pattern in FREE_PATTERNS)

    # Check for price indicators
    paid_found = any(re.search(pattern, cleaned_text, re.IGNORECASE) for pattern in PRICE_PATTERNS)

    # Special case: $0 or $0.00 should be treated as FREE
    if re.search(r"\$0(?:\.00)?\b", cleaned_text):
        free_found = True
        paid_found = False

    # Determine status
    if free_found and not paid_found:
        return True, PaidStatus.FREE, EventType.FREE_EVENT
    elif paid_found and not free_found:
        return False, PaidStatus.PAID, EventType.PAID_EVENT
    elif paid_found and free_found:
        # Both found - check context
        # If "free with RSVP" or similar, treat as free
        if re.search(
            r"\bfree\s+(?:with|for)\s+(?:rsvp|registration)\b", cleaned_text, re.IGNORECASE
        ):
            return True, PaidStatus.FREE, EventType.FREE_EVENT
        # Otherwise, if there's a price, treat as paid
        return False, PaidStatus.PAID, EventType.PAID_EVENT
    else:
        # Neither found - unknown
        return None, PaidStatus.UNKNOWN, EventType.EVENT


def extract_cost_text(description: str = "") -> str | None:
    """
    Extract cost-related text from description for display.

    Returns the sentence or phrase containing price information.
    """
    if not description:
        return None

    cleaned = clean_text_for_price_detection(description)

    # Look for sentences with price indicators
    sentences = re.split(r"[.!?]\s+", cleaned)

    for sentence in sentences:
        # Check if sentence contains price or free indicators
        has_price = any(
            re.search(pattern, sentence, re.IGNORECASE)
            for pattern in PRICE_PATTERNS + FREE_PATTERNS
        )

        if has_price:
            # Return trimmed sentence
            return sentence.strip()[:200]  # Cap at 200 chars

    return None


# ============================================================================
# EVENT FILTERING
# ============================================================================

UNWANTED_FEED_PATTERNS = [
    ("FILTER_OWA", r"\bowa\b"),
    ("FILTER_TROPIC_FALLS", r"\btropic\s+falls\b"),
    ("FILTER_GULF_SHORES", r"\bgulf\s+shores\b"),
    ("FILTER_ORANGE_BEACH", r"\borange\s+beach\b"),
    ("FILTER_ONECLUB", r"\boneclub\b"),
    ("FILTER_GULF_STATE_PARK", r"\bgulf\s+state\s+park\b"),
    ("FILTER_RIBBON_CUTTING", r"\bribbon[\s-]*cutting\b"),
    ("FILTER_BAR45", r"\bbar45\b"),
    ("FILTER_BROWN_BAG_LUNCH", r"\bbrown\s+bag\s+lunch\b"),
    ("FILTER_LUNCH_SERIES", r"\blunch\s+series\b"),
    ("FILTER_SANDERS_BEACH", r"\bsanders\s+beach\b"),
    ("FILTER_EVERMAN_COOP", r"\bever'?man\s+coop\b"),
    ("FILTER_NOTEBOOKLM", r"\bnotebooklm\b"),
    ("FILTER_SMALL_BUSINESS", r"\bsmall\s+business\b"),
    ("FILTER_VIRTUAL_EVENT", r"\bvirtual\s+event\b"),
    ("FILTER_NETWORKING", r"\bnetworking\b"),
    ("FILTER_MONTHLY_MEETING", r"\bmonthly\s+meeting\b"),
    ("FILTER_BOARD_OF_DIRECTORS", r"\bboard\s+of\s+directors\b"),
    ("FILTER_COMMITTEE", r"\bcommittee\b"),
]


def should_filter_brandon_styles_owa(
    title: str = "", location: str = "", description: str = ""
) -> bool:
    """
    Check if event should be filtered (Brandon Styles at OWA in Foley, AL).

    We want to exclude Brandon Styles events at OWA (Foley, AL) but keep
    events on the Florida side.

    Args:
        title: Event title
        location: Event location
        description: Event description

    Returns:
        True if event should be filtered (excluded), False otherwise
    """
    combined_text = " ".join([title or "", location or "", description or ""])
    text_lower = combined_text.lower()

    # Check for "Brandon Styles" (case-insensitive)
    has_brandon_styles = bool(re.search(r"\bbrandon\s+styles\b", text_lower))

    if not has_brandon_styles:
        return False

    # Check for OWA and Foley, AL indicators
    has_owa = bool(re.search(r"\bowa\b", text_lower))
    has_foley = bool(re.search(r"\bfoley\b", text_lower))
    has_alabama = bool(re.search(r"\b(?:al|alabama)\b", text_lower))

    # Filter if Brandon Styles AND (OWA OR (Foley AND Alabama))
    if has_owa or (has_foley and has_alabama):
        return True

    return False


def get_unwanted_feed_filter_reason(
    title: str = "", location: str = "", description: str = ""
) -> str | None:
    """Return the first configured unwanted-feed filter reason that matches."""
    combined_text = " ".join([title or "", location or "", description or ""])
    text_lower = combined_text.lower()

    for reason, pattern in UNWANTED_FEED_PATTERNS:
        if re.search(pattern, text_lower):
            return reason

    return None


def get_filter_reason(title: str = "", location: str = "", description: str = "") -> str | None:
    """
    Get filter reason if event should be filtered.

    Returns:
        Filter reason string if event should be filtered, None otherwise
    """
    if should_filter_brandon_styles_owa(title, location, description):
        return "FILTER_BRANDON_STYLES_OWA_AL"

    unwanted_reason = get_unwanted_feed_filter_reason(title, location, description)
    if unwanted_reason:
        return unwanted_reason

    return None


# ============================================================================
# EVENT ENRICHMENT
# ============================================================================


def enrich_event(event_dict: dict) -> dict:
    """
    Enrich event data with normalized fields.

    Adds:
    - is_free, paid_status, event_type
    - cost_text (extracted)
    - tags (inferred)
    - venue_id, normalized_location (if matched)
    - filter_reason (if applicable)

    Args:
        event_dict: Event dictionary with fields like title, description, location

    Returns:
        Enriched event dictionary
    """
    import tag_taxonomy
    import venue_registry

    enriched = event_dict.copy()

    # 1. Detect paid/free status
    is_free, paid_status, event_type = detect_paid_or_free(
        title=event_dict.get("title", ""),
        description=event_dict.get("description", ""),
        cost_text=event_dict.get("cost", ""),
    )

    enriched["is_free"] = is_free
    enriched["paid_status"] = paid_status.value
    enriched["event_type"] = event_type.value

    # Extract cost text for display
    if not enriched.get("cost"):
        cost_text = extract_cost_text(event_dict.get("description", ""))
        if cost_text:
            enriched["cost_text"] = cost_text

    # 2. Infer tags
    tags = tag_taxonomy.infer_tags(
        title=event_dict.get("title", ""),
        description=event_dict.get("description", ""),
        location=event_dict.get("location", ""),
        category=event_dict.get("category", ""),
    )
    enriched["tags"] = tags

    # 3. Resolve venue
    venue = venue_registry.resolve_venue(event_dict.get("location", ""))
    if venue:
        enriched["venue_id"] = venue.id
        enriched["venue_name"] = venue.canonical_name
        # Also update location to canonical name for consistency
        enriched["normalized_location"] = venue.canonical_name

    # 4. Check filter conditions
    filter_reason = get_filter_reason(
        title=event_dict.get("title", ""),
        location=event_dict.get("location", ""),
        description=event_dict.get("description", ""),
    )

    if filter_reason:
        enriched["filter_reason"] = filter_reason
        enriched["should_filter"] = True
    else:
        enriched["should_filter"] = False

    return enriched


def enrich_events_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich a DataFrame of events.

    Args:
        df: DataFrame with event data

    Returns:
        Enriched DataFrame with new columns
    """
    enriched_events = []

    for _, row in df.iterrows():
        event_dict = row.to_dict()
        enriched = enrich_event(event_dict)
        enriched_events.append(enriched)

    return pd.DataFrame(enriched_events)


def filter_events_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter events DataFrame based on filter conditions.

    Args:
        df: DataFrame with enriched event data (must have 'should_filter' column)

    Returns:
        Tuple of (kept_events_df, filtered_events_df)
    """
    if "should_filter" not in df.columns:
        # If not enriched yet, enrich first
        df = enrich_events_dataframe(df)

    kept = df[~df["should_filter"]].copy()
    filtered = df[df["should_filter"]].copy()

    return kept, filtered
