import csv
import json
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from keboola.component.base import ComponentBase, sync_action
from keboola.component.dao import BaseType, ColumnDefinition, SupportedDataTypes
from keboola.component.exceptions import UserException
from keboola.component.sync_actions import SelectElement
from keboola.utils.date import get_past_date
from datetime import datetime, timezone

from configuration import Configuration, ReportConfig
from xero_client import XeroClient

# Constants
KEY_STATE_OAUTH_TOKEN_DICT = "#oauth_token_dict"
DATE_FIELDS = ["fromDate", "toDate", "date"]
TIMEFRAME_MAP = {"MONTH": 1, "QUARTER": 3, "YEAR": 12}

# Mapping from Python snake_case field names to Xero API camelCase parameter names
FIELD_NAME_TO_API_PARAM = {
    "report_year": "reportYear",
    "from_date": "fromDate",
    "to_date": "toDate",
    "contact_id": "contactID",
    "tracking_option_id": "trackingOptionID",
    "tracking_category_id": "trackingCategoryID",
    "tracking_option_id_2": "trackingOptionID2",
    "tracking_category_id_2": "trackingCategoryID2",
    "standard_layout": "standardLayout",
    "payments_only": "paymentsOnly",
    "report_id": "reportID",
    # Fields that are already in the correct format
    "date": "date",
    "periods": "periods",
    "timeframe": "timeframe",
}


@dataclass
class ColumnMetadata:
    """Metadata for output table columns."""

    name: str
    dtype: str
    nullable: bool
    description: str


# Output table column definitions - single source of truth
COLUMNS = [
    ColumnMetadata(name="xero_tenant_id", dtype="STRING", nullable=False, description="Xero tenant identifier"),
    ColumnMetadata(
        name="row_id", dtype="INTEGER", nullable=False, description="Unique row identifier within the report"
    ),
    ColumnMetadata(name="row_type", dtype="STRING", nullable=False, description="Type of row (Row, SummaryRow, etc.)"),
    ColumnMetadata(name="column_index", dtype="INTEGER", nullable=True, description="Zero-based column index"),
    ColumnMetadata(
        name="column_name", dtype="STRING", nullable=False, description="Name of the column from report header"
    ),
    ColumnMetadata(name="value", dtype="STRING", nullable=True, description="Cell value from the report"),
    ColumnMetadata(
        name="others",
        dtype="STRING",
        nullable=True,
        description="JSON string containing additional row and cell attributes",
    ),
    ColumnMetadata(
        name="extracted_at", dtype="TIMESTAMP", nullable=True, description="Timestamp when the data was extracted (UTC)"
    ),
]

