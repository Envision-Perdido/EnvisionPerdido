---
name: calendar-docker-build
description: Build the Envision Perdido calendar Docker runtime when the user wants to prepare or refresh the container image before running repo commands.
---

# Calendar Docker Build

Use this skill when the task is to build or rebuild the repository's Docker image.

## Command

Run from the repository root:

```bash
docker compose build
```

## Workflow

1. Confirm you are in the repo root so `docker-compose.yml` is in the current directory.
2. Run `docker compose build`.
3. If the user plans to execute pipeline, upload, health-check, or ad hoc commands next, keep using the `app` service from `docker-compose.yml`.

## Notes

- The image is built from `Dockerfile`.
- The container starts in `/app`.
- `bash` is available in the image, so interactive runs can use the shell directly.
