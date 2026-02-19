# Core Utilities & Modules

Shared utility modules used across the pipeline.

## Scripts (5)

- `env_loader.py` — Cross-platform environment loader
  - Loads env vars from platform-specific config files
  - Windows: `windows/env.ps1` (PowerShell format)
  - macOS/Linux: `macos/env.sh` (Bash/Zsh format)
  - Fallback: `~/.secrets/` directory
  - Respects already-set environment variables (no override)
  - Validates required configuration

- `logger.py` — Structured logging system
  - JSON format for file logs (machine-readable)
  - Human-readable format for console output
  - Automatic log rotation (10 MB default)
  - Pipeline metrics collection and reporting
  - Singleton pattern for consistent logging
  - Color-coded console output by severity

- `health_check.py` — System health verification
  - Validates WordPress REST API connectivity
  - Tests email (SMTP) connectivity
  - Checks for upcoming events with valid times
  - Verifies public calendar page loads
  - Sends email alerts on failure
  - Used in CI/CD and scheduled monitoring

- `tag_taxonomy.py` — Controlled tag vocabulary
  - Single source of truth for event tags
  - Organized by category: Community, Art, Sports, etc.
  - Keyword mapping for tag inference
  - Consistent tagging across pipeline
  - Used by classifiers and enrichment

- `venue_registry.py` — Known venues database
  - Canonical venue names and aliases
  - Location normalization and matching
  - Venue metadata (address, coordinates, phone)
  - Used for deduplication and enrichment
  - Maintained manually with version control

## Usage

### Environment Loader
```python
from core.env_loader import load_env, validate_env_config

load_env()  # Load from platform-specific config
validate_env_config()  # Verify required vars are set
```

### Logging
```python
from core.logger import get_logger

logger = get_logger()
logger.info("Event processed", event_id=123, source="chamber")
```

### Health Check
```bash
python core/health_check.py
# Checks API, email, events, and calendar page
# Sends alert email on any failure
```

### Tag Taxonomy
```python
from core.tag_taxonomy import TagTaxonomy

tags = TagTaxonomy()
print(tags.COMMUNITY_TAGS)  # All community event tags
print(tags.TAG_KEYWORDS)  # Keywords for inference
```

### Venue Registry
```python
from core.venue_registry import normalize_location_text, get_known_venue

loc = normalize_location_text("  Perdido Community Library  ")
venue = get_known_venue(loc)
```

## Configuration

### Environment Variables
- `WP_SITE_URL` — WordPress site URL
- `WP_USERNAME` — WordPress admin username
- `WP_APP_PASSWORD` — WordPress Application Password
- `SMTP_SERVER` — Email SMTP server
- `SMTP_PORT` — SMTP port (usually 587)
- `SENDER_EMAIL` — Sender email address
- `EMAIL_PASSWORD` — Email password (Gmail App Password)
- `SITE_TIMEZONE` — Site timezone (default: America/Chicago)
- `AUTO_UPLOAD` — Enable auto-upload (default: false)

### Logging Configuration
- `LOG_DIR` — Log output directory (default: `output/logs/`)
- `LOG_LEVEL` — Logging level (default: INFO)
- `LOG_MAX_BYTES` — Log rotation size (default: 10 MB)
- `LOG_BACKUP_COUNT` — Rotated log files to keep (default: 5)

## Integration

These modules are used by:
- **All scripts** — env_loader for configuration
- **Pipeline** — logger for metrics and debugging
- **Monitoring** — health_check for alerts
- **Classifiers** — tag_taxonomy for consistent tagging
- **Deduplication** — venue_registry for normalization

## Testing

Unit tests available for each module:
```bash
pytest tests/unit/test_logger.py
pytest tests/unit/test_tag_taxonomy.py
```

See `tests/unit/` for comprehensive test coverage.
