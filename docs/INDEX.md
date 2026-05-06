# EnvisionPerdido Documentation Index

##  Getting Started

Start here if you're new to the project:

- **[README](../README.md)** - Project overview and quick setup
- **[Quick Start Guide](CROSS_PLATFORM_SETUP.md)** - Step-by-step guide to run the pipeline
- **[PROJECT_STRUCTURE](PROJECT_STRUCTURE.md)** - Folder organization and file locations

##  Setup & Configuration

- **[CROSS_PLATFORM_SETUP](CROSS_PLATFORM_SETUP.md)** - Complete setup guide for Windows and macOS
- **[COMMANDS](COMMANDS.md)** - Common commands reference (covers quick reference and automation setup)
- **[GITHUB_SECRETS](GITHUB_SECRETS.md)** - All GitHub secrets and variables required before making the repo public

##  WordPress Integration

- **[WORDPRESS_INTEGRATION_GUIDE](WORDPRESS_INTEGRATION_GUIDE.md)** - Complete WordPress upload workflow
- **[WORDPRESS_EVENT_API_SPEC](WORDPRESS_EVENT_API_SPEC.md)** - Exact EventON create payload and field mapping used by the uploader
- **[EVENTON_PLUGIN_INSTALL](EVENTON_PLUGIN_INSTALL.md)** - Installing the EventON REST API plugin
- **[IMAGE_UPLOAD_GUIDE](WORDPRESS_INTEGRATION_GUIDE.md#images)** - Automatic and manual image handling (see WORDPRESS_INTEGRATION_GUIDE)

##  Remote Handoffs

- **[remote-handoffs/README](remote-handoffs/README.md)** - External handoff bundles and repo-specific implementation notes
- **[Play Perdido Implementation Plan](remote-handoffs/event-engine-bundle/IMPLEMENTATION_PLAN.md)** - Enforcement plan for the Play Perdido ingest and copy contract

##  Machine Learning & Classification

- **[SVM_USAGE_GUIDE](SVM_USAGE_GUIDE.md)** - Training and using the classification model

##  Architecture & Implementation

- **[ARCHITECTURE_AND_DATAFLOW](ARCHITECTURE_AND_DATAFLOW.md)** - System architecture and data flow diagrams
- **[SOURCES_INTEGRATION_SUMMARY](SOURCES_INTEGRATION_SUMMARY.md)** - Integration patterns for event sources
- **[EVENT_NORMALIZATION_QUICK_REFERENCE](EVENT_NORMALIZATION_QUICK_REFERENCE.md)** - Event enrichment features and normalization

##  Testing & CI/CD

- **[CI_CD_GUIDE](CI_CD_GUIDE.md)** - GitHub Actions workflows and automated testing
- **[LIVE_TESTS](CI_CD_GUIDE.md#live-tests)** - Running tests against a real WordPress site (see CI_CD_GUIDE)

##  Contributing

- **[CONTRIBUTING](CONTRIBUTING.md)** - Development workflow and contribution guidelines (includes branching strategy)

##  Archive

Archived documentation (dated snapshots):
- [archive/](archive/) - Historical assessments and implementation summaries
