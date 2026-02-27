"""
WordPress EventON Calendar Uploader

This script uploads classified community events to the WordPress calendar
using the WordPress REST API.

EventON uses a custom post type called 'ajde_events'.
"""

import hashlib
import json
import mimetypes
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from env_loader import load_env

load_env()

# WordPress Configuration
WORDPRESS_CONFIG = {
    "site_url": os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org"),
    "username": os.getenv("WP_USERNAME", ""),  # WordPress admin username
    "app_password": os.getenv("WP_APP_PASSWORD", ""),  # WordPress Application Password
}


def _create_session_with_retries(
    retries: int = 5,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 503),
) -> requests.Session:
    """Create a requests session with exponential backoff retry strategy.

    Args:
        retries: Maximum number of retries (default: 5)
        backoff_factor: Exponential backoff factor (default: 0.5)
        status_forcelist: HTTP status codes to retry on (default: 429, 503)

    Returns:
        Configured requests.Session with retry strategy mounted.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class WordPressEventUploader:
    """Handle uploading events to WordPress EventON calendar."""

    def __init__(self, site_url, username, app_password, max_workers=5):
        self.site_url = site_url.rstrip("/")
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(username, app_password)
        self.session = _create_session_with_retries()
        self.session.auth = self.auth
        self.max_workers = max_workers
        self._hash_cache_path = Path(__file__).parent.parent / "data" / "cache" / "media_hash_cache.json"

    def test_connection(self) -> bool:
        """Test WordPress API connection and authentication.

        Returns:
            True if connection successful, False otherwise.
        """
        log("Testing WordPress API connection...")

        try:
            response = self.session.get(f"{self.api_base}/users/me", auth=self.auth)

            if response.status_code == 200:
                user_data = response.json()
                log(f"OK: Connected as: {user_data.get('name', 'Unknown')}")
                return True
            elif response.status_code == 401:
                log("ERROR: Authentication failed! Check username and app password.")
                return False
            else:
                log(f"ERROR: API error: {response.status_code}")
                return False

        except requests.RequestException as e:
            log(f"ERROR: Connection error: {e}")
            return False

    def get_event_locations(self) -> dict:
        """Get existing event locations from WordPress.

        Returns:
            Dictionary mapping location names to location IDs.
        """
        try:
            response = self.session.get(f"{self.api_base}/event_location", auth=self.auth)
            if response.status_code == 200:
                locations = response.json()
                return {loc["name"]: loc["id"] for loc in locations}
            return {}
        except requests.RequestException as e:
            log(f"Warning: Could not fetch locations: {e}")
            return {}

    def get_event_by_uid(self, uid: str) -> int | None:
        """Find an existing event by its UID meta field.

        Args:
            uid: The event UID to search for (from ICS file).

        Returns:
            Event ID if found, None otherwise.
        """
        if not uid:
            return None

        try:
            response = self.session.get(
                f"{self.api_base}/ajde_events",
                auth=self.auth,
                params={
                    "meta_key": "_event_uid",
                    "meta_value": uid,
                    "per_page": 1,
                },
            )

            if response.status_code == 200:
                events = response.json()
                if events and len(events) > 0:
                    return events[0]["id"]

            return None
        except requests.RequestException as e:
            log(f"Warning: Could not query for existing event UID {uid}: {e}")
            return None

    def create_or_get_location(self, location_name: str) -> int | None:
        """Create a new location or get existing location ID.

        Args:
            location_name: Name of the location.

        Returns:
            Location ID, or None if not found/created.
        """
        if not location_name or pd.isna(location_name):
            return None

        # Check existing locations
        locations = self.get_event_locations()
        if location_name in locations:
            return locations[location_name]

        # Create new location
        try:
            response = self.session.post(
                f"{self.api_base}/event_location", auth=self.auth, json={"name": location_name}
            )
            if response.status_code == 201:
                return response.json()["id"]
        except requests.RequestException as e:
            log(f"Warning: Could not create location '{location_name}': {e}")

        return None

    def parse_event_metadata(self, event_row: pd.Series) -> dict:
        """Parse event data into EventON metadata format.

        Args:
            event_row: Pandas Series with event data.

        Returns:
            Dictionary of EventON metadata fields.
        """
        metadata = {}

        # Event start and end times
        # NOTE: EventON ignores hour/min/ampm fields and uses only evcal_srow epoch
        # EventON interprets the epoch as local time (not UTC), so we store the "local epoch"
        # i.e., the timestamp of the local time treating it as if it were UTC
        if pd.notna(event_row.get("start")):
            start_dt = pd.to_datetime(event_row["start"])
            start_local = start_dt
            try:
                from zoneinfo import ZoneInfo

                local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
                # Treat naive as local time
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=local_tz)
                # WORKAROUND: Store "local epoch" - epoch of local time
                # treating as UTC
                local_naive = start_dt.replace(tzinfo=None)
                epoch = int(local_naive.timestamp())
                metadata["evcal_srow"] = str(epoch)
            except Exception:  # pylint: disable=broad-except
                # Fallback: use naive timestamp
                epoch = int(pd.Timestamp(start_dt).timestamp())
                metadata["evcal_srow"] = str(epoch)
            # Use local time for display fields (EventON ignores these)
            metadata["evcal_start_date"] = start_local.strftime("%Y-%m-%d")
            metadata["evcal_start_time_hour"] = start_local.strftime("%I")
            metadata["evcal_start_time_min"] = start_local.strftime("%M")
            metadata["evcal_start_time_ampm"] = start_local.strftime("%p").lower()

        if pd.notna(event_row.get("end")):
            end_dt = pd.to_datetime(event_row["end"])
            end_local = end_dt
            try:
                from zoneinfo import ZoneInfo

                local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=local_tz)
                # WORKAROUND: Store "local epoch"
                local_naive = end_dt.replace(tzinfo=None)
                epoch = int(local_naive.timestamp())
                metadata["evcal_erow"] = str(epoch)
            except Exception:  # pylint: disable=broad-except
                epoch = int(pd.Timestamp(end_dt).timestamp())
                metadata["evcal_erow"] = str(epoch)
            # Use local time for display fields
            metadata["evcal_end_date"] = end_local.strftime("%Y-%m-%d")
            metadata["evcal_end_time_hour"] = end_local.strftime("%I")
            metadata["evcal_end_time_min"] = end_local.strftime("%M")
            metadata["evcal_end_time_ampm"] = end_local.strftime("%p").lower()

        # Store UID for deduplication (prevents duplicate event uploads)
        if pd.notna(event_row.get("uid")):
            metadata["_event_uid"] = str(event_row["uid"])

        # Location - use normalized location if available
        location_text = event_row.get("normalized_location") or event_row.get("location")
        if pd.notna(location_text):
            location_id = self.create_or_get_location(str(location_text))
            if location_id:
                metadata["event_location"] = location_id

        # Store venue_id if available (for future reference)
        if pd.notna(event_row.get("venue_id")):
            metadata["_venue_id"] = str(event_row["venue_id"])

        # URL
        if pd.notna(event_row.get("url")):
            metadata["evcal_lmlink"] = str(event_row["url"])

        # Cost/Price information
        if pd.notna(event_row.get("cost_text")):
            metadata["_event_cost"] = str(event_row["cost_text"])

        # Event type (free/paid)
        if pd.notna(event_row.get("event_type")):
            metadata["_event_type"] = str(event_row["event_type"])
        if pd.notna(event_row.get("paid_status")):
            metadata["_paid_status"] = str(event_row["paid_status"])
        if pd.notna(event_row.get("is_free")):
            metadata["_is_free"] = "yes" if event_row["is_free"] else "no"

        # EventON specific settings for better display
        metadata["_evcal_exlink_option"] = "1"  # Open link in new window
        metadata["_evcal_exlink_target"] = "yes"  # Enable external link
        metadata["evo_hide_endtime"] = "no"  # Show end time
        metadata["evo_year_long"] = "no"  # Not a year-long event
        metadata["_evo_featured_img"] = "no"  # Don't show featured image in event details popup

        return metadata

    # ------------------------------------------------------------------
    # Image deduplication helpers
    # ------------------------------------------------------------------

    def _get_image_hash(self, image_data: bytes) -> str:
        """Compute SHA-256 hex digest of image bytes.

        Args:
            image_data: Raw bytes of the image.

        Returns:
            Lowercase hex SHA-256 string.
        """
        return hashlib.sha256(image_data).hexdigest()

    def _load_hash_cache(self) -> dict:
        """Load the local hash → WP media ID cache from disk.

        Returns:
            Dict mapping SHA-256 hex string to WordPress media ID (int).
        """
        if self._hash_cache_path.exists():
            try:
                with open(self._hash_cache_path) as f:
                    return json.load(f)
            except Exception:  # pylint: disable=broad-except
                return {}
        return {}

    def _save_hash_cache(self, cache: dict) -> None:
        """Persist the hash → media ID cache to disk.

        Args:
            cache: Dict mapping SHA-256 hex strings to WordPress media IDs.
        """
        try:
            self._hash_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._hash_cache_path, "w") as f:
                json.dump(cache, f, indent=2)
        except OSError as e:
            log(f"   Warning: Could not save media hash cache: {e}")

    def find_existing_media_by_hash(self, image_hash: str) -> int | None:
        """Look up an existing WP media attachment by SHA-256 hash.

        Checks the local cache first, then searches the WP REST API for
        the structured token ``ep_hash=SHA256:<hash>`` embedded in the
        attachment's description field.

        Args:
            image_hash: SHA-256 hex digest of the image bytes.

        Returns:
            WordPress media ID if a match is found, None otherwise.
        """
        # Layer 1: local cache
        cache = self._load_hash_cache()
        if image_hash in cache:
            return int(cache[image_hash])

        # Layer 2: WP REST API full-text search for the hash token
        hash_token = f"ep_hash=SHA256:{image_hash}"
        try:
            response = self.session.get(
                f"{self.api_base}/media",
                auth=self.auth,
                params={"search": hash_token, "per_page": 1},
            )
            if response.status_code == 200:
                results = response.json()
                if isinstance(results, list) and results:
                    media_id = int(results[0]["id"])
                    cache[image_hash] = media_id
                    self._save_hash_cache(cache)
                    return media_id
        except requests.RequestException as e:
            log(f"   Warning: Could not search media by hash: {e}")

        return None

    def find_existing_media_by_filename(self, filename: str) -> int | None:
        """Look up an existing WP media attachment by filename (fallback).

        Searches the WP REST API using the base filename (without extension)
        and verifies the result by comparing the filename in the source URL
        or attachment slug.

        Args:
            filename: The image filename (e.g. ``event_image.jpg``).

        Returns:
            WordPress media ID if a match is found, None otherwise.
        """
        try:
            slug = filename.rsplit(".", 1)[0]
            response = self.session.get(
                f"{self.api_base}/media",
                auth=self.auth,
                params={"search": slug, "per_page": 10},
            )
            if response.status_code == 200:
                results = response.json()
                if isinstance(results, list):
                    for item in results:
                        source_url = item.get("source_url", "")
                        item_slug = item.get("slug", "")
                        if filename in source_url or slug == item_slug:
                            return int(item["id"])
        except requests.RequestException as e:
            log(f"   Warning: Could not search media by filename: {e}")

        return None

    def upload_image(self, image_path_or_url: str, title: str | None = None) -> int | None:
        """Upload an image to WordPress media library, reusing existing media when possible.

        Before uploading, checks for a matching existing attachment using two layers:
        1. SHA-256 hash (exact content match) via local cache and WP API search.
        2. Filename/slug fallback via WP REST API search.

        If a match is found the existing media ID is returned immediately (no upload).
        On a fresh upload the hash token ``ep_hash=SHA256:<hash>`` is stored in the
        attachment description so future runs can find it, and the local cache is updated.

        Args:
            image_path_or_url: Local file path or URL to image.
            title: Optional title for the image.

        Returns:
            Media ID if successful, None otherwise.
        """
        try:
            # Determine if it's a URL or local file
            is_url = image_path_or_url.startswith("http://") or image_path_or_url.startswith(
                "https://"
            )
            if is_url:
                # Download image from URL
                response = requests.get(image_path_or_url, timeout=30)
                response.raise_for_status()
                image_data = response.content
                # Extract filename from URL
                filename = image_path_or_url.split("/")[-1].split("?")[0]
                if not filename or "." not in filename:
                    filename = "event_image.jpg"
            else:
                # Read local file
                with open(image_path_or_url, "rb") as f:
                    image_data = f.read()
                filename = os.path.basename(image_path_or_url)

            # --- Deduplication: prefer reuse over upload ---

            # Layer A: strong match via SHA-256 hash
            image_hash = self._get_image_hash(image_data)
            existing_id = self.find_existing_media_by_hash(image_hash)
            if existing_id:
                log(f"   Reusing existing media ID {existing_id} (hash match: {filename})")
                return existing_id

            # Layer B: fallback match via filename/slug
            existing_id = self.find_existing_media_by_filename(filename)
            if existing_id:
                log(f"   Reusing existing media ID {existing_id} (filename match: {filename})")
                # Populate local cache so future runs skip the WP query
                cache = self._load_hash_cache()
                cache[image_hash] = existing_id
                self._save_hash_cache(cache)
                return existing_id

            # No existing match — upload to WordPress media library
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = "image/jpeg"  # Default fallback

            headers = {
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": mime_type,
            }

            response = self.session.post(
                f"{self.api_base}/media", auth=self.auth, headers=headers, data=image_data
            )

            if response.status_code == 201:
                media_data = response.json()
                media_id = media_data["id"]

                # Embed hash token in description so future runs can match without re-uploading.
                # The token format is: ep_hash=SHA256:<hex>
                hash_token = f"ep_hash=SHA256:{image_hash}"
                update_payload = {"description": hash_token}
                if title:
                    update_payload["title"] = title
                self.session.post(
                    f"{self.api_base}/media/{media_id}", auth=self.auth, json=update_payload
                )

                # Persist to local cache
                cache = self._load_hash_cache()
                cache[image_hash] = media_id
                self._save_hash_cache(cache)

                log(f"   Uploaded image: {filename} (Media ID: {media_id})")
                return media_id
            else:
                log(f"   Warning: Failed to upload image: {response.status_code}")
                return None

        except OSError as e:  # File access errors
            log(f"   Warning: Error uploading image: {e}")
            return None
        except requests.RequestException as e:  # Network errors
            log(f"   Warning: Error uploading image: {e}")
            return None

    def create_event(self, event_row: pd.Series, image_column: str = "image_url") -> int | None:
        """Create a single event in WordPress.

        Args:
            event_row: Pandas Series with event data.
            image_column: Name of column containing image URL/path.

        Returns:
            Event ID if created successfully, None otherwise.
        """
        try:
            # Check for duplicate by UID first (idempotency check)
            uid = event_row.get("uid")
            if uid:
                existing_id = self.get_event_by_uid(uid)
                if existing_id:
                    log(
                        f"SKIPPED: Event {event_row.get('title', 'Unknown')} "
                        f"already exists in WordPress (UID: {uid}, ID: {existing_id})"
                    )
                    return None  # Don't create; already exists

            # Prepare event data
            title = event_row.get("title", "Untitled Event")
            description = event_row.get("description", "")

            # Parse metadata
            metadata = self.parse_event_metadata(event_row)

            # Always store UID in metadata for future dedup checks
            if uid:
                metadata["_event_uid"] = str(uid)
            # Handle tags - EventON supports event_type taxonomy
            tags = []
            if pd.notna(event_row.get("tags")):
                # Tags might be stored as JSON string or list
                tag_data = event_row["tags"]
                if isinstance(tag_data, str):
                    try:
                        import json as json_lib

                        tags = json_lib.loads(tag_data)
                    except ValueError:  # JSON parse error
                        # Try splitting as comma-separated
                        tags = [t.strip() for t in tag_data.split(",") if t.strip()]
                elif isinstance(tag_data, list):
                    tags = tag_data

            # Handle featured image for calendar thumbnail display
            featured_media_id = None
            image_url = None
            if image_column in event_row and pd.notna(event_row[image_column]):
                image_source = event_row[image_column]
                featured_media_id = self.upload_image(image_source, title=title)

                if featured_media_id:
                    # Store image ID in custom meta field instead of
                    # featured_media. This prevents EventON from showing it
                    # in the popup.
                    metadata["_event_image_id"] = str(featured_media_id)

                    # Try to get the image URL for calendar display
                    try:
                        response = self.session.get(
                            f"{self.api_base}/media/{featured_media_id}", auth=self.auth
                        )
                        if response.status_code == 200:
                            image_url = response.json().get("source_url", "")
                            metadata["_event_image_url"] = image_url
                    except requests.RequestException:  # pylint: disable=broad-except
                        pass

            # Create post data with featured image if available
            post_data = {
                "title": title,
                "content": (description if pd.notna(description) else ""),
                "status": "draft",
                "type": "ajde_events",
                "meta": metadata,
            }

            # Set featured image for EventON to display
            if featured_media_id:
                post_data["featured_media"] = featured_media_id

            # Add location and tags to post data
            if "event_location" in metadata:
                post_data["event_location"] = metadata.pop("event_location")

            # Add tags if available (EventON uses event_type taxonomy)
            if tags:
                # Convert tag slugs to display names for EventON
                tag_names = [tag.replace("_", " ").title() for tag in tags]
                # Store tag IDs if available, or create them
                tag_ids = self._get_or_create_event_tags(tags)
                if tag_ids:
                    post_data["event_type"] = tag_ids
                # Also store in meta for reference
                metadata["_event_tags"] = ",".join(tags)
                metadata["_event_tags_display"] = ",".join(tag_names)

            # Send to WordPress
            response = self.session.post(
                f"{self.api_base}/ajde_events", auth=self.auth, json=post_data
            )

            if response.status_code == 201:
                event_data = response.json()
                event_id = event_data["id"]
                log(f"OK: Created event: {title} (ID: {event_id})")

                # Try to set tags via taxonomy (if EventON supports it)
                if tags:
                    self._set_event_tags(event_id, tags)

                return event_id
            else:
                log(f"ERROR: Failed to create event '{title}': {response.status_code}")
                log(f"   Response: {response.text[:200]}")
                return None

        except Exception as e:  # pylint: disable=broad-except
            event_title = event_row.get("title", "Unknown")
            log(f"ERROR: Error creating event '{event_title}': {e}")
            return None

    def _get_or_create_event_tags(self, tag_slugs: list[str]) -> list[int]:
        """Get or create event tags and return their IDs.

        Args:
            tag_slugs: List of tag slug strings.

        Returns:
            List of tag IDs that can be assigned to event_type taxonomy.
        """
        tag_ids = []
        try:
            for tag_slug in tag_slugs:
                # Convert slug to proper name
                tag_name = tag_slug.replace("_", " ").title()

                # Try to fetch existing tag
                response = self.session.get(
                    f"{self.api_base}/event_type", params={"search": tag_name}, auth=self.auth
                )

                tag_id = None
                if response.status_code == 200:
                    terms = response.json()
                    if terms:
                        tag_id = terms[0]["id"]

                # Create tag if not found
                if not tag_id:
                    create_response = self.session.post(
                        f"{self.api_base}/event_type",
                        auth=self.auth,
                        json={"name": tag_name, "slug": tag_slug},
                    )
                    if create_response.status_code == 201:
                        tag_id = create_response.json()["id"]

                if tag_id:
                    tag_ids.append(tag_id)
        except requests.RequestException as e:  # pylint: disable=broad-except
            log(f"   Warning: Could not fetch/create tags: {e}")

        return tag_ids

    def _set_event_tags(self, event_id: int, tags: list[str]) -> None:
        """Attempt to set event tags via taxonomy after creation.

        This is a fallback if tags weren't set during event creation.

        Args:
            event_id: WordPress event post ID.
            tags: List of tag slugs to assign.
        """
        try:
            tag_ids = self._get_or_create_event_tags(tags)
            if tag_ids:
                self.session.post(
                    f"{self.api_base}/ajde_events/{event_id}",
                    auth=self.auth,
                    json={"event_type": tag_ids},
                )
        except requests.RequestException as e:  # pylint: disable=broad-except
            log(f"   Note: Could not set tags via taxonomy: {e}")

    def _create_events_parallel(self, events_list: list[pd.Series], max_workers: int) -> list[int]:
        """Create multiple events in parallel using thread pool.

        Args:
            events_list: List of pandas Series (rows) with event data.
            max_workers: Maximum number of worker threads.

        Returns:
            List of created event IDs.
        """
        created_ids = []
        total = len(events_list)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all event creation tasks
            future_to_event = {
                executor.submit(self.create_event, event): event for event in events_list
            }

            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_event), 1):
                event = future_to_event[future]
                try:
                    event_id = future.result()
                    if event_id:
                        created_ids.append(event_id)
                    # Progress indicator
                    if i % 10 == 0 or i == total:
                        log(f"  Progress: {i}/{total} events processed")
                except Exception as e:  # pylint: disable=broad-except
                    event_title = event.get("title", "Unknown")
                    log(f"ERROR: Failed to create event '{event_title}': {e}")

        return created_ids

    def upload_events_from_csv(
        self, csv_path: Path, dry_run: bool = True, max_workers: int | None = None
    ) -> list[int]:
        """Upload events from CSV file in parallel.

        Args:
            csv_path: Path to CSV file with events.
            dry_run: If True, show events but don't create them.
            max_workers: Maximum number of worker threads.

        Returns:
            List of created event IDs.
        """
        log(f"Loading events from {csv_path}...")

        df = pd.read_csv(csv_path)
        log(f"Found {len(df)} events to upload")

        if dry_run:
            log("DRY RUN MODE - No events will be created")
            log("Review the following events:")
            for idx, row in df.iterrows():
                log(f"  - {row.get('title', 'Untitled')} ({row.get('start', 'No date')})")
            log("\nTo actually upload, run with dry_run=False")
            return []

        # Convert DataFrame rows to list for parallel processing
        events_list = [row for idx, row in df.iterrows()]
        workers = max_workers or self.max_workers

        # Upload events in parallel
        created_ids = self._create_events_parallel(events_list, workers)

        log(f"Upload complete: {len(created_ids)}/{len(df)} events created")
        return created_ids

    def publish_events(self, event_ids: list[int], max_workers: int | None = None) -> int:
        """Publish events that were created as drafts in parallel.

        Args:
            event_ids: List of event IDs to publish.
            max_workers: Maximum number of worker threads.

        Returns:
            Number of events successfully published.
        """
        log(f"Publishing {len(event_ids)} events...")

        workers = max_workers or self.max_workers
        published = self._publish_events_parallel(event_ids, workers)

        log(f"Published {published}/{len(event_ids)} events")
        return published

    def _publish_single_event(self, event_id: int) -> bool:
        """Publish a single event.

        Args:
            event_id: WordPress event post ID.

        Returns:
            True if published successfully, False otherwise.
        """
        try:
            response = self.session.post(
                f"{self.api_base}/ajde_events/{event_id}",
                auth=self.auth,
                json={"status": "publish"},
            )
            return response.status_code == 200
        except requests.RequestException as e:  # pylint: disable=broad-except
            log(f"Error publishing event {event_id}: {e}")
            return False

    def _publish_events_parallel(self, event_ids: list[int], max_workers: int) -> int:
        """Publish multiple events in parallel using thread pool.

        Args:
            event_ids: List of event IDs to publish.
            max_workers: Maximum number of worker threads.

        Returns:
            Number of events successfully published.
        """
        published_count = 0
        total = len(event_ids)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all publish tasks
            future_to_event_id = {
                executor.submit(self._publish_single_event, event_id): event_id
                for event_id in event_ids
            }

            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_event_id), 1):
                event_id = future_to_event_id[future]
                try:
                    if future.result():
                        published_count += 1
                    # Progress indicator
                    if i % 10 == 0 or i == total:
                        log(f"  Progress: {i}/{total} events published")
                except Exception as e:  # pylint: disable=broad-except
                    log(f"ERROR: Failed to publish event {event_id}: {e}")

        return published_count


def setup_wordpress_credentials() -> dict[str, str]:
    """Interactive setup for WordPress credentials.

    Returns:
        Dictionary with site_url, username, and app_password.
    """
    print("\n" + "=" * 80)
    print("WORDPRESS CREDENTIALS SETUP")
    print("=" * 80)
    print("\nYou need WordPress Application Password for authentication.")
    print("To create one:")
    print("1. Log into WordPress admin")
    print("2. Go to Users → Profile")
    print("3. Scroll to 'Application Passwords'")
    print("4. Enter a name (e.g., 'Event Uploader') and click 'Add New'")
    print("5. Copy the generated password (it will look like: 'xxxx xxxx xxxx xxxx xxxx xxxx')")
    print("\n" + "=" * 80)

    site_url = input(
        "\nWordPress Site URL (default: https://sandbox.envisionperdido.org): "
    ).strip()
    if not site_url:
        site_url = "https://sandbox.envisionperdido.org"

    username = input("WordPress Username: ").strip()
    app_password = input("Application Password: ").strip()

    # Save to environment variables (for this session)
    os.environ["WP_SITE_URL"] = site_url
    os.environ["WP_USERNAME"] = username
    os.environ["WP_APP_PASSWORD"] = app_password

    print("\nCredentials set for this session.")
    print("To make permanent, add to your environment variables or .env file:")
    print(f"  WP_SITE_URL={site_url}")
    print(f"  WP_USERNAME={username}")
    print("  WP_APP_PASSWORD=<your_password>")

    return site_url, username, app_password


def main() -> None:
    """Main upload workflow."""
    print("\n" + "=" * 80)
    print("WORDPRESS CALENDAR UPLOADER")
    print("=" * 80)

    # Check for credentials
    if not WORDPRESS_CONFIG["username"] or not WORDPRESS_CONFIG["app_password"]:
        log("WordPress credentials not found in environment variables.")
        site_url, username, app_password = setup_wordpress_credentials()
    else:
        site_url = WORDPRESS_CONFIG["site_url"]
        username = WORDPRESS_CONFIG["username"]
        app_password = WORDPRESS_CONFIG["app_password"]
        uploader = WordPressEventUploader(site_url, username, app_password)
        log(f"Using credentials from environment for {username}")
    # Create uploader
    uploader = WordPressEventUploader(site_url, username, app_password)

    # Test connection
    if not uploader.test_connection():
        log("Cannot continue without valid WordPress connection.")
        return

    # Find latest calendar upload file
    base_dir = Path(__file__).parent.parent
    # Check new organized path first, fall back to legacy
    output_dir = base_dir / "output" / "pipeline"
    if not output_dir.exists():
        output_dir = base_dir / "pipeline_output"

    if not output_dir.exists():
        log(f"Output directory not found: {output_dir}")
        log("Please run the automated pipeline first to generate events.")
        return

    # Find most recent calendar upload file
    csv_files = list(output_dir.glob("calendar_upload_*.csv"))
    if not csv_files:
        log("No calendar upload files found.")
        log("Please run the automated pipeline first.")
        return

    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    log(f"Using file: {latest_csv.name}")

    # Upload events (dry run first)
    print("\n" + "=" * 80)
    print("DRY RUN - Reviewing events before upload")
    print("=" * 80)
    uploader.upload_events_from_csv(latest_csv, dry_run=True)

    # Confirm upload
    print("\n" + "=" * 80)
    response = input("Upload these events to WordPress? (yes/no): ").strip().lower()

    if response == "yes":
        print("\n" + "=" * 80)
        print("UPLOADING TO WORDPRESS")
        print("=" * 80)
        created_ids = uploader.upload_events_from_csv(latest_csv, dry_run=False)

        if created_ids:
            response = (
                input(f"\n{len(created_ids)} events created as DRAFTS. Publish them? (yes/no): ")
                .strip()
                .lower()
            )
            if response == "yes":
                uploader.publish_events(created_ids)
                log("OK: Upload complete! Check your WordPress calendar.")
            else:
                log("Events saved as drafts. You can publish them manually in WordPress.")
    else:
        log("Upload cancelled.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
