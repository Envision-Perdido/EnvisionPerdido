---
name: calendar-health-check
description: Run the Envision Perdido health check in Docker when the user wants to verify system status, connectivity, and alerting behavior.
---

# Calendar Health Check

Use this skill when the task is to run the project's documented health monitoring command.

## Command

Run from the repository root:

```bash
docker compose run --rm app python scripts/pipeline/health_check.py
```

## Preconditions

- The Docker image should exist. If not, build it with `docker compose build`.
- Any environment variables required by the health check should be present before execution.

## Workflow

1. Confirm `docker-compose.yml` is in the current directory.
2. Build the image if needed.
3. Run the health-check command above.
4. Review logs or generated outputs under `container-data/output/` if the script writes reports.

## Notes

- Use this skill for monitoring and diagnostics, not for event scraping or upload operations.
- The README lists this as the documented health-check command.
