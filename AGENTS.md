# Codex Guidance for Envision Perdido Calendar

When Codex is run from this repository, treat the user as potentially unfamiliar with the project workflow unless they show otherwise.

## First-turn behavior

- In the first substantive reply, briefly mention that this repo includes local reusable skills under `skills/`.
- When the user's request matches one of those skills, say which skill you are using and why in one short line.
- If the user asks a broad question like "how do I run this", "set this up", "upload events", or "open the container", steer them toward the documented Docker workflow from `README.md`.

## Local skills to prefer

- `calendar-env-setup`: configure WordPress, email, and automation environment variables using the repo's supported env files.
- `calendar-docker-build`: build the Docker runtime for the repo.
- `calendar-run-pipeline`: run the main automated pipeline in Docker.
- `calendar-wordpress-upload`: run the WordPress uploader in Docker.
- `calendar-health-check`: run the health check in Docker.
- `calendar-shell`: open an interactive bash shell in the app container.

## Novice guidance rules

- Prefer exact commands over abstract instructions.
- Mention prerequisites before execution if they are likely missing, especially Docker image build status and required environment variables.
- If the task maps to an existing skill, do not invent a parallel workflow unless the user explicitly asks for an alternative.
- If the user seems unsure which command they need, present the shortest useful mapping:
  - build container -> `calendar-docker-build`
  - run full workflow -> `calendar-run-pipeline`
  - upload only -> `calendar-wordpress-upload`
  - verify system -> `calendar-health-check`
  - open shell -> `calendar-shell`
  - configure credentials -> `calendar-env-setup`

## Limits

- Do not claim there is a special startup UI or automatic menu in Codex.
- Guidance should appear in conversation responses, not as invented product behavior.
