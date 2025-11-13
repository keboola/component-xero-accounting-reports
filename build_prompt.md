# Keboola Xero Accounting Reports Component - Build Prompt

## Project Overview
This is a Keboola extraction component that retrieves accounting reports from Xero via their API. The component uses a **row-based configuration** approach where each report is configured as a separate row, and the component is executed once per row.

### Key API Reference
- **Xero Reports API**: https://developer.xero.com/documentation/api/accounting/reports
- Base endpoint has variable endings depending on the report type
- Must support both predefined Xero reports AND custom reports

---

## Component Architecture

### UI Configuration Type
- **UI Mode**: `genericDockerUI-rows`
- **How it works**:
  - User can create multiple configuration rows (e.g., 10 rows)
  - Each row = one report configuration
  - When component runs, Keboola passes ONE row at a time and executes the component 10 times
  - **Benefit**: No need for batch processing in the code - each execution handles a single report

### Configuration Structure

#### 1. **configSchema.json** (Component-Level Configuration)
Located at: `component_config/configSchema.json`

**Purpose**: Handles OAuth authentication that applies to ALL rows

**Requirements**:
- OAuth is handled by a **separate Keboola OAuth component**
- The OAuth component authenticates and passes back the access token
- This component receives the token as a parameter

**Schema Structure**:
```json
{
  "type": "object",
  "title": "Xero Accounting Reports Configuration",
  "required": [],
  "properties": {
    "debug": {
      "type": "boolean",
      "title": "Debug Mode",
      "description": "Enable verbose logging for troubleshooting",
      "default": false,
      "propertyOrder": 100
    }
  }
}
```

**OAuth Integration Notes**:
- Keboola's OAuth component handles the authentication flow separately
- Access token is injected into the component's configuration automatically at runtime
- Component receives token as `#oauth_token` (encrypted parameter with `#` prefix)
- **In Python code**: Access via `ComponentConfiguration` model with Field alias:
  ```python
  oauth_token: str = Field(alias="#oauth_token")
  ```
- No need to implement OAuth flow in this component - just use the provided token
- The OAuth token is NOT visible in the configSchema.json - it's injected by Keboola's platform

#### 2. **configRowSchema.json** (Row-Level Configuration)
Located at: `component_config/configRowSchema.json`

**Purpose**: Configure individual report extraction per row

**Required Fields Structure** (using UI Elements JSON Schema format):
```json
{
  "type": "object",
  "title": "Report Configuration",
  "required": ["report_type"],
  "properties": {
    "report_type": {
      "type": "string",
      "title": "Report Type",
      "propertyOrder": 10,
      "enum": [
        "BalanceSheet",
        "ProfitAndLoss",
        "TrialBalance",
        "BankStatement",
        "AgedReceivables",
        "AgedPayables",
        "ExecutiveSummary",
        "BudgetSummary",
        "Custom"
      ],
      "description": "Select the Xero report to extract"
    },
    "custom_report_id": {
      "type": "string",
      "title": "Custom Report ID",
      "propertyOrder": 20,
      "description": "Required if report_type is 'Custom'. The Xero report ID or name."
    },
    "predefined_parameters": {
      "type": "object",
      "title": "Common Report Parameters",
      "description": "Standard parameters that work across most reports. Supports dynamic dates.",
      "propertyOrder": 30,
      "properties": {
        "fromDate": {
          "type": "string",
          "title": "From Date",
          "description": "Start date. Supports: '3 days ago', 'yesterday', 'YYYY-MM-DD', etc.",
          "format": "date"
        },
        "toDate": {
          "type": "string",
          "title": "To Date",
          "description": "End date. Supports: 'today', 'yesterday', 'YYYY-MM-DD', etc.",
          "format": "date"
        },
        "date": {
          "type": "string",
          "title": "Date",
          "description": "Single date parameter for reports that use one date",
          "format": "date"
        },
        "periods": {
          "type": "integer",
          "title": "Number of Periods",
          "description": "Number of periods to include in the report"
        }
      }
    },
    "custom_parameters": {
      "type": "array",
      "title": "Additional Custom Parameters",
      "description": "Add any report-specific parameters as key-value pairs",
      "propertyOrder": 40,
      "format": "table",
      "items": {
        "type": "object",
        "properties": {
          "key": {
            "type": "string",
            "title": "Parameter Name"
          },
          "value": {
            "type": "string",
            "title": "Parameter Value"
          }
        },
        "required": ["key", "value"]
      }
    }
  }
}
```

