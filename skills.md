# VCR Datadir Testing — Setup Guide

End-to-end process for applying VCR-based functional testing to any Keboola Python component.

## Prerequisites

- Python 3.12+
- `uv` or `pip` for dependency management
- Real API credentials for recording (one-time)

## Step 1: Prepare configs.json

Create a JSON array of Keboola config objects with **dummy** credential values:

```json
[
  {
    "parameters": {
      "reports": [{"report_type": "ProfitAndLoss", ...}]
    },
    "action": "run",
    "authorization": {
      "oauth_api": {
        "credentials": {
          "#data": "{\"access_token\": \"dummy\", \"refresh_token\": \"dummy\"}",
          "appKey": "TEST_APP_KEY",
          "#appSecret": "TEST_APP_SECRET"
        }
      }
    }
  }
]
```

The scaffolder auto-detects raw Keboola configs and generates test names from `parameters.reports[0].report_type`.

## Step 2: Prepare secrets.json (gitignored)

Create `secrets.json` with real credentials that will be deep-merged at recording time:

**OAuth pattern:**
```json
{
  "authorization": {
    "oauth_api": {
      "credentials": {
        "#data": "{\"access_token\": \"real_token\", \"refresh_token\": \"real_token\"}",
        "appKey": "real_client_id",
        "#appSecret": "real_client_secret"
      }
    }
  }
}
```

**Username/password pattern:**
```json
{
  "parameters": {
    "#password": "real_password",
    "username": "real_user"
  }
}
```

## Step 3: Add datadirtest[vcr] Dependency

In `pyproject.toml`:

```toml
dependencies = [
    "datadirtest[vcr] @ git+https://github.com/keboola/datadirtest.git@feature/vcr-testing",
    ...
]
```

Then: `uv sync` or `pip install -e ".[dev]"`

## Step 4: Update .gitignore

```
secrets.json
configs.json
tests/functional/*/source/data/config.secrets.json
```

## Step 5: Run the Scaffolder

```bash
python -m datadirtest scaffold configs.json tests/functional src/component.py --secrets secrets.json
```

This will:
1. Auto-detect raw config format and generate test names (e.g., `01_ProfitAndLoss`)
2. Create directory structure for each test
3. Deep-merge secrets.json into config (in memory only) for recording
4. Record HTTP cassettes via VCR
5. Copy outputs to `expected/` directories
6. Restore dummy credentials in `config.json`

### Scaffold without recording (structure only):
```bash
python -m datadirtest scaffold configs.json tests/functional --no-record
```

## Step 6: Set Up Test Runner

Replace `tests/test_functional.py`:

```python
import unittest
from pathlib import Path
from datadirtest.vcr import VCRDataDirTester

class TestComponent(unittest.TestCase):
    def test_functional(self):
        functional_tests = VCRDataDirTester(
            data_dir=str(Path(__file__).parent / "functional"),
            component_script=str(Path(__file__).parent.parent / "src" / "component.py"),
        )
        functional_tests.run()

if __name__ == "__main__":
    unittest.main()
```

## Step 7: Run Tests

```bash
# Replay from cassettes (CI-friendly, no network)
pytest tests/test_functional.py -v

# Full suite
pytest tests/ -v
```

## Re-recording When APIs Change

When the upstream API changes and cassettes become stale:

1. Ensure `secrets.json` has valid credentials
2. Delete stale cassettes: `rm tests/functional/*/source/data/cassettes/requests.json`
3. Re-run scaffolder: `python -m datadirtest scaffold configs.json tests/functional src/component.py --secrets secrets.json`
4. Review changes to expected outputs and cassettes
5. Commit updated cassettes and expected files

## Directory Structure After Scaffolding

```
tests/functional/01_ProfitAndLoss/
├── source/data/
│   ├── config.json          (dummy credentials)
│   ├── in/state.json
│   ├── cassettes/
│   │   └── requests.json    (recorded HTTP interactions)
│   └── out/tables/          (gitignored, regenerated)
└── expected/data/out/tables/ (expected output for comparison)
```
