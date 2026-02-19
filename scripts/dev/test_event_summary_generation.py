"""
Event Summary Generator - Development Test Harness

Tests the summary generation logic without requiring WordPress.
Run locally to verify summaries look good before deploying.

Usage:
    python test_event_summary_generation.py
"""

import re
import hashlib
from typing import List, Tuple

# ============================================================================
# CORE FUNCTIONS (matching PHP plugin logic)
# ============================================================================

ABBREVIATIONS = [
    'U.S.', 'U.K.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.',
    'Ph.D.', 'M.D.', 'Inc.', 'Ltd.', 'Corp.', 'Co.', 'St.', 'Ave.', 'Blvd.',
    'No.', 'Dept.', 'Est.', 'Gov.', 'etc.', 'i.e.', 'e.g.', 'a.m.', 'p.m.',
    'v.s.', 'vs.', 'oz.', 'et al.', 'e.v.'
]

def strip_html_tags(text: str) -> str:
    """Remove HTML tags (simplified - PHP does this with wp_strip_all_tags)."""
    return re.sub(r'<[^>]+>', '', text)

def generate_event_summary(description: str, max_chars: int = 280) -> str:
    """
    Generate a summary from event description.
    Mirrors the PHP generate_event_summary() function.
    """
    if not description or not description.strip():
        return ''

    # Strip HTML tags (simplified)
    text = strip_html_tags(description)

    # Remove common boilerplate phrases
    boilerplate_patterns = [
        (r'\s*click\s+here\s*', ' ', re.IGNORECASE),
        (r'\s*learn\s+more\s*', ' ', re.IGNORECASE),
        (r'\s*for\s+more\s+information.*?(?=\.|$)', ' ', re.IGNORECASE),
        (r'https?://[^\s.]+(?:\.\S+)?', '', 0),  # URLs (preserve some trailing dots)
        (r'\b[\d\(\)\s-]{10,}\b', ' ', 0),  # Phone numbers
        (r'\s*RSVP\s+(?:at|to).*?(?=\.|$)', ' ', re.IGNORECASE),  # RSVP instructions
        (r'\s+or\s+call\s*', ' ', re.IGNORECASE),  # "or call" instructions
        (r'\.com(?![a-z])', '', 0),  # Orphaned .com fragments
    ]

    for pattern, replacement, flags in boilerplate_patterns:
        if flags:
            text = re.sub(pattern, replacement, text, flags=flags)
        else:
            text = re.sub(pattern, replacement, text)

    # Remove multiple spaces and clean up orphaned punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove orphaned punctuation at end
    text = re.sub(r'[\s.!?]+$', '', text).strip()
    
    if not text:
        return ''

    # If already short enough, return as-is
    if len(text) <= max_chars:
        return text

    # Extract 1-3 sentences without truncating mid-word
    summary = truncate_at_sentence_boundary(text, max_chars)

    return summary.strip()


def truncate_at_sentence_boundary(text: str, max_chars: int) -> str:
    """
    Truncate text at sentence boundary.
    Tries to fit as many complete sentences as possible within max_chars.
    """
    if len(text) <= max_chars:
        return text

    # Split at sentence boundaries (., !, ?) using a simpler approach
    # Look for a sentence-ending punctuation followed by whitespace and a capital letter
    # This avoids the variable-width lookbehind issue
    pattern = r'[.!?]+\s+(?=[A-Z])'
    sentences = re.split(pattern, text[:max_chars * 2])

    summary = ''
    sentence_count = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        test_summary = (summary + ' ' + sentence).strip() if summary else sentence

        # Stop if we've hit 3 sentences or exceeded max length
        if sentence_count >= 2 or len(test_summary) > max_chars:
            break

        summary = test_summary
        sentence_count += 1

    # Add period if missing
    if summary and summary[-1] not in '.!?':
        summary += '.'

    # Fallback: if no sentences found, truncate at word boundary
    if not summary:
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            summary = truncated[:last_space] + '...'
        else:
            summary = truncated + '...'

    return summary.strip()


# ============================================================================
# TEST CASES
# ============================================================================

TEST_CASES: List[Tuple[str, str, str]] = [
    # (input_description, expected_summary_snippet, test_name)
    (
        """
        <p>Join us for the Annual Community Health Fair! This is a FREE event open to all residents.
        We'll have health screenings, fitness activities, and nutrition counseling. Click here to learn more!
        For more information, visit https://example.com/health-fair or call (850) 555-1234.</p>
        """,
        "Join us for the Annual Community Health Fair! This is a FREE event open to all residents.",
        "Removes boilerplate and URLs"
    ),
    (
        """The U.S. Army Corps of Engineers will present a seminar on environmental management.
        Dr. Smith from the Army will discuss best practices. This is part of the Dr. initiative program.
        Lunch will be provided. Come join us!""",
        "The U.S. Army Corps of Engineers will present a seminar",
        "Handles U.S. abbreviation correctly"
    ),
    (
        """Perdido Key Chamber of Commerce presents: Networking Night. Connect with local business owners and expand your network.
        Light refreshments will be served. RSVP at perdidochamber.com.""",
        "Perdido Key Chamber of Commerce presents: Networking Night.",
        "Preserves essential details, removes URLs"
    ),
    (
        """Pensacola State College Charter Academy Information Session.
        Learn more about an incredible educational opportunity! Join us at one of our information sessions to discover
        how students in grades 9-12 can earn a high school diploma AND college credits simultaneously for FREE!
        Through our dual enrollment program, students pay no cost for tuition, books, or technology including a free laptop!
        Only 75 seats available per grade level.""",
        "Pensacola State College Charter Academy Information Session.",
        "Long description - should extract first 1-2 sentences"
    ),
    (
        """
        <h2>Summer Music Festival</h2>
        <p>Celebrate music with local and regional artists performing across multiple stages.</p>
        <p>Gates open at noon. Free admission for children under 12.</p>
        """,
        "Celebrate music with local and regional artists",
        "Strips HTML tags"
    ),
    (
        """""",  # Empty
        "",
        "Handles empty description"
    ),
    (
        "   \n\n   ",  # Only whitespace
        "",
        "Handles whitespace-only description"
    ),
]