**UI Design Notes**:

1. **Report Selection**: Dropdown to choose report type
   - Uses `enum` in JSON Schema to create dropdown
   - `propertyOrder: 10` ensures it appears first

2. **Conditional Field**: `custom_report_id` should only show when `report_type` is "Custom"
   - Can use JSON Schema conditional (`if`/`then`/`else`) if supported
   - Or handle in UI layer
   - `propertyOrder: 20` places it after report_type

3. **Parameter Handling**: Two parameter sections
   - **Predefined Parameters** (`propertyOrder: 30`):
     - Object type with individual properties for common params
     - Each property has `format: "date"` for date picker UI
     - NOT required - user can leave blank
   - **Custom Parameters** (`propertyOrder: 40`):
     - Array type with `format: "table"` for table UI
     - Each item is an object with `key` and `value` properties
     - Allows unlimited rows for report-specific parameters

4. **Date Parsing**: All date values MUST be processed through `keboola.utils` date parser
   - User enters: `"3 days ago"` → Parser outputs: `"2024-11-10"`
   - User enters: `"yesterday"` → Parser outputs: `"2024-11-12"`
   - User enters: `"2024-01-01"` → Parser outputs: `"2024-01-01"`

5. **UI Elements Used**:
   - **Dropdown**: `type: "string"` + `enum: [...]`
   - **Text input**: `type: "string"`
   - **Date picker**: `type: "string"` + `format: "date"`
   - **Number input**: `type: "integer"`
   - **Table/Array editor**: `type: "array"` + `format: "table"` + `items: {object}`
   - **Object group**: `type: "object"` + `properties: {...}`

**Outstanding Tasks**:
- ⚠️ **TODO: Complete Report List** - Add ALL Xero reports to the enum (current list is incomplete)
- ❓ **Sync Action for Parameters** - OPTIONAL enhancement
  - Ideally: implement a sync action that queries Xero API for available parameters per report type
  - If Xero API doesn't provide parameter discovery: hard-code parameter validation/hints in UI
  - **Decision needed**: Research if Xero API has an endpoint to describe report parameters
  - **Alternative**: Create comprehensive mapping of report → allowed parameters in code comments/docs

---

## Code Implementation

### File Structure
```
src/
├── component.py          # Main component logic
├── configuration.py      # Pydantic configuration models
└── xero_client.py        # (NEW) Xero API client wrapper
```

### Configuration Models (configuration.py)

**Component Configuration**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class ComponentConfiguration(BaseModel):
    """Component-level configuration (OAuth token passed from OAuth component)"""
    oauth_token: str = Field(alias="#oauth_token")  # Encrypted parameter from OAuth component
    debug: bool = False
```

**Row Configuration**:
```python
class CustomParameter(BaseModel):
    key: str
    value: str

class PredefinedParameters(BaseModel):
    fromDate: Optional[str] = None
    toDate: Optional[str] = None
    date: Optional[str] = None
    periods: Optional[int] = None

