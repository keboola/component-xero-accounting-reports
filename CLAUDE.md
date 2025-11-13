# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Keboola Connection component for extracting data from Xero Accounting Reports. It's a Python-based data extractor component that follows Keboola's component architecture patterns. The component uses Docker for deployment and integrates with the Keboola Developer Portal for distribution.

## Development Commands

### Environment Setup
```bash
# Build the Docker image
docker-compose build

# Run the component in development mode
docker-compose run --rm dev

# Run tests and linting
docker-compose run --rm test
```

### Testing
```bash
# Run unit tests only
python -m unittest discover

# Run flake8 linting
flake8 --config=flake8.cfg

# Run both (full test suite)
docker-compose run --rm test
```

### Local Development
- The component reads configuration from `data/config.json` in development
- Input/output data is mounted to `./data` directory
- Environment variable `KBC_DATADIR` controls the data directory path (default: `./data`)

## Architecture

### Core Components

**Component Entry Point** (`src/component.py`)
- Extends `ComponentBase` from `keboola.component.base`
- Main execution logic is in the `run()` method
- The component follows Keboola's state management pattern:
  - Reads previous state from `data/in/state.json`
  - Writes new state via `write_state_file()`
  - Creates output tables with manifests using `create_out_table_definition()` and `write_manifest()`

**Configuration** (`src/configuration.py`)
- Uses Pydantic for configuration validation
- Configuration parameters are defined in the `Configuration` class
- Encrypted parameters (like API tokens) use the `#` prefix (e.g., `#api_token`)
- Custom validators can be added using `@field_validator` decorators
- Validation errors are automatically converted to `UserException` for user-friendly error messages

**Component Configuration** (`component_config/`)
- `configSchema.json` - JSON schema defining the UI configuration form
- `configRowSchema.json` - Schema for row-based configurations
- `component_long_description.md` / `component_short_description.md` - Component descriptions for the Developer Portal
- `sample-config/` - Sample configuration for testing

### Key Dependencies
- `keboola-component` (>=1.6.10) - Base component framework
- `keboola-http-client` (>=1.0.1) - HTTP client utilities
- `xero-python` (>=9.2.0) - Xero API client
- `pydantic` (>=2.11.3) - Configuration validation

### Data Flow
1. Component reads `config.json` from `data/` directory
2. Configuration is validated using Pydantic models
3. Component processes input tables from `data/in/tables/`
4. Results are written to `data/out/tables/` with accompanying manifest files
5. State is persisted to `data/out/state.json` for incremental processing

## Keboola Component Patterns

### Error Handling
- Use `UserException` for user-facing errors (exit code 1)
- Use generic `Exception` for system errors (exit code 2)
- Always provide clear, actionable error messages

### OAuth Integration
The component supports OAuth authentication:
- OAuth credentials are available in `config.json` under `authorization.oauth_api.credentials`
- Encrypted data is in the `#data` field
- App secrets are in the `#appSecret` field

### Incremental Loading
- Use `get_state_file()` to retrieve previous run state
- Use `write_state_file()` to persist state for next run
- Set `incremental=True` when creating output tables for incremental writes

## Deployment

### CI/CD Pipeline (GitHub Actions)
The `.github/workflows/push.yml` handles:
1. Building Docker image
2. Running tests (flake8 + unittest)
3. Optional KBC integration tests (if configured)
4. Pushing to ECR (Elastic Container Registry)
5. Deploying to Keboola Developer Portal (on semantic version tags)

### Deployment Requirements
- Tag commits with semantic versions (e.g., `v1.0.0`) on main branch
- Requires secrets: `KBC_DEVELOPERPORTAL_PASSWORD`, `KBC_STORAGE_TOKEN`, `DOCKERHUB_TOKEN`
- Component ID: `keboola.ex-xero-accounting-reports`
- Vendor: `keboola`

### Manual Deployment
The `deploy.sh` script handles manual deployments (legacy, primarily for CI/CD reference).

## Code Quality

### Linting Configuration
- Max line length: 120 characters
- Ignores: E203, W503
- Excludes: `__pycache__`, `.git`, `.venv`, `venv`

### Python Version
- Requires Python 3.13+
- Uses `uv` for fast dependency management in Docker

## Important Notes

- All component code must be compatible with the Keboola platform
- Configuration parameters with `#` prefix are encrypted in Keboola
- The component must handle the KBC_DATADIR environment variable for data folder location
- Always validate configuration thoroughly to provide clear user feedback
