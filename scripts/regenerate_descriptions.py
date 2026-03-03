#!/usr/bin/env python3
"""
Regenerate event descriptions using OpenAI GPT.
Can be used standalone or imported into the pipeline.

Usage (standalone):
    python scripts/regenerate_descriptions.py [--dry-run] [--model gpt-4o-mini]

Usage (imported):
    from regenerate_descriptions import enhance_event_descriptions
    enhanced_events = enhance_event_descriptions(events, dry_run=False)
"""

import os
import sys
from typing import List, Dict, Optional
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai package not installed. Run: pip install openai")
    sys.exit(1)

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from logger import get_logger

logger = get_logger(__name__)


def generate_single_description(
    client: OpenAI,
    event: Dict,
    model: str = "gpt-4o-mini",
    dry_run: bool = False
) -> str:
    """
    Generate improved description for a single event.
    
    Args:
        client: OpenAI client
        event: Event dict with keys: Title, Description, Start Date, Location
        model: Model name
        dry_run: If True, return placeholder
    
    Returns:
        Enhanced description (or original if dry_run or error)
    """
    if dry_run:
        logger.debug(f"[DRY-RUN] Would enhance: {event.get('Title', 'Unknown')}")
        return event.get('Description', 'No description')
    
    title = event.get('Title', 'Unknown Event')
    original_desc = event.get('Description', 'No description provided')
    location = event.get('Location', 'TBD')
    start_date = event.get('Start Date', 'TBD')
    
    # Skip if no description
    if not original_desc or original_desc.strip() == '':
        logger.debug(f"Skipping (no description): {title}")
        return original_desc
    
    prompt = f"""You are a professional event marketing copywriter. 
Improve the following event description to be more engaging, informative, and compelling.
Keep it concise (2-3 sentences, max 150 words). Maintain factual accuracy.

Event Details:
- Title: {title}
- Location: {location}
- Start Date: {start_date}
- Original Description: {original_desc}

Provide ONLY the improved description text, no labels or formatting."""
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        enhanced = response.content[0].text.strip()
        logger.info(f"✓ Enhanced: {title}")
        logger.debug(f"  Original: {original_desc[:80]}...")
        logger.debug(f"  Enhanced: {enhanced[:80]}...")
        return enhanced
    except Exception as e:
        logger.error(f"OpenAI API error for '{title}': {e}")
        return original_desc  # Fall back to original


def enhance_event_descriptions(
    events: List[Dict],
    dry_run: bool = False,
    model: str = "gpt-4o-mini"
) -> List[Dict]:
    """
    Enhance descriptions for a list of events using OpenAI.
    
    Args:
        events: List of event dictionaries
        dry_run: If True, don't call API (returns events unchanged)
        model: OpenAI model to use
    
    Returns:
        List of events with enhanced descriptions
    
    Raises:
        ValueError: If OPENAI_API_KEY not set
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not set. Skipping description enhancement.")
        return events
    
    if not events:
        logger.warning("No events to enhance")
        return events
    
    logger.info(f"Enhancing {len(events)} event descriptions (dry_run={dry_run}, model={model})...")
    
    client = OpenAI(api_key=api_key)
    enhanced_count = 0
    
    for i, event in enumerate(events, 1):
        title = event.get('Title', f'Event {i}')
        logger.info(f"[{i}/{len(events)}] {title}")
        
        enhanced_desc = generate_single_description(client, event, model, dry_run)
        event['Description'] = enhanced_desc
        enhanced_count += 1
    
    logger.info(f"Completed enhancement of {enhanced_count} events")
    return events


def main():
    """Standalone CLI usage"""
    import argparse
    import csv
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Regenerate event descriptions using OpenAI")
    parser.add_argument('--dry-run', action='store_true', help="Don't call OpenAI API")
    parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model')
    parser.add_argument('--csv', type=Path, help='Specific CSV file to process')
    args = parser.parse_args()
    
    # Find CSV
    if args.csv:
        csv_path = args.csv
    else:
        pipeline_dir = Path("output/pipeline")
        if not pipeline_dir.exists():
            logger.error(f"Pipeline directory not found: {pipeline_dir}")
            sys.exit(1)
        
        csv_files = sorted(pipeline_dir.glob("calendar_upload_*.csv"), key=os.path.getmtime, reverse=True)
        if not csv_files:
            logger.error(f"No calendar_upload_*.csv files found in {pipeline_dir}")
            sys.exit(1)
        
        csv_path = csv_files[0]
    
    logger.info(f"Processing: {csv_path}")
    
    # Read CSV
    events = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            events = list(reader)
        logger.info(f"Loaded {len(events)} events")
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        sys.exit(1)
    
    # Enhance
    enhanced_events = enhance_event_descriptions(events, dry_run=args.dry_run, model=args.model)
    
    # Write output
    output_dir = Path("output/pipeline")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"calendar_upload_enhanced_{timestamp}.csv"
    
    try:
        fieldnames = enhanced_events[0].keys()
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(enhanced_events)
        logger.info(f"✓ Wrote enhanced CSV: {output_path}")
        print(output_path)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
