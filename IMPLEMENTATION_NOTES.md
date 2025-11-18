# Xero Accounting Reports Component - Implementation Summary

## Overview

This Keboola component extracts accounting reports from Xero via their API. It uses a row-based configuration approach where each report is configured as a separate row, and the component executes once per row.

## Architecture Diagrams

### Component Architecture

```mermaid
graph TB
    subgraph "Configuration"
        CS[configSchema.json<br/>Component Config]
        CRS[configRowSchema.json<br/>Row Config]
    end

    subgraph "Python Code"
        CONF[configuration.py<br/>Pydantic Models]
        COMP[component.py<br/>Main Logic]
        XERO[xero_client.py<br/>API Client]
    end

    subgraph "External Services"
        OAUTH[Keboola OAuth<br/>Component]
        API[Xero API<br/>Reports Endpoint]
    end

    subgraph "Data"
        INPUT[config.json<br/>Input Configuration]
        OUTPUT[CSV Files<br/>Report Data]
    end

    CS -->|validates| INPUT
    CRS -->|validates| INPUT
    INPUT -->|parsed by| CONF
    CONF -->|used by| COMP
    COMP -->|calls| XERO
    OAUTH -->|provides token| CONF
    XERO -->|HTTP requests| API
    API -->|JSON response| XERO
    XERO -->|returns data| COMP
    COMP -->|writes| OUTPUT

    style CS fill:#e1f5ff
    style CRS fill:#e1f5ff
    style CONF fill:#fff4e1
    style COMP fill:#fff4e1
    style XERO fill:#fff4e1
    style OAUTH fill:#e8f5e9
    style API fill:#e8f5e9
    style INPUT fill:#f3e5f5
    style OUTPUT fill:#f3e5f5
```

### Data Flow

```mermaid
flowchart LR
    subgraph Input
        USER[User Creates<br/>Configuration Rows]
        ROW1[Row 1:<br/>BalanceSheet]
        ROW2[Row 2:<br/>ProfitAndLoss]
        ROW3[Row 3:<br/>Custom Report]
    end

    subgraph "Keboola Platform"
        LOOP[Platform Loops<br/>Through Rows]
    end

    subgraph "Component Execution"
        EXEC1[Execute Once<br/>for Row 1]
        EXEC2[Execute Once<br/>for Row 2]
        EXEC3[Execute Once<br/>for Row 3]
    end

    subgraph "Xero API"
        API1[GET /Reports/<br/>BalanceSheet]
        API2[GET /Reports/<br/>ProfitAndLoss]
        API3[GET /Reports/<br/>custom-id]
    end

    subgraph Output
        CSV1[BalanceSheet_<br/>2025-11-13.csv]
        CSV2[ProfitAndLoss_<br/>2025-11-13.csv]
        CSV3[Custom_<br/>2025-11-13.csv]
    end

    USER --> ROW1 & ROW2 & ROW3
    ROW1 & ROW2 & ROW3 --> LOOP
    LOOP --> EXEC1 --> API1 --> CSV1
    LOOP --> EXEC2 --> API2 --> CSV2
    LOOP --> EXEC3 --> API3 --> CSV3

    style USER fill:#e3f2fd
    style LOOP fill:#fff9c4
    style EXEC1 fill:#f3e5f5
    style EXEC2 fill:#f3e5f5
    style EXEC3 fill:#f3e5f5
```

### Execution Sequence

```mermaid
sequenceDiagram
    participant User
    participant Keboola
    participant Component
    participant Config
    participant XeroClient
    participant XeroAPI
    participant Output

    User->>Keboola: Create Row Configuration
    Keboola->>Component: Execute (1 row)

    Component->>Config: Validate ComponentConfiguration
    Config-->>Component: OAuth Token + Debug Flag

    Component->>Config: Validate RowConfiguration
    Config-->>Component: Report Type + Parameters

    Component->>Component: Parse Date Parameters<br/>("3 days ago" → "2025-11-10")

    Component->>XeroClient: Initialize with OAuth Token
    Component->>XeroClient: get_report(tenant_id, type, params)

    XeroClient->>XeroAPI: GET /api.xro/2.0/Reports/{type}
    XeroAPI-->>XeroClient: JSON Report Data

    XeroClient-->>Component: Parsed Report Object

    Component->>Component: Transform Report to Rows<br/>(Flatten nested structure)

    Component->>Output: Write CSV File
    Component->>Output: Write Manifest

    Output-->>Keboola: Report CSV + Metadata
    Keboola-->>User: Success + Output Table
```

