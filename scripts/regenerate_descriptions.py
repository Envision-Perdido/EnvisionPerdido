#!/usr/bin/env python3
"""
Regenerate event descriptions using OpenAI GPT with Batch API support.

Features:
- OpenAI Batch API for 50% cost reduction and async processing
- Cache system to avoid re-processing
- Top-N confidence filtering (only enhance high-confidence events)
- Fallback to sync API for immediate results

Usage (standalone):
    python scripts/regenerate_descriptions.py [OPTIONS]
    
Options:
    --batch              Use OpenAI Batch API (async, cheaper)
    --sync               Use sync API (default, immediate results)
    --top-n N            Only enhance top N confidence events (default: 100)
    --min-confidence X   Only enhance events with confidence >= X (default: 0.75)
    --no-cache           Ignore cache, re-enhance all events
    --skip-cache         Don't save results to cache
    --dry-run            Don't call OpenAI API
    --model MODEL        OpenAI model (default: gpt-4o-mini)
    --csv CSV_PATH       Specific CSV file to process

Usage (imported):
    from regenerate_descriptions import enhance_event_descriptions
    enhanced_events = enhance_event_descriptions(
        events,
        dry_run=False,
        use_batch=True,
        top_n=100,
        min_confidence=0.75
    )
"""

import json
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    from openai import OpenAI, APIError
except ImportError:
    print("[ERROR] openai package not installed. Run: pip install openai")
    sys.exit(1)

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from logger import get_logger

logger = get_logger(__name__)

# Cache configuration
CACHE_DIR = Path("data/cache/descriptions")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "enhanced_descriptions.json"


def _load_cache() -> Dict[str, str]:
    """Load cached enhanced descriptions from JSON file."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"Loaded cache with {len(cache)} entries")
            return cache
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return {}
    return {}


def _save_cache(cache: Dict[str, str]) -> None:
    """Save enhanced descriptions to JSON cache file."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(cache)} entries to cache")
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")


def _get_cache_key(event: Dict) -> str:
    """Generate cache key from event description using hash."""
    title = event.get('Title', '')
    description = event.get('Description', '')
    location = event.get('Location', '')

    # Hash the original description to detect if it changed
    combined = f"{title}|{description}|{location}"
    return hashlib.md5(combined.encode()).hexdigest()


def _build_batch_request(event: Dict, request_id: str, model: str = "gpt-4o-mini") -> Dict:
    """Build a single request for the Batch API (JSONL format)."""
    title = event.get('Title', 'Unknown Event')
    original_desc = event.get('Description', 'No description provided')
    location = event.get('Location', 'TBD')
    start_date = event.get('Start Date', 'TBD')

    prompt = f"""You are a professional event marketing copywriter. 
Improve the following event description to be more engaging, informative, and compelling.
Keep it concise (2-3 sentences, max 150 words). Maintain factual accuracy.

Event Details:
- Title: {title}
- Location: {location}
- Start Date: {start_date}
- Original Description: {original_desc}

Provide ONLY the improved description text, no labels or formatting."""

    return {
        "custom_id": request_id,
        "method": "POST",
        "url": "/v1/messages",
        "body": {
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }
    }


def _submit_batch(client: OpenAI, requests: List[Dict]) -> str:
    """Submit batch to OpenAI Batch API and return batch ID."""
    logger.info(f"Submitting batch with {len(requests)} requests to OpenAI...")

    try:
        # OpenAI SDK handles JSONL conversion
        batch_response = client.beta.batch.create(
            requests=requests
        )
        batch_id = batch_response.id
        logger.info(f"Batch submitted successfully. Batch ID: {batch_id}")
        logger.info(f"You can check status with: openai api batch.retrieve -id {batch_id}")
        return batch_id
    except APIError as e:
        logger.error(f"Failed to submit batch: {e}")
        raise


