# Changelog

All notable changes to this project should be documented in this file.

## 2026-03-09

### Added

- Added a containerized runtime via `Dockerfile` and `docker-compose.yml` so the project can run its documented Python commands without a host Python environment.
- Added a persistent host-mounted `container-data/` workspace for generated outputs and cache files.
- Added `.dockerignore` to keep local artifacts and secrets out of the Docker build context.

### Changed

- Updated `README.md` with Docker build and run commands for the main workflows.
- Updated `.gitignore` to exclude `container-data/` from version control.

### Notes

- This entry documents changes made by Codex.