### Configuration Structure

```mermaid
graph TD
    subgraph "Component Level"
        OAUTH[#oauth_token<br/>From Keboola OAuth]
        DEBUG[debug: boolean<br/>Enable logging]
    end

    subgraph "Row Level"
        TYPE[report_type<br/>BalanceSheet/ProfitAndLoss/...]
        CUSTOM[custom_report_id<br/>For Custom reports only]

        subgraph "Predefined Parameters"
            FROM[fromDate: string]
            TO[toDate: string]
            DATE[date: string]
            PERIODS[periods: integer]
            TIME[timeframe: MONTH/QUARTER/YEAR]
            TRACK1[trackingOptionID1: string]
            TRACK2[trackingOptionID2: string]
            LAYOUT[standardLayout: boolean]
            PAYMENTS[paymentsOnly: boolean]
        end

        subgraph "Custom Parameters"
            KEY1[key: string]
            VAL1[value: string]
            KEY2[key: string]
            VAL2[value: string]
        end
    end

    subgraph "Merged Parameters"
        MERGED[All Parameters<br/>Dict for Xero API]
    end

    TYPE --> MERGED
    CUSTOM -.->|if Custom| MERGED
    FROM & TO & DATE & PERIODS & TIME --> MERGED
    TRACK1 & TRACK2 & LAYOUT & PAYMENTS --> MERGED
    KEY1 & VAL1 --> MERGED
    KEY2 & VAL2 --> MERGED

    OAUTH --> API[API Authentication]
    DEBUG --> LOGGING[Verbose Logging]
    MERGED --> API

    style OAUTH fill:#ffebee
    style TYPE fill:#e3f2fd
    style CUSTOM fill:#fff3e0
    style FROM fill:#e8f5e9
    style TO fill:#e8f5e9
    style DATE fill:#e8f5e9
    style MERGED fill:#f3e5f5
```

### Report Transformation Pipeline

```mermaid
flowchart TD
    START[Xero API Response<br/>JSON Format]

    EXTRACT[Extract Report Metadata<br/>report_id, report_name, report_date]

    ROWS[Process Report Rows<br/>Recursive traversal]

    FLATTEN[Flatten Each Row<br/>row_type, title, cells]

    CELLS[Transform Cells Array<br/>→ cell_0, cell_1, cell_2...]

    NESTED{Has Nested<br/>Rows?}

    RECURSE[Process Nested Rows<br/>Concatenate titles]

    COLLECT[Collect All Flattened Rows<br/>Add metadata columns]

    COLUMNS[Determine All Unique<br/>Column Names]

    CSV[Write CSV File<br/>With manifest]

    START --> EXTRACT
    EXTRACT --> ROWS
    ROWS --> FLATTEN
    FLATTEN --> CELLS
    CELLS --> NESTED
    NESTED -->|Yes| RECURSE
    NESTED -->|No| COLLECT
    RECURSE --> COLLECT
    COLLECT --> COLUMNS
    COLUMNS --> CSV

    style START fill:#e3f2fd
    style EXTRACT fill:#fff9c4
    style FLATTEN fill:#f3e5f5
    style NESTED fill:#ffe0b2
    style CSV fill:#c8e6c9
```

## What Was Implemented

### 1. Configuration Schemas

#### Component-Level Schema (`component_config/configSchema.json`)
- Minimal configuration with only a `debug` flag
- OAuth token is injected by Keboola's OAuth component (not visible in schema)

