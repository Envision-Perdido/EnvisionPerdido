---
name: calendar-shell
description: Open an interactive bash shell in the Envision Perdido Docker app container when the user wants to inspect the repo or run commands manually inside the documented runtime.
---

# Calendar Shell

Use this skill when the user wants an interactive shell inside the repository's Docker container.

## Command

Run from the repository root:

```bash
docker compose run --rm app
```

Equivalent explicit form:

```bash
docker compose run --rm app bash
```

## Workflow

1. Confirm the current directory is the repo root.
2. Build the image first with `docker compose build` if it has not been built yet.
3. Launch the shell command above.
4. Run repo commands manually inside `/app`.

## Notes

- The image installs `bash`, and both the Dockerfile and compose service are configured for interactive shell use.
- Host directories `container-data/output/` and `container-data/data-cache/` are mounted into the containerized app paths, so files created there persist after the shell exits.