def _poll_batch_status(client: OpenAI, batch_id: str, max_wait: int = 3600, poll_interval: int = 30) -> bool:
    """Poll batch status until complete. Returns True if successful."""
    logger.info(f"Polling batch {batch_id} for completion (max wait: {max_wait}s)...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            batch = client.beta.batch.retrieve(batch_id)
            status = batch.status

            logger.info(f"Batch status: {status}")
            logger.info(f"  Processed: {batch.request_counts.completed}/{batch.request_counts.total}")

            if status == "completed":
                logger.info("Batch completed!")
                return True
            elif status == "failed":
                logger.error("✗ Batch failed")
                if hasattr(batch, 'errors') and batch.errors:
                    for error in batch.errors:
                        logger.error(f"  Error: {error}")
                return False
            elif status == "expired":
                logger.error("✗ Batch expired")
                return False

            logger.debug(f"Batch still processing... waiting {poll_interval}s before next check")
            time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Failed to check batch status: {e}")
            raise

    logger.error(f"Batch did not complete within {max_wait} seconds")
    logger.info(f"Batch ID for manual checking: {batch_id}")
    return False


def _retrieve_batch_results(client: OpenAI, batch_id: str) -> Dict[str, str]:
    """Retrieve results from completed batch. Returns dict of custom_id -> enhanced_description."""
    logger.info(f"Retrieving results from batch {batch_id}...")

    results = {}
    try:
        # Get all results from the batch
        result_lines = client.beta.batch.results(batch_id)

        for line in result_lines:
            if line.result.status == "succeeded":
                custom_id = line.custom_id
                # Extract enhanced description from OpenAI response
                content = line.result.message.content[0].text
                enhanced_desc = content.strip()
                results[custom_id] = enhanced_desc
                logger.debug(f"Result {custom_id}: {enhanced_desc[:80]}...")
            else:
                custom_id = line.custom_id
                logger.warning(f"Request {custom_id} failed: {line.result.error}")

        logger.info(f"Retrieved {len(results)} successful results")
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve batch results: {e}")
        raise


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
        logger.info(f"Enhanced: {title}")
        logger.debug(f"  Original: {original_desc[:80]}...")
        logger.debug(f"  Enhanced: {enhanced[:80]}...")
        return enhanced
    except Exception as e:
        logger.error(f"OpenAI API error for '{title}': {e}")
        return original_desc  # Fall back to original


def enhance_event_descriptions(
    events: List[Dict],
    dry_run: bool = False,
    model: str = "gpt-4o-mini",
    use_batch: bool = False,
    top_n: Optional[int] = 100,
    min_confidence: float = 0.75,
    use_cache: bool = True,
    save_cache: bool = True
) -> List[Dict]:
    """
    Enhance descriptions for events using OpenAI.
    
    Args:
        events: List of event dictionaries
        dry_run: If True, don't call API
        model: OpenAI model to use
        use_batch: Use Batch API (async, cheaper, slower)
        top_n: Only enhance top N confidence events
        min_confidence: Only enhance events with confidence >= this threshold
        use_cache: Load cached enhancements
        save_cache: Save enhancements to cache
    
    Returns:
        List of events with enhanced descriptions
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not set. Skipping description enhancement.")
        return events

    if not events:
        logger.warning("No events to enhance")
        return events

    # Load cache
    cache = _load_cache() if use_cache else {}

    # Filter events by confidence (top-N)
    events_to_enhance = []
    for event in events:
        original_desc = event.get('Description', '')
        if not original_desc or original_desc.strip() == '':
            continue

        confidence = event.get('confidence', 1.0)
        if confidence >= min_confidence:
            events_to_enhance.append(event)

    # Sort by confidence descending, take top N
    events_to_enhance.sort(key=lambda e: e.get('confidence', 0), reverse=True)
    if top_n:
        events_to_enhance = events_to_enhance[:top_n]

    logger.info(f"Will enhance {len(events_to_enhance)}/{len(events)} events (top_n={top_n}, min_confidence={min_confidence})")

    # Check cache and filter out already-enhanced
    cache_hits = 0
    still_to_enhance = []
    for event in events_to_enhance:
        cache_key = _get_cache_key(event)
        if cache_key in cache:
            event['Description'] = cache[cache_key]
            cache_hits += 1
        else:
            still_to_enhance.append(event)

    logger.info(f"Cache hits: {cache_hits}, still need to enhance: {len(still_to_enhance)}")

    # If nothing left to enhance, return events with cached enhancements
    if not still_to_enhance:
        logger.info("All events already in cache!")
        return events

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    if dry_run:
        logger.info("[DRY-RUN] Would enhance descriptions (no API calls)")
        return events

    # Use Batch API or sync
    if use_batch:
        logger.info("Using OpenAI Batch API (async processing)...")

        # Build batch requests
        batch_requests = []
        for i, event in enumerate(still_to_enhance):
            request_id = f"event_{i}_{_get_cache_key(event)}"
            batch_requests.append(_build_batch_request(event, request_id, model))

        # Submit batch
        batch_id = _submit_batch(client, batch_requests)

        # Poll for completion
        if _poll_batch_status(client, batch_id):
            # Retrieve results
            batch_results = _retrieve_batch_results(client, batch_id)

            # Apply results and update cache
            for event in still_to_enhance:
                cache_key = _get_cache_key(event)
                # Try to find result using various ID formats
                for request_id, enhanced_desc in batch_results.items():
                    if cache_key in request_id:
                        event['Description'] = enhanced_desc
                        cache[cache_key] = enhanced_desc
                        break
        else:
            logger.error("Batch processing failed, skipping enhancement")
            return events
    else:
        # Sync mode (immediate results)
        logger.info(f"Using OpenAI sync API for {len(still_to_enhance)} events...")
        for i, event in enumerate(still_to_enhance, 1):
            title = event.get('Title', f'Event {i}')
            logger.info(f"[{i}/{len(still_to_enhance)}] {title}")

            enhanced_desc = generate_single_description(client, event, model, dry_run=False)
            event['Description'] = enhanced_desc

            # Update cache
            cache_key = _get_cache_key(event)
            cache[cache_key] = enhanced_desc

    # Save cache
    if save_cache:
        _save_cache(cache)

    logger.info(f"Enhancement complete (cache entries: {len(cache)})")
    return events


def main():
    """Standalone CLI usage"""
    import argparse
    import csv

    parser = argparse.ArgumentParser(description="Regenerate event descriptions using OpenAI")
    parser.add_argument('--batch', action='store_true', help="Use OpenAI Batch API (async, cheaper)")
    parser.add_argument('--sync', action='store_true', help="Use sync API (default, immediate results)")
    parser.add_argument('--top-n', type=int, default=100, help="Only enhance top N confidence events")
    parser.add_argument('--min-confidence', type=float, default=0.75, help="Only enhance events with confidence >= X")
    parser.add_argument('--no-cache', action='store_true', help="Ignore cache, re-enhance all events")
    parser.add_argument('--skip-cache', action='store_true', help="Don't save results to cache")
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
    use_batch = args.batch or not args.sync  # Default to batch if neither specified
    enhanced_events = enhance_event_descriptions(
        events,
        dry_run=args.dry_run,
        model=args.model,
        use_batch=use_batch,
        top_n=args.top_n,
        min_confidence=args.min_confidence,
        use_cache=not args.no_cache,
        save_cache=not args.skip_cache
    )

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
        logger.info(f"Wrote enhanced CSV: {output_path}")
        print(output_path)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
