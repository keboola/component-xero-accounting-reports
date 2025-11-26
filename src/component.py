import csv
import json
import logging
from collections import OrderedDict
from typing import Any

from keboola.component.base import ComponentBase, sync_action
from keboola.component.dao import BaseType, ColumnDefinition, SupportedDataTypes
from keboola.component.exceptions import UserException
from keboola.component.sync_actions import SelectElement
from keboola.utils.date import get_past_date

from configuration import Configuration
from xero_client import XeroClient

# Constants
KEY_STATE_OAUTH_TOKEN_DICT = "#oauth_token_dict"
DATE_FIELDS = ["fromDate", "toDate", "date"]
TIMEFRAME_MAP = {"MONTH": 1, "QUARTER": 3, "YEAR": 12}
PRIMARY_KEY_COLUMNS = ["xero_tenant_id", "row_id", "column_index"]
NOT_NULLABLE_COLUMNS = ["xero_tenant_id", "row_id", "row_type", "column_index"]
CSV_FIELDNAMES = [
    "xero_tenant_id",
    "row_id",
    "row_type",
    "column_index",
    "column_name",
    "value",
    "others",
]


class Component(ComponentBase):

    def __init__(self):
        super().__init__()
        self.config = Configuration(**self.configuration.parameters)
        self.new_state = {}
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Xero client from state or OAuth credentials."""
        logging.info("Initializing Xero client")
        state = self.get_state_file()
        state_authorization_params = state.get(KEY_STATE_OAUTH_TOKEN_DICT)

        if self._state_contains_authorization_parameters(state_authorization_params):
            logging.info("Initializing client from state")
            self._init_client_from_state(state_authorization_params)
        else:
            logging.info("Initializing client from OAuth credentials")
            self._init_client_from_config()

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

    def _init_client_from_state(self, state_authorization_params: Any) -> None:
        """Initialize client using OAuth credentials from state."""
        oauth_data = self._load_state_oauth(state_authorization_params)

        # Get client credentials from config for token refresh
        # In Keboola, appKey is client_id and appSecret is client_secret
        try:
            oauth_creds = self.configuration.oauth_credentials
            client_id = oauth_creds.appKey
            client_secret = oauth_creds.appSecret
        except Exception:
            client_id = None
            client_secret = None
            logging.warning("Could not retrieve client_id/client_secret for token refresh")

        self.client = XeroClient(
            access_token=oauth_data["access_token"],
            refresh_token=oauth_data.get("refresh_token"),
            client_id=client_id,
            client_secret=client_secret,
            oauth_token_dict=oauth_data,
        )

    def _init_client_from_config(self) -> None:
        """Initialize client using OAuth credentials from configuration."""
        try:
            oauth_creds = self.configuration.oauth_credentials
            access_token = oauth_creds.data.get("access_token")
            refresh_token = oauth_creds.data.get("refresh_token")
            # In Keboola, appKey is client_id and appSecret is client_secret
            client_id = oauth_creds.appKey
            client_secret = oauth_creds.appSecret

            if not access_token:
                raise UserException("OAuth access token not found in credentials")

            # Build full oauth token dict
            oauth_token_dict = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": oauth_creds.data.get("token_type", "Bearer"),
            }

            self.client = XeroClient(
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

    def run(self) -> None:
        """Main execution method - fetch and process Xero reports."""
        # Refresh token and save to state at the start
        self.refresh_token_and_save_state()
        # Convert parameters to dict for API calls
        params = {}
        for param in self.config.parameters:
            if isinstance(param.value, bool):
                params[param.key] = "true" if param.value else "false"
            elif isinstance(param.value, int):
                params[param.key] = str(param.value)
            else:
                params[param.key] = param.value

        parsed_params = self._parse_date_parameters(params)

        tenant_ids = (
            [self.config.xero_tenant_id]
            if self.config.xero_tenant_id
            else [tenant["tenantId"] for tenant in self.client.get_tenants()]
        )
        logging.info(f"Processing {len(tenant_ids)} tenant(s)")

        # Get report name
        report_name = self.config.custom_report_id if self.config.report_type == "Custom" else self.config.report_type

        all_data = []
        for tenant_id in tenant_ids:
            logging.debug(f"Fetching report for tenant: {tenant_id}")
            report_data = self.client.get_report(report_name, tenant_id, parsed_params)
            tenant_data = self._process_report_data(report_data, self.config.report_type, tenant_id)
            all_data.extend(tenant_data)

        if all_data:
            self._write_data_to_csv(all_data, self.config.report_type)
        else:
            logging.warning("No data extracted from any tenant")

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

    def _build_schema(self, fieldnames: list[str]) -> OrderedDict:
        """Build dynamic schema for output table with appropriate data types.

        Args:
            fieldnames: List of column names from the CSV

        Returns:
            OrderedDict mapping column names to ColumnDefinition objects
        """
        schema = OrderedDict()

        # Define data type mappings based on column characteristics
        column_type_map = {
            "row_id": SupportedDataTypes.INTEGER,
            "column_index": SupportedDataTypes.INTEGER,
        }

        # Column descriptions
        column_descriptions = {
            "xero_tenant_id": "Xero tenant identifier",
            "row_id": "Unique row identifier within the report",
            "row_type": "Type of row (Row, SummaryRow, etc.)",
            "column_index": "Zero-based column index",
            "column_name": "Name of the column from report header",
            "value": "Cell value from the report",
            "others": "JSON string containing additional row and cell attributes",
        }

        # Build schema dynamically from fieldnames
        for column in fieldnames:
            dtype = column_type_map.get(column, SupportedDataTypes.STRING)
            description = column_descriptions.get(column)
            is_primary_key = column in PRIMARY_KEY_COLUMNS
            nullable = column not in NOT_NULLABLE_COLUMNS

            schema[column] = ColumnDefinition(
                data_types=BaseType(dtype=dtype),
                nullable=nullable,
                primary_key=is_primary_key,
                description=description,
            )

        return schema

    def _write_data_to_csv(self, data: list[dict[str, Any]], report_type: str) -> None:
        """Write collected data to CSV output file.

        Args:
            data: list of flattened data rows
            report_type: Report type used for filename
        """
        output_file = f"{report_type}.csv"
        schema = self._build_schema(CSV_FIELDNAMES)
        table = self.create_out_table_definition(
            output_file, incremental=self.config.incremental, schema=schema, has_header=True
        )

        # Serialize 'others' dict to JSON string for consistent CSV schema
        output_data = []
        for row in data:
            output_row = {k: v for k, v in row.items() if k != "others"}
            output_row["others"] = json.dumps(row.get("others", {})) if row.get("others") else ""
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
                        section_rows, report_type, tenant_id, header_values, row_id_counter
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
                        "column_name": header_values[idx] if idx < len(header_values) else "",
                        "value": value,
                        "others": {**others, **cell_attributes},
                    }

                    long_format.append(long_row)

        return long_format

    def _parse_date_parameters(self, params: dict[str, str]) -> dict[str, str]:
        """Parse and normalize date parameters from configuration.

        Handles natural language dates (e.g., '7 days ago') and converts them
        to ISO format. Also converts BudgetSummary timeframe values to integers.

        Args:
            params: Raw parameter dictionary from configuration

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
            elif key == "timeframe" and self.config.report_type == "BudgetSummary":
                if value in TIMEFRAME_MAP:
                    parsed[key] = TIMEFRAME_MAP[value]
                    logging.debug(f"Converted timeframe: '{value}' -> {parsed[key]}")
                else:
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    @sync_action("get_tenants")
    def get_tenants(self) -> list[SelectElement]:
        """Sync action to fetch available Xero tenants for UI dropdown.

        Returns:
            list of SelectElement objects for tenant selection in UI
        """
        tenants = self.client.get_tenants()
        logging.debug(f"Found {len(tenants)} Xero tenants")
        return [SelectElement(t["tenantId"], f"{t['tenantName']} ({t['tenantType']})") for t in tenants]


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
