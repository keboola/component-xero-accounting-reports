# Xero Accounting Reports Extractor

Keboola component for extracting reports from Xero's Accounting API.

## Features

- **Multiple Reports**: Configure multiple reports with individual destination settings
- **11+ Standard Reports**: Supports all Xero standard reports (Profit & Loss, Balance Sheet, etc.)
- **Dynamic Date Parsing**: Use relative dates like "yesterday", "30 days ago", "start of month"
- **OAuth 2.0 Authentication**: Secure authentication via Keboola's OAuth integration

## Supported Reports

- 1099 Report (US organizations)
- Aged Payables By Contact
- Aged Receivables By Contact
- Balance Sheet
- Bank Summary
- BAS Report (Australia organizations)
- Budget Summary
- Executive Summary
- GST Report (New Zealand organizations)
- Profit and Loss
- Trial Balance
- Custom Reports

## Configuration

### Report Type
Select the type of report you want to extract from the dropdown.

### Parameters
Common parameters supported:
- `fromDate` / `toDate` - Date range for the report (supports dynamic dates)
- `date` - As-at date for snapshot reports
- `periods` - Number of comparison periods (1-12)
- `timeframe` - Period size (MONTH, QUARTER, YEAR)
- `contactID` - Required for Aged Payables/Receivables reports
- Additional report-specific parameters

### Dynamic Dates
Use natural language for dates:
- `yesterday`, `today`
- `3 days ago`, `1 week ago`, `30 days ago`
- `start of month`, `end of month`
- Or absolute dates: `2024-01-31`

### Custom Parameters
Add any additional parameters not listed in the standard parameters table.

## Development

Build and run locally:
```bash
docker-compose build
docker-compose run --rm dev
```

Run tests:
```bash
docker-compose run --rm test
```

## Output

Each report generates a CSV file with the report data. The Xero report structure (nested Rows/Cells) is flattened into columns for easy analysis in Keboola Storage.

## Integration

For details about deployment and integration with Keboola, refer to the [deployment section of the developer documentation](https://developers.keboola.com/extend/component/deployment/).
