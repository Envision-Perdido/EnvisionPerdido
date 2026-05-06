---
name: calendar-wordpress-upload
description: Run the Envision Perdido WordPress uploader in Docker when the user wants to push approved events to the EventON calendar.
---

# Calendar WordPress Upload

Use this skill when the task is to upload events to WordPress from the repository's containerized runtime.

## Command

Run from the repository root:

```bash
docker compose run --rm app python scripts/pipeline/wordpress_uploader.py
```

## Preconditions

- The Docker image should exist. If not, run `docker compose build`.
- WordPress credentials must be set in environment variables:
  - `WP_SITE_URL`
  - `WP_USERNAME`
  - `WP_APP_PASSWORD`

## Workflow

1. Confirm Docker is available and the repo is at the compose root.
2. Ensure the required WordPress credentials are present.
3. Run the uploader command above.
4. Inspect output files in `container-data/output/` if the script emits reports or logs.

## Notes

- This skill is narrower than the full pipeline and is appropriate when the user only wants the upload step.
- The container runs in `/app`, matching the repository layout.