# ============================================================================
# TEST RUNNER
# ============================================================================

class bcolors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    HEADER = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def run_tests():
    """Run all test cases and display results."""
    print(f"\n{bcolors.HEADER}{bcolors.BOLD}Event Summary Generator - Test Harness{bcolors.ENDC}\n")

    passed = 0
    failed = 0

    for i, (input_desc, expected_snippet, test_name) in enumerate(TEST_CASES, 1):
        print(f"{bcolors.BOLD}Test {i}: {test_name}{bcolors.ENDC}")

        # Generate summary
        summary = generate_event_summary(input_desc, max_chars=280)

        # Check result
        if not expected_snippet:
            # Test expects empty summary
            if summary == '':
                print(f"  {bcolors.OK}✓ PASS{bcolors.ENDC}: Got empty summary as expected")
                passed += 1
            else:
                print(f"  {bcolors.FAIL}✗ FAIL{bcolors.ENDC}: Expected empty, got: {repr(summary[:50])}")
                failed += 1
        else:
            # Test expects summary containing a specific snippet
            if expected_snippet in summary:
                print(f"  {bcolors.OK}✓ PASS{bcolors.ENDC}")
                print(f"    Input: {input_desc[:80].strip()}...")
                print(f"    Output: {summary}")
                passed += 1
            else:
                print(f"  {bcolors.FAIL}✗ FAIL{bcolors.ENDC}")
                print(f"    Expected snippet: {expected_snippet}")
                print(f"    Got: {summary}")
                failed += 1

        print()

    # Summary
    total = passed + failed
    print(f"{bcolors.BOLD}{'=' * 60}{bcolors.ENDC}")
    print(f"Tests Passed: {bcolors.OK}{passed}/{total}{bcolors.ENDC}")

    if failed > 0:
        print(f"Tests Failed: {bcolors.FAIL}{failed}/{total}{bcolors.ENDC}")
    else:
        print(f"All tests passed! {bcolors.OK}✓{bcolors.ENDC}")

    return failed == 0


# ============================================================================
# REAL-WORLD EXAMPLES
# ============================================================================

REAL_EXAMPLES = [
    {
        'event': 'Military Appreciation Committee Meeting',
        'description': """The Military Appreciation Committee is dedicated to recognizing and supporting 
        our active duty, reserve, and retired military members. We're committed to ensuring they feel 
        appreciated and supported. Join us in making a difference! Volunteers can contact Staff Committee Chair, 
        Madelyn Bell, to learn how to participate. Visit perdidochamber.com/military-appreciation-committee for more info.""",
    },
    {
        'event': 'Pensacola State College Info Session',
        'description': """Pensacola State College Charter Academy Information Session. 
        Learn more about an incredible educational opportunity! Join us at one of our information sessions to discover 
        how students in grades 9-12 can earn a high school diploma AND college credits simultaneously for FREE! 
        Through our dual enrollment program, students pay no cost for tuition, books, or technology including a free laptop! 
        Only 75 seats are available per grade level, so secure your spot before it's too late. 
        Parents and students, come learn how to set yourself up for a successful future!
        Learn more at https://business.perdidochamber.com/events/details/psc-info-session-01-28-2025-38708""",
    },
    {
        'event': 'Networking Night',
        'description': """Perdido Key Chamber of Commerce Networking Night. Connect with local business owners, 
        entrepreneurs, and professionals in our community. This casual networking event is perfect for building relationships 
        and expanding your business network. Light refreshments will be provided. RSVP required. 
        Click here to register: https://business.perdidochamber.com/events/register. For questions, call (850) 555-0123.""",
    },
]


def show_real_examples():
    """Show real-world examples of summaries."""
    print(f"\n{bcolors.HEADER}{bcolors.BOLD}Real-World Examples (Before/After){bcolors.ENDC}\n")

    for i, example in enumerate(REAL_EXAMPLES, 1):
        event_name = example['event']
        description = example['description']
        summary = generate_event_summary(description, max_chars=280)

        print(f"{bcolors.BOLD}Example {i}: {event_name}{bcolors.ENDC}")
        print(f"  Full Description ({len(description)} chars):")
        print(f"    {description[:120]}...")
        print(f"\n  Generated Summary ({len(summary)} chars):")
        print(f"    {summary}")
        print()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Run tests
    all_passed = run_tests()

    # Show real examples
    show_real_examples()

    # Exit with appropriate code
    exit(0 if all_passed else 1)
