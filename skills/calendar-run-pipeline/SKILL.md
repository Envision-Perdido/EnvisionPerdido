---
name: calendar-run-pipeline
description: Run the Envision Perdido automated pipeline in Docker when the user wants to scrape, classify, email, and upload events using the documented repo workflow.
---

# Calendar Run Pipeline

Use this skill when the user wants to execute the main automated calendar pipeline.

## Command

Run from the repository root:

```bash
docker compose run --rm app python scripts/automated_pipeline.py
```

## Preconditions

- The Docker image should exist. If not, build it first with `docker compose build`.
- Required environment variables for WordPress and email must be available to the process if the full pipeline will upload or send notifications.

## Workflow

1. Verify the repo root contains `docker-compose.yml`.
2. Build the image if needed.
3. Run the pipeline command above.
4. Check generated artifacts under `container-data/output/` and cached data under `container-data/data-cache/`.

## Notes

- This is the documented Docker entrypoint for the main scrape -> classify -> email -> upload flow.
- If the user wants a safer wrapper with smoke tests, consider `scripts/run_pipeline_with_smoketest.py`, but the README-documented command is `scripts/automated_pipeline.py`.
