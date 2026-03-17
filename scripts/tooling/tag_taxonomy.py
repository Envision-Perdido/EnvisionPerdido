"""
Tag Taxonomy for Event Classification

This module defines the controlled tag taxonomy used for event tagging.
Tags are organized by category and provide a consistent, deterministic
vocabulary for classifying events.
"""

import re

# ============================================================================
# TAG TAXONOMY - Single Source of Truth
# ============================================================================


class TagTaxonomy:
    """Controlled tag vocabulary organized by category."""

    # Music & Entertainment
    LIVE_MUSIC = "live_music"
    DJ = "dj"
    OPEN_MIC = "open_mic"
    KARAOKE = "karaoke"
    COMEDY = "comedy"
    THEATER = "theater"

    # Food & Drink
    FOOD_DRINK = "food_drink"
    HAPPY_HOUR = "happy_hour"
    WINE = "wine"
    BEER = "beer"
    COCKTAILS = "cocktails"
    BRUNCH = "brunch"
    DINNER = "dinner"

    # Family & Kids
    FAMILY_FRIENDLY = "family_friendly"
    KIDS = "kids"

    # Outdoors & Recreation
    OUTDOORS = "outdoors"
    BEACH = "beach"
    RUN_WALK = "run_walk"
    FITNESS = "fitness"
    SPORTS_EVENT = "sports_event"
    FISHING = "fishing"
    WATER_SPORTS = "water_sports"

    # Arts & Culture
    ART = "art"
    CRAFT = "craft"
    GALLERY = "gallery"
    EXHIBITION = "exhibition"

    # Community & Social
    FUNDRAISER = "fundraiser"
    NONPROFIT = "nonprofit"
    CHARITY = "charity"
    NETWORKING = "networking"
    MARKET = "market"
    FESTIVAL = "festival"
    PARADE = "parade"

    # Special Occasions
    HOLIDAY = "holiday"
    SEASONAL = "seasonal"

    # Other
    SPORTS_WATCH = "sports_watch"
    TRIVIA = "trivia"
    EDUCATIONAL = "educational"
    WORKSHOP = "workshop"


# ============================================================================
# TAG KEYWORD MAPPING - For Inference
# ============================================================================