class RowConfiguration(BaseModel):
    """Configuration for a single row execution"""
    report_type: str
    custom_report_id: Optional[str] = None
    predefined_parameters: Optional[PredefinedParameters] = None
    custom_parameters: Optional[List[CustomParameter]] = []

    def get_all_parameters(self) -> Dict[str, str]:
        """
        Merge predefined and custom parameters into a single dict.
        This will be passed to Xero API as query parameters.
        """
        params = {}

        # Add predefined parameters (if they exist)
        if self.predefined_parameters:
            if self.predefined_parameters.fromDate:
                params['fromDate'] = self.predefined_parameters.fromDate
            if self.predefined_parameters.toDate:
                params['toDate'] = self.predefined_parameters.toDate
            if self.predefined_parameters.date:
                params['date'] = self.predefined_parameters.date
            if self.predefined_parameters.periods:
                params['periods'] = str(self.predefined_parameters.periods)

        # Add custom parameters
        if self.custom_parameters:
            for param in self.custom_parameters:
                params[param.key] = param.value

        return params

    def validate_custom_report(self):
        """Ensure custom_report_id is provided when report_type is Custom"""
        if self.report_type == "Custom" and not self.custom_report_id:
            raise ValueError("custom_report_id is required when report_type is 'Custom'")
```

### Main Component Logic (component.py)

**Key responsibilities**:
1. Parse row configuration (remember: ONE row per execution)
2. Get OAuth token from component-level config
3. Parse date parameters using keboola.utils
4. Build API request URL based on report type
5. Fetch report data from Xero
6. Transform to CSV format
7. Save to output table
8. (Optional) Handle state for incremental loading

**Implementation structure**:
```python
from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException
from configuration import RowConfiguration, ComponentConfiguration
import logging

class Component(ComponentBase):

    def run(self):
        """
        Main execution - processes ONE report configuration (one row)
        """
        try:
            # 1. Parse component-level config (OAuth token)
            comp_config = ComponentConfiguration(**self.configuration)
            oauth_token = comp_config.oauth_token

            # 2. Parse row configuration (THIS row's report settings)
            row_config = RowConfiguration(**self.configuration.parameters)
            row_config.validate_custom_report()

            # 3. Initialize Xero client with OAuth token
            from xero_client import XeroClient
            xero_client = XeroClient(oauth_token)

            # 4. Parse date parameters (convert "3 days ago" to actual dates)
            raw_params = row_config.get_all_parameters()
            parsed_params = self.parse_date_parameters(raw_params)

            logging.info(f"Fetching report: {row_config.report_type}")
            logging.info(f"Parameters: {parsed_params}")

            # 5. Determine report endpoint URL
            report_url = self.build_report_url(
                row_config.report_type,
                row_config.custom_report_id
            )

            # 6. Fetch report data from Xero
            report_data = xero_client.get_report(report_url, parsed_params)

            # 7. Transform to CSV and save
            output_filename = f"{row_config.report_type}_{row_config.custom_report_id or 'report'}.csv"
            output_table = self.create_out_table_definition(output_filename)

            self.save_report_data(report_data, output_table)
            self.write_manifest(output_table)

            logging.info(f"Successfully extracted report to {output_filename}")

        except Exception as e:
            logging.error(f"Error extracting report: {str(e)}")
            raise UserException(f"Failed to extract Xero report: {str(e)}")

    def parse_date_parameters(self, params: Dict[str, str]) -> Dict[str, str]:
        """
        Parse date strings using keboola.utils date parser.
        Converts human-readable dates to ISO format.

        Examples:
        - "3 days ago" -> "2024-11-10"
        - "yesterday" -> "2024-11-12"
        - "2024-01-01" -> "2024-01-01" (already formatted)
        """
        from keboola.utils import parse_datetime_interval

        parsed = params.copy()
        date_fields = ['fromDate', 'toDate', 'date']

        for field in date_fields:
            if field in parsed and parsed[field]:
                try:
                    # Use keboola.utils to parse the date string
                    # This handles "3 days ago", "yesterday", etc.
                    parsed_date = parse_datetime_interval(parsed[field])
                    parsed[field] = parsed_date.strftime('%Y-%m-%d')
                    logging.debug(f"Parsed {field}: {params[field]} -> {parsed[field]}")
                except Exception as e:
                    logging.warning(f"Could not parse date for {field}: {e}. Using as-is.")

        return parsed

    def build_report_url(self, report_type: str, custom_id: Optional[str] = None) -> str:
        """
        Build Xero API endpoint URL for the report.

        Standard reports: /api.xro/2.0/Reports/{ReportType}
        Custom reports: /api.xro/2.0/Reports/{CustomReportID}
        """
        base = "https://api.xero.com/api.xro/2.0/Reports"

        if report_type == "Custom":
            if not custom_id:
                raise UserException("Custom report ID is required for custom reports")
            return f"{base}/{custom_id}"
        else:
            return f"{base}/{report_type}"

    def save_report_data(self, report_data: Dict, output_table):
        """
        Transform Xero report data to CSV and save.

        Note: Xero report structure varies by report type.
        May need different parsers for different report formats.
        """
        import csv

        # TODO: Parse report_data structure
        # Xero reports typically have a structure like:
        # {
        #   "Reports": [{
        #     "ReportID": "...",
        #     "ReportName": "...",
        #     "Rows": [...]
        #   }]
        # }

        # Extract and transform to tabular format
        # Write to output_table.full_path as CSV

        pass  # Implementation depends on Xero report structure