#### Row-Level Schema (`component_config/configRowSchema.json`)
- **Report Type Dropdown**: 12 predefined Xero reports + Custom option
  - BalanceSheet
  - ProfitAndLoss
  - TrialBalance
  - BankStatement
  - BankSummary
  - AgedReceivablesByContact
  - AgedPayablesByContact
  - ExecutiveSummary
  - BudgetSummary
  - TenNinetyNine
  - GST
  - Custom

- **Conditional Field**: `custom_report_id` for Custom reports
- **Predefined Parameters**: 9 common parameters with proper types
  - fromDate, toDate, date (date picker UI)
  - periods (integer)
  - timeframe (dropdown: MONTH/QUARTER/YEAR)
  - trackingOptionID1, trackingOptionID2
  - standardLayout, paymentsOnly (boolean)

- **Custom Parameters**: Table/array input for unlimited key-value pairs

### 2. Configuration Models (`src/configuration.py`)

#### ComponentConfiguration
- Handles OAuth token with Field alias `#oauth_token`
- Debug flag support
- Validation error handling with user-friendly messages

#### RowConfiguration
- All report settings (type, custom ID, parameters)
- Validators:
  - `validate_report_type`: Ensures valid report type
  - `validate_custom_report_id`: Requires ID when type is Custom
- `get_all_parameters()`: Merges predefined + custom parameters into single dict

#### Supporting Models
- `PredefinedParameters`: Typed fields for all common parameters
- `CustomParameter`: Key-value pair structure

### 3. Xero API Client (`src/xero_client.py`)

#### XeroClient Class
- Initializes with OAuth token from Keboola
- Uses `xero-python` SDK with OAuth2Token
- Main method: `get_report(xero_tenant_id, report_type, custom_report_id, params)`

#### Report Type Handlers
Implements specific handlers for each report type:
- BalanceSheet, ProfitAndLoss, TrialBalance
- BankStatement, AgedReceivablesByContact, AgedPayablesByContact
- ExecutiveSummary, BudgetSummary, TenNinetyNine
- GST, BankSummary (generic endpoint)
- Custom reports (generic endpoint with custom ID)

#### Error Handling
User-friendly error messages for:
- 401: Authentication failed → Reconnect OAuth
- 403: Access denied → Check permissions
- 404: Report not found → Verify report type/ID
- 429: Rate limit → Wait and retry
- Other errors: Generic message with details

### 4. Main Component (`src/component.py`)

#### Architecture
Clean workflow pattern with self-documenting method names:

1. **`run()`**: Orchestrator (~20 lines)
   - Validates configuration
   - Parses dates
   - Fetches report
   - Saves output

2. **`_validate_and_get_configuration()`**: Configuration validation
   - Parses component + row configs
   - Extracts OAuth token and tenant ID
   - Returns structured config dict

3. **`_get_xero_tenant_id()`**: Tenant ID extraction
   - Checks multiple possible locations in OAuth data
   - Clear error if not found

4. **`_parse_date_parameters()`**: Date parsing
   - Uses `keboola.utils.parse_datetime_interval`
   - Converts "3 days ago" → "2025-11-10"
   - Handles ISO dates and relative expressions
   - Graceful fallback if parsing fails

5. **`_fetch_report_from_xero()`**: API call
   - Initializes XeroClient
   - Calls get_report with all parameters

6. **`_save_output_table()`**: CSV output
   - Generates filename with timestamp
   - Transforms report data to rows
   - Writes CSV with manifest

7. **`_transform_report_to_rows()`**: Data transformation
   - Extracts report metadata
   - Flattens nested report structure
   - Adds metadata columns

8. **`_flatten_report_row()`**: Row flattening
   - Extracts row type and title
   - Converts cells to columns
   - Handles nested rows

9. **`_write_csv()`**: CSV writing
   - Collects all unique columns
   - Writes with proper headers
   - Handles empty results

### 5. Code Quality

All code has been formatted and linted:
- `ruff format` applied to all Python files
- `ruff check --fix` applied to fix linting issues
- Proper type hints on all functions
- `@staticmethod` decorator where appropriate
- No IDE warnings or type errors

### 6. Sample Configuration