# CSV fieldnames derived from COLUMNS
CSV_FIELDNAMES = [col.name for col in COLUMNS]


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        self.config = Configuration(**self.configuration.parameters)
        self.new_state = {}
        self.client = self._init_client()

    def run(self) -> None:
        """Main execution method - fetch and process Xero reports."""
        # Refresh token and save to state at the start
        self.refresh_token_and_save_state()

        # Get tenant IDs from config or fetch all
        tenant_ids = self.config.get_tenant_ids()
        if not tenant_ids:
            logging.info("No tenant IDs specified, fetching all connected tenants")
            tenant_ids = [tenant["tenantId"] for tenant in self.client.get_tenants()]
        logging.info(f"Processing {len(tenant_ids)} tenant(s)")

        # Track errors for logging
        errors = []

        # Process each report configuration
        for report_config in self.config.reports:
            logging.info(f"Processing report: {report_config.report_type}")

            # Extract and parse report parameters
            params = self._extract_report_params(report_config)
            parsed_params = self._parse_date_parameters(params, report_config.report_type)

            # Collect data for this report across all tenants
            # Note: Data is accumulated in memory before writing. This is acceptable because
            # Xero report data is typically small (< 10MB even for large organizations), and
            # this approach simplifies the code. If OOM becomes an issue in practice, this
            # could be refactored to write incrementally to the CSV file.
            all_data = []
            for tenant_id in tenant_ids:
                try:
                    logging.debug(f"Fetching {report_config.report_type} for tenant: {tenant_id}")
                    report_data = self.client.get_report(report_config.report_type, tenant_id, parsed_params)
                    tenant_data = self._process_report_data(report_data, report_config.report_type, tenant_id)
                    all_data.extend(tenant_data)
                except Exception as e:
                    error_msg = f"Failed to fetch {report_config.report_type} for tenant {tenant_id}: {str(e)}"
                    logging.warning(error_msg)
                    errors.append(error_msg)
                    continue

            # Write data for this report type
            if all_data:
                self._write_data_to_csv(all_data, report_config)
            else:
                logging.warning(f"No data extracted for report {report_config.report_type}")

        # Log summary of errors if any occurred
        if errors:
            logging.warning(
                f"Completed with {len(errors)} error(s). Failed report/tenant combinations:\n"
                + "\n".join(f"  - {err}" for err in errors)
            )

    def _init_client(self) -> XeroClient:
        """Initialize Xero client from state or OAuth credentials.

        Returns:
            Initialized XeroClient instance
        """
        logging.debug("Initializing Xero client")
        state = self.get_state_file()
        state_authorization_params = state.get(KEY_STATE_OAUTH_TOKEN_DICT)

        if self._state_contains_authorization_parameters(state_authorization_params):
            logging.debug("Initializing client from state")
            return self._init_client_from_state(state_authorization_params)
        else:
            logging.debug("Initializing client from OAuth credentials")
            return self._init_client_from_config()

    def _state_contains_authorization_parameters(self, state_authorization_params: Any) -> bool:
        """Check if state contains valid OAuth authorization parameters."""
        if not state_authorization_params:
            return False

        oauth_data = self._load_state_oauth(state_authorization_params)
        required_fields = ["access_token", "refresh_token"]
        return all(oauth_data.get(field) for field in required_fields)

    @staticmethod
    def _load_state_oauth(state_authorization_params: Any) -> dict:
        """Load OAuth data from state, handling both string and dict formats."""
        if isinstance(state_authorization_params, str):
            return json.loads(state_authorization_params)
        elif isinstance(state_authorization_params, dict):
            return state_authorization_params
        else:
            raise UserException("Invalid state format, please contact support")

    def _init_client_from_state(self, state_authorization_params: Any) -> XeroClient:
        """Initialize client using OAuth credentials from state.

        Returns:
            Initialized XeroClient instance
        """
        oauth_data = self._load_state_oauth(state_authorization_params)

        # Get client credentials from config for token refresh
        # In Keboola, encrypted fields have # prefix: #appKey and #appSecret
        try:
            oauth_creds = self.configuration.oauth_credentials
            # Try with # prefix first (encrypted fields), fall back to without prefix
            client_id = getattr(oauth_creds, "#appKey", None) or getattr(oauth_creds, "appKey", None)
            client_secret = getattr(oauth_creds, "#appSecret", None) or getattr(oauth_creds, "appSecret", None)
        except Exception:
            client_id = None
            client_secret = None
            logging.warning("Could not retrieve client_id/client_secret for token refresh")

        return XeroClient(
            access_token=oauth_data["access_token"],
            refresh_token=oauth_data.get("refresh_token"),
            client_id=client_id,
            client_secret=client_secret,
            oauth_token_dict=oauth_data,
        )

    def _init_client_from_config(self) -> XeroClient:
        """Initialize client using OAuth credentials from configuration.

        Returns:
            Initialized XeroClient instance
        """
        try:
            oauth_creds = self.configuration.oauth_credentials
            access_token = oauth_creds.data.get("access_token")
            refresh_token = oauth_creds.data.get("refresh_token")
            # In Keboola, encrypted fields have # prefix: #appKey and #appSecret
            # Try with # prefix first (encrypted fields), fall back to without prefix
            client_id = getattr(oauth_creds, "#appKey", None) or getattr(oauth_creds, "appKey", None)
            client_secret = getattr(oauth_creds, "#appSecret", None) or getattr(oauth_creds, "appSecret", None)

            if not access_token:
                raise UserException("OAuth access token not found in credentials")

            # Build full oauth token dict
            oauth_token_dict = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": oauth_creds.data.get("token_type", "Bearer"),
            }

            return XeroClient(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                oauth_token_dict=oauth_token_dict,
            )
        except Exception as e:
            raise UserException(f"Failed to retrieve OAuth credentials: {str(e)}")

    def refresh_token_and_save_state(self) -> None:
        """Refresh the OAuth token and save it to state."""
        logging.info("Refreshing OAuth token and saving to state")
        self.client.refresh_access_token()
        self.new_state[KEY_STATE_OAUTH_TOKEN_DICT] = json.dumps(self.client.get_oauth_token_dict())
        self.write_state_file(self.new_state)
        logging.info("Token refreshed and saved to state")

    def _extract_report_params(self, report_config: ReportConfig) -> dict[str, str]:
        """Extract non-empty report parameters from configuration.

        Iterates through all ReportConfig fields, excluding report_type and destination,
        to automatically extract parameters without maintaining a separate constant.
        Converts snake_case field names to camelCase for Xero API compatibility.

        Args:
            report_config: Report configuration containing parameter values

        Returns:
            Dictionary of parameter names (in camelCase) to string values for API calls
        """
        params = {}
        # Fields to exclude from parameter extraction
        excluded_fields = {"report_type", "destination"}

        for field_name in report_config.__class__.model_fields:
            if field_name in excluded_fields:
                continue

            value = getattr(report_config, field_name)
            # Skip empty strings and None values
            if value == "" or value is None:
                continue
            # Skip default integer/bool values (0 or False)
            if isinstance(value, int) and value == 0:
                continue
            if isinstance(value, bool) and value is False:
                continue

            # Convert snake_case field name to camelCase API parameter name
            api_param_name = FIELD_NAME_TO_API_PARAM.get(field_name, field_name)

            # Convert to string format for API calls
            if isinstance(value, bool):
                params[api_param_name] = "true" if value else "false"
            elif isinstance(value, int):
                params[api_param_name] = str(value)
            else:
                params[api_param_name] = value

        return params

    def _process_report_data(
        self, report_data: dict[str, Any], report_type: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        """Process report data and flatten into long format rows.

        Args:
            report_data: Raw API response from Xero
            report_type: Type of report being processed
            tenant_id: Xero tenant ID for tracking

        Returns:
            list of flattened data rows in long format
        """
        reports = report_data.get("Reports", [])
        if not reports:
            logging.warning(f"No report data returned for tenant {tenant_id}")
            return []

        report = reports[0]
        rows = report.get("Rows", [])
        long_format_data = self._flatten_report_rows_long_format(rows, report_type, tenant_id)

        if not long_format_data:
            logging.warning(f"No data rows found in report for tenant {tenant_id}")
            return []

        logging.debug(f"Processed {len(long_format_data)} rows for tenant {tenant_id}")
        return long_format_data

    def _build_schema(self, fieldnames: list[str], primary_keys: list[str]) -> OrderedDict:
        """Build dynamic schema for output table with appropriate data types.

        Args:
            fieldnames: List of column names from the CSV
            primary_keys: List of primary key column names

        Returns:
            OrderedDict mapping column names to ColumnDefinition objects
        """
        schema = OrderedDict()

        # Create lookup dict from COLUMNS for efficient access
        columns_by_name = {col.name: col for col in COLUMNS}

        # Map string dtype to SupportedDataTypes enum
        dtype_map = {
            "STRING": SupportedDataTypes.STRING,
            "INTEGER": SupportedDataTypes.INTEGER,
            "TIMESTAMP": SupportedDataTypes.TIMESTAMP,
        }

        # Use user-configured primary keys
        user_primary_keys = primary_keys if primary_keys else []

        # Build schema dynamically from fieldnames
        for column_name in fieldnames:
            col_metadata = columns_by_name.get(column_name)
            if col_metadata:
                dtype = dtype_map.get(col_metadata.dtype, SupportedDataTypes.STRING)
                description = col_metadata.description
                nullable = col_metadata.nullable
            else:
                # Fallback for unknown columns
                dtype = SupportedDataTypes.STRING
                description = None
                nullable = True

            # Use user-configured PKs if provided, otherwise no PKs for full load
            is_primary_key = column_name in user_primary_keys

            schema[column_name] = ColumnDefinition(
                data_types=BaseType(dtype=dtype),
                nullable=nullable,
                primary_key=is_primary_key,
                description=description,
            )

        return schema

    def _write_data_to_csv(self, data: list[dict[str, Any]], report_config: ReportConfig) -> None:
        """Write collected data to CSV output file.

        Args:
            data: list of flattened data rows
            report_config: Report configuration including destination settings
        """
        # Table name is either custom name or report type
        table_name = report_config.destination.output_table_name or report_config.report_type
        output_file = f"{table_name}.csv"

        # Determine if incremental based on load_type
        is_incremental = report_config.destination.load_type == "incremental_load"

        schema = self._build_schema(CSV_FIELDNAMES, report_config.destination.primary_keys)
        table = self.create_out_table_definition(
            output_file,
            incremental=is_incremental,
            schema=schema,
            has_header=True,
        )

        extracted_at = datetime.now(timezone.utc).isoformat()
        output_data = []
        for row in data:
            output_row = {k: v for k, v in row.items() if k != "others"}
            output_row["others"] = json.dumps(row.get("others", {})) if row.get("others") else ""
            output_row["extracted_at"] = extracted_at
            output_data.append(output_row)

        with open(table.full_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(output_data)

        self.write_manifest(table)
        logging.info(f"Successfully extracted {len(data)} rows to {output_file}")

    def _flatten_report_rows_long_format(
        self,
        rows: list[dict[str, Any]],
        report_type: str,
        tenant_id: str,
        header_values: list[str] | None = None,
        row_id_counter: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert Xero report rows into long format (unpivoted).

        Recursively processes report structure, converting each cell into a separate
        row with metadata. This enables easier data analysis and transformation.

        Args:
            rows: list of row dictionaries from Xero report
            report_type: Type of report being processed
            tenant_id: Xero tenant ID
            header_values: Column headers (extracted automatically if None)
            row_id_counter: Mutable counter for row IDs across recursion

        Returns:
            list of flattened rows with each cell as a separate record
        """
        long_format = []

        if row_id_counter is None:
            row_id_counter = [0]

        if header_values is None:
            header_values = []
            for row in rows:
                if row.get("RowType") == "Header":
                    cells = row.get("Cells", [])
                    header_values = [cell.get("Value", "") for cell in cells]
                    break

        for row in rows:
            row_type = row.get("RowType")

            if row_type == "Header":
                continue

            if row_type == "Section":
                section_rows = row.get("Rows", [])
                long_format.extend(
                    self._flatten_report_rows_long_format(
                        section_rows,
                        report_type,
                        tenant_id,
                        header_values,
                        row_id_counter,
                    )
                )

            elif row_type in ["Row", "SummaryRow"]:
                current_row_id = row_id_counter[0]
                row_id_counter[0] += 1

                cells = row.get("Cells", [])
                others = {k: v for k, v in row.items() if k not in ["RowType", "Cells"]}

                for idx, cell in enumerate(cells):
                    value = cell.get("Value", "")
                    cell_attributes = {
                        attr.get("Id", ""): attr.get("Value", "")
                        for attr in cell.get("Attributes", [])
                        if attr.get("Id") and attr.get("Value")
                    }

                    long_row = {
                        "xero_tenant_id": tenant_id,
                        "row_id": current_row_id,
                        "row_type": row_type,
                        "column_index": idx,
                        "column_name": (header_values[idx] if idx < len(header_values) else ""),
                        "value": value,
                        "others": {**others, **cell_attributes},
                    }

                    long_format.append(long_row)

        return long_format

    def _parse_date_parameters(self, params: dict[str, str], report_type: str) -> dict[str, str]:
        """Parse and normalize date parameters from configuration.

        Handles natural language dates (e.g., '7 days ago') and converts them
        to ISO format. Also converts BudgetSummary timeframe values to integers.

        Args:
            params: Raw parameter dictionary from configuration
            report_type: Type of report being processed

        Returns:
            Parsed parameter dictionary with normalized values
        """
        parsed = {}

        for key, value in params.items():
            if key in DATE_FIELDS and value:
                try:
                    parsed_date = get_past_date(value)
                    if parsed_date:
                        parsed[key] = parsed_date.strftime("%Y-%m-%d")
                        logging.debug(f"Parsed date parameter {key}: '{value}' -> '{parsed[key]}'")
                    else:
                        parsed[key] = value
                        logging.debug(f"Using date parameter {key}='{value}' as-is")
                except Exception as e:
                    logging.debug(f"Failed to parse date parameter {key}='{value}': {e}. Using as-is.")
                    parsed[key] = value
            elif key == "timeframe" and report_type == "BudgetSummary":
                if value in TIMEFRAME_MAP:
                    parsed[key] = TIMEFRAME_MAP[value]
                    logging.debug(f"Converted timeframe: '{value}' -> {parsed[key]}")
                else:
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    @sync_action("get_output_columns")
    def get_output_columns(self) -> list[SelectElement]:
        """Load columns from output table and return as select elements for UI.

        All Xero reports produce the same output schema, so we return a static list
        of columns that will be available after the first run.

        Returns:
            list of SelectElement objects for column selection in UI
        """
        return [
            SelectElement(
                value=col.name,
                label=f"{col.name} ({col.dtype.lower()})",
            )
            for col in COLUMNS
        ]


if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