```

### Xero Client (xero_client.py)

**NEW FILE** - Wrapper for xero-python SDK:
```python
"""
Xero API client wrapper.
Handles authentication and API calls to Xero.
"""

from xero_python.api_client import ApiClient, Configuration
from xero_python.accounting import AccountingApi
from typing import Dict, Optional
import logging

class XeroClient:
    """
    Client for interacting with Xero Accounting API.
    Uses OAuth token provided by Keboola's OAuth component.
    """

    def __init__(self, oauth_token: str):
        """
        Initialize Xero API client with OAuth token.

        Args:
            oauth_token: OAuth 2.0 access token from Keboola OAuth component
        """
        self.oauth_token = oauth_token

        # Configure xero-python client
        config = Configuration()
        config.access_token = oauth_token

        self.api_client = ApiClient(configuration=config)
        self.accounting_api = AccountingApi(self.api_client)

    def get_report(self, report_endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict:
        """
        Fetch report data from Xero.

        Args:
            report_endpoint: Full URL to the report endpoint
            params: Query parameters for the report

        Returns:
            Dict containing report data
        """
        try:
            # Call Xero API with parameters
            # Note: xero-python may have specific methods for reports
            # Check SDK documentation for exact method

            logging.info(f"Fetching report from: {report_endpoint}")
            logging.debug(f"Parameters: {params}")

            # TODO: Implement actual API call using xero-python SDK
            # response = self.accounting_api.get_report(...)

            # Notes on pagination:
            # - Most Xero reports don't require pagination
            # - They return complete data in one response
            # - But check report size limits in Xero docs

            pass

        except Exception as e:
            logging.error(f"Error fetching report from Xero: {str(e)}")
            raise
```

---

## TODO List for Builders

### Critical Tasks (Must Do)

1. ⚠️ **Complete Xero Report List**
   - Research and add ALL available Xero reports to `configRowSchema.json` enum
   - Current list is incomplete - check Xero API docs for full list
   - Include report names exactly as they appear in Xero API

2. ⚠️ **OAuth Token Integration**
   - Confirm the exact parameter name for OAuth token (e.g., `#oauth_token`, `#access_token`)
   - Verify how Keboola's OAuth component passes the token
   - Update `ComponentConfiguration` model accordingly

3. ⚠️ **Date Parsing Integration**
   - Integrate `keboola.utils.parse_datetime_interval` or equivalent
   - Ensure it handles all common date expressions:
     - Relative: "3 days ago", "yesterday", "today", "last month"
     - Absolute: "2024-01-01"
     - Edge cases: "first day of last month", "last monday"
   - Add to `requirements.txt` if not already included

4. ⚠️ **Xero API Client Implementation**
   - Complete `xero_client.py` using `xero-python` SDK
   - Find the correct method for fetching reports
   - Handle authentication with OAuth token
   - Add error handling for:
     - Invalid tokens (401)
     - Rate limits (429)
     - Invalid report types (404)
     - API errors (500+)

5. ⚠️ **Report Data Parsing**
   - Understand Xero report response structure
   - Implement `save_report_data()` to transform JSON → CSV
   - Handle different report formats (they may vary by report type)
   - Ensure all data is properly flattened for CSV

### Implementation Tasks

- [ ] Update `configSchema.json` (minimal - just debug flag)
- [ ] Create complete `configRowSchema.json` with:
  - [ ] Full list of all Xero reports
  - [ ] Conditional logic for `custom_report_id` (show only when report_type="Custom")
  - [ ] Proper `propertyOrder` values
  - [ ] Clear descriptions for each field
- [ ] Implement `RowConfiguration` in `configuration.py`
- [ ] Implement `ComponentConfiguration` in `configuration.py`
- [ ] Create `xero_client.py` with OAuth token auth
- [ ] Update `component.py` with report extraction logic
- [ ] Implement date parsing using keboola.utils
- [ ] Implement report data → CSV transformation
- [ ] Add comprehensive error handling
- [ ] Add logging at key points
- [ ] Update `pyproject.toml` dependencies if needed

### Testing Tasks

- [ ] Test OAuth token authentication
- [ ] Test each predefined report type
- [ ] Test custom reports with custom IDs
- [ ] Test date parsing with various formats:
  - [ ] "3 days ago"
  - [ ] "yesterday"
  - [ ] "today"
  - [ ] "last month"
  - [ ] "2024-01-01" (ISO format)
  - [ ] Invalid dates (should fail gracefully)
- [ ] Test with no parameters
- [ ] Test with only predefined parameters
- [ ] Test with only custom parameters
- [ ] Test with both predefined and custom parameters
- [ ] Test with 10+ rows (component should run 10+ times)
- [ ] Test error scenarios:
  - [ ] Invalid OAuth token
  - [ ] Invalid report type
  - [ ] Missing required parameters
  - [ ] Xero API errors
  - [ ] Network errors

### Nice-to-Have Enhancements

- [ ] **Sync Action for Parameter Discovery** (OPTIONAL)
  - Research if Xero API provides endpoint to list valid parameters per report
  - If yes: implement sync action in component
  - If no: add documentation mapping reports → parameters
- [ ] Add validation for required parameters per report type
- [ ] Support incremental loading (if reports support it)
- [ ] Add progress logging for large reports
- [ ] Support different output formats (if needed)
- [ ] Add caching for frequently requested reports (if beneficial)

---

## Key Dependencies

From `pyproject.toml` (ensure these are present):
```toml
[tool.poetry.dependencies]
python = "^3.9"
keboola.component = "^1.0"
xero-python = "^latest"  # Xero API SDK
pydantic = "^2.0"  # Configuration validation
# keboola.utils should already be included for date parsing
```

---

## Important Notes for AI Builders

### 1. **Row-Based Execution Model**
- ⚠️ **CRITICAL**: Your code runs ONCE per row
- Don't try to loop through multiple reports
- Keboola handles the looping - you just process the current row's config
- Each execution is isolated - no shared state between rows

### 2. **OAuth is External**
- OAuth authentication is handled by **Keboola's OAuth component**, not this component
- You just receive the token as a parameter
- No need to implement OAuth flow, refresh logic, or credential storage
- Just use the provided token in API calls

### 3. **Date Parsing is Critical**
- Users WILL use expressions like "3 days ago"
- Always parse dates through `keboola.utils`
- Never assume dates are in ISO format
- Handle parsing errors gracefully with clear messages

### 4. **Report URL Pattern**
- Standard reports: `https://api.xero.com/api.xro/2.0/Reports/{ReportType}`
  - Example: `https://api.xero.com/api.xro/2.0/Reports/BalanceSheet`
- Custom reports: `https://api.xero.com/api.xro/2.0/Reports/{CustomReportId}`
  - Example: `https://api.xero.com/api.xro/2.0/Reports/abc-123-def-456`

### 5. **No Batch Processing Needed**
- Xero reports typically return complete data in one response
- Pagination probably not needed (but verify in Xero docs)
- One API call per report should be sufficient

### 6. **Error Handling Strategy**
- If one row fails, only that row fails - others continue
- Make error messages descriptive and actionable
- Log enough detail for debugging but don't expose sensitive data
- User-facing errors should suggest solutions

### 7. **Testing with Multiple Rows**
- Locally, you can only test one row at a time
- In Keboola, create multiple rows to test the full flow
- Each row should produce a separate output CSV file

---

## Example User Scenarios

### Scenario 1: Extract Balance Sheet for Last Month
**Row Configuration**:
```json
{
  "report_type": "BalanceSheet",
  "predefined_parameters": {
    "date": "last day of last month"
  }
}
```

**Expected Behavior**:
1. Date parser converts "last day of last month" → "2024-10-31"
2. API call: `GET /Reports/BalanceSheet?date=2024-10-31`
3. Output: `BalanceSheet_report.csv`

### Scenario 2: Extract P&L for Q3 2024
**Row Configuration**:
```json
{
  "report_type": "ProfitAndLoss",
  "predefined_parameters": {
    "fromDate": "2024-07-01",
    "toDate": "2024-09-30",
    "periods": 3
  }
}
```

**Expected Behavior**:
1. Dates already in ISO format - no parsing needed
2. API call: `GET /Reports/ProfitAndLoss?fromDate=2024-07-01&toDate=2024-09-30&periods=3`
3. Output: `ProfitAndLoss_report.csv`

### Scenario 3: Extract Custom Report with Tracking
**Row Configuration**:
```json
{
  "report_type": "Custom",
  "custom_report_id": "my-custom-report-123",
  "predefined_parameters": {
    "fromDate": "first day of this year",
    "toDate": "today"
  },
  "custom_parameters": [
    {"key": "trackingOptionID", "value": "DEPT-SALES"},
    {"key": "standardLayout", "value": "true"}
  ]
}
```

**Expected Behavior**:
1. Validate custom_report_id is present
2. Parse dates: "first day of this year" → "2024-01-01", "today" → "2024-11-13"
3. Merge all parameters
4. API call: `GET /Reports/my-custom-report-123?fromDate=2024-01-01&toDate=2024-11-13&trackingOptionID=DEPT-SALES&standardLayout=true`
5. Output: `Custom_my-custom-report-123.csv`

### Scenario 4: Multiple Reports in One Job
**User creates 5 rows**:
1. BalanceSheet for last month
2. ProfitAndLoss for last quarter
3. AgedReceivables as of today
4. AgedPayables as of today
5. Custom report with ID xyz-789

**Expected Behavior**:
- Keboola executes component 5 times
- Each execution processes one row
- 5 CSV files are produced
- All use the same OAuth token
- Failures in one row don't affect others

---

## Configuration Schema Reference

Based on the attached "UI Elements (JSON Schema) & App Configuration" document, ensure all JSON schemas follow Keboola's conventions:

- Use `propertyOrder` to control field display order
- Use `format: "table"` for array inputs that should display as tables
- Use `description` for helpful tooltips
- Use `enum` for dropdowns
- Use conditional logic (if supported) to show/hide fields
- Follow naming conventions (camelCase for properties)
- Use encrypted parameters with `#` prefix for sensitive data

---

## Final Checklist Before Deployment

- [ ] All Xero reports are in the configRowSchema enum
- [ ] OAuth token integration is tested and working
- [ ] Date parsing handles all common expressions
- [ ] Report data is correctly transformed to CSV
- [ ] Error messages are clear and actionable
- [ ] Component works with multiple rows (tested with 10+ rows)
- [ ] Output files have meaningful names
- [ ] Logging is comprehensive but not verbose
- [ ] All dependencies are in pyproject.toml
- [ ] Code follows Keboola component patterns
- [ ] Documentation is updated
- [ ] Tests pass for all report types