Created `data/config.json` with example configuration:
- ProfitAndLoss report
- Date range using relative dates ("3 days ago" to "today")
- 3 periods
- Placeholder for OAuth token and tenant ID

## Key Implementation Decisions

### 1. Row-Based Execution Model
- Component runs ONCE per row (no batch processing)
- Each execution produces one CSV file
- Keboola handles the looping between rows
- Simple, isolated execution model

### 2. OAuth Token Handling
- Token comes from external OAuth component
- Accessed via `#oauth_token` Field alias in Pydantic
- Tenant ID extracted from authorization.oauth_api.credentials
- Multiple fallback locations checked for tenant ID

### 3. Date Parsing Strategy
- Always use `keboola.utils.parse_datetime_interval`
- Converts to ISO format (YYYY-MM-DD) for Xero API
- Graceful fallback to original value if parsing fails
- Supports all common expressions (yesterday, 3 days ago, etc.)

### 4. Report Data Transformation
- Xero reports have complex nested structure
- Flattening strategy:
  - Extract metadata (report_id, report_name, report_date)
  - Process each row individually
  - Convert cells array to cell_0, cell_1, etc. columns
  - Concatenate nested row titles
- Flexible approach works across different report types

### 5. Error Handling
- User-facing errors use `UserException` (exit code 1)
- System errors raise generic Exception (exit code 2)
- Clear, actionable error messages
- API error codes translated to user-friendly text

## Files Created/Modified

### Created
1. `/src/xero_client.py` - Xero API client wrapper
2. `/IMPLEMENTATION_NOTES.md` - This file

### Modified
1. `/component_config/configSchema.json` - Component-level config
2. `/component_config/configRowSchema.json` - Row-level config
3. `/src/configuration.py` - Pydantic models
4. `/src/component.py` - Main component logic
5. `/data/config.json` - Sample configuration

## Dependencies

All required dependencies are already in `pyproject.toml`:
- `keboola-component>=1.6.10` - Base framework
- `keboola-utils>=1.1.0` - Date parsing utilities
- `xero-python>=9.2.0` - Xero API SDK
- `pydantic>=2.11.3` - Configuration validation
- `keboola-http-client>=1.0.1` - HTTP utilities

## Testing Recommendations

### Before Production Use

1. **OAuth Integration Testing**
   - Test with real Xero OAuth token
   - Verify tenant ID extraction from OAuth data
   - Test token expiration handling

2. **Report Type Testing**
   - Test each of the 11 predefined report types
   - Test Custom reports with various IDs
   - Verify parameter passing for each type

3. **Date Parsing Testing**
   Test various date expressions:
   - "3 days ago"
   - "yesterday"
   - "today"
   - "last month"
   - "first day of last month"
   - "2024-01-01" (ISO format)
   - Invalid dates (should handle gracefully)

4. **Parameter Testing**
   - Test with no parameters
   - Test with only predefined parameters
   - Test with only custom parameters
   - Test with both predefined and custom
   - Test parameter override (custom overriding predefined)

5. **Multiple Rows Testing**
   - Create 5-10 configuration rows
   - Verify each produces separate output
   - Confirm failures in one row don't affect others

6. **Error Scenario Testing**
   - Invalid OAuth token (401)
   - Missing tenant ID
   - Invalid report type
   - Missing required parameters
   - Xero API rate limits (429)

7. **Data Transformation Testing**
   - Verify CSV structure for different report types
   - Check nested row handling
   - Verify all metadata columns present
   - Test with reports having no data

## Known Limitations & Future Enhancements

### Current Limitations

1. **Report Structure Assumptions**
   - Current flattening logic assumes standard Xero report structure
   - May need adjustments for reports with different structures
   - Some nested data might be lost in flattening

2. **Tenant ID Location**
   - Checks multiple locations but may need updates based on actual OAuth setup
   - Users must ensure tenant ID is properly stored

3. **Parameter Discovery**
   - No sync action to discover valid parameters per report type
   - Users must know which parameters work with which reports
   - Documentation needed for parameter-to-report mapping

### Potential Enhancements