TAG_KEYWORDS = {
    # Music & Entertainment - High priority patterns
    TagTaxonomy.LIVE_MUSIC: [
        r"\blive\s+music\b",
        r"\blive\s+band\b",
        r"\bperformance\b",
        r"\bconcert\b",
        r"\bmusician\b",
        r"\bsinger\b",
        r"\bacoustic\b",
    ],
    TagTaxonomy.DJ: [
        r"\bdj\b",
        r"\bdisc\s+jockey\b",
    ],
    TagTaxonomy.OPEN_MIC: [
        r"\bopen\s+mic\b",
        r"\bopen\s+mike\b",
    ],
    TagTaxonomy.KARAOKE: [
        r"\bkaraoke\b",
    ],
    TagTaxonomy.COMEDY: [
        r"\bcomedy\b",
        r"\bcomedian\b",
        r"\bstand\s*-?\s*up\b",
    ],
    TagTaxonomy.THEATER: [
        r"\btheater\b",
        r"\btheatre\b",
        r"\bplay\b",
        r"\bdrama\b",
        r"\bperformance\s+art\b",
    ],
    # Food & Drink
    TagTaxonomy.FOOD_DRINK: [
        r"\bfood\b",
        r"\bdrink\b",
        r"\bdining\b",
        r"\bmenu\b",
        r"\bspecials\b",
    ],
    TagTaxonomy.HAPPY_HOUR: [
        r"\bhappy\s+hour\b",
    ],
    TagTaxonomy.WINE: [
        r"\bwine\b",
        r"\bwinery\b",
        r"\bvineyard\b",
    ],
    TagTaxonomy.BEER: [
        r"\bbeer\b",
        r"\bbrewery\b",
        r"\bcraft\s+beer\b",
        r"\bale\b",
        r"\bipa\b",
    ],
    TagTaxonomy.COCKTAILS: [
        r"\bcocktail\b",
        r"\bmixed\s+drink\b",
        r"\bmartini\b",
    ],
    TagTaxonomy.BRUNCH: [
        r"\bbrunch\b",
    ],
    TagTaxonomy.DINNER: [
        r"\bdinner\b",
        r"\bsupper\b",
    ],
    # Family & Kids
    TagTaxonomy.FAMILY_FRIENDLY: [
        r"\bfamily\s+friendly\b",
        r"\bfamily\s+fun\b",
        r"\ball\s+ages\b",
    ],
    TagTaxonomy.KIDS: [
        r"\bkids\b",
        r"\bchildren\b",
        r"\bchild\b",
        r"\byouth\b",
    ],
    # Outdoors & Recreation
    TagTaxonomy.OUTDOORS: [
        r"\boutdoor\b",
        r"\boutside\b",
        r"\bpark\b",
    ],
    TagTaxonomy.BEACH: [
        r"\bbeach\b",
        r"\bsand\b",
        r"\bcoastal\b",
        r"\bseaside\b",
    ],
    TagTaxonomy.RUN_WALK: [
        r"\b\d+k\s+run\b",
        r"\bmarathon\b",
        r"\bhalf\s+marathon\b",
        r"\b5k\b",
        r"\b10k\b",
        r"\bfun\s+run\b",
        r"\bwalk\s+for\b",
        r"\bwalking\s+event\b",
    ],
    TagTaxonomy.FITNESS: [
        r"\bfitness\b",
        r"\byoga\b",
        r"\bworkout\b",
        r"\bexercise\b",
        r"\bgym\b",
    ],
    TagTaxonomy.SPORTS_EVENT: [
        r"\btournament\b",
        r"\bsports\s+event\b",
        r"\bcompetition\b",
        r"\bgolf\b",
        r"\btennis\b",
        r"\bsoccer\b",
        r"\bbaseball\b",
        r"\bbasketball\b",
    ],
    TagTaxonomy.FISHING: [
        r"\bfishing\b",
        r"\brodeo\b",
    ],
    TagTaxonomy.WATER_SPORTS: [
        r"\bkayak\b",
        r"\bpaddleboard\b",
        r"\bsurfing\b",
        r"\bboating\b",
    ],
    # Arts & Culture
    TagTaxonomy.ART: [
        r"\bart\b",
        r"\bartist\b",
        r"\bpainting\b",
        r"\bsculpture\b",
    ],
    TagTaxonomy.CRAFT: [
        r"\bcraft\b",
        r"\bhandmade\b",
        r"\bartisan\b",
    ],
    TagTaxonomy.GALLERY: [
        r"\bgallery\b",
        r"\bart\s+show\b",
    ],
    TagTaxonomy.EXHIBITION: [
        r"\bexhibition\b",
        r"\bexhibit\b",
        r"\bshowcase\b",
    ],
    # Community & Social
    TagTaxonomy.FUNDRAISER: [
        r"\bfundraiser\b",
        r"\bfund\s+raiser\b",
        r"\braising\s+funds\b",
    ],
    TagTaxonomy.NONPROFIT: [
        r"\bnon\s*-?\s*profit\b",
        r"\bcharity\b",
    ],
    TagTaxonomy.CHARITY: [
        r"\bcharity\b",
        r"\bdonation\b",
    ],
    TagTaxonomy.NETWORKING: [
        r"\bnetworking\b",
        r"\bmixer\b",
        r"\bbusiness\s+social\b",
    ],
    TagTaxonomy.MARKET: [
        r"\bmarket\b",
        r"\bfarmers\s+market\b",
        r"\bflea\s+market\b",
        r"\bvendor\b",
    ],
    TagTaxonomy.FESTIVAL: [
        r"\bfestival\b",
        r"\bfest\b",
    ],
    TagTaxonomy.PARADE: [
        r"\bparade\b",
    ],
    # Special Occasions
    TagTaxonomy.HOLIDAY: [
        r"\bholiday\b",
        r"\bchristmas\b",
        r"\bthanksgiving\b",
        r"\bhalloween\b",
        r"\beaster\b",
        r"\b4th\s+of\s+july\b",
        r"\bindependence\s+day\b",
        r"\bnew\s+year\b",
    ],
    TagTaxonomy.SEASONAL: [
        r"\bseasonal\b",
        r"\bspring\b",
        r"\bsummer\b",
        r"\bfall\b",
        r"\bwinter\b",
    ],
    # Other
    TagTaxonomy.SPORTS_WATCH: [
        r"\bwatch\s+party\b",
        r"\bgame\s+watch\b",
        r"\bviewing\s+party\b",
    ],
    TagTaxonomy.TRIVIA: [
        r"\btrivia\b",
        r"\bquiz\b",
    ],
    TagTaxonomy.EDUCATIONAL: [
        r"\beducational\b",
        r"\blearning\b",
        r"\bseminar\b",
        r"\bworkshop\b",
        r"\bclass\b",
    ],
    TagTaxonomy.WORKSHOP: [
        r"\bworkshop\b",
        r"\bhands\s*-?\s*on\b",
    ],
}


# ============================================================================
# TAG INFERENCE LOGIC
# ============================================================================


def infer_tags(
    title: str = "",
    description: str = "",
    location: str = "",
    category: str = "",
    max_tags: int = 5,
) -> list[str]:
    """
    Infer tags from event fields using keyword matching.

    Args:
        title: Event title
        description: Event description
        location: Event location
        category: Event category
        max_tags: Maximum number of tags to return (default: 5)

    Returns:
        List of tag identifiers (up to max_tags)
    """
    # Build combined text for matching
    text_parts = []
    if title:
        text_parts.append(title.lower())
    if description:
        text_parts.append(description.lower())
    if location:
        text_parts.append(location.lower())
    if category:
        text_parts.append(category.lower())

    combined_text = " ".join(text_parts)

    # Score each tag based on keyword matches
    tag_scores = {}

    for tag, patterns in TAG_KEYWORDS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            score += len(matches)

        if score > 0:
            tag_scores[tag] = score

    # Sort by score (descending) and return top max_tags
    sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
    top_tags = [tag for tag, score in sorted_tags[:max_tags]]

    return top_tags


def get_all_tags() -> list[str]:
    """Get list of all available tags."""
    return [
        value
        for key, value in vars(TagTaxonomy).items()
        if not key.startswith("_") and isinstance(value, str)
    ]


def validate_tags(tags: list[str]) -> list[str]:
    """Validate that tags are in the controlled taxonomy."""
    valid_tags_set = set(get_all_tags())
    return [tag for tag in tags if tag in valid_tags_set]