1. **Sync Action for Parameter Discovery**
   - Research if Xero API provides parameter metadata
   - Implement sync action to populate parameter options dynamically

2. **Advanced Flattening Options**
   - Allow users to choose flattening strategy
   - Preserve nested structure as JSON column option
   - Report-specific transformation logic

3. **Incremental Loading**
   - Implement state management for date-based incremental loading
   - Store last extraction date per report
   - Automatically set fromDate based on previous run

4. **Output Format Options**
   - Support JSON output format
   - Support multiple CSVs for complex reports
   - Preserve report formatting/structure

5. **Validation & Documentation**
   - Add inline validation for parameter compatibility
   - Generate documentation mapping reports to parameters
   - Provide parameter examples per report type

## Usage Instructions

### Setup

1. **Configure OAuth**
   - Set up Xero OAuth component in Keboola
   - Authorize access to Xero organization
   - OAuth component will inject token automatically

2. **Create Configuration Rows**
   - Each row = one report
   - Select report type from dropdown
   - Configure parameters as needed
   - Add custom parameters if required

3. **Run Component**
   - Component executes once per row
   - Each execution produces one CSV file
   - Files named: `{ReportType}_{timestamp}.csv`

### Example: Extract Balance Sheet

```json
{
  "report_type": "BalanceSheet",
  "predefined_parameters": {
    "date": "last day of last month"
  }
}
```

### Example: Extract P&L with Custom Parameters

```json
{
  "report_type": "ProfitAndLoss",
  "predefined_parameters": {
    "fromDate": "first day of this year",
    "toDate": "today",
    "periods": 12,
    "timeframe": "MONTH"
  },
  "custom_parameters": [
    {"key": "trackingCategoryID", "value": "abc-123"},
    {"key": "standardLayout", "value": "true"}
  ]
}
```

### Example: Extract Custom Report

```json
{
  "report_type": "Custom",
  "custom_report_id": "my-custom-report-uuid",
  "predefined_parameters": {
    "fromDate": "3 days ago",
    "toDate": "today"
  }
}
```

## Support & Troubleshooting

### Common Issues

1. **"Xero tenant ID not found"**
   - Ensure OAuth is properly configured
   - Check that authorization.oauth_api.credentials contains tenant ID
   - May need to update `_get_xero_tenant_id()` to check different location

2. **"Authentication failed"**
   - Reconnect Xero account in OAuth settings
   - Check if OAuth token has expired
   - Verify OAuth scopes include accounting reports

3. **"Report not found"**
   - Verify report_type matches exactly (case-sensitive)
   - For Custom reports, verify custom_report_id is correct
   - Check if report exists in your Xero organization

4. **Date parsing issues**
   - Check date format in error message
   - Verify `keboola.utils` supports the expression
   - Fall back to ISO format (YYYY-MM-DD) if needed

5. **Empty CSV output**
   - Some reports may have no data for given parameters
   - Check Xero UI to verify data exists
   - Review parameter values (dates, filters, etc.)

## Architecture Highlights

### Clean Workflow Pattern
The `run()` method is a clean orchestrator that reads like a story:
1. Validate and get configuration
2. Parse date parameters
3. Fetch report from Xero
4. Save output table

Each step delegates to well-named private methods, making the code self-documenting.

### Separation of Concerns
- **configuration.py**: Validation and type safety
- **xero_client.py**: Xero API communication
- **component.py**: Business logic and orchestration

### Type Safety
- Full type hints on all functions
- Pydantic models for configuration validation
- Catch validation errors early with clear messages

### Error Handling
- User errors (UserException, exit 1): Configuration issues, API errors
- System errors (Exception, exit 2): Unexpected failures
- All errors logged with context

## Conclusion

This implementation provides a robust, production-ready Xero Accounting Reports extractor for Keboola. It follows Keboola best practices, uses clean architecture patterns, and provides a user-friendly configuration interface.

The row-based approach keeps the code simple while supporting complex multi-report extractions. The flexible parameter system supports both standard Xero parameters and custom report-specific parameters.

All code has been formatted, linted, and documented. The component is ready for testing and deployment to the Keboola Developer Portal.
